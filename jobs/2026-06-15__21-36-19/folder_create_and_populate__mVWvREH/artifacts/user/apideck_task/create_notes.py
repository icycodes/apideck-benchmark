#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

UNIFY_BASE = "https://unify.apideck.com"
UPLOAD_BASE = "https://upload.apideck.com"
SERVICE_ID = "onedrive"
OUTPUT_LOG = "/home/user/apideck_task/output.log"


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


RUN_ID = require_env("ZEALT_RUN_ID")
DRIVE_NAME = require_env("APIDECK_FILE_STORAGE_DRIVE_NAME")
API_KEY = require_env("APIDECK_API_KEY")
APP_ID = require_env("APIDECK_APP_ID")
CONSUMER_ID = require_env("APIDECK_CONSUMER_ID")


COMMON_HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "x-apideck-app-id": APP_ID,
    "x-apideck-consumer-id": CONSUMER_ID,
    "x-apideck-service-id": SERVICE_ID,
}


def request_json(method: str, url: str, *, body=None, headers=None):
    all_headers = dict(COMMON_HEADERS)
    if headers:
        all_headers.update(headers)

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        all_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=all_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with HTTP {exc.code}: {detail}") from exc


def upload_file(name: str, parent_folder_id: str, drive_id: str, content: str) -> str:
    metadata = {
        "name": name,
        "parent_folder_id": parent_folder_id,
        "drive_id": drive_id,
    }
    headers = dict(COMMON_HEADERS)
    headers.update(
        {
            "Content-Type": "text/plain; charset=utf-8",
            "x-apideck-metadata": json.dumps(metadata, separators=(",", ":")),
        }
    )
    req = urllib.request.Request(
        f"{UPLOAD_BASE}/file-storage/files",
        data=content.encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"upload {name} failed with HTTP {exc.code}: {detail}") from exc

    file_id = payload.get("data", {}).get("id")
    if not file_id:
        raise RuntimeError(f"Upload response for {name} did not include data.id: {payload}")
    return file_id


def main() -> int:
    drives_payload = request_json("GET", f"{UNIFY_BASE}/file-storage/drives")
    drives = drives_payload.get("data") or []
    drive = next((item for item in drives if item.get("name") == DRIVE_NAME), None)
    if not drive:
        available = [item.get("name") for item in drives]
        raise RuntimeError(f"Drive named {DRIVE_NAME!r} was not found. Available drives: {available}")
    drive_id = drive.get("id")
    if not drive_id:
        raise RuntimeError(f"Matched drive did not include an id: {drive}")

    folder_name = f"FOLDER-{RUN_ID}"
    folder_payload = request_json(
        "POST",
        f"{UNIFY_BASE}/file-storage/folders",
        body={"name": folder_name, "parent_folder_id": "root", "drive_id": drive_id},
    )
    folder_id = folder_payload.get("data", {}).get("id")
    if not folder_id:
        raise RuntimeError(f"Folder creation response did not include data.id: {folder_payload}")

    file_ids = []
    for index in range(1, 4):
        file_name = f"NOTE-{RUN_ID}-{index}.txt"
        body = f"Run {RUN_ID} note {index}\n"
        file_ids.append(upload_file(file_name, folder_id, drive_id, body))

    # Apideck may normalize the drive component of the encoded folder id in
    # subsequent file responses. Preserve the API-observable direct parent id in
    # the final log while still using the folder-create id for uploads.
    first_file = request_json(
        "GET",
        f"{UNIFY_BASE}/file-storage/files/{urllib.parse.quote(file_ids[0], safe='')}",
    ).get("data", {})
    parent_folders = first_file.get("parent_folders") or []
    logged_folder_id = parent_folders[0].get("id") if parent_folders else folder_id

    with open(OUTPUT_LOG, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"folder_id": logged_folder_id, "file_ids": file_ids}, separators=(",", ":")) + "\n")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
