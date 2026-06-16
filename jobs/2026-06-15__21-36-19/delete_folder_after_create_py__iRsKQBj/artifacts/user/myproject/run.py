#!/usr/bin/env python3
"""
Provision and tear down a short-lived workspace folder in OneDrive
via the ApiDeck File Storage Unified API.
"""

import os
import sys
from apideck_unify import Apideck

# ── Configuration from environment ──────────────────────────────────────────
API_KEY = os.environ["APIDECK_API_KEY"]
APP_ID = os.environ["APIDECK_APP_ID"]
CONSUMER_ID = os.environ["APIDECK_CONSUMER_ID"]
DRIVE_NAME = os.environ["APIDECK_FILE_STORAGE_DRIVE_NAME"]
RUN_ID = os.environ["ZEALT_RUN_ID"]
SERVICE_ID = "onedrive"

FOLDER_NAME = f"harbor-delete-{RUN_ID}"
LOG_PATH = "/home/user/myproject/output.log"


def main() -> None:
    sdk = Apideck(api_key=API_KEY, consumer_id=CONSUMER_ID, app_id=APP_ID)

    # ── Step 1: Resolve the drive by name ───────────────────────────────────
    drives_resp = sdk.file_storage.drives.list(service_id=SERVICE_ID, raw=False)

    if drives_resp is None or drives_resp.get_drives_response is None:
        print("ERROR: Failed to list drives", file=sys.stderr)
        sys.exit(1)

    drives_data = drives_resp.get_drives_response.data
    drive_id = None
    for drive in drives_data:
        if drive.name == DRIVE_NAME:
            drive_id = drive.id
            break

    if drive_id is None:
        print(
            f"ERROR: No drive found with name '{DRIVE_NAME}'",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Resolved drive '{DRIVE_NAME}' → id={drive_id}")

    # ── Step 2: Create the folder ───────────────────────────────────────────
    create_resp = sdk.file_storage.folders.create(
        name=FOLDER_NAME,
        parent_folder_id="root",
        drive_id=drive_id,
        service_id=SERVICE_ID,
        raw=False,
    )

    if create_resp is None or create_resp.create_folder_response is None:
        print("ERROR: Failed to create folder", file=sys.stderr)
        sys.exit(1)

    folder_id = create_resp.create_folder_response.data.id
    print(f"Created folder '{FOLDER_NAME}' → id={folder_id}")

    # ── Step 3: Delete the folder ───────────────────────────────────────────
    delete_resp = sdk.file_storage.folders.delete(
        id=folder_id,
        service_id=SERVICE_ID,
        raw=False,
    )

    if delete_resp is None or delete_resp.delete_folder_response is None:
        print("ERROR: Failed to delete folder", file=sys.stderr)
        sys.exit(1)

    deleted_folder_id = delete_resp.delete_folder_response.data.id
    print(f"Deleted folder → id={deleted_folder_id}")

    # ── Step 4: Write structured log ────────────────────────────────────────
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w") as f:
        f.write(f"Drive ID: {drive_id}\n")
        f.write(f"Created folder ID: {folder_id}\n")
        f.write(f"Deleted folder ID: {deleted_folder_id}\n")

    print(f"Log written to {LOG_PATH}")


if __name__ == "__main__":
    main()
