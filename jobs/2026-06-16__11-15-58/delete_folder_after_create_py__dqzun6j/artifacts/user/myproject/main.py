#!/usr/bin/env python3
"""
ApiDeck File Storage – create and delete a OneDrive folder in one round-trip.

Environment variables required:
  APIDECK_APP_ID
  APIDECK_API_KEY
  APIDECK_CONSUMER_ID
  APIDECK_FILE_STORAGE_DRIVE_NAME
  ZEALT_RUN_ID
"""

import os
import sys

from apideck_unify import Apideck

# ---------------------------------------------------------------------------
# Read credentials / configuration from the environment
# ---------------------------------------------------------------------------
API_KEY      = os.environ["APIDECK_API_KEY"]
APP_ID       = os.environ["APIDECK_APP_ID"]
CONSUMER_ID  = os.environ["APIDECK_CONSUMER_ID"]
DRIVE_NAME   = os.environ["APIDECK_FILE_STORAGE_DRIVE_NAME"]
RUN_ID       = os.environ["ZEALT_RUN_ID"]
SERVICE_ID   = "onedrive"

FOLDER_NAME  = f"harbor-delete-{RUN_ID}"
LOG_PATH     = "/home/user/myproject/output.log"

# ---------------------------------------------------------------------------
# Initialise the SDK client
# ---------------------------------------------------------------------------
client = Apideck(
    api_key=API_KEY,
    app_id=APP_ID,
    consumer_id=CONSUMER_ID,
)

# ---------------------------------------------------------------------------
# Step 1 – Resolve the drive id whose name matches APIDECK_FILE_STORAGE_DRIVE_NAME
# ---------------------------------------------------------------------------
print(f"[1] Listing drives to find '{DRIVE_NAME}' …")

drives_response = client.file_storage.drives.list(
    service_id=SERVICE_ID,
    limit=200,
)

drive_id = None
if drives_response and drives_response.get_drives_response and drives_response.get_drives_response.data:
    for drive in drives_response.get_drives_response.data:
        if drive.name == DRIVE_NAME:
            drive_id = drive.id
            break

if drive_id is None:
    available = []
    if drives_response and drives_response.get_drives_response and drives_response.get_drives_response.data:
        available = [d.name for d in drives_response.get_drives_response.data]
    print(f"ERROR: No drive named '{DRIVE_NAME}' found. Available: {available}", file=sys.stderr)
    sys.exit(1)

print(f"    Drive ID: {drive_id}")

# ---------------------------------------------------------------------------
# Step 2 – Create the folder at the drive root
# ---------------------------------------------------------------------------
print(f"[2] Creating folder '{FOLDER_NAME}' in drive {drive_id} …")

create_response = client.file_storage.folders.create(
    service_id=SERVICE_ID,
    name=FOLDER_NAME,
    parent_folder_id="root",
    drive_id=drive_id,
)

folder_id = None
if create_response and create_response.create_folder_response and create_response.create_folder_response.data:
    folder_id = create_response.create_folder_response.data.id

if folder_id is None:
    print("ERROR: Create folder call succeeded but returned no folder id.", file=sys.stderr)
    print(f"Response: {create_response}", file=sys.stderr)
    sys.exit(1)

print(f"    Folder ID: {folder_id}")

# ---------------------------------------------------------------------------
# Step 3 – Delete the folder
# ---------------------------------------------------------------------------
print(f"[3] Deleting folder {folder_id} …")

delete_response = client.file_storage.folders.delete(
    id=folder_id,
    service_id=SERVICE_ID,
)

print(f"    Delete HTTP status: {delete_response.http_meta.response.status_code}")

# ---------------------------------------------------------------------------
# Step 4 – Write the structured log
# ---------------------------------------------------------------------------
log_lines = [
    f"Drive ID: {drive_id}",
    f"Created folder ID: {folder_id}",
    f"Deleted folder ID: {folder_id}",
]

with open(LOG_PATH, "w") as fh:
    fh.write("\n".join(log_lines) + "\n")

print(f"[4] Log written to {LOG_PATH}")
for line in log_lines:
    print(f"    {line}")

print("Done.")
