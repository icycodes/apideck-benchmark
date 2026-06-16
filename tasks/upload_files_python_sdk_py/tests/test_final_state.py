import json
import os

import requests

PROJECT_DIR = "/home/user/myproject"
LOG_FILE = os.path.join(PROJECT_DIR, "output.log")

UNIFY_BASE = "https://unify.apideck.com"
SERVICE_ID = "onedrive"


def _required_env(name: str) -> str:
    value = os.environ.get(name, "")
    assert value, f"Required environment variable {name} is missing or empty."
    return value


def _apideck_headers() -> dict:
    return {
        "Authorization": f"Bearer {_required_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _required_env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _required_env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": SERVICE_ID,
    }


def _expected_names() -> tuple[str, str]:
    run_id = _required_env("ZEALT_RUN_ID")
    return (
        f"report-{run_id}-alpha.txt",
        f"report-{run_id}-beta.txt",
    )


def _load_log_payload() -> dict:
    assert os.path.isfile(LOG_FILE), f"Log file {LOG_FILE} does not exist."
    with open(LOG_FILE, "r", encoding="utf-8") as fh:
        raw = fh.read().strip()
    assert raw, f"Log file {LOG_FILE} is empty."

    # Accept either a single JSON object or a single line containing one.
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        lines = [line for line in raw.splitlines() if line.strip()]
        assert len(lines) == 1, (
            f"Log file {LOG_FILE} must contain exactly one JSON object, "
            f"found {len(lines)} non-empty lines."
        )
        payload = json.loads(lines[0])

    assert isinstance(payload, dict), (
        f"Log payload must be a JSON object, got {type(payload).__name__}."
    )
    return payload


def _resolve_drive_id() -> str:
    drive_name = _required_env("APIDECK_FILE_STORAGE_DRIVE_NAME")
    headers = _apideck_headers()
    url = f"{UNIFY_BASE}/file-storage/drives"
    cursor = None
    while True:
        params = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(url, headers=headers, params=params, timeout=60)
        assert resp.status_code == 200, (
            f"List Drives failed with {resp.status_code}: {resp.text}"
        )
        body = resp.json()
        for drive in body.get("data") or []:
            if drive.get("name") == drive_name:
                drive_id = drive.get("id")
                assert drive_id, (
                    f"Drive entry for name {drive_name!r} has no id: {drive}"
                )
                return drive_id
        cursor = (body.get("meta") or {}).get("cursors", {}).get("next")
        if not cursor:
            break
    raise AssertionError(
        f"Could not find a OneDrive drive named {drive_name!r} via List Drives."
    )


def test_log_file_contains_expected_payload():
    alpha_name, beta_name = _expected_names()
    payload = _load_log_payload()

    assert set(payload.keys()) == {"alpha", "beta"}, (
        f"Log payload must have exactly keys 'alpha' and 'beta', got {list(payload.keys())}."
    )

    for key, expected_name in (("alpha", alpha_name), ("beta", beta_name)):
        entry = payload[key]
        assert isinstance(entry, dict), (
            f"Payload entry {key!r} must be an object, got {type(entry).__name__}."
        )
        assert set(entry.keys()) == {"name", "id"}, (
            f"Payload entry {key!r} must have keys 'name' and 'id', got {list(entry.keys())}."
        )
        assert entry["name"] == expected_name, (
            f"Payload entry {key!r} name {entry['name']!r} does not match expected {expected_name!r}."
        )
        assert isinstance(entry["id"], str) and entry["id"], (
            f"Payload entry {key!r} id must be a non-empty string, got {entry['id']!r}."
        )


def test_files_exist_via_get_file_api():
    alpha_name, beta_name = _expected_names()
    payload = _load_log_payload()
    headers = _apideck_headers()

    for key, expected_name in (("alpha", alpha_name), ("beta", beta_name)):
        file_id = payload[key]["id"]
        url = f"{UNIFY_BASE}/file-storage/files/{file_id}"
        resp = requests.get(url, headers=headers, timeout=60)
        assert resp.status_code == 200, (
            f"GET /file-storage/files/{file_id} for {key!r} returned "
            f"{resp.status_code}: {resp.text}"
        )
        body = resp.json()
        data = body.get("data") or {}
        assert data.get("name") == expected_name, (
            f"Apideck file {file_id} reports name {data.get('name')!r}, "
            f"expected {expected_name!r}."
        )
        assert data.get("type") == "file", (
            f"Apideck file {file_id} reports type {data.get('type')!r}, expected 'file'."
        )


def test_files_are_in_configured_drive_via_list_files():
    alpha_name, beta_name = _expected_names()
    payload = _load_log_payload()
    headers = _apideck_headers()
    drive_id = _resolve_drive_id()

    expected_ids = {payload["alpha"]["id"], payload["beta"]["id"]}
    expected_pairs = {
        payload["alpha"]["id"]: alpha_name,
        payload["beta"]["id"]: beta_name,
    }
    found: dict[str, str] = {}

    url = f"{UNIFY_BASE}/file-storage/files"
    cursor = None
    pages = 0
    max_pages = 50  # Safety bound

    while pages < max_pages:
        params: dict = {
            "limit": 200,
            "filter[drive_id]": drive_id,
        }
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(url, headers=headers, params=params, timeout=60)
        assert resp.status_code == 200, (
            f"List Files failed with {resp.status_code}: {resp.text}"
        )
        body = resp.json()
        for entry in body.get("data") or []:
            entry_id = entry.get("id")
            if entry_id in expected_ids and entry_id not in found:
                found[entry_id] = entry.get("name", "")
        if expected_ids.issubset(found.keys()):
            break
        cursor = (body.get("meta") or {}).get("cursors", {}).get("next")
        pages += 1
        if not cursor:
            break

    missing = expected_ids - set(found.keys())
    assert not missing, (
        f"Uploaded file ids {sorted(missing)} were not found in drive {drive_id!r} "
        f"via List Files."
    )
    for file_id, expected_name in expected_pairs.items():
        assert found[file_id] == expected_name, (
            f"List Files returned name {found[file_id]!r} for id {file_id!r}, "
            f"expected {expected_name!r}."
        )
