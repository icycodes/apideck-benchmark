#!/usr/bin/env python3
"""Run Apideck Issue Tracking comment edit/delete workflow for GitHub."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://unify.apideck.com"
SERVICE_ID = os.environ.get("APIDECK_SERVICE_ID", "github")
OUTPUT_LOG = Path(__file__).with_name("output.log")
MARKER = "[COMMENT-EDIT-DELETE]"


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


API_KEY = require_env("APIDECK_API_KEY")
APP_ID = require_env("APIDECK_APP_ID")
CONSUMER_ID = require_env("APIDECK_CONSUMER_ID")
COLLECTION_ID = require_env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
RUN_ID = require_env("ZEALT_RUN_ID")


HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "x-apideck-app-id": APP_ID,
    "x-apideck-consumer-id": CONSUMER_ID,
    "x-apideck-service-id": SERVICE_ID,
    "Accept": "application/json",
    "Content-Type": "application/json",
}


def path_segment(value: str) -> str:
    return quote(str(value), safe="")


def request_json(method: str, path: str, body: dict[str, Any] | None = None, query: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    if query:
        clean_query = {key: value for key, value in query.items() if value is not None}
        if clean_query:
            url = f"{url}?{urlencode(clean_query, doseq=True)}"

    data = None if body is None else json.dumps(body).encode("utf-8")
    req = Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urlopen(req, timeout=60) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload) if payload else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed with HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"{method} {path} failed: {exc.reason}") from exc


def collection_path(suffix: str = "") -> str:
    base = f"/issue-tracking/collections/{path_segment(COLLECTION_ID)}"
    return f"{base}{suffix}"


def ticket_path(ticket_id: str, suffix: str = "") -> str:
    return collection_path(f"/tickets/{path_segment(ticket_id)}{suffix}")


def comments_path(ticket_id: str, suffix: str = "") -> str:
    return ticket_path(ticket_id, f"/comments{suffix}")


def extract_created_id(response: dict[str, Any], resource: str) -> str:
    data = response.get("data") or {}
    resource_id = data.get("id")
    if not resource_id:
        raise RuntimeError(f"Create/update {resource} response did not include data.id: {json.dumps(response)}")
    return str(resource_id)


def list_all(path: str, *, limit: int = 200) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        response = request_json("GET", path, query={"limit": limit, "cursor": cursor})
        data = response.get("data") or []
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected list response shape: {json.dumps(response)}")
        records.extend(data)
        cursor = ((response.get("meta") or {}).get("cursors") or {}).get("next")
        if not cursor:
            return records


def matching_tickets() -> list[dict[str, Any]]:
    all_tickets = list_all(collection_path("/tickets"))
    return [
        ticket
        for ticket in all_tickets
        if MARKER in str(ticket.get("subject", "")) and RUN_ID in str(ticket.get("subject", ""))
    ]


def wait_for_comments(ticket_id: str, expected_bodies: set[str], forbidden_bodies: set[str], attempts: int = 8) -> list[dict[str, Any]]:
    last_comments: list[dict[str, Any]] = []
    for _ in range(attempts):
        last_comments = list_all(comments_path(ticket_id))
        bodies = {str(comment.get("body", "")) for comment in last_comments}
        if len(last_comments) == len(expected_bodies) and bodies == expected_bodies and not (bodies & forbidden_bodies):
            return last_comments
        time.sleep(2)
    bodies = [comment.get("body") for comment in last_comments]
    raise RuntimeError(f"Final comments did not match expected state. Found {len(last_comments)} comments: {bodies}")


def main() -> int:
    subject = f"{MARKER} Comment edit/delete workflow {RUN_ID}"
    expected_bodies = {f"A-{RUN_ID}", f"B-EDITED-{RUN_ID}", f"D-{RUN_ID}"}
    forbidden_bodies = {f"B-{RUN_ID}", f"C-{RUN_ID}"}

    log_lines: list[str] = [
        f"Run ID: {RUN_ID}",
        f"Collection ID: {COLLECTION_ID}",
        f"Service ID: {SERVICE_ID}",
    ]

    stale_tickets = matching_tickets()
    for ticket in stale_tickets:
        stale_id = str(ticket.get("id"))
        if stale_id and stale_id != "None":
            request_json("DELETE", ticket_path(stale_id))
            log_lines.append(f"Deleted stale ticket ID: {stale_id}")

    create_ticket_response = request_json(
        "POST",
        collection_path("/tickets"),
        {
            "subject": subject,
            "description": f"Apideck comment edit/delete workflow for ZEALT_RUN_ID={RUN_ID}",
            "status": "open",
            "priority": "normal",
        },
    )
    ticket_id = extract_created_id(create_ticket_response, "ticket")
    log_lines.append(f"Ticket ID: {ticket_id}")
    log_lines.append(f"Ticket Subject: {subject}")

    comment_ids: dict[str, str] = {}
    for label in ("A", "B", "C", "D"):
        body = f"{label}-{RUN_ID}"
        response = request_json("POST", comments_path(ticket_id), {"body": body})
        comment_id = extract_created_id(response, f"comment {label}")
        comment_ids[label] = comment_id
        log_lines.append(f"Comment {label} ID: {comment_id}")

    request_json("PATCH", comments_path(ticket_id, f"/{path_segment(comment_ids['B'])}"), {"body": f"B-EDITED-{RUN_ID}"})
    log_lines.append(f"Edited Comment B ID: {comment_ids['B']}")

    request_json("DELETE", comments_path(ticket_id, f"/{path_segment(comment_ids['C'])}"))
    log_lines.append(f"Deleted Comment C ID: {comment_ids['C']}")

    final_comments = wait_for_comments(ticket_id, expected_bodies, forbidden_bodies)
    for comment in final_comments:
        log_lines.append(f"Remaining Comment ID: {comment.get('id')} Body: {comment.get('body')}")

    matches = matching_tickets()
    matching_ids = [str(ticket.get("id")) for ticket in matches]
    log_lines.append(f"Matching Ticket Count: {len(matches)}")
    log_lines.append(f"Matching Ticket IDs: {', '.join(matching_ids)}")
    if matching_ids != [ticket_id]:
        raise RuntimeError(f"Expected exactly the created ticket to match subject marker/run. Found: {matching_ids}")

    OUTPUT_LOG.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(f"Workflow complete. Ticket ID: {ticket_id}. Log: {OUTPUT_LOG}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        existing = OUTPUT_LOG.read_text(encoding="utf-8") if OUTPUT_LOG.exists() else ""
        OUTPUT_LOG.write_text(f"{existing}ERROR: {exc}\n", encoding="utf-8")
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
