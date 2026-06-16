#!/usr/bin/env python3
"""
Upload 3 files to OneDrive via Apideck upload API and create/update a ticket.
"""
import os
import json
import subprocess
import sys

API_KEY = "(*****SECRET_LEAK_DETECTED*****)"
APP_ID = "605EzrgGklBBo5T9tcIgkHs4omRyk3ykcJVtcIg"
CONSUMER_ID = "test-consumer"
RUN_ID = os.environ.get("ZEALT_RUN_ID", "zr-y3jhgm3")
COLLECTION_ID = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID", "zealt-user-default-repo")
DRIVE_ID = "3ada079b78534ff1"

UPLOAD_BASE = "https://upload.apideck.com"
UNIFY_BASE = "https://unify.apideck.com"

print(f"=== ZEALT_RUN_ID: {RUN_ID} ===")
print(f"=== COLLECTION_ID: {COLLECTION_ID} ===")


def upload_file(filename: str, content: str) -> str:
    """Upload a file to OneDrive via Apideck and return its Apideck file id."""
    metadata = json.dumps({
        "name": filename,
        "parent_folder_id": "root",
        "drive_id": DRIVE_ID
    })
    print(f"\nUploading {filename} ...")
    result = subprocess.run(
        [
            "curl", "-s", "-X", "POST",
            f"{UPLOAD_BASE}/file-storage/files",
            "-H", f"Authorization: Bearer {API_KEY}",
            "-H", f"x-apideck-app-id: {APP_ID}",
            "-H", f"x-apideck-consumer-id: {CONSUMER_ID}",
            "-H", f"x-apideck-service-id: onedrive",
            "-H", f"x-apideck-metadata: {metadata}",
            "-H", "Content-Type: text/plain",
            "--data-binary", content,
        ],
        capture_output=True, text=True
    )
    resp = result.stdout
    print(f"Response: {resp}")
    data = json.loads(resp)
    file_id = data["data"]["id"]
    print(f"File ID: {file_id}")
    return file_id


def update_ticket(ticket_id: str, subject: str, description: str):
    """Update an existing ticket."""
    payload = json.dumps({
        "subject": subject,
        "description": description,
    })
    print(f"\nUpdating ticket {ticket_id} ...")
    result = subprocess.run(
        [
            "curl", "-s", "-X", "PATCH",
            f"{UNIFY_BASE}/issue-tracking/collections/{COLLECTION_ID}/tickets/{ticket_id}",
            "-H", f"Authorization: Bearer {API_KEY}",
            "-H", f"x-apideck-app-id: {APP_ID}",
            "-H", f"x-apideck-consumer-id: {CONSUMER_ID}",
            "-H", "x-apideck-service-id: github",
            "-H", "Content-Type: application/json",
            "-d", payload,
        ],
        capture_output=True, text=True
    )
    resp = result.stdout
    print(f"Update response: {resp}")
    return json.loads(resp)


def create_ticket(subject: str, description: str):
    """Create a new ticket."""
    payload = json.dumps({
        "subject": subject,
        "description": description,
        "status": "open",
    })
    print(f"\nCreating ticket ...")
    result = subprocess.run(
        [
            "curl", "-s", "-X", "POST",
            f"{UNIFY_BASE}/issue-tracking/collections/{COLLECTION_ID}/tickets",
            "-H", f"Authorization: Bearer {API_KEY}",
            "-H", f"x-apideck-app-id: {APP_ID}",
            "-H", f"x-apideck-consumer-id: {CONSUMER_ID}",
            "-H", "x-apideck-service-id: github",
            "-H", "Content-Type: application/json",
            "-d", payload,
        ],
        capture_output=True, text=True
    )
    resp = result.stdout
    print(f"Create response: {resp}")
    return json.loads(resp)


# Step 1: Upload 3 files
file_a = f"REPORT-{RUN_ID}-A.txt"
file_b = f"REPORT-{RUN_ID}-B.txt"
file_c = f"REPORT-{RUN_ID}-C.txt"

id_a = upload_file(file_a, f"Report A for run {RUN_ID}\n")
id_b = upload_file(file_b, f"Report B for run {RUN_ID}\n")
id_c = upload_file(file_c, f"Report C for run {RUN_ID}\n")

print(f"\n=== File IDs ===")
print(f"A ({file_a}): {id_a}")
print(f"B ({file_b}): {id_b}")
print(f"C ({file_c}): {id_c}")

# Step 2: Sort IDs ascending
sorted_ids = sorted([id_a, id_b, id_c])
print(f"\n=== Sorted IDs ===")
for i in sorted_ids:
    print(i)

# Step 3: Build description (newline-joined, nothing else)
description = "\n".join(sorted_ids)
subject = f"[FILE-INDEX] {RUN_ID} uploaded reports"

print(f"\n=== Subject: {subject} ===")
print(f"=== Description ===\n{description}")

# Step 4: Update existing bad ticket 196, then create a proper new one
# First update the bad ticket to close it / mark it something else
# Actually we can't delete via github connector, so let's update ticket 196 properly
# with the correct data
update_result = update_ticket("196", subject, description)
if update_result.get("status_code") in (200, 201):
    print(f"\n=== SUCCESS: Updated ticket 196 ===")
    tid = update_result.get("data", {}).get("id", "196")
    print(f"Ticket ID: {tid}")
else:
    print(f"\nUpdate failed, creating new ticket...")
    create_result = create_ticket(subject, description)
    print(f"Create result: {json.dumps(create_result, indent=2)}")

print("\n=== DONE ===")
