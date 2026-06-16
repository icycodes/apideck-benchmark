"""
Upload two text-report files to OneDrive via the Apideck Unify File Storage API.

Environment variables required:
  APIDECK_API_KEY            – Apideck API key
  APIDECK_APP_ID             – Apideck application ID
  APIDECK_CONSUMER_ID        – Apideck consumer ID
  APIDECK_SERVICE_ID         – Service ID of the OneDrive connector (e.g. "onedrive")
  APIDECK_FILE_STORAGE_DRIVE_NAME – Display name of the target OneDrive drive
  ZEALT_RUN_ID               – Run identifier used to name the uploaded files
"""

import json
import os
import sys

from apideck_unify import Apideck

# ---------------------------------------------------------------------------
# Read configuration from environment
# ---------------------------------------------------------------------------
api_key = os.environ["APIDECK_API_KEY"]
app_id = os.environ["APIDECK_APP_ID"]
consumer_id = os.environ["APIDECK_CONSUMER_ID"]
service_id = os.environ["APIDECK_SERVICE_ID"]
drive_name = os.environ["APIDECK_FILE_STORAGE_DRIVE_NAME"]
run_id = os.environ["ZEALT_RUN_ID"]

# ---------------------------------------------------------------------------
# Build the two files to upload
# ---------------------------------------------------------------------------
files_to_upload = [
    {
        "key": "alpha",
        "name": f"report-{run_id}-alpha.txt",
        "content": f"alpha payload for {run_id}\n".encode("utf-8"),
    },
    {
        "key": "beta",
        "name": f"report-{run_id}-beta.txt",
        "content": f"beta payload for {run_id}\n".encode("utf-8"),
    },
]

# ---------------------------------------------------------------------------
# Initialise the SDK client
# ---------------------------------------------------------------------------
client = Apideck(
    api_key=api_key,
    app_id=app_id,
    consumer_id=consumer_id,
)

# ---------------------------------------------------------------------------
# Resolve the drive ID by listing drives and matching on the drive name
# ---------------------------------------------------------------------------
drive_id: str | None = None

drives_resp = client.file_storage.drives.list(service_id=service_id)
if drives_resp and drives_resp.get_drives_response and drives_resp.get_drives_response.data:
    for drive in drives_resp.get_drives_response.data:
        if drive.name == drive_name:
            drive_id = drive.id
            break

# Page through results if the first page did not contain a match
if drive_id is None and drives_resp and callable(getattr(drives_resp, "next", None)):
    page = drives_resp.next()
    while page is not None and drive_id is None:
        if page.get_drives_response and page.get_drives_response.data:
            for drive in page.get_drives_response.data:
                if drive.name == drive_name:
                    drive_id = drive.id
                    break
        page = page.next() if callable(getattr(page, "next", None)) else None

if drive_id is None:
    print(
        f"ERROR: Could not find a drive named '{drive_name}' "
        f"in service '{service_id}'.",
        file=sys.stderr,
    )
    sys.exit(1)

print(f"Resolved drive '{drive_name}' → id={drive_id!r}")

# ---------------------------------------------------------------------------
# Upload each file using an upload session (create → upload part → finish)
# ---------------------------------------------------------------------------
results: dict[str, dict] = {}

for spec in files_to_upload:
    file_name: str = spec["name"]
    file_bytes: bytes = spec["content"]
    file_size: int = len(file_bytes)

    print(f"Uploading '{file_name}' ({file_size} bytes) …")

    # 1. Create an upload session
    session_resp = client.file_storage.upload_sessions.create(
        name=file_name,
        parent_folder_id="root",
        size=file_size,
        drive_id=drive_id,
        service_id=service_id,
    )

    session_id: str = session_resp.create_upload_session_response.data.id
    print(f"  Upload session created: {session_id!r}")

    # 2. Upload the entire file as a single part (part_number=1)
    client.file_storage.upload_sessions.upload(
        id=session_id,
        part_number=1,
        request_body=file_bytes,
        service_id=service_id,
    )
    print(f"  Part 1 uploaded.")

    # 3. Finish the upload session – response contains the new file record
    finish_resp = client.file_storage.upload_sessions.finish(
        id=session_id,
        service_id=service_id,
    )

    file_id: str = finish_resp.get_file_response.data.id
    print(f"  File committed, Apideck file id = {file_id!r}")

    results[spec["key"]] = {"name": file_name, "id": file_id}

# ---------------------------------------------------------------------------
# Append a single JSON record to output.log
# ---------------------------------------------------------------------------
log_path = os.path.join(os.path.dirname(__file__), "output.log")
log_record = {
    "alpha": results["alpha"],
    "beta": results["beta"],
}

with open(log_path, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(log_record, separators=(",", ":")) + "\n")

print(f"\nLog written to {log_path}")
print(json.dumps(log_record, indent=2))
