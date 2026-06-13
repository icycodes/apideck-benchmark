import os
import re

import pytest
import requests


PROJECT_DIR = "/home/user/myproject"
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
    return f"renamed-{run_id}.txt"


@pytest.fixture(scope="module")
def forbidden_name(run_id: str) -> str:
    return f"original-{run_id}.txt"


@pytest.fixture(scope="module")
def log_contents() -> str:
    assert os.path.isfile(LOG_FILE), (
        f"Log file {LOG_FILE} does not exist. The executor must write the "
        f"unified file ID and final file name there."
    )
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def parsed_log(log_contents: str) -> dict:
    id_match = re.search(r"^File ID:\s*(\S+)\s*$", log_contents, re.MULTILINE)
    name_match = re.search(
        r"^File Name:\s*(\S.*?)\s*$", log_contents, re.MULTILINE
    )
    assert id_match, (
        "Log file does not contain a line matching 'File ID: <unified_file_id>'."
    )
    assert name_match, (
        "Log file does not contain a line matching 'File Name: <final_file_name>'."
    )
    return {
        "file_id": id_match.group(1).strip(),
        "file_name": name_match.group(1).strip(),
    }


def test_log_file_records_expected_name(parsed_log: dict, expected_name: str):
    actual_name = parsed_log["file_name"]
    assert actual_name == expected_name, (
        f"Expected log 'File Name' to equal {expected_name!r}, got {actual_name!r}."
    )


def test_get_file_by_id_returns_renamed_file(
    parsed_log: dict, expected_name: str
):
    file_id = parsed_log["file_id"]
    url = f"{APIDECK_BASE_URL}/file-storage/files/{file_id}"
    response = requests.get(url, headers=_apideck_headers(), timeout=60)
    assert response.status_code == 200, (
        f"Expected GET {url} to return 200, got {response.status_code}: "
        f"{response.text}"
    )
    body = response.json()
    data = body.get("data") or {}
    actual_name = data.get("name")
    actual_type = data.get("type")
    assert actual_name == expected_name, (
        f"Expected Apideck file data.name to equal {expected_name!r}, "
        f"got {actual_name!r}. Full data: {data}"
    )
    assert actual_type == "file", (
        f"Expected Apideck file data.type to equal 'file', got {actual_type!r}."
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


def test_list_files_contains_renamed_and_not_original(
    parsed_log: dict, expected_name: str, forbidden_name: str
):
    headers = _apideck_headers()
    file_id = parsed_log["file_id"]

    renamed_found = False
    renamed_id_matches = False
    for item in _iter_all_files(headers):
        name = item.get("name")
        if name == forbidden_name:
            pytest.fail(
                f"Found file named {forbidden_name!r} in /file-storage/files; "
                f"the original upload should have been renamed, not left in place."
            )
        if name == expected_name:
            renamed_found = True
            if item.get("id") == file_id:
                renamed_id_matches = True

    assert renamed_found, (
        f"Did not find any file named {expected_name!r} in the OneDrive drive "
        f"listing returned by /file-storage/files."
    )
    # Soft tie-back to the logged ID when the listing exposes ids
    assert renamed_id_matches, (
        f"Found a file named {expected_name!r} in the listing, but its id did "
        f"not match the logged unified file id {file_id!r}."
    )
