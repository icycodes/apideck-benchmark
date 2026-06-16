#!/usr/bin/env python3
"""
Apideck File Storage task:
1. Find the drive ID for APIDECK_FILE_STORAGE_DRIVE_NAME
2. Upload 4 marker files to the root of that drive
3. Search for KEEP-{run_id} files and collect their IDs
4. Write output.log with {"search_result_ids": [...]}
"""

import os
import sys
import json
import time
import urllib.parse
import urllib.request
import urllib.error

# ─── Config ────────────────────────────────────────────────────────────────────
RUN_ID      = os.environ["ZEALT_RUN_ID"]
APP_ID      = os.environ["APIDECK_APP_ID"]
CONSUMER_ID = os.environ["APIDECK_CONSUMER_ID"]
API_KEY     = os.environ["APIDECK_API_KEY"]
DRIVE_NAME  = os.environ["APIDECK_FILE_STORAGE_DRIVE_NAME"]

UNIFY_BASE  = "https://unify.apideck.com"
UPLOAD_BASE = "https://upload.apideck.com"
SERVICE_ID  = "onedrive"
LOG_FILE    = "/home/user/apideck_task/output.log"

COMMON_HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "x-apideck-app-id": APP_ID,
    "x-apideck-consumer-id": CONSUMER_ID,
    "x-apideck-service-id": SERVICE_ID,
    "Accept": "application/json",
}

# ─── Helper ─────────────────────────────────────────────────────────────────────
def api_request(method, url, headers=None, data=None):
    h = dict(COMMON_HEADERS)
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        if isinstance(data, (dict, list)):
            body = json.dumps(data).encode()
            h["Content-Type"] = "application/json"
        elif isinstance(data, str):
            body = data.encode()
        elif isinstance(data, bytes):
            body = data
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  HTTP {e.code} error: {body[:500]}", file=sys.stderr)
        try:
            return json.loads(body)
        except Exception:
            return {"error": body}

# ─── Step 1: Find drive ─────────────────────────────────────────────────────────
print(f"==> RUN_ID: {RUN_ID}")
print(f"==> Looking for drive: {DRIVE_NAME}")

resp = api_request("GET", f"{UNIFY_BASE}/file-storage/drives")
drives = resp.get("data", [])
drive_id = None
for d in drives:
    print(f"  Drive: {d.get('name')} -> {d.get('id')}")
    if d.get("name") == DRIVE_NAME:
        drive_id = d["id"]

if not drive_id:
    print(f"ERROR: drive '{DRIVE_NAME}' not found", file=sys.stderr)
    sys.exit(1)

print(f"==> Drive ID: {drive_id}")

# ─── Step 2: Upload 4 files ─────────────────────────────────────────────────────
files_to_upload = [
    f"KEEP-{RUN_ID}-1.txt",
    f"KEEP-{RUN_ID}-2.txt",
    f"SKIP-{RUN_ID}-1.txt",
    f"SKIP-{RUN_ID}-2.txt",
]

uploaded_ids = {}

for fname in files_to_upload:
    print(f"==> Uploading {fname}...")
    metadata = json.dumps({
        "name": fname,
        "parent_folder_id": "root",
        "drive_id": drive_id,
    })
    content = f"Marker file {fname} for run {RUN_ID}".encode()
    resp = api_request(
        "POST",
        f"{UPLOAD_BASE}/file-storage/files",
        headers={
            "Content-Type": "text/plain",
            "x-apideck-metadata": metadata,
        },
        data=content,
    )
    print(f"  Response: {json.dumps(resp)}")
    fid = resp.get("data", {}).get("id")
    if fid:
        uploaded_ids[fname] = fid
        print(f"  Uploaded ID: {fid}")
    else:
        print(f"  WARNING: no ID returned for {fname}")

print(f"==> All uploads done. IDs: {uploaded_ids}")

# ─── Step 3: Search for KEEP files ─────────────────────────────────────────────
# OneDrive search may need a moment to index newly uploaded files.
# Retry up to 5 times with increasing delays.
query = f"KEEP-{RUN_ID}"
search_ids = []

MAX_ATTEMPTS = 6
DELAY_SECS = [5, 10, 15, 20, 25, 30]

for attempt in range(MAX_ATTEMPTS):
    wait = DELAY_SECS[attempt] if attempt < len(DELAY_SECS) else 30
    print(f"==> Search attempt {attempt+1}/{MAX_ATTEMPTS}, waiting {wait}s for indexing...")
    time.sleep(wait)

    search_ids = []
    cursor = None
    page = 0

    while True:
        page += 1
        url = f"{UNIFY_BASE}/file-storage/files/search"
        if cursor:
            url += f"?cursor={urllib.parse.quote(cursor, safe='')}"

        print(f"  Page {page}, cursor={cursor!r}")
        resp = api_request("POST", url, data={"query": query})
        print(f"  Search response: {json.dumps(resp)[:500]}")

        if resp.get("status_code", 200) >= 400:
            print(f"  Search error on page {page}, stopping pagination")
            break

        for item in resp.get("data", []):
            search_ids.append(item["id"])
            print(f"  Found: {item.get('name')} -> {item['id']}")

        # Get next cursor
        next_cursor = (
            resp.get("meta", {})
                .get("cursors", {})
                .get("next")
        )
        if not next_cursor:
            break
        cursor = next_cursor

    if len(search_ids) >= 2:
        print(f"==> Found {len(search_ids)} results, done.")
        break
    else:
        print(f"==> Only {len(search_ids)} results so far, will retry...")

print(f"==> Final search IDs: {search_ids}")

# ─── Step 4: Write output.log ───────────────────────────────────────────────────
result = {"search_result_ids": search_ids}
with open(LOG_FILE, "w") as f:
    f.write(json.dumps(result))

print(f"==> Written to {LOG_FILE}: {json.dumps(result)}")
