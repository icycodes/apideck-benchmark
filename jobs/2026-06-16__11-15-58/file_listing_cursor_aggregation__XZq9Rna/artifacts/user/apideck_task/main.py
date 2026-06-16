#!/usr/bin/env python3
"""
Apideck File Storage: Upload files and aggregate IDs via cursor pagination.
"""

import os
import sys
import json
import requests
import time

# --- Read environment variables ---
APP_ID = os.environ["APIDECK_APP_ID"]
API_KEY = os.environ["APIDECK_API_KEY"]
CONSUMER_ID = os.environ["APIDECK_CONSUMER_ID"]
DRIVE_NAME = os.environ["APIDECK_FILE_STORAGE_DRIVE_NAME"]
RUN_ID = os.environ["ZEALT_RUN_ID"]

PREFIX = f"AGG-{RUN_ID}-"

# --- Common headers ---
COMMON_HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "x-apideck-app-id": APP_ID,
    "x-apideck-consumer-id": CONSUMER_ID,
    "x-apideck-service-id": "onedrive",
}

UNIFY_BASE = "https://unify.apideck.com"
UPLOAD_BASE = "https://upload.apideck.com"


def find_drive_id():
    """Find the drive ID for the drive matching DRIVE_NAME."""
    url = f"{UNIFY_BASE}/file-storage/drives"
    headers = {**COMMON_HEADERS}
    params = {"limit": 200}
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()
    for drive in data.get("data", []):
        if drive.get("name") == DRIVE_NAME:
            return drive["id"]
    # If no drives match by name, return None and we'll try without a drive filter
    print(f"Warning: No drive found with name '{DRIVE_NAME}'. Available drives:")
    for drive in data.get("data", []):
        print(f"  - {drive.get('name')} (id: {drive.get('id')})")
    return None


def upload_file(filename, content, drive_id=None):
    """Upload a small text file to the drive root."""
    url = f"{UPLOAD_BASE}/file-storage/files"
    headers = {
        **COMMON_HEADERS,
        "Content-Type": "text/plain",
    }
    # Build metadata
    metadata = {"name": filename, "parent_folder_id": "root"}
    if drive_id:
        metadata["drive_id"] = drive_id
    headers["x-apideck-metadata"] = json.dumps(metadata)

    resp = requests.post(url, headers=headers, data=content.encode("utf-8"))
    if resp.status_code not in (200, 201):
        print(f"Upload failed for {filename}: {resp.status_code} {resp.text}")
        resp.raise_for_status()
    result = resp.json()
    file_id = result.get("data", {}).get("id")
    print(f"Uploaded {filename} -> id={file_id}")
    return file_id


def list_files_with_cursor(drive_id=None):
    """Walk the file listing using cursor pagination with limit=3.
    Aggregate and return IDs of files whose names start with PREFIX."""
    url = f"{UNIFY_BASE}/file-storage/files"
    headers = {**COMMON_HEADERS}
    aggregated_ids = []
    cursor = None
    page_num = 0

    while True:
        params = {"limit": 3}
        if cursor:
            params["cursor"] = cursor
        if drive_id:
            params["filter[drive_id]"] = drive_id

        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        page_num += 1
        files = data.get("data", [])
        print(f"Page {page_num}: {len(files)} files returned")

        for f in files:
            name = f.get("name", "")
            if name.startswith(PREFIX):
                aggregated_ids.append(f["id"])
                print(f"  Matched: {name} -> id={f['id']}")

        next_cursor = data.get("meta", {}).get("cursors", {}).get("next")
        if not next_cursor:
            print("No more pages (next cursor is empty).")
            break
        cursor = next_cursor

    return aggregated_ids


def main():
    print(f"Run ID: {RUN_ID}")
    print(f"Prefix: {PREFIX}")
    print(f"Drive name: {DRIVE_NAME}")
    print()

    # Step 1: Find drive ID
    print("=== Finding drive ID ===")
    drive_id = find_drive_id()
    if drive_id:
        print(f"Found drive ID: {drive_id}")
    else:
        print("No matching drive found by name; will proceed without drive filter.")
    print()

    # Step 2: Upload 7 text files
    print("=== Uploading 7 files ===")
    uploaded_ids = []
    for i in range(1, 8):
        filename = f"{PREFIX}{i}.txt"
        content = f"Content of file {i} for run {RUN_ID}"
        file_id = upload_file(filename, content, drive_id=drive_id)
        uploaded_ids.append(file_id)
        # Small delay to avoid rate limiting
        time.sleep(0.5)
    print(f"Uploaded {len(uploaded_ids)} files")
    print()

    # Step 3: Wait a moment for indexing
    print("Waiting 5 seconds for files to be indexed...")
    time.sleep(5)
    print()

    # Step 4: Walk file listing with cursor pagination (limit=3) and aggregate IDs
    print("=== Cursor-paginated listing (limit=3) ===")
    aggregated_ids = list_files_with_cursor(drive_id=drive_id)
    print()

    # Step 5: Write output.log
    summary = {
        "count": len(aggregated_ids),
        "ids": aggregated_ids,
    }
    print(f"Aggregated {summary['count']} file IDs: {summary['ids']}")

    output_path = "/home/user/apideck_task/output.log"
    with open(output_path, "w") as f:
        json.dump(summary, f)
    print(f"Written summary to {output_path}")


if __name__ == "__main__":
    main()