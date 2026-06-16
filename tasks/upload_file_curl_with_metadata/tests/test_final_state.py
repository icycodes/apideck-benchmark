import os
import re
from pathlib import Path
from typing import Optional

import pytest
import requests

PROJECT_DIR = "/home/user/myproject"
OUTPUT_LOG = os.path.join(PROJECT_DIR, "output.log")
UNIFY_BASE_URL = "https://unify.apideck.com"
SERVICE_ID = "onedrive"
REQUEST_TIMEOUT = 60


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"Required environment variable {name} is not set in the verifier environment."
    return value


@pytest.fixture(scope="module")
def env_config() -> dict:
    return {
        "app_id": _required_env("APIDECK_APP_ID"),
        "api_key": _required_env("APIDECK_API_KEY"),
        "consumer_id": _required_env("APIDECK_CONSUMER_ID"),
        "drive_name": _required_env("APIDECK_FILE_STORAGE_DRIVE_NAME"),
        "run_id": _required_env("ZEALT_RUN_ID"),
    }


@pytest.fixture(scope="module")
def apideck_headers(env_config: dict) -> dict:
    return {
        "Authorization": f"Bearer {env_config['api_key']}",
        "x-apideck-app-id": env_config["app_id"],
        "x-apideck-consumer-id": env_config["consumer_id"],
        "x-apideck-service-id": SERVICE_ID,
        "Accept": "application/json",
    }


@pytest.fixture(scope="module")
def expected_filename(env_config: dict) -> str:
    return f"apideck-curl-{env_config['run_id']}.txt"


@pytest.fixture(scope="module")
def uploaded_file_id() -> str:
    assert os.path.isfile(OUTPUT_LOG), (
        f"Expected the executor to produce {OUTPUT_LOG}, but the file is missing."
    )
    raw_lines = Path(OUTPUT_LOG).read_text(encoding="utf-8").splitlines()
    non_empty = [line.strip() for line in raw_lines if line.strip()]
    assert len(non_empty) == 1, (
        f"Expected exactly one non-empty line (the uploaded file ID) in {OUTPUT_LOG}, "
        f"got {len(non_empty)} lines: {non_empty!r}"
    )
    return non_empty[0]


@pytest.fixture(scope="module")
def expected_drive_id(apideck_headers: dict, env_config: dict) -> str:
    url = f"{UNIFY_BASE_URL}/file-storage/drives"
    params: dict[str, str] = {"limit": "200"}
    next_cursor: Optional[str] = None
    matches: list[dict] = []
    for _ in range(50):
        if next_cursor:
            params["cursor"] = next_cursor
        else:
            params.pop("cursor", None)
        response = requests.get(url, headers=apideck_headers, params=params, timeout=REQUEST_TIMEOUT)
        assert response.status_code == 200, (
            f"GET {url} returned status {response.status_code}: {response.text}"
        )
        body = response.json()
        data = body.get("data") or []
        assert isinstance(data, list), f"Expected list at data, got {type(data).__name__}: {body!r}"
        for entry in data:
            if isinstance(entry, dict) and entry.get("name") == env_config["drive_name"]:
                matches.append(entry)
        next_cursor = (((body.get("meta") or {}).get("cursors") or {}).get("next"))
        if not next_cursor:
            break
    assert matches, (
        f"No drive named {env_config['drive_name']!r} was returned by List Drives; "
        f"cannot verify the upload target."
    )
    drive_id = matches[0].get("id")
    assert drive_id, (
        f"Drive named {env_config['drive_name']!r} is missing an `id` in the List Drives response: "
        f"{matches[0]!r}"
    )
    return drive_id


def test_output_log_has_single_file_id(uploaded_file_id: str):
    assert uploaded_file_id, f"Expected a non-empty file ID in {OUTPUT_LOG}."


