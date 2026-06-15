import json
import os
from typing import Any, Dict, List, Optional

import pytest
import requests


PROJECT_DIR = "/home/user/apideck_task"
OUTPUT_LOG = os.path.join(PROJECT_DIR, "output.log")

UNIFY_BASE_URL = "https://unify.apideck.com"
SERVICE_ID = "onedrive"
HTTP_TIMEOUT = 60


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"Environment variable {name} must be set for verification."
    return value


def _apideck_headers() -> Dict[str, str]:
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
def folder_ids() -> Dict[str, str]:
    assert os.path.isfile(OUTPUT_LOG), (
        f"Output log {OUTPUT_LOG} must exist and contain the folder ids."
    )
    with open(OUTPUT_LOG, "r", encoding="utf-8") as fh:
        raw = fh.read().strip()
    assert raw, f"Output log {OUTPUT_LOG} is empty."
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        pytest.fail(f"Output log {OUTPUT_LOG} is not valid JSON: {exc}")
    assert isinstance(data, dict), (
        f"Output log {OUTPUT_LOG} must contain a JSON object, got {type(data).__name__}."
    )
    ids: Dict[str, str] = {}
    for key in ("level1_id", "level2_id", "level3_id", "level4_id"):
        value = data.get(key)
        assert isinstance(value, str) and value.strip(), (
            f"Output log {OUTPUT_LOG} is missing non-empty string key '{key}'."
        )
        ids[key] = value.strip()
    distinct = set(ids.values())
    assert len(distinct) == 4, (
        f"Folder ids in {OUTPUT_LOG} must be distinct, got: {ids}"
    )
    return ids


@pytest.fixture(scope="session")
def drive_id(drive_name: str) -> str:
    url = f"{UNIFY_BASE_URL}/file-storage/drives"
    response = requests.get(url, headers=_apideck_headers(), timeout=HTTP_TIMEOUT)
    assert response.status_code == 200, (
        f"GET /file-storage/drives returned {response.status_code}: {response.text}"
    )
    payload = response.json()
    drives = payload.get("data") or []
    matches = [d for d in drives if isinstance(d, dict) and d.get("name") == drive_name]
    assert matches, (
        f"No OneDrive drive named '{drive_name}' found. Drives: "
        f"{[d.get('name') for d in drives if isinstance(d, dict)]}"
    )
    resolved_id = matches[0].get("id")
    assert isinstance(resolved_id, str) and resolved_id, (
        f"Drive '{drive_name}' is missing an id in the API response."
    )
    return resolved_id


def _get_file(file_id: str) -> Dict[str, Any]:
    url = f"{UNIFY_BASE_URL}/file-storage/files/{file_id}"
    response = requests.get(url, headers=_apideck_headers(), timeout=HTTP_TIMEOUT)
    assert response.status_code == 200, (
        f"GET /file-storage/files/{file_id} returned {response.status_code}: {response.text}"
    )
    payload = response.json()
    data = payload.get("data")
    assert isinstance(data, dict), (
        f"GET /file-storage/files/{file_id} response missing 'data' object."
    )
    return data


