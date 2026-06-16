#!/usr/bin/env python3
"""
Apideck File Storage Task:
- Upload 7 text files to the OneDrive drive root via Apideck upload API
- Walk file listing with cursor pagination (limit=3)
- Aggregate IDs of files matching the run-scoped prefix
- Write JSON summary to output.log
"""

import json
import os
import sys
import time

import requests

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
APP_ID       = os.environ["APIDECK_APP_ID"]
API_KEY      = os.environ["APIDECK_API_KEY"]
CONSUMER_ID  = os.environ["APIDECK_CONSUMER_ID"]
DRIVE_NAME   = os.environ["APIDECK_FILE_STORAGE_DRIVE_NAME"]
RUN_ID       = os.environ["ZEALT_RUN_ID"]

SERVICE_ID   = "onedrive"
UPLOAD_HOST  = "https://upload.apideck.com"
UNIFY_HOST   = "https://unify.apideck.com"

PREFIX       = f"AGG-{RUN_ID}-"
OUTPUT_LOG   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output.log")

# ---------------------------------------------------------------------------
# Shared headers helpers
# ---------------------------------------------------------------------------

def auth_headers(extra=None):
    h = {
        "Authorization":         f"Bearer {API_KEY}",
        "x-apideck-app-id":      APP_ID,
        "x-apideck-consumer-id": CONSUMER_ID,
        "x-apideck-service-id":  SERVICE_ID,
    }
    if extra:
        h.update(extra)
    return h


# ---------------------------------------------------------------------------
# Step 1: Resolve the drive ID for APIDECK_FILE_STORAGE_DRIVE_NAME
# ---------------------------------------------------------------------------

def get_drive_id():
    """Return the Apideck drive ID that corresponds to DRIVE_NAME."""
    url = f"{UNIFY_HOST}/file-storage/drives"
    resp = requests.get(url, headers=auth_headers())
    resp.raise_for_status()
    body = resp.json()
    drives = body.get("data", [])
    for drive in drives:
        if drive.get("name") == DRIVE_NAME:
            drive_id = drive["id"]
            print(f"[INFO] Resolved drive '{DRIVE_NAME}' -> id={drive_id}")
            return drive_id
    # If only one drive exists, use it regardless of name match
    if len(drives) == 1:
        drive_id = drives[0]["id"]
        print(f"[WARN] Drive '{DRIVE_NAME}' not found by name; using only drive id={drive_id}")
        return drive_id
    raise RuntimeError(
        f"Drive named '{DRIVE_NAME}' not found. Available: {[d.get('name') for d in drives]}"
    )


# ---------------------------------------------------------------------------
# Step 2: Upload 7 files
# ---------------------------------------------------------------------------

def upload_file(filename: str, content: bytes, drive_id: str) -> str:
    """Upload a single file to the drive root; return its Apideck file ID."""
    metadata = json.dumps({
        "name": filename,
        "parent_folder_id": "root",
        "drive_id": drive_id,
    })
    headers = auth_headers({
        "x-apideck-metadata": metadata,
        "Content-Type":        "text/plain",
    })
    url = f"{UPLOAD_HOST}/file-storage/files"
    resp = requests.post(url, headers=headers, data=content)
    if not resp.ok:
        print(f"[ERROR] Upload failed for {filename}: {resp.status_code} {resp.text}")
        resp.raise_for_status()
    body = resp.json()
    file_id = body["data"]["id"]
    print(f"[INFO] Uploaded {filename} -> id={file_id}")
    return file_id


def upload_all_files(drive_id: str) -> list[str]:
    """Upload AGG-{RUN_ID}-1.txt .. AGG-{RUN_ID}-7.txt; return list of file IDs."""
    uploaded_ids = []
    for i in range(1, 8):
        filename = f"{PREFIX}{i}.txt"
        content  = f"Run {RUN_ID} file {i}\n".encode()
        file_id  = upload_file(filename, content, drive_id)
        uploaded_ids.append(file_id)
        # Small back-off to avoid rate limits
        time.sleep(0.3)
    return uploaded_ids


# ---------------------------------------------------------------------------
# Step 3: Cursor-paginated listing — aggregate matching IDs
# ---------------------------------------------------------------------------

def list_files_paginated(drive_id: str) -> list[str]:
    """
    Walk all pages (limit=3) of the file listing for drive_id.
    Return IDs of every file whose name starts with PREFIX.
    """
    matched_ids = []
    cursor      = None
    page_num    = 0

    while True:
        page_num += 1
        params = {
            "limit":             3,
            "filter[drive_id]":  drive_id,
        }
        if cursor:
            params["cursor"] = cursor

        url  = f"{UNIFY_HOST}/file-storage/files"
        resp = requests.get(url, headers=auth_headers(), params=params)
        if not resp.ok:
            print(f"[ERROR] List page {page_num} failed: {resp.status_code} {resp.text}")
            resp.raise_for_status()

        body  = resp.json()
        items = body.get("data", [])
        meta  = body.get("meta", {})

        print(f"[INFO] Page {page_num}: {len(items)} item(s)")

        for item in items:
            name = item.get("name", "")
            if name.startswith(PREFIX):
                matched_ids.append(item["id"])
                print(f"  [MATCH] {name} -> {item['id']}")

        # Advance cursor
        next_cursor = meta.get("cursors", {}).get("next")
        if not next_cursor:
            print(f"[INFO] No next cursor — pagination complete after {page_num} page(s).")
            break
        cursor = next_cursor

    return matched_ids


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"[INFO] Run ID     : {RUN_ID}")
    print(f"[INFO] Prefix     : {PREFIX}")
    print(f"[INFO] Drive name : {DRIVE_NAME}")

    # 1. Resolve drive
    drive_id = get_drive_id()

    # 2. Upload 7 files
    print("[INFO] Uploading 7 files ...")
    upload_all_files(drive_id)

    # Brief pause to let the listing reflect the new files
    print("[INFO] Waiting 3s for uploads to propagate ...")
    time.sleep(3)

    # 3. Paginated listing
    print("[INFO] Walking file listing with cursor pagination (limit=3) ...")
    matched_ids = list_files_paginated(drive_id)

    # 4. Write output.log
    summary = {"count": len(matched_ids), "ids": matched_ids}
    with open(OUTPUT_LOG, "w") as fh:
        json.dump(summary, fh)
        fh.write("\n")

    print(f"[INFO] Summary written to {OUTPUT_LOG}")
    print(f"[INFO] count={summary['count']}, ids={summary['ids']}")

    if summary["count"] != 7:
        print(f"[WARN] Expected 7 matching files but found {summary['count']}.")
        sys.exit(1)

    print("[DONE] All 7 files aggregated successfully.")


if __name__ == "__main__":
    main()
