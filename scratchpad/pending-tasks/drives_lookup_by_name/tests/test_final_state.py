import json
import os

import pytest
import requests


PROJECT_DIR = "/home/user/apideck_task"
LOG_FILE = os.path.join(PROJECT_DIR, "output.log")
UNIFY_BASE = "https://unify.apideck.com"
SERVICE_ID = "onedrive"


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"Required environment variable {name} is not set in the verifier environment."
    return value


def _apideck_headers() -> dict:
    return {
        "Authorization": f"Bearer {_required_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _required_env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _required_env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": SERVICE_ID,
        "Accept": "application/json",
    }


@pytest.fixture(scope="session")
def run_id() -> str:
    return _required_env("ZEALT_RUN_ID")


@pytest.fixture(scope="session")
def drive_name() -> str:
    return _required_env("APIDECK_FILE_STORAGE_DRIVE_NAME")


@pytest.fixture(scope="session")
def log_payload() -> dict:
    assert os.path.isfile(LOG_FILE), (
        f"Expected log file at {LOG_FILE}; the task must write a JSON object with "
        "'drive_id' and 'folder_id' there."
    )
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"Log file at {LOG_FILE} is not valid JSON: {exc}. Raw contents: {raw!r}"
        )
    assert isinstance(payload, dict), (
        f"Expected the log file to contain a JSON object, got {type(payload).__name__}: {payload!r}."
    )
    return payload


@pytest.fixture(scope="session")
def ids_from_log(log_payload: dict) -> dict:
    extracted = {}
    for key in ("drive_id", "folder_id"):
        value = log_payload.get(key)
        assert isinstance(value, str) and value, (
            f"Log JSON is missing a non-empty string field {key!r}; got {value!r}."
        )
        extracted[key] = value
    return extracted


def _list_all_drives() -> list:
    drives: list = []
    cursor = None
    for _ in range(10):
        params: dict = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        response = requests.get(
            f"{UNIFY_BASE}/file-storage/drives",
            headers=_apideck_headers(),
            params=params,
            timeout=30,
        )
        assert response.status_code == 200, (
            f"Listing drives via Apideck failed: status={response.status_code}, body={response.text}"
        )
        payload = response.json() or {}
        for item in payload.get("data") or []:
            if isinstance(item, dict):
                drives.append(item)
        cursor = ((payload.get("meta") or {}).get("cursors") or {}).get("next")
        if not cursor:
            break
    return drives


def test_drive_id_matches_named_drive(ids_from_log, drive_name):
    drives = _list_all_drives()
    matches = [d for d in drives if d.get("name") == drive_name]
    assert len(matches) == 1, (
        f"Expected exactly one drive whose name equals {drive_name!r}, found {len(matches)} "
        f"among {len(drives)} drives returned by Apideck."
    )
    resolved_id = matches[0].get("id")
    assert resolved_id == ids_from_log["drive_id"], (
        f"The drive_id {ids_from_log['drive_id']!r} written to the log does not match the "
        f"id {resolved_id!r} of the Apideck drive whose name equals {drive_name!r}."
    )


def test_probe_folder_is_correct(ids_from_log, run_id):
    folder_id = ids_from_log["folder_id"]
    response = requests.get(
        f"{UNIFY_BASE}/file-storage/files/{folder_id}",
        headers=_apideck_headers(),
        timeout=30,
    )
    assert response.status_code == 200, (
        f"Getting folder {folder_id!r} via Apideck failed: status={response.status_code}, "
        f"body={response.text}"
    )
    data = (response.json() or {}).get("data") or {}
    assert data.get("type") == "folder", (
        f"Expected the resolved resource to be a folder, got type={data.get('type')!r}."
    )
    expected_name = f"DRIVE-PROBE-{run_id}"
    assert data.get("name") == expected_name, (
        f"Folder name mismatch: expected {expected_name!r}, got {data.get('name')!r}."
    )


def test_exactly_one_probe_folder_in_drive_root(ids_from_log, run_id):
    folder_id = ids_from_log["folder_id"]
    expected_name = f"DRIVE-PROBE-{run_id}"

    matching_ids: list = []
    cursor = None
    for _ in range(20):
        params: dict = {"limit": 200, "filter[folder_id]": "root"}
        if cursor:
            params["cursor"] = cursor
        response = requests.get(
            f"{UNIFY_BASE}/file-storage/files",
            headers=_apideck_headers(),
            params=params,
            timeout=30,
        )
        assert response.status_code == 200, (
            f"List Files call failed: status={response.status_code}, body={response.text}"
        )
        payload = response.json() or {}
        for item in payload.get("data") or []:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "folder" and item.get("name") == expected_name:
                matching_ids.append(item.get("id"))
        cursor = ((payload.get("meta") or {}).get("cursors") or {}).get("next")
        if not cursor:
            break

    assert len(matching_ids) == 1, (
        f"Expected exactly one folder named {expected_name!r} at the drive root, "
        f"found {len(matching_ids)}: {matching_ids!r}."
    )
    assert matching_ids[0] == folder_id, (
        f"The single folder named {expected_name!r} at the drive root has id "
        f"{matching_ids[0]!r}, which does not match the folder_id {folder_id!r} written to the log."
    )