def _immediate_parent(file_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    parents = file_data.get("parent_folders")
    if not isinstance(parents, list) or not parents:
        return None
    last = parents[-1]
    return last if isinstance(last, dict) else None


def test_level1_folder_metadata(folder_ids: Dict[str, str], run_id: str):
    data = _get_file(folder_ids["level1_id"])
    assert data.get("type") == "folder", (
        f"level1_id {folder_ids['level1_id']} is not a folder (type={data.get('type')})."
    )
    expected_name = f"LEVEL1-{run_id}"
    assert data.get("name") == expected_name, (
        f"level1 folder name must equal '{expected_name}', got '{data.get('name')}'."
    )


def test_level2_folder_metadata(folder_ids: Dict[str, str]):
    data = _get_file(folder_ids["level2_id"])
    assert data.get("type") == "folder", (
        f"level2_id {folder_ids['level2_id']} is not a folder (type={data.get('type')})."
    )
    assert data.get("name") == "LEVEL2", (
        f"level2 folder name must equal 'LEVEL2', got '{data.get('name')}'."
    )


def test_level3_folder_metadata(folder_ids: Dict[str, str]):
    data = _get_file(folder_ids["level3_id"])
    assert data.get("type") == "folder", (
        f"level3_id {folder_ids['level3_id']} is not a folder (type={data.get('type')})."
    )
    assert data.get("name") == "LEVEL3", (
        f"level3 folder name must equal 'LEVEL3', got '{data.get('name')}'."
    )


def test_level4_folder_metadata(folder_ids: Dict[str, str]):
    data = _get_file(folder_ids["level4_id"])
    assert data.get("type") == "folder", (
        f"level4_id {folder_ids['level4_id']} is not a folder (type={data.get('type')})."
    )
    assert data.get("name") == "LEVEL4", (
        f"level4 folder name must equal 'LEVEL4', got '{data.get('name')}'."
    )


def test_level1_parent_is_drive_root(folder_ids: Dict[str, str], drive_id: str):
    data = _get_file(folder_ids["level1_id"])
    parents = data.get("parent_folders")
    if not parents:
        return
    assert isinstance(parents, list), (
        f"level1 parent_folders must be a list, got {type(parents).__name__}."
    )
    last = parents[-1] if parents else None
    assert isinstance(last, dict), (
        "level1 parent_folders must contain folder objects."
    )
    parent_id = last.get("id")
    accepted = {drive_id, "root"}
    assert parent_id in accepted, (
        f"level1's immediate parent must reference the drive root "
        f"(expected one of {accepted}), got '{parent_id}'."
    )


def test_level2_parent_is_level1(folder_ids: Dict[str, str]):
    data = _get_file(folder_ids["level2_id"])
    parent = _immediate_parent(data)
    assert parent is not None, (
        "level2 parent_folders must list its immediate parent."
    )
    assert parent.get("id") == folder_ids["level1_id"], (
        f"level2's immediate parent id must equal level1_id "
        f"('{folder_ids['level1_id']}'), got '{parent.get('id')}'."
    )


def test_level3_parent_is_level2(folder_ids: Dict[str, str]):
    data = _get_file(folder_ids["level3_id"])
    parent = _immediate_parent(data)
    assert parent is not None, (
        "level3 parent_folders must list its immediate parent."
    )
    assert parent.get("id") == folder_ids["level2_id"], (
        f"level3's immediate parent id must equal level2_id "
        f"('{folder_ids['level2_id']}'), got '{parent.get('id')}'."
    )


def test_level4_parent_is_level3(folder_ids: Dict[str, str]):
    data = _get_file(folder_ids["level4_id"])
    parent = _immediate_parent(data)
    assert parent is not None, (
        "level4 parent_folders must list its immediate parent."
    )
    assert parent.get("id") == folder_ids["level3_id"], (
        f"level4's immediate parent id must equal level3_id "
        f"('{folder_ids['level3_id']}'), got '{parent.get('id')}'."
    )


def test_level1_visible_in_list_files(
    folder_ids: Dict[str, str],
    drive_id: str,
    run_id: str,
):
    expected_name = f"LEVEL1-{run_id}"
    headers = _apideck_headers()
    cursor: Optional[str] = None
    seen: List[str] = []
    for _ in range(50):
        params: Dict[str, Any] = {
            "limit": 200,
            "filter[drive_id]": drive_id,
        }
        if cursor:
            params["cursor"] = cursor
        response = requests.get(
            f"{UNIFY_BASE_URL}/file-storage/files",
            headers=headers,
            params=params,
            timeout=HTTP_TIMEOUT,
        )
        assert response.status_code == 200, (
            f"GET /file-storage/files returned {response.status_code}: {response.text}"
        )
        payload = response.json()
        entries = payload.get("data") or []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("id") == folder_ids["level1_id"]:
                assert entry.get("name") == expected_name, (
                    f"List Files reports level1 name '{entry.get('name')}', "
                    f"expected '{expected_name}'."
                )
                assert entry.get("type") == "folder", (
                    f"List Files reports level1 type '{entry.get('type')}', expected 'folder'."
                )
                return
            seen.append(str(entry.get("id")))
        cursors = (payload.get("meta") or {}).get("cursors") or {}
        next_cursor = cursors.get("next")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
    pytest.fail(
        f"level1 folder id '{folder_ids['level1_id']}' was not found in List Files "
        f"results for drive '{drive_id}'."
    )
