#!/usr/bin/env python3
"""Upload Apideck File Storage files and aggregate IDs via cursor pagination."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

PROJECT_DIR = Path("/home/user/apideck_task")
OUTPUT_LOG = PROJECT_DIR / "output.log"
UNIFY_HOST = "https://unify.apideck.com"
UPLOAD_HOST = "https://upload.apideck.com"
SERVICE_ID = "onedrive"
PAGE_SIZE = 3


class ApideckError(RuntimeError):
    pass


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ApideckError(f"Missing required environment variable: {name}")
    return value


APP_ID = require_env("APIDECK_APP_ID")
API_KEY = require_env("APIDECK_API_KEY")
CONSUMER_ID = require_env("APIDECK_CONSUMER_ID")
DRIVE_NAME = require_env("APIDECK_FILE_STORAGE_DRIVE_NAME")
RUN_ID = require_env("ZEALT_RUN_ID")
PREFIX = f"AGG-{RUN_ID}-"
EXPECTED_NAMES = [f"{PREFIX}{i}.txt" for i in range(1, 8)]


session = requests.Session()
BASE_HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "x-apideck-app-id": APP_ID,
    "x-apideck-consumer-id": CONSUMER_ID,
    "x-apideck-service-id": SERVICE_ID,
}


def request_json(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    response = session.request(method, url, timeout=60, **kwargs)
    if not response.ok:
        raise ApideckError(
            f"{method} {url} failed with HTTP {response.status_code}: {response.text[:1000]}"
        )
    if not response.text:
        return {}
    return response.json()


def find_drive_id() -> str:
    cursor: str | None = None
    fallback_ids: list[str] = []

    while True:
        params: dict[str, Any] = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        payload = request_json(
            "GET",
            f"{UNIFY_HOST}/file-storage/drives",
            headers=BASE_HEADERS,
            params=params,
        )
        for drive in payload.get("data", []):
            drive_id = drive.get("id")
            if drive_id:
                fallback_ids.append(drive_id)
            if drive.get("name") == DRIVE_NAME or drive.get("id") == DRIVE_NAME:
                return drive_id
        cursor = ((payload.get("meta") or {}).get("cursors") or {}).get("next")
        if not cursor:
            break

    if fallback_ids and DRIVE_NAME == "root":
        return fallback_ids[0]
    raise ApideckError(f"Drive named {DRIVE_NAME!r} was not found")


def list_root_files_cursor_paginated(drive_id: str, *, limit: int = PAGE_SIZE) -> list[dict[str, Any]]:
    """List every file at the drive root by walking meta.cursors.next."""
    all_files: list[dict[str, Any]] = []
    cursor: str | None = None

    while True:
        params: dict[str, Any] = {
            "filter[drive_id]": drive_id,
            "filter[folder_id]": "root",
            "limit": limit,
        }
        if cursor:
            params["cursor"] = cursor

        payload = request_json(
            "GET",
            f"{UNIFY_HOST}/file-storage/files",
            headers=BASE_HEADERS,
            params=params,
        )
        all_files.extend(payload.get("data", []))
        cursor = ((payload.get("meta") or {}).get("cursors") or {}).get("next")
        if not cursor:
            return all_files


def matching_prefix_files(drive_id: str) -> list[dict[str, Any]]:
    return [
        item
        for item in list_root_files_cursor_paginated(drive_id, limit=PAGE_SIZE)
        if str(item.get("name", "")).startswith(PREFIX)
    ]


def delete_file(file_id: str) -> None:
    encoded_id = quote(file_id, safe="")
    request_json(
        "DELETE",
        f"{UNIFY_HOST}/file-storage/files/{encoded_id}",
        headers=BASE_HEADERS,
    )


def cleanup_existing_prefix_files(drive_id: str) -> None:
    # Repeat until the prefix is gone, because deleting while cursor-paginating can
    # change page boundaries in some downstream providers.
    for _ in range(5):
        matches = matching_prefix_files(drive_id)
        if not matches:
            return
        for item in matches:
            file_id = item.get("id")
            if file_id:
                delete_file(file_id)
        time.sleep(2)
    remaining = matching_prefix_files(drive_id)
    if remaining:
        names = [str(item.get("name")) for item in remaining]
        raise ApideckError(f"Could not clean existing prefixed files: {names}")


def upload_text_file(name: str, body: str) -> str:
    headers = {
        **BASE_HEADERS,
        "Content-Type": "text/plain; charset=utf-8",
        "x-apideck-metadata": json.dumps(
            {"name": name, "parent_folder_id": "root"}, separators=(",", ":")
        ),
    }
    payload = request_json(
        "POST",
        f"{UPLOAD_HOST}/file-storage/files",
        headers=headers,
        data=body.encode("utf-8"),
    )
    file_id = (payload.get("data") or {}).get("id")
    if not isinstance(file_id, str) or not file_id:
        raise ApideckError(f"Upload for {name} did not return a file id: {payload}")
    return file_id


def upload_expected_files() -> None:
    for index, name in enumerate(EXPECTED_NAMES, start=1):
        upload_text_file(
            name,
            f"Apideck cursor pagination aggregation file {index}\nrun_id={RUN_ID}\n",
        )


def aggregate_uploaded_ids(drive_id: str) -> list[str]:
    matches = matching_prefix_files(drive_id)
    ids_by_name: dict[str, str] = {}
    unexpected_names: list[str] = []

    for item in matches:
        name = str(item.get("name", ""))
        file_id = item.get("id")
        if name in EXPECTED_NAMES and isinstance(file_id, str) and file_id:
            ids_by_name[name] = file_id
        else:
            unexpected_names.append(name)

    missing = [name for name in EXPECTED_NAMES if name not in ids_by_name]
    if missing or unexpected_names or len(ids_by_name) != 7:
        raise ApideckError(
            "Unexpected prefixed file set after upload: "
            f"missing={missing}, unexpected={unexpected_names}, found={sorted(ids_by_name)}"
        )

    return [ids_by_name[name] for name in EXPECTED_NAMES]


def main() -> int:
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    drive_id = find_drive_id()
    cleanup_existing_prefix_files(drive_id)
    upload_expected_files()

    # Give OneDrive's listing index a short moment to converge before the final
    # required cursor-paginated aggregation pass.
    ids: list[str] | None = None
    last_error: Exception | None = None
    for _ in range(10):
        try:
            ids = aggregate_uploaded_ids(drive_id)
            break
        except Exception as exc:  # retry only the read-after-write validation
            last_error = exc
            time.sleep(2)
    if ids is None:
        raise ApideckError(f"Could not aggregate uploaded files: {last_error}")

    summary = {"count": len(ids), "ids": ids}
    OUTPUT_LOG.write_text(json.dumps(summary, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
