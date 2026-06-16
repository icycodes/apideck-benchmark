import json
import os
from typing import Any

import pytest
import requests

UNIFY_BASE_URL = "https://unify.apideck.com"
SERVICE_ID = "onedrive"
PROJECT_DIR = "/home/user/apideck_task"
LOG_FILE = os.path.join(PROJECT_DIR, "output.log")


def _apideck_headers() -> dict[str, str]:
    api_key = os.environ["APIDECK_API_KEY"]
    app_id = os.environ["APIDECK_APP_ID"]
    consumer_id = os.environ["APIDECK_CONSUMER_ID"]
    return {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": SERVICE_ID,
        "Accept": "application/json",
    }


def _resolve_drive_id(drive_name: str) -> str:
    headers = _apideck_headers()
    cursor: str | None = None
    seen_names: list[str] = []
    while True:
        params: dict[str, Any] = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(
            f"{UNIFY_BASE_URL}/file-storage/drives",
            headers=headers,
            params=params,
            timeout=60,
        )
        assert resp.status_code == 200, (
            f"List Drives failed: status={resp.status_code} body={resp.text}"
        )
        payload = resp.json()
        for drive in payload.get("data", []) or []:
            name = drive.get("name")
            if name:
                seen_names.append(name)
            if name == drive_name:
                drive_id = drive.get("id")
                assert isinstance(drive_id, str) and drive_id, (
                    f"Matched drive '{drive_name}' has no string id: {drive}"
                )
                return drive_id
        cursor = (payload.get("meta") or {}).get("cursors", {}).get("next")
        if not cursor:
            break
    raise AssertionError(
        f"Drive named {drive_name!r} not found via List Drives. Saw: {seen_names}"
    )


def _list_run_files(drive_id: str, run_id: str) -> dict[str, list[dict[str, Any]]]:
    """Return all files at the drive root whose name starts with KEEP-{run_id} or SKIP-{run_id}."""
    headers = _apideck_headers()
    result: dict[str, list[dict[str, Any]]] = {}
    cursor: str | None = None
    prefixes = (f"KEEP-{run_id}", f"SKIP-{run_id}")
    while True:
        params: dict[str, Any] = {
            "limit": 200,
            "filter[drive_id]": drive_id,
        }
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(
            f"{UNIFY_BASE_URL}/file-storage/files",
            headers=headers,
            params=params,
            timeout=60,
        )
        assert resp.status_code == 200, (
            f"List Files failed: status={resp.status_code} body={resp.text}"
        )
        payload = resp.json()
        for item in payload.get("data", []) or []:
            name = item.get("name")
            item_type = item.get("type")
            if not isinstance(name, str):
                continue
            if item_type != "file":
                continue
            if any(name.startswith(prefix) for prefix in prefixes):
                result.setdefault(name, []).append(item)
        cursor = (payload.get("meta") or {}).get("cursors", {}).get("next")
        if not cursor:
            break
    return result


def test_log_file_exists_and_has_valid_shape():
    assert os.path.isfile(LOG_FILE), f"Log file {LOG_FILE} does not exist."
    with open(LOG_FILE) as f:
        content = f.read().strip()
    assert content, f"Log file {LOG_FILE} is empty."
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        pytest.fail(f"Log file {LOG_FILE} does not contain valid JSON: {exc}\n---\n{content}")
    assert isinstance(payload, dict), (
        f"Log payload must be a JSON object, got {type(payload).__name__}"
    )
    assert "search_result_ids" in payload, (
        f"Log payload missing required key 'search_result_ids': {payload}"
    )
    ids = payload["search_result_ids"]
    assert isinstance(ids, list), (
        f"'search_result_ids' must be a list, got {type(ids).__name__}"
    )
    assert all(isinstance(i, str) and i for i in ids), (
        f"'search_result_ids' must contain non-empty strings: {ids}"
    )
    assert len(ids) == 2, (
        f"'search_result_ids' must contain exactly 2 ids, got {len(ids)}: {ids}"
    )
    assert len(set(ids)) == 2, (
        f"'search_result_ids' must contain unique ids: {ids}"
    )


def test_four_expected_files_exist_on_drive():
    run_id = os.environ["ZEALT_RUN_ID"]
    drive_name = os.environ["APIDECK_FILE_STORAGE_DRIVE_NAME"]
    drive_id = _resolve_drive_id(drive_name)
    files_by_name = _list_run_files(drive_id, run_id)
    expected_names = {
        f"KEEP-{run_id}-1.txt",
        f"KEEP-{run_id}-2.txt",
        f"SKIP-{run_id}-1.txt",
        f"SKIP-{run_id}-2.txt",
    }
    missing = expected_names - set(files_by_name.keys())
    assert not missing, (
        f"Expected files missing on drive {drive_name!r}: missing={missing}, "
        f"present={sorted(files_by_name.keys())}"
    )


def test_search_result_ids_match_keep_files():
    run_id = os.environ["ZEALT_RUN_ID"]
    drive_name = os.environ["APIDECK_FILE_STORAGE_DRIVE_NAME"]
    drive_id = _resolve_drive_id(drive_name)
    files_by_name = _list_run_files(drive_id, run_id)

    keep_name_1 = f"KEEP-{run_id}-1.txt"
    keep_name_2 = f"KEEP-{run_id}-2.txt"
    assert keep_name_1 in files_by_name, (
        f"Expected file {keep_name_1!r} not found on drive {drive_name!r}"
    )
    assert keep_name_2 in files_by_name, (
        f"Expected file {keep_name_2!r} not found on drive {drive_name!r}"
    )

    expected_keep_ids = set()
    for name in (keep_name_1, keep_name_2):
        entries = files_by_name[name]
        assert len(entries) == 1, (
            f"Expected exactly one file named {name!r} on the drive, found {len(entries)}: "
            f"{[e.get('id') for e in entries]}"
        )
        file_id = entries[0].get("id")
        assert isinstance(file_id, str) and file_id, (
            f"File {name!r} has no string id: {entries[0]}"
        )
        expected_keep_ids.add(file_id)

    with open(LOG_FILE) as f:
        payload = json.loads(f.read().strip())
    actual_ids = set(payload["search_result_ids"])

    assert actual_ids == expected_keep_ids, (
        f"search_result_ids do not match the two KEEP file ids.\n"
        f"  expected (from List Files): {sorted(expected_keep_ids)}\n"
        f"  actual   (from log):        {sorted(actual_ids)}"
    )
