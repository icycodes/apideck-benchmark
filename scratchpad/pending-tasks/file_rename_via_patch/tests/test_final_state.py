import os
import re

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
def expected_name(run_id: str) -> str:
    return f"RENAMED-{run_id}.txt"


@pytest.fixture(scope="module")
def forbidden_name(run_id: str) -> str:
    return f"ORIGINAL-{run_id}.txt"


@pytest.fixture(scope="module")
def logged_file_id() -> str:
    assert os.path.isfile(LOG_FILE), (
        f"Log file {LOG_FILE} does not exist. The executor must write the "
        f"unified file id there."
    )
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        contents = f.read()
    match = re.search(r"^File ID:\s*(\S+)\s*$", contents, re.MULTILINE)
    assert match, (
        f"Log file {LOG_FILE} does not contain a line matching "
        f"'File ID: <unified_file_id>'. Full contents:\n{contents!r}"
    )
    return match.group(1).strip()


def _is_root_parent_folders(parent_folders, drive_name: str) -> bool:
    """Return True if `parent_folders` describes the drive root.

    OneDrive via Apideck may surface the root in several shapes:
    - missing/empty array
    - a single entry whose `id` is the literal string `"root"`
    - a single entry whose `name` matches the drive name or `"root"`
    """
    if not parent_folders:
        return True
    if not isinstance(parent_folders, list):
        return False
    if len(parent_folders) != 1:
        return False
    entry = parent_folders[0] or {}
    entry_id = (entry.get("id") or "").lower()
    entry_name = (entry.get("name") or "").lower()
    candidates = {"root", drive_name.lower()}
    return entry_id == "root" or entry_name in candidates


def test_get_file_by_logged_id_returns_renamed_file_at_root(
    logged_file_id: str, expected_name: str
):
    drive_name = _get_env("APIDECK_FILE_STORAGE_DRIVE_NAME")
    url = f"{APIDECK_BASE_URL}/file-storage/files/{logged_file_id}"
    response = requests.get(url, headers=_apideck_headers(), timeout=60)
    assert response.status_code == 200, (
        f"Expected GET {url} to return 200, got {response.status_code}: "
        f"{response.text}"
    )
    body = response.json()
    data = body.get("data") or {}

    actual_name = data.get("name")
    assert actual_name == expected_name, (
        f"Expected Apideck file data.name to equal {expected_name!r}, "
        f"got {actual_name!r}. Full data: {data}"
    )

    actual_type = data.get("type")
    assert actual_type == "file", (
        f"Expected Apideck file data.type to equal 'file', got "
        f"{actual_type!r}."
    )

    parent_folders = data.get("parent_folders")
    assert _is_root_parent_folders(parent_folders, drive_name), (
        f"Expected the renamed file to live at the drive root, but "
        f"parent_folders={parent_folders!r} for drive {drive_name!r}."
    )


def _iter_all_files(headers: dict):
    """Yield file records from `GET /file-storage/files`, following cursors."""
    url = f"{APIDECK_BASE_URL}/file-storage/files"
    params = {"limit": 200}
    seen_cursors: set[str] = set()
    while True:
        response = requests.get(
            url, headers=headers, params=params, timeout=60
        )
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


def test_listing_has_no_original_and_exactly_one_renamed_with_matching_id(
    logged_file_id: str, expected_name: str, forbidden_name: str
):
    headers = _apideck_headers()

    original_count = 0
    renamed_matches: list[dict] = []
    for item in _iter_all_files(headers):
        if (item.get("type") or "file") != "file":
            continue
        name = item.get("name")
        if name == forbidden_name:
            original_count += 1
        if name == expected_name:
            renamed_matches.append(item)

    assert original_count == 0, (
        f"Expected zero files named {forbidden_name!r} in the OneDrive drive "
        f"listing, but found {original_count}. The rename must replace the "
        f"original name, not leave it behind."
    )

    assert len(renamed_matches) == 1, (
        f"Expected exactly one file named {expected_name!r} in the OneDrive "
        f"drive listing, but found {len(renamed_matches)}: "
        f"{[m.get('id') for m in renamed_matches]!r}"
    )

    renamed = renamed_matches[0]
    renamed_id = renamed.get("id")
    assert renamed_id == logged_file_id, (
        f"The file named {expected_name!r} has id {renamed_id!r}, which does "
        f"not match the id {logged_file_id!r} recorded in the log. The rename "
        f"must preserve the unified id (PATCH), not be a delete+create."
    )
