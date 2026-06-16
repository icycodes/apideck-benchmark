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
                    f"Matched drive {drive_name!r} has no string id: {drive}"
                )
                return drive_id
        cursor = (payload.get("meta") or {}).get("cursors", {}).get("next")
        if not cursor:
            break
    raise AssertionError(
        f"Drive named {drive_name!r} not found via List Drives. Saw: {seen_names}"
    )


def _list_files(drive_id: str, folder_id: str) -> list[dict[str, Any]]:
    """Page through List Files restricted to the given drive_id and folder_id."""
    headers = _apideck_headers()
    out: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        params: dict[str, Any] = {
            "limit": 200,
            "filter[drive_id]": drive_id,
            "filter[folder_id]": folder_id,
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
            f"List Files failed (drive={drive_id}, folder={folder_id}): "
            f"status={resp.status_code} body={resp.text}"
        )
        payload = resp.json()
        for item in payload.get("data", []) or []:
            out.append(item)
        cursor = (payload.get("meta") or {}).get("cursors", {}).get("next")
        if not cursor:
            break
    return out


def _get_file(file_id: str) -> dict[str, Any]:
    headers = _apideck_headers()
    resp = requests.get(
        f"{UNIFY_BASE_URL}/file-storage/files/{file_id}",
        headers=headers,
        timeout=60,
    )
    assert resp.status_code == 200, (
        f"Get File failed (id={file_id}): status={resp.status_code} body={resp.text}"
    )
    payload = resp.json()
    data = payload.get("data")
    assert isinstance(data, dict), (
        f"Get File for {file_id!r} returned non-object data: {payload}"
    )
    return data


def _load_log_payload() -> dict[str, Any]:
    assert os.path.isfile(LOG_FILE), f"Log file {LOG_FILE} does not exist."
    with open(LOG_FILE) as f:
        content = f.read().strip()
    assert content, f"Log file {LOG_FILE} is empty."
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"Log file {LOG_FILE} does not contain valid JSON: {exc}\n---\n{content}"
        )
    assert isinstance(payload, dict), (
        f"Log payload must be a JSON object, got {type(payload).__name__}"
    )
    return payload


def test_log_file_has_valid_shape():
    payload = _load_log_payload()
    assert set(payload.keys()) >= {"folder_id", "file_ids"}, (
        f"Log payload missing required keys 'folder_id' and 'file_ids': {payload}"
    )
    folder_id = payload["folder_id"]
    assert isinstance(folder_id, str) and folder_id, (
        f"'folder_id' must be a non-empty string: {folder_id!r}"
    )
    file_ids = payload["file_ids"]
    assert isinstance(file_ids, list), (
        f"'file_ids' must be a list, got {type(file_ids).__name__}"
    )
    assert len(file_ids) == 3, (
        f"'file_ids' must contain exactly 3 ids, got {len(file_ids)}: {file_ids}"
    )
    assert all(isinstance(i, str) and i for i in file_ids), (
        f"'file_ids' must contain non-empty strings: {file_ids}"
    )
    assert len(set(file_ids)) == 3, (
        f"'file_ids' must contain unique ids: {file_ids}"
    )


def test_folder_exists_at_drive_root():
    run_id = os.environ["ZEALT_RUN_ID"]
    drive_name = os.environ["APIDECK_FILE_STORAGE_DRIVE_NAME"]
    expected_name = f"FOLDER-{run_id}"

    payload = _load_log_payload()
    log_folder_id = payload["folder_id"]

    drive_id = _resolve_drive_id(drive_name)
    entries = _list_files(drive_id, "root")
    matches = [
        e for e in entries
        if e.get("type") == "folder" and e.get("name") == expected_name
    ]
    assert len(matches) == 1, (
        f"Expected exactly one folder named {expected_name!r} at the root of drive "
        f"{drive_name!r}, found {len(matches)}: "
        f"{[ (e.get('id'), e.get('name')) for e in matches ]}"
    )
    actual_folder_id = matches[0].get("id")
    assert isinstance(actual_folder_id, str) and actual_folder_id, (
        f"Folder {expected_name!r} has no string id: {matches[0]}"
    )
    assert actual_folder_id == log_folder_id, (
        f"Logged folder_id {log_folder_id!r} does not match the folder discovered "
        f"on the drive {actual_folder_id!r}."
    )


