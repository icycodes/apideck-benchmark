import json
import os

import pytest
import requests

PROJECT_DIR = "/home/user/myproject"
LOG_FILE = os.path.join(PROJECT_DIR, "output.log")
PACKAGE_JSON = os.path.join(PROJECT_DIR, "package.json")
APIDECK_BASE = "https://unify.apideck.com"


def _env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"Required environment variable {name} is not set."
    return value


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": "onedrive",
        "Accept": "application/json",
    }


@pytest.fixture(scope="module")
def log_payload() -> dict:
    assert os.path.isfile(LOG_FILE), (
        f"Expected log file {LOG_FILE} to exist after the task runs."
    )
    with open(LOG_FILE) as f:
        raw = f.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        pytest.fail(f"Log file {LOG_FILE} is not valid JSON: {e}\nContent: {raw!r}")
    assert isinstance(payload, dict), (
        f"Expected the log JSON to be an object, got {type(payload).__name__}."
    )
    return payload


def test_log_file_contains_required_fields(log_payload: dict):
    required_fields = [
        "drive_id",
        "parent_folder_id",
        "parent_folder_name",
        "child_folder_id",
        "child_folder_name",
    ]
    for key in required_fields:
        assert key in log_payload, (
            f"Log file missing required field {key!r}. Got keys: {sorted(log_payload.keys())}"
        )
        assert isinstance(log_payload[key], str) and log_payload[key].strip(), (
            f"Log field {key!r} must be a non-empty string, got {log_payload[key]!r}."
        )


def test_log_folder_names_use_run_id(log_payload: dict):
    run_id = _env("ZEALT_RUN_ID")
    expected_parent = f"apideck-parent-{run_id}"
    expected_child = f"apideck-child-{run_id}"
    assert log_payload["parent_folder_name"] == expected_parent, (
        f"Expected parent_folder_name {expected_parent!r}, got {log_payload['parent_folder_name']!r}."
    )
    assert log_payload["child_folder_name"] == expected_child, (
        f"Expected child_folder_name {expected_child!r}, got {log_payload['child_folder_name']!r}."
    )


def test_log_folder_ids_distinct(log_payload: dict):
    assert log_payload["parent_folder_id"] != log_payload["child_folder_id"], (
        "parent_folder_id and child_folder_id must be different ids."
    )


def test_package_json_contains_apideck_unify():
    assert os.path.isfile(PACKAGE_JSON), (
        f"Expected {PACKAGE_JSON} to exist (the task must use a Node.js project)."
    )
    with open(PACKAGE_JSON) as f:
        pkg = json.load(f)
    deps = {}
    for key in ("dependencies", "devDependencies"):
        section = pkg.get(key) or {}
        if isinstance(section, dict):
            deps.update(section)
    assert "@apideck/unify" in deps, (
        f"Expected '@apideck/unify' in package.json dependencies, got: {sorted(deps.keys())}"
    )


def _iter_drives():
    """Yield all drive objects across paginated /file-storage/drives responses."""
    url = f"{APIDECK_BASE}/file-storage/drives"
    cursor = None
    for _ in range(20):  # hard cap to avoid infinite loops
        params = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(url, headers=_headers(), params=params, timeout=60)
        assert resp.status_code == 200, (
            f"List Drives failed: status={resp.status_code}, body={resp.text}"
        )
        body = resp.json()
        for drive in body.get("data") or []:
            yield drive
        cursor = ((body.get("meta") or {}).get("cursors") or {}).get("next")
        if not cursor:
            return


@pytest.fixture(scope="module")
def resolved_drive_id(log_payload: dict) -> str:
    drive_name = _env("APIDECK_FILE_STORAGE_DRIVE_NAME")
    matches = [d for d in _iter_drives() if d.get("name") == drive_name]
    assert matches, (
        f"No drive named {drive_name!r} returned by Apideck List Drives for OneDrive."
    )
    drive_ids = {d.get("id") for d in matches}
    logged_drive_id = log_payload["drive_id"]
    assert logged_drive_id in drive_ids, (
        f"drive_id {logged_drive_id!r} from log does not match any OneDrive drive id "
        f"with name {drive_name!r}; available ids: {drive_ids}"
    )
    return logged_drive_id


def _iter_files(filter_params: dict):
    """Yield file/folder objects across paginated /file-storage/files responses."""
    url = f"{APIDECK_BASE}/file-storage/files"
    cursor = None
    for _ in range(40):
        params = {"limit": 200}
        for k, v in filter_params.items():
            params[k] = v
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(url, headers=_headers(), params=params, timeout=60)
        assert resp.status_code == 200, (
            f"List Files failed: status={resp.status_code}, params={params}, body={resp.text}"
        )
        body = resp.json()
        for item in body.get("data") or []:
            yield item
        cursor = ((body.get("meta") or {}).get("cursors") or {}).get("next")
        if not cursor:
            return


def _get_file(file_id: str) -> dict:
    url = f"{APIDECK_BASE}/file-storage/files/{file_id}"
    resp = requests.get(url, headers=_headers(), timeout=60)
    assert resp.status_code == 200, (
        f"Get File {file_id} failed: status={resp.status_code}, body={resp.text}"
    )
    body = resp.json()
    data = body.get("data")
    assert isinstance(data, dict), f"Expected a data object for file {file_id}, got {body!r}"
    return data


def test_parent_folder_exists_in_drive(log_payload: dict, resolved_drive_id: str):
    parent_id = log_payload["parent_folder_id"]
    expected_name = log_payload["parent_folder_name"]
    parent = _get_file(parent_id)
    assert parent.get("type") == "folder", (
        f"Expected parent {parent_id} to be a folder, got type={parent.get('type')!r}."
    )
    assert parent.get("name") == expected_name, (
        f"Expected parent folder name {expected_name!r}, got {parent.get('name')!r}."
    )


def test_child_folder_exists_and_nested_under_parent(
    log_payload: dict, resolved_drive_id: str
):
    child_id = log_payload["child_folder_id"]
    parent_id = log_payload["parent_folder_id"]
    expected_child_name = log_payload["child_folder_name"]

    child = _get_file(child_id)
    assert child.get("type") == "folder", (
        f"Expected child {child_id} to be a folder, got type={child.get('type')!r}."
    )
    assert child.get("name") == expected_child_name, (
        f"Expected child folder name {expected_child_name!r}, got {child.get('name')!r}."
    )

    parent_chain_ids = [p.get("id") for p in (child.get("parent_folders") or [])]
    if parent_id in parent_chain_ids:
        return

    # Fallback: list folder contents under the parent folder via filter[folder_id]
    listed = list(_iter_files({"filter[folder_id]": parent_id}))
    listed_ids = {item.get("id") for item in listed if item.get("type") == "folder"}
    assert child_id in listed_ids, (
        f"Child folder {child_id!r} ({expected_child_name!r}) is not nested under "
        f"parent {parent_id!r}: parent_folders chain={parent_chain_ids}, "
        f"folder listing ids under parent={listed_ids}."
    )
