import os
import re

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
def log_contents() -> str:
    assert os.path.isfile(LOG_FILE), (
        f"Expected log file at {LOG_FILE}; the task must write Drive ID / Folder ID / File ID there."
    )
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="session")
def ids_from_log(log_contents: str) -> dict:
    patterns = {
        "drive_id": re.compile(r"^Drive ID:\s*(\S+)\s*$", re.MULTILINE),
        "folder_id": re.compile(r"^Folder ID:\s*(\S+)\s*$", re.MULTILINE),
        "file_id": re.compile(r"^File ID:\s*(\S+)\s*$", re.MULTILINE),
    }
    extracted = {}
    for key, regex in patterns.items():
        match = regex.search(log_contents)
        assert match, (
            f"Could not find a line matching {regex.pattern!r} in the log file. "
            "Make sure the agent wrote `Drive ID:`, `Folder ID:`, and `File ID:` "
            "lines to /home/user/apideck_task/output.log."
        )
        extracted[key] = match.group(1)
    return extracted


def test_log_contains_required_ids(ids_from_log):
    for key in ("drive_id", "folder_id", "file_id"):
        assert ids_from_log[key], f"{key} extracted from log is empty."


def test_drive_id_matches_configured_drive(ids_from_log, drive_name):
    response = requests.get(
        f"{UNIFY_BASE}/file-storage/drives",
        headers=_apideck_headers(),
        params={"limit": 200},
        timeout=30,
    )
    assert response.status_code == 200, (
        f"Listing drives via Apideck failed: status={response.status_code}, body={response.text}"
    )
    payload = response.json()
    drives = payload.get("data") or []
    by_id = {d.get("id"): d for d in drives if isinstance(d, dict)}
    drive = by_id.get(ids_from_log["drive_id"])
    assert drive is not None, (
        f"The drive_id {ids_from_log['drive_id']!r} from the log was not found among "
        f"the {len(drives)} drives returned by Apideck."
    )
    assert drive.get("name") == drive_name, (
        f"The resolved drive's name is {drive.get('name')!r}, but APIDECK_FILE_STORAGE_DRIVE_NAME "
        f"is {drive_name!r}."
    )


def test_folder_resource_is_correct(ids_from_log, run_id):
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
    expected_name = f"harbor-report-{run_id}"
    assert data.get("name") == expected_name, (
        f"Folder name mismatch: expected {expected_name!r}, got {data.get('name')!r}."
    )


def test_file_resource_is_correct(ids_from_log, run_id):
    file_id = ids_from_log["file_id"]
    folder_id = ids_from_log["folder_id"]
    response = requests.get(
        f"{UNIFY_BASE}/file-storage/files/{file_id}",
        headers=_apideck_headers(),
        timeout=30,
    )
    assert response.status_code == 200, (
        f"Getting file {file_id!r} via Apideck failed: status={response.status_code}, "
        f"body={response.text}"
    )
    data = (response.json() or {}).get("data") or {}
    assert data.get("type") == "file", (
        f"Expected the resolved resource to be a file, got type={data.get('type')!r}."
    )
    expected_name = f"report-{run_id}.txt"
    assert data.get("name") == expected_name, (
        f"File name mismatch: expected {expected_name!r}, got {data.get('name')!r}."
    )
    parent_folders = data.get("parent_folders") or []
    assert isinstance(parent_folders, list) and parent_folders, (
        f"Expected non-empty parent_folders list for the uploaded file, got: {parent_folders!r}."
    )
    parent_ids = {p.get("id") for p in parent_folders if isinstance(p, dict)}
    assert folder_id in parent_ids, (
        f"The uploaded file's parent_folders {parent_ids!r} do not include the created "
        f"folder id {folder_id!r}."
    )


def test_file_appears_in_listing(ids_from_log, run_id):
    file_id = ids_from_log["file_id"]
    folder_id = ids_from_log["folder_id"]
    expected_name = f"report-{run_id}.txt"

    cursor = None
    seen = False
    for _ in range(10):  # at most 10 pages of 200 entries
        params = {"limit": 200, "filter[folder_id]": folder_id}
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
            if item.get("id") == file_id and item.get("name") == expected_name:
                seen = True
                break
        if seen:
            break
        cursor = ((payload.get("meta") or {}).get("cursors") or {}).get("next")
        if not cursor:
            break

    assert seen, (
        f"Did not find file id={file_id!r} with name={expected_name!r} under folder "
        f"{folder_id!r} via the List Files endpoint."
    )
