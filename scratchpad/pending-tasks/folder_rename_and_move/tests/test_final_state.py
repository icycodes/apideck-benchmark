import json
import os

import pytest
import requests


PROJECT_DIR = "/home/user/apideck_task"
LOG_FILE = os.path.join(PROJECT_DIR, "output.log")

APIDECK_BASE_URL = "https://unify.apideck.com"


def _get_env(name: str) -> str:
    value = os.environ.get(name, "")
    assert value, f"Required environment variable {name} is not set."
    return value


def _apideck_headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _get_env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _get_env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": "onedrive",
        "Accept": "application/json",
    }


@pytest.fixture(scope="module")
def run_id() -> str:
    return _get_env("ZEALT_RUN_ID")


@pytest.fixture(scope="module")
def outer_name(run_id: str) -> str:
    return f"OUTER-{run_id}"


@pytest.fixture(scope="module")
def inner_old_name(run_id: str) -> str:
    return f"INNER-{run_id}"


@pytest.fixture(scope="module")
def inner_new_name(run_id: str) -> str:
    return f"INNER-RENAMED-{run_id}"


@pytest.fixture(scope="module")
def parsed_log() -> dict:
    assert os.path.isfile(LOG_FILE), (
        f"Log file {LOG_FILE} does not exist. The executor must write the "
        f"resulting folder ids there as JSON."
    )
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        raw = f.read().strip()
    assert raw, f"Log file {LOG_FILE} is empty."
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"Log file {LOG_FILE} is not valid JSON: {exc}. Contents: {raw!r}"
        )
    assert isinstance(payload, dict), (
        f"Log file JSON must be an object, got {type(payload).__name__}."
    )
    assert set(payload.keys()) == {"outer_id", "inner_id"}, (
        f"Log JSON must contain exactly the keys 'outer_id' and 'inner_id'; "
        f"got keys {sorted(payload.keys())!r}."
    )
    outer_id = payload["outer_id"]
    inner_id = payload["inner_id"]
    assert isinstance(outer_id, str) and outer_id, (
        f"'outer_id' must be a non-empty string, got {outer_id!r}."
    )
    assert isinstance(inner_id, str) and inner_id, (
        f"'inner_id' must be a non-empty string, got {inner_id!r}."
    )
    return {"outer_id": outer_id, "inner_id": inner_id}


def _get_folder(folder_id: str) -> dict:
    url = f"{APIDECK_BASE_URL}/file-storage/folders/{folder_id}"
    response = requests.get(url, headers=_apideck_headers(), timeout=60)
    assert response.status_code == 200, (
        f"Expected GET {url} to return 200, got {response.status_code}: "
        f"{response.text}"
    )
    body = response.json()
    data = body.get("data") or {}
    assert isinstance(data, dict) and data, (
        f"Response for folder {folder_id} did not include a populated 'data' "
        f"object. Body: {body}"
    )
    return data


def _iter_all_files(headers: dict):
    """Yield every entry from `GET /file-storage/files`, following cursors."""
    url = f"{APIDECK_BASE_URL}/file-storage/files"
    params: dict = {"limit": 200}
    seen_cursors: set = set()
    while True:
        response = requests.get(url, headers=headers, params=params, timeout=60)
        assert response.status_code == 200, (
            f"Expected GET /file-storage/files to return 200, got "
            f"{response.status_code}: {response.text}"
        )
        body = response.json()
        for item in body.get("data") or []:
            yield item
        cursors = (body.get("meta") or {}).get("cursors") or {}
        next_cursor = cursors.get("next")
        if not next_cursor or next_cursor in seen_cursors:
            break
        seen_cursors.add(next_cursor)
        params = {"limit": 200, "cursor": next_cursor}


def test_outer_folder_exists_at_drive_root(parsed_log: dict, outer_name: str):
    data = _get_folder(parsed_log["outer_id"])
    actual_name = data.get("name")
    assert actual_name == outer_name, (
        f"Expected folder {parsed_log['outer_id']!r} to be named "
        f"{outer_name!r}, got {actual_name!r}."
    )
    parents = data.get("parent_folders") or []
    # The folder must be at the drive root: either empty parents, or its only
    # parent is the drive root itself (not another user-created folder).
    non_root_parents = [
        p for p in parents
        if (p.get("name") or "").strip().lower() not in {"", "root", "/", "drive"}
    ]
    assert not non_root_parents, (
        f"Expected {outer_name!r} to live at the drive root, but it has "
        f"non-root parents: {non_root_parents!r}."
    )


def test_inner_renamed_folder_is_inside_outer(
    parsed_log: dict, inner_new_name: str, outer_name: str
):
    data = _get_folder(parsed_log["inner_id"])
    actual_name = data.get("name")
    assert actual_name == inner_new_name, (
        f"Expected folder {parsed_log['inner_id']!r} to be named "
        f"{inner_new_name!r}, got {actual_name!r}. This proves the renamed "
        f"folder must be reachable via the inner_id reported in the log."
    )
    parents = data.get("parent_folders") or []
    assert parents, (
        f"Expected {inner_new_name!r} to have a parent folder (it should be "
        f"inside {outer_name!r}), but parent_folders was empty — the folder "
        f"appears to still be at the drive root."
    )
    parent_ids = {p.get("id") for p in parents if p.get("id")}
    parent_names = {p.get("name") for p in parents if p.get("name")}
    assert (
        parsed_log["outer_id"] in parent_ids or outer_name in parent_names
    ), (
        f"Expected {inner_new_name!r} to be inside {outer_name!r} "
        f"(id={parsed_log['outer_id']!r}), but parent_folders was {parents!r}."
    )


def test_listing_reflects_rename_and_move(
    parsed_log: dict,
    outer_name: str,
    inner_old_name: str,
    inner_new_name: str,
):
    headers = _apideck_headers()

    renamed_matches: list = []
    outer_matches: list = []
    for item in _iter_all_files(headers):
        if (item.get("type") or "").lower() != "folder":
            continue
        name = item.get("name")
        if name == inner_old_name:
            pytest.fail(
                f"Found a folder named {inner_old_name!r} in "
                f"/file-storage/files; the original inner folder must have "
                f"been renamed via PATCH, not left in place."
            )
        if name == inner_new_name:
            renamed_matches.append(item)
        if name == outer_name:
            outer_matches.append(item)

    assert len(renamed_matches) == 1, (
        f"Expected exactly one folder named {inner_new_name!r} on the drive, "
        f"found {len(renamed_matches)}: {renamed_matches!r}."
    )
    assert renamed_matches[0].get("id") == parsed_log["inner_id"], (
        f"The folder named {inner_new_name!r} in the listing has id "
        f"{renamed_matches[0].get('id')!r}, which does not match the "
        f"inner_id {parsed_log['inner_id']!r} reported in the log. The agent "
        f"must have renamed the existing folder via PATCH rather than "
        f"deleting and recreating it."
    )

    assert any(item.get("id") == parsed_log["outer_id"] for item in outer_matches), (
        f"Did not find a folder named {outer_name!r} with id "
        f"{parsed_log['outer_id']!r} in the /file-storage/files listing."
    )