def test_get_file_returns_expected_metadata(
    uploaded_file_id: str,
    expected_filename: str,
    expected_drive_id: str,
    apideck_headers: dict,
):
    url = f"{UNIFY_BASE_URL}/file-storage/files/{uploaded_file_id}"
    response = requests.get(url, headers=apideck_headers, timeout=REQUEST_TIMEOUT)
    assert response.status_code == 200, (
        f"GET {url} returned status {response.status_code}: {response.text}"
    )
    body = response.json()
    data = body.get("data")
    assert isinstance(data, dict), f"Unexpected response shape for {url}: {body!r}"
    assert data.get("id") == uploaded_file_id, (
        f"File lookup mismatch: requested {uploaded_file_id!r}, got data.id={data.get('id')!r}."
    )
    assert data.get("name") == expected_filename, (
        f"Uploaded file has name {data.get('name')!r}; expected {expected_filename!r}."
    )
    assert data.get("type") == "file", (
        f"Uploaded resource has type {data.get('type')!r}; expected 'file'."
    )
    # If the connector populated drive_id on the file, ensure it matches the expected drive.
    drive_id_on_file = data.get("drive_id")
    if drive_id_on_file:
        assert drive_id_on_file == expected_drive_id, (
            f"Uploaded file reports drive_id={drive_id_on_file!r}; "
            f"expected the drive named matching APIDECK_FILE_STORAGE_DRIVE_NAME ({expected_drive_id!r})."
        )


def test_file_appears_in_list_files(
    uploaded_file_id: str,
    expected_filename: str,
    apideck_headers: dict,
):
    url = f"{UNIFY_BASE_URL}/file-storage/files"
    params: dict[str, str] = {"limit": "200"}
    next_cursor: Optional[str] = None
    matched_entry: Optional[dict] = None
    for _ in range(50):
        if next_cursor:
            params["cursor"] = next_cursor
        else:
            params.pop("cursor", None)
        response = requests.get(url, headers=apideck_headers, params=params, timeout=REQUEST_TIMEOUT)
        assert response.status_code == 200, (
            f"GET {url} returned status {response.status_code}: {response.text}"
        )
        body = response.json()
        data = body.get("data") or []
        assert isinstance(data, list), f"Expected list at data, got {type(data).__name__}: {body!r}"
        for entry in data:
            if isinstance(entry, dict) and entry.get("id") == uploaded_file_id:
                matched_entry = entry
                break
        if matched_entry is not None:
            break
        next_cursor = (((body.get("meta") or {}).get("cursors") or {}).get("next"))
        if not next_cursor:
            break
    assert matched_entry is not None, (
        f"Uploaded file ID {uploaded_file_id!r} was not found when paginating List Files."
    )
    assert matched_entry.get("name") == expected_filename, (
        f"List Files entry for {uploaded_file_id!r} has name {matched_entry.get('name')!r}; "
        f"expected {expected_filename!r}."
    )
    assert matched_entry.get("type") == "file", (
        f"List Files entry for {uploaded_file_id!r} has type {matched_entry.get('type')!r}; "
        f"expected 'file'."
    )


def test_solution_uses_curl_and_not_sdk():
    project_path = Path(PROJECT_DIR)
    assert project_path.is_dir(), f"Project directory {PROJECT_DIR} is missing."

    interesting_suffixes = {".sh", ".bash", ".py", ".js", ".mjs", ".ts", ".rb", ".pl"}
    sources: list[tuple[Path, str]] = []
    for path in project_path.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in interesting_suffixes and path.name != "Makefile":
            continue
        try:
            sources.append((path, path.read_text(encoding="utf-8", errors="ignore")))
        except OSError:
            continue

    assert sources, (
        f"Expected at least one persisted solution script under {PROJECT_DIR} "
        "(e.g., a shell or Python file invoking curl)."
    )

    curl_pattern = re.compile(r"\bcurl\b")
    upload_host_pattern = re.compile(r"upload\.apideck\.com")
    metadata_header_pattern = re.compile(r"x-apideck-metadata", re.IGNORECASE)
    sdk_python_pattern = re.compile(r"\bapideck_unify\b")
    sdk_js_pattern = re.compile(r"@apideck/unify")

    # Forbid the SDK in any persisted solution file.
    for source_file, text in sources:
        assert not sdk_python_pattern.search(text), (
            f"{source_file} appears to use the `apideck_unify` Python SDK, but the task "
            "requires the upload to be performed via raw curl."
        )
        assert not sdk_js_pattern.search(text), (
            f"{source_file} appears to use the `@apideck/unify` SDK, but the task "
            "requires the upload to be performed via raw curl."
        )

    # Require at least one file that exercises both friction points (host + metadata header) via curl.
    qualifying = [
        path
        for path, text in sources
        if curl_pattern.search(text)
        and upload_host_pattern.search(text)
        and metadata_header_pattern.search(text)
    ]
    assert qualifying, (
        "No persisted solution file under /home/user/myproject invokes `curl` against "
        "`upload.apideck.com` with an `x-apideck-metadata` header; the task requires the executor "
        "to exercise both friction points using curl."
    )
