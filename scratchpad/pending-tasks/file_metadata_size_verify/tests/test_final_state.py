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
    assert value, f"Required environment variable {name} is not set."
    return value


def _apideck_headers() -> dict:
    return {
        "Authorization": f"Bearer {_required_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _required_env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _required_env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": SERVICE_ID,
        "Accept": "application/json",
    }


@pytest.fixture(scope="module")
def run_id() -> str:
    return _required_env("ZEALT_RUN_ID")


@pytest.fixture(scope="module")
def expected_name(run_id: str) -> str:
    return f"SIZED-{run_id}.txt"


@pytest.fixture(scope="module")
def expected_size(run_id: str) -> int:
    line = f"ApiDeck-{run_id}-payload-line\n"
    return len(line.encode("utf-8")) * 100


@pytest.fixture(scope="module")
def logged_file_id() -> str:
    assert os.path.isfile(LOG_FILE), f"Log file {LOG_FILE} does not exist."
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"^\s*File ID:\s*(\S+)\s*$", content, flags=re.MULTILINE)
    assert match, (
        f"Log file {LOG_FILE} must contain a line in the format 'File ID: <file_id>'."
    )
    return match.group(1)


def _list_all_files() -> list:
    headers = _apideck_headers()
    url = f"{UNIFY_BASE}/file-storage/files"
    params = {"limit": 200}
    collected: list = []
    seen_cursors: set = set()
    next_cursor = None
    while True:
        req_params = dict(params)
        if next_cursor:
            req_params["cursor"] = next_cursor
        resp = requests.get(url, headers=headers, params=req_params, timeout=60)
        assert resp.status_code == 200, (
            f"GET /file-storage/files returned {resp.status_code}: {resp.text}"
        )
        payload = resp.json()
        data = payload.get("data") or []
        assert isinstance(data, list), (
            f"Expected 'data' array in list files response, got: {type(data).__name__}"
        )
        collected.extend(data)
        cursors = ((payload.get("meta") or {}).get("cursors") or {})
        next_cursor = cursors.get("next")
        if not next_cursor or next_cursor in seen_cursors:
            break
        seen_cursors.add(next_cursor)
    return collected


def test_exactly_one_named_file_at_drive_root(expected_name: str, logged_file_id: str):
    drive_name = _required_env("APIDECK_FILE_STORAGE_DRIVE_NAME")
    all_files = _list_all_files()
    matches = []
    for item in all_files:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "file":
            continue
        if item.get("name") != expected_name:
            continue
        parents = item.get("parent_folders") or []
        if len(parents) == 0:
            matches.append(item)
            continue
        if len(parents) == 1:
            parent_name = (parents[0] or {}).get("name") or ""
            if parent_name == drive_name or parent_name.lower() in {"root", "/", ""}:
                matches.append(item)
    assert len(matches) == 1, (
        f"Expected exactly one file named {expected_name!r} at the drive root, "
        f"found {len(matches)}."
    )
    found_id = matches[0].get("id")
    assert found_id == logged_file_id, (
        f"File id from List Files ({found_id!r}) does not match the id logged in "
        f"{LOG_FILE} ({logged_file_id!r})."
    )


def test_get_file_metadata_size_matches(
    expected_name: str, expected_size: int, logged_file_id: str
):
    headers = _apideck_headers()
    url = f"{UNIFY_BASE}/file-storage/files/{logged_file_id}"
    resp = requests.get(url, headers=headers, timeout=60)
    assert resp.status_code == 200, (
        f"GET /file-storage/files/{logged_file_id} returned {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    data = body.get("data") or {}
    assert data.get("name") == expected_name, (
        f"Get File metadata name {data.get('name')!r} != expected {expected_name!r}."
    )
    assert data.get("type") == "file", (
        f"Get File metadata type {data.get('type')!r} != 'file'."
    )
    size = data.get("size")
    assert isinstance(size, int), (
        f"Get File metadata 'size' must be an integer, got {type(size).__name__}: {size!r}."
    )
    assert size == expected_size, (
        f"Get File metadata size {size} != expected payload byte length {expected_size}."
    )
