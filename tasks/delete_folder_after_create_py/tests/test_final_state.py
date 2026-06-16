import os
import re

import pytest
import requests

PROJECT_DIR = "/home/user/myproject"
LOG_PATH = os.path.join(PROJECT_DIR, "output.log")
APIDECK_BASE_URL = "https://unify.apideck.com"


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"Required environment variable {name} is missing or empty."
    return value


def _apideck_headers() -> dict:
    return {
        "Authorization": f"Bearer {_required_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _required_env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _required_env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": "onedrive",
    }


def _read_log() -> str:
    assert os.path.isfile(LOG_PATH), (
        f"Expected log file {LOG_PATH} to exist after the task runs."
    )
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _extract(pattern: str, content: str, label: str) -> str:
    match = re.search(pattern, content, re.MULTILINE)
    assert match, (
        f"Could not find a line matching `{label}` in {LOG_PATH}.\n"
        f"--- Log contents ---\n{content}\n--- end ---"
    )
    captured = match.group(1).strip()
    assert captured, (
        f"Captured value for `{label}` in {LOG_PATH} is empty."
    )
    return captured


@pytest.fixture(scope="module")
def log_contents() -> str:
    return _read_log()


@pytest.fixture(scope="module")
def parsed_ids(log_contents: str) -> dict:
    drive_id = _extract(r"^Drive ID:\s*(\S+)\s*$", log_contents, "Drive ID: <drive_id>")
    created_id = _extract(
        r"^Created folder ID:\s*(\S+)\s*$",
        log_contents,
        "Created folder ID: <folder_id>",
    )
    deleted_id = _extract(
        r"^Deleted folder ID:\s*(\S+)\s*$",
        log_contents,
        "Deleted folder ID: <folder_id>",
    )
    return {
        "drive_id": drive_id,
        "created_id": created_id,
        "deleted_id": deleted_id,
    }


def test_log_file_exists_and_has_required_lines(parsed_ids: dict):
    assert parsed_ids["drive_id"], "Drive ID must be a non-empty string in the log."
    assert parsed_ids["created_id"], (
        "Created folder ID must be a non-empty string in the log."
    )
    assert parsed_ids["deleted_id"], (
        "Deleted folder ID must be a non-empty string in the log."
    )


def test_deleted_id_matches_created_id(parsed_ids: dict):
    assert parsed_ids["created_id"] == parsed_ids["deleted_id"], (
        f"Created folder ID ({parsed_ids['created_id']}) must equal "
        f"Deleted folder ID ({parsed_ids['deleted_id']})."
    )


def test_logged_drive_id_matches_apideck_drive_lookup(parsed_ids: dict):
    """Verify that the drive_id recorded in the log is the actual ApiDeck drive
    whose `name` equals APIDECK_FILE_STORAGE_DRIVE_NAME."""
    drive_name = _required_env("APIDECK_FILE_STORAGE_DRIVE_NAME")
    drive_id = parsed_ids["drive_id"]

    cursor = None
    found = False
    for _ in range(10):  # safety cap on pagination
        params = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        response = requests.get(
            f"{APIDECK_BASE_URL}/file-storage/drives",
            headers=_apideck_headers(),
            params=params,
            timeout=60,
        )
        assert response.status_code == 200, (
            f"GET /file-storage/drives returned {response.status_code}: "
            f"{response.text[:500]}"
        )
        payload = response.json()
        data = payload.get("data") or []
        for drive in data:
            if drive.get("name") == drive_name and drive.get("id") == drive_id:
                found = True
                break
        if found:
            break
        cursor = (payload.get("meta") or {}).get("cursors", {}).get("next")
        if not cursor:
            break

    assert found, (
        f"Drive with name='{drive_name}' and id='{drive_id}' was not found via "
        "GET /file-storage/drives. Either the drive name does not match the env "
        "variable or the wrong drive id was logged."
    )


def test_folder_no_longer_exists_via_get_folder(parsed_ids: dict):
    """Get Folder on the deleted folder must return 404."""
    folder_id = parsed_ids["deleted_id"]
    response = requests.get(
        f"{APIDECK_BASE_URL}/file-storage/folders/{folder_id}",
        headers=_apideck_headers(),
        timeout=60,
    )
    assert response.status_code == 404, (
        f"Expected GET /file-storage/folders/{folder_id} to return 404 after "
        f"deletion, but got {response.status_code}: {response.text[:500]}"
    )


def test_folder_name_not_listed_in_drive(parsed_ids: dict):
    """The expected folder name must not appear in the drive's file listing."""
    run_id = _required_env("ZEALT_RUN_ID")
    expected_name = f"harbor-delete-{run_id}"

    cursor = None
    for _ in range(10):  # safety cap on pagination
        params = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        response = requests.get(
            f"{APIDECK_BASE_URL}/file-storage/files",
            headers=_apideck_headers(),
            params=params,
            timeout=60,
        )
        assert response.status_code == 200, (
            f"GET /file-storage/files returned {response.status_code}: "
            f"{response.text[:500]}"
        )
        payload = response.json()
        data = payload.get("data") or []
        for item in data:
            if item.get("name") == expected_name and item.get("type") == "folder":
                pytest.fail(
                    f"Folder '{expected_name}' (id={item.get('id')}) is still "
                    "present in the drive listing; it should have been deleted."
                )
        cursor = (payload.get("meta") or {}).get("cursors", {}).get("next")
        if not cursor:
            break
