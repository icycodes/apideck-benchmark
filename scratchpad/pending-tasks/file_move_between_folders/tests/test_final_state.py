import json
import os
import time
from typing import Any

import pytest
import requests


PROJECT_DIR = "/home/user/apideck_task"
LOG_PATH = os.path.join(PROJECT_DIR, "output.log")
UNIFY_BASE = "https://unify.apideck.com"
SERVICE_ID = "onedrive"


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"Required environment variable {name} is not set."
    return value


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_required_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _required_env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _required_env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": SERVICE_ID,
        "Accept": "application/json",
    }


def _get_with_retry(url: str, params: dict[str, Any] | None = None) -> requests.Response:
    last_exc: Exception | None = None
    for attempt in range(4):
        try:
            response = requests.get(
                url, headers=_headers(), params=params, timeout=30
            )
        except requests.RequestException as exc:  # pragma: no cover - network jitter
            last_exc = exc
            time.sleep(2 ** attempt)
            continue
        if response.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** attempt)
            continue
        return response
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"Failed GET {url} after retries")


def _list_all_files() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    cursor: str | None = None
    seen_cursors: set[str] = set()
    while True:
        params: dict[str, Any] = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        response = _get_with_retry(f"{UNIFY_BASE}/file-storage/files", params=params)
        assert response.status_code == 200, (
            "List Files request failed: "
            f"status={response.status_code}, body={response.text[:500]}"
        )
        payload = response.json()
        data = payload.get("data") or []
        assert isinstance(data, list), (
            f"Expected list in 'data' from list-files response, got: {type(data).__name__}"
        )
        items.extend(data)
        next_cursor = (
            payload.get("meta", {}).get("cursors", {}).get("next")
            if isinstance(payload.get("meta"), dict)
            else None
        )
        if not next_cursor or next_cursor in seen_cursors:
            break
        seen_cursors.add(next_cursor)
        cursor = next_cursor
    return items


@pytest.fixture(scope="module")
def run_id() -> str:
    return _required_env("ZEALT_RUN_ID")


@pytest.fixture(scope="module")
def log_payload() -> dict[str, Any]:
    assert os.path.isfile(LOG_PATH), f"Log file {LOG_PATH} does not exist."
    with open(LOG_PATH, "r", encoding="utf-8") as fh:
        content = fh.read()
    non_empty = [line.strip() for line in content.splitlines() if line.strip()]
    assert non_empty, f"Log file {LOG_PATH} is empty."
    last_line = non_empty[-1]
    try:
        parsed = json.loads(last_line)
    except json.JSONDecodeError as exc:
        pytest.fail(
            "Last non-empty log line is not valid JSON: "
            f"{last_line!r} (error: {exc})"
        )
    assert isinstance(parsed, dict), (
        f"Expected JSON object on last log line, got: {type(parsed).__name__}"
    )
    for key in ("file_id", "src_folder_id", "dst_folder_id"):
        assert key in parsed, f"Log JSON is missing required key '{key}'."
        assert isinstance(parsed[key], str) and parsed[key], (
            f"Log JSON key '{key}' must be a non-empty string, got: {parsed[key]!r}"
        )
    return parsed


@pytest.fixture(scope="module")
def all_files() -> list[dict[str, Any]]:
    return _list_all_files()


def _is_root_or_empty(parent_folders: Any) -> bool:
    if parent_folders is None:
        return True
    if not isinstance(parent_folders, list):
        return False
    if not parent_folders:
        return True
    for entry in parent_folders:
        if not isinstance(entry, dict):
            return False
        name = (entry.get("name") or "").strip().lower()
        entry_id = (entry.get("id") or "").strip().lower()
        if name in {"", "root", "/"}:
            continue
        if entry_id in {"root", ""}:
            continue
        return False
    return True


def test_src_folder_exists_at_drive_root(
    run_id: str, log_payload: dict[str, Any], all_files: list[dict[str, Any]]
):
    expected_name = f"SRC-{run_id}"
    matches = [
        item
        for item in all_files
        if item.get("type") == "folder" and item.get("name") == expected_name
    ]
    assert len(matches) == 1, (
        f"Expected exactly one folder named {expected_name!r} at drive root, "
        f"found {len(matches)}."
    )
    folder = matches[0]
    assert _is_root_or_empty(folder.get("parent_folders")), (
        f"Folder {expected_name!r} is not at the drive root; "
        f"parent_folders={folder.get('parent_folders')!r}"
    )
    assert folder.get("id") == log_payload["src_folder_id"], (
        f"Folder {expected_name!r} id {folder.get('id')!r} does not match "
        f"src_folder_id {log_payload['src_folder_id']!r} from the log."
    )