def test_note_files_are_not_at_drive_root():
    run_id = os.environ["ZEALT_RUN_ID"]
    drive_name = os.environ["APIDECK_FILE_STORAGE_DRIVE_NAME"]
    drive_id = _resolve_drive_id(drive_name)
    entries = _list_files(drive_id, "root")
    prefix = f"NOTE-{run_id}-"
    misplaced = [
        e.get("name") for e in entries
        if e.get("type") == "file" and isinstance(e.get("name"), str)
        and e.get("name", "").startswith(prefix)
    ]
    assert not misplaced, (
        f"Found NOTE-{run_id}-* files at the root of drive {drive_name!r}, "
        f"they must live only inside the FOLDER-{run_id} folder: {misplaced}"
    )


def test_three_note_files_live_inside_created_folder():
    run_id = os.environ["ZEALT_RUN_ID"]
    drive_name = os.environ["APIDECK_FILE_STORAGE_DRIVE_NAME"]
    expected_names = {
        f"NOTE-{run_id}-1.txt",
        f"NOTE-{run_id}-2.txt",
        f"NOTE-{run_id}-3.txt",
    }

    payload = _load_log_payload()
    log_folder_id = payload["folder_id"]
    log_file_ids = set(payload["file_ids"])

    drive_id = _resolve_drive_id(drive_name)
    entries = _list_files(drive_id, log_folder_id)

    matched: dict[str, str] = {}
    for entry in entries:
        if entry.get("type") != "file":
            continue
        name = entry.get("name")
        if not isinstance(name, str) or name not in expected_names:
            continue
        fid = entry.get("id")
        assert isinstance(fid, str) and fid, (
            f"File {name!r} inside folder {log_folder_id!r} has no string id: {entry}"
        )
        assert name not in matched, (
            f"Found duplicate file named {name!r} inside folder {log_folder_id!r}: "
            f"ids={matched[name]!r} and {fid!r}"
        )
        matched[name] = fid

    missing = expected_names - set(matched.keys())
    assert not missing, (
        f"Expected NOTE files missing inside folder {log_folder_id!r}: "
        f"missing={sorted(missing)}, present={sorted(matched.keys())}"
    )

    found_ids = set(matched.values())
    assert found_ids == log_file_ids, (
        f"File ids inside folder {log_folder_id!r} do not match log file_ids.\n"
        f"  expected (from log): {sorted(log_file_ids)}\n"
        f"  actual   (from list): {sorted(found_ids)}"
    )


def test_each_uploaded_file_reports_correct_parent_folder():
    run_id = os.environ["ZEALT_RUN_ID"]
    expected_names = {
        f"NOTE-{run_id}-1.txt",
        f"NOTE-{run_id}-2.txt",
        f"NOTE-{run_id}-3.txt",
    }

    payload = _load_log_payload()
    log_folder_id = payload["folder_id"]
    log_file_ids: list[str] = list(payload["file_ids"])

    seen_names: set[str] = set()
    for fid in log_file_ids:
        data = _get_file(fid)
        assert data.get("type") == "file", (
            f"File id {fid!r} reports type {data.get('type')!r}, expected 'file'"
        )
        name = data.get("name")
        assert isinstance(name, str) and name in expected_names, (
            f"File id {fid!r} has unexpected name {name!r}; "
            f"expected one of {sorted(expected_names)}"
        )
        assert name not in seen_names, (
            f"Duplicate name {name!r} returned across logged file ids."
        )
        seen_names.add(name)
        parents = data.get("parent_folders")
        assert isinstance(parents, list) and parents, (
            f"File {name!r} (id={fid!r}) has empty parent_folders: {data}"
        )
        first_parent = parents[0]
        assert isinstance(first_parent, dict), (
            f"File {name!r} parent_folders[0] is not an object: {first_parent!r}"
        )
        parent_id = first_parent.get("id")
        assert parent_id == log_folder_id, (
            f"File {name!r} (id={fid!r}) reports parent_folders[0].id={parent_id!r}, "
            f"expected {log_folder_id!r}"
        )

    assert seen_names == expected_names, (
        f"Logged file ids did not cover every expected NOTE file. "
        f"covered={sorted(seen_names)}, expected={sorted(expected_names)}"
    )
