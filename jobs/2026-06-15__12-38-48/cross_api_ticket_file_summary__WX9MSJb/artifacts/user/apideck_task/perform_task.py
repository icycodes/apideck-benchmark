import json
import os
import sys
from typing import Any, Dict, List, Optional

import requests

API_KEY = os.environ["APIDECK_API_KEY"]
APP_ID = os.environ["APIDECK_APP_ID"]
CONSUMER_ID = os.environ["APIDECK_CONSUMER_ID"]
RUN_ID = os.environ["ZEALT_RUN_ID"]
COLLECTION_ID = os.environ["APIDECK_ISSUE_TRACKING_COLLECTION_ID"]
DRIVE_NAME = os.environ.get("APIDECK_FILE_STORAGE_DRIVE_NAME")

UNIFY_BASE = "https://unify.apideck.com"
UPLOAD_BASE = "https://upload.apideck.com"

FILE_SERVICE_ID = "onedrive"
ISSUE_SERVICE_ID = "github"
MARKER = "[FILE-INDEX]"

TARGET_NAMES = [
    f"REPORT-{RUN_ID}-A.txt",
    f"REPORT-{RUN_ID}-B.txt",
    f"REPORT-{RUN_ID}-C.txt",
]


def headers(service_id: str, content_type: Optional[str] = "application/json") -> Dict[str, str]:
    result = {
        "Authorization": f"Bearer {API_KEY}",
        "x-apideck-app-id": APP_ID,
        "x-apideck-consumer-id": CONSUMER_ID,
        "x-apideck-service-id": service_id,
        "Accept": "application/json",
    }
    if content_type:
        result["Content-Type"] = content_type
    return result


def request_json(method: str, url: str, *, service_id: str, expected: List[int], **kwargs: Any) -> Dict[str, Any]:
    response = requests.request(method, url, headers=headers(service_id, kwargs.pop("content_type", "application/json")), timeout=60, **kwargs)
    if response.status_code not in expected:
        raise RuntimeError(
            f"{method} {url} failed with {response.status_code}: {response.text[:4000]}"
        )
    if response.content:
        return response.json()
    return {}


def list_all(url: str, *, service_id: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    params = dict(params or {})
    params.setdefault("limit", 200)
    items: List[Dict[str, Any]] = []
    cursor = None
    while True:
        page_params = dict(params)
        if cursor:
            page_params["cursor"] = cursor
        payload = request_json("GET", url, service_id=service_id, expected=[200], params=page_params)
        items.extend(payload.get("data") or [])
        cursor = (((payload.get("meta") or {}).get("cursors") or {}).get("next"))
        if not cursor:
            break
    return items


def find_drive_id() -> Optional[str]:
    drives = list_all(f"{UNIFY_BASE}/file-storage/drives", service_id=FILE_SERVICE_ID, params={"limit": 200})
    if not drives:
        return None
    if DRIVE_NAME:
        for drive in drives:
            if drive.get("name") == DRIVE_NAME:
                return drive.get("id")
    return drives[0].get("id")


def list_root_files(drive_id: Optional[str]) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"filter[folder_id]": "root", "limit": 200}
    if drive_id:
        params["filter[drive_id]"] = drive_id
    return list_all(f"{UNIFY_BASE}/file-storage/files", service_id=FILE_SERVICE_ID, params=params)


def delete_file(file_id: str) -> None:
    request_json(
        "DELETE",
        f"{UNIFY_BASE}/file-storage/files/{file_id}",
        service_id=FILE_SERVICE_ID,
        expected=[200, 204],
    )


def upload_file(name: str, drive_id: Optional[str]) -> str:
    metadata: Dict[str, Any] = {"name": name, "parent_folder_id": "root"}
    if drive_id:
        metadata["drive_id"] = drive_id
    body = f"Report file {name}\nZEALT_RUN_ID={RUN_ID}\n".encode("utf-8")
    upload_headers = headers(FILE_SERVICE_ID, "text/plain")
    upload_headers["x-apideck-metadata"] = json.dumps(metadata, separators=(",", ":"))
    response = requests.post(
        f"{UPLOAD_BASE}/file-storage/files",
        headers=upload_headers,
        data=body,
        timeout=60,
    )
    if response.status_code != 201:
        raise RuntimeError(f"POST upload {name} failed with {response.status_code}: {response.text[:4000]}")
    payload = response.json()
    return payload["data"]["id"]


def list_matching_tickets() -> List[Dict[str, Any]]:
    tickets = list_all(
        f"{UNIFY_BASE}/issue-tracking/collections/{COLLECTION_ID}/tickets",
        service_id=ISSUE_SERVICE_ID,
        params={"limit": 200, "sort[by]": "created_at", "sort[direction]": "desc"},
    )
    return [t for t in tickets if RUN_ID in (t.get("subject") or "") and MARKER in (t.get("subject") or "")]


def delete_ticket(ticket_id: str) -> None:
    request_json(
        "DELETE",
        f"{UNIFY_BASE}/issue-tracking/collections/{COLLECTION_ID}/tickets/{ticket_id}",
        service_id=ISSUE_SERVICE_ID,
        expected=[200, 204],
    )


def create_ticket(description: str) -> str:
    subject = f"{MARKER} {RUN_ID} file index"
    payload = {"subject": subject, "description": description, "status": "open"}
    created = request_json(
        "POST",
        f"{UNIFY_BASE}/issue-tracking/collections/{COLLECTION_ID}/tickets",
        service_id=ISSUE_SERVICE_ID,
        expected=[201],
        json=payload,
    )
    return created["data"]["id"]


def main() -> None:
    drive_id = find_drive_id()

    # Remove stale files for this run before uploading, so the drive root has exactly the target names once done.
    stale_files = [f for f in list_root_files(drive_id) if f.get("name") in TARGET_NAMES]
    for file_obj in stale_files:
        delete_file(file_obj["id"])

    uploaded_ids_by_name = {name: upload_file(name, drive_id) for name in TARGET_NAMES}
    sorted_ids = sorted(uploaded_ids_by_name.values())
    description = "\n".join(sorted_ids)

    # Remove stale matching tickets if the service supports deletion, then create exactly one current index ticket.
    stale_tickets = list_matching_tickets()
    for ticket in stale_tickets:
        delete_ticket(ticket["id"])

    ticket_id = create_ticket(description)

    print(json.dumps({
        "run_id": RUN_ID,
        "drive_id": drive_id,
        "uploaded_files": uploaded_ids_by_name,
        "sorted_file_ids": sorted_ids,
        "ticket_id": ticket_id,
        "ticket_description": description,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
