#!/usr/bin/env python3
"""Create and delete a OneDrive folder via ApiDeck File Storage Unified API.

Required environment variables:
  APIDECK_APP_ID
  APIDECK_API_KEY
  APIDECK_CONSUMER_ID
  APIDECK_FILE_STORAGE_DRIVE_NAME
  ZEALT_RUN_ID
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable, Optional

from apideck_unify import Apideck

SERVICE_ID = "onedrive"
PARENT_FOLDER_ID = "root"
LOG_PATH = Path("/home/user/myproject/output.log")
REQUIRED_ENV_VARS = (
    "APIDECK_APP_ID",
    "APIDECK_API_KEY",
    "APIDECK_CONSUMER_ID",
    "APIDECK_FILE_STORAGE_DRIVE_NAME",
    "ZEALT_RUN_ID",
)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def resolve_drive_id(client: Apideck, target_drive_name: str) -> str:
    """Return the unified drive id for the OneDrive drive with the exact target name."""
    response = client.file_storage.drives.list(service_id=SERVICE_ID, limit=200)

    while response is not None:
        drives_response = response.get_drives_response
        if drives_response is None:
            break

        for drive in drives_response.data:
            if drive.name == target_drive_name:
                return drive.id

        response = response.next() if response.next is not None else None

    raise RuntimeError(f"No OneDrive drive found with name: {target_drive_name}")


def create_folder(client: Apideck, drive_id: str, folder_name: str) -> str:
    response = client.file_storage.folders.create(
        service_id=SERVICE_ID,
        name=folder_name,
        parent_folder_id=PARENT_FOLDER_ID,
        drive_id=drive_id,
    )
    create_response = response.create_folder_response
    if create_response is None or create_response.data is None:
        raise RuntimeError("Create Folder response did not include a folder id")
    return create_response.data.id


def delete_folder(client: Apideck, folder_id: str) -> None:
    client.file_storage.folders.delete(service_id=SERVICE_ID, id=folder_id)


def append_log(lines: Iterable[str]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        for line in lines:
            log_file.write(f"{line}\n")


def main() -> int:
    env = {name: require_env(name) for name in REQUIRED_ENV_VARS}
    folder_name = f"harbor-delete-{env['ZEALT_RUN_ID']}"

    client = Apideck(
        api_key=env["APIDECK_API_KEY"],
        app_id=env["APIDECK_APP_ID"],
        consumer_id=env["APIDECK_CONSUMER_ID"],
    )

    created_folder_id: Optional[str] = None
    try:
        drive_id = resolve_drive_id(client, env["APIDECK_FILE_STORAGE_DRIVE_NAME"])
        created_folder_id = create_folder(client, drive_id, folder_name)
        delete_folder(client, created_folder_id)

        append_log(
            (
                f"Drive ID: {drive_id}",
                f"Created folder ID: {created_folder_id}",
                f"Deleted folder ID: {created_folder_id}",
            )
        )
        print(
            f"Created and deleted OneDrive folder {folder_name!r} "
            f"with unified id {created_folder_id!r} in drive {drive_id!r}."
        )
        return 0
    except Exception:
        # Best-effort cleanup if the create succeeded but a later step failed.
        if created_folder_id:
            try:
                delete_folder(client, created_folder_id)
            except Exception:
                pass
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
