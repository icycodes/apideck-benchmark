import os

import pytest
import requests


PROJECT_DIR = "/home/user/myproject"
APIDECK_UNIFY_URL = "https://unify.apideck.com"
APIDECK_UPLOAD_URL = "https://upload.apideck.com"


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


def _seed_file_names(run_id: str) -> list[tuple[str, str]]:
    """Return the (name, mime_type) pairs for the 6 seeded source files."""
    pairs: list[tuple[str, str]] = []
    for i in (1, 2, 3):
        pairs.append((f"RAW-{run_id}-{i}.txt", "text/plain"))
    for i in (1, 2, 3):
        pairs.append((f"RAW-{run_id}-{i}.md", "text/markdown"))
    return pairs


def _list_all_root_items(headers: dict) -> list[dict]:
    """Page through `/file-storage/files` and return every item."""
    url = f"{APIDECK_UNIFY_URL}/file-storage/files"
    params: dict = {"limit": 200}
    seen: set[str] = set()
    items: list[dict] = []
    while True:
        response = requests.get(url, headers=headers, params=params, timeout=60)
        assert response.status_code == 200, (
            f"GET /file-storage/files returned {response.status_code}: "
            f"{response.text}"
        )
        body = response.json()
        for item in body.get("data") or []:
            items.append(item)
        cursors = (body.get("meta") or {}).get("cursors") or {}
        next_cursor = cursors.get("next")
        if not next_cursor or next_cursor in seen:
            break
        seen.add(next_cursor)
        params = {"limit": 200, "cursor": next_cursor}
    return items


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_requests_importable():
    assert requests is not None, "requests library is not importable."


def test_apideck_unify_sdk_importable():
    pytest.importorskip(
        "apideck_unify",
        reason="The 'apideck-unify' Python SDK should be installed in the environment.",
    )


def test_apideck_env_vars_present():
    required = [
        "APIDECK_APP_ID",
        "APIDECK_API_KEY",
        "APIDECK_CONSUMER_ID",
        "APIDECK_FILE_STORAGE_DRIVE_NAME",
        "ZEALT_RUN_ID",
    ]
    missing = [name for name in required if not os.environ.get(name)]
    assert not missing, (
        f"Required Apideck environment variables are not set: {missing}"
    )


def test_seed_six_source_files_at_drive_root():
    """Upload the six RAW-${run-id}-N.{txt,md} source files to the drive root.

    The agent task is to MOVE pre-existing files into per-extension folders, so
    the source files must already exist before the agent runs. This test seeds
    them via the unified Upload File endpoint and then asserts they are
    visible via List Files.
    """
    run_id = _get_env("ZEALT_RUN_ID")
    headers = _apideck_headers()

    expected_names = {name for name, _mime in _seed_file_names(run_id)}

    existing = {item.get("name") for item in _list_all_root_items(headers)}
    missing = expected_names - existing

    for name in sorted(missing):
        mime = "text/markdown" if name.endswith(".md") else "text/plain"
        metadata = (
            '{"name":"' + name + '","parent_folder_id":"root"}'
        )
        upload_headers = {
            "Authorization": headers["Authorization"],
            "x-apideck-app-id": headers["x-apideck-app-id"],
            "x-apideck-consumer-id": headers["x-apideck-consumer-id"],
            "x-apideck-service-id": "onedrive",
            "x-apideck-metadata": metadata,
            "Content-Type": mime,
        }
        body = f"seed {name}".encode("utf-8")
        response = requests.post(
            f"{APIDECK_UPLOAD_URL}/file-storage/files",
            headers=upload_headers,
            data=body,
            timeout=120,
        )
        assert response.status_code in (200, 201), (
            f"Failed to seed source file {name!r}: "
            f"{response.status_code} {response.text}"
        )

    items = _list_all_root_items(headers)
    found_names = {item.get("name") for item in items}
    still_missing = expected_names - found_names
    assert not still_missing, (
        f"After seeding, the following source files are still missing from "
        f"the drive listing: {sorted(still_missing)}"
    )