def test_dst_folder_exists_at_drive_root(
    run_id: str, log_payload: dict[str, Any], all_files: list[dict[str, Any]]
):
    expected_name = f"DST-{run_id}"
    matches = [
        item
        for item in all_files
        if item.get("type") == "folder" and item.get("name") == expected_name
    ]
    assert len(matches) == 1, (
        f"Expected exactly one folder named {expected_name!r} at drive root, "
        f"found {len(matches)}."
    )
    folder = matches[0]
    assert _is_root_or_empty(folder.get("parent_folders")), (
        f"Folder {expected_name!r} is not at the drive root; "
        f"parent_folders={folder.get('parent_folders')!r}"
    )
    assert folder.get("id") == log_payload["dst_folder_id"], (
        f"Folder {expected_name!r} id {folder.get('id')!r} does not match "
        f"dst_folder_id {log_payload['dst_folder_id']!r} from the log."
    )


def test_moved_file_exists_with_preserved_name(
    run_id: str, log_payload: dict[str, Any], all_files: list[dict[str, Any]]
):
    expected_name = f"MOVE-{run_id}.txt"
    matches = [
        item
        for item in all_files
        if item.get("type") == "file" and item.get("name") == expected_name
    ]
    assert len(matches) == 1, (
        f"Expected exactly one file named {expected_name!r} after the move, "
        f"found {len(matches)}."
    )
    file_item = matches[0]
    assert file_item.get("id") == log_payload["file_id"], (
        f"File id {file_item.get('id')!r} does not match file_id "
        f"{log_payload['file_id']!r} from the log."
    )


def test_moved_file_parent_is_destination_not_source(
    log_payload: dict[str, Any], all_files: list[dict[str, Any]]
):
    file_id = log_payload["file_id"]
    src_id = log_payload["src_folder_id"]
    dst_id = log_payload["dst_folder_id"]
    matches = [item for item in all_files if item.get("id") == file_id]
    assert matches, f"File with id {file_id!r} not found in list response."
    file_item = matches[0]
    parents = file_item.get("parent_folders") or []
    assert isinstance(parents, list) and parents, (
        f"File {file_id!r} has no parent_folders entries; got: {parents!r}"
    )
    parent_ids = [
        entry.get("id") for entry in parents if isinstance(entry, dict)
    ]
    assert dst_id in parent_ids, (
        f"Destination folder id {dst_id!r} is not in file parent_folders: "
        f"{parent_ids!r}"
    )
    assert src_id not in parent_ids, (
        f"Source folder id {src_id!r} must not appear in file parent_folders "
        f"after the move; got: {parent_ids!r}"
    )


def test_get_file_endpoint_confirms_move(
    run_id: str, log_payload: dict[str, Any]
):
    file_id = log_payload["file_id"]
    expected_name = f"MOVE-{run_id}.txt"
    response = _get_with_retry(f"{UNIFY_BASE}/file-storage/files/{file_id}")
    assert response.status_code == 200, (
        "Get File request failed: "
        f"status={response.status_code}, body={response.text[:500]}"
    )
    payload = response.json()
    data = payload.get("data") or {}
    assert isinstance(data, dict), (
        f"Expected object in 'data' from get-file response, got: {type(data).__name__}"
    )
    assert data.get("name") == expected_name, (
        f"Get File returned name {data.get('name')!r}, expected {expected_name!r}."
    )
    parents = data.get("parent_folders") or []
    parent_ids = [
        entry.get("id") for entry in parents if isinstance(entry, dict)
    ]
    assert log_payload["dst_folder_id"] in parent_ids, (
        "Get File parent_folders does not include destination folder id "
        f"{log_payload['dst_folder_id']!r}; got: {parent_ids!r}"
    )
    assert log_payload["src_folder_id"] not in parent_ids, (
        "Get File parent_folders still includes source folder id "
        f"{log_payload['src_folder_id']!r}; got: {parent_ids!r}"
    )
