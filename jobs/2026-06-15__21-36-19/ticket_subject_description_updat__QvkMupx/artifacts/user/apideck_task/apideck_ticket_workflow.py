#!/usr/bin/env python3
"""Create and revise one Apideck Issue Tracking ticket for the current ZEALT run."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BASE_URL = "https://unify.apideck.com"
SERVICE_ID = "github"
OUTPUT_LOG = Path("/home/user/apideck_task/output.log")
PENDING_TICKET_FILE = Path("/home/user/apideck_task/.pending_ticket_id")


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
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def request_json(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        error_payload = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with HTTP {exc.code}: {error_payload}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc}") from exc


def data_object(response: dict[str, Any]) -> dict[str, Any]:
    data = response.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected response.data object, got: {json.dumps(response, indent=2)}")
    return data


def ticket_id_from(response: dict[str, Any]) -> str:
    data = data_object(response)
    ticket_id = data.get("id")
    if not ticket_id:
        raise RuntimeError(f"Ticket response did not include data.id: {json.dumps(response, indent=2)}")
    return str(ticket_id)


def create_ticket() -> str:
    subject = f"[UPDATE-V1] Apideck ticket revision workflow {RUN_ID}"
    description = f"Initial draft for ZEALT run {RUN_ID}"
    response = request_json(
        "POST",
        f"/issue-tracking/collections/{urllib.parse.quote(COLLECTION_ID, safe='')}/tickets",
        {"subject": subject, "description": description},
    )
    return ticket_id_from(response)


def update_ticket(ticket_id: str) -> dict[str, Any]:
    subject = f"[UPDATE-V2] Apideck ticket revision workflow {RUN_ID}"
    description = f"Revised draft v2 for ZEALT run {RUN_ID}"
    # The live Apideck Issue Tracking PATCH schema rejects an `id` request-body field
    # even though the ticket id is required in the official unified endpoint path.
    return request_json(
        "PATCH",
        f"/issue-tracking/collections/{urllib.parse.quote(COLLECTION_ID, safe='')}/tickets/{urllib.parse.quote(ticket_id, safe='')}",
        {"subject": subject, "description": description},
    )


def list_all_tickets() -> list[dict[str, Any]]:
    tickets: list[dict[str, Any]] = []
    cursor: str | None = None
    encoded_collection_id = urllib.parse.quote(COLLECTION_ID, safe="")

    while True:
        path = f"/issue-tracking/collections/{encoded_collection_id}/tickets"
        if cursor:
            path = f"{path}?cursor={urllib.parse.quote(cursor, safe='')}"
        response = request_json("GET", path)
        data = response.get("data")
        if isinstance(data, list):
            tickets.extend(item for item in data if isinstance(item, dict))
        elif data is not None:
            raise RuntimeError(f"Expected list response.data from List Tickets, got: {json.dumps(response, indent=2)}")

        next_cursor = ((response.get("meta") or {}).get("cursors") or {}).get("next")
        if not next_cursor:
            break
        cursor = str(next_cursor)

    return tickets


def verify_ticket_state(ticket_id: str) -> None:
    # Give the GitHub-backed connector a short window to reflect the title/body update in list results.
    last_summary = ""
    for _ in range(8):
        tickets = list_all_tickets()
        v1_matches = [
            ticket for ticket in tickets
            if RUN_ID in str(ticket.get("subject", "")) and "[UPDATE-V1]" in str(ticket.get("subject", ""))
        ]
        v2_matches = [
            ticket for ticket in tickets
            if RUN_ID in str(ticket.get("subject", "")) and "[UPDATE-V2]" in str(ticket.get("subject", ""))
        ]
        logged_ticket = next((ticket for ticket in tickets if str(ticket.get("id")) == ticket_id), None)
        description = "" if logged_ticket is None else str(logged_ticket.get("description", ""))
        last_summary = (
            f"v1_matches={len(v1_matches)}, v2_matches={len(v2_matches)}, "
            f"logged_ticket_found={logged_ticket is not None}, description={description!r}"
        )
        if not v1_matches and len(v2_matches) == 1 and logged_ticket and "Revised draft v2" in description:
            return
        time.sleep(2)

    raise RuntimeError(f"Final verification failed: {last_summary}")


def existing_ticket_id() -> str | None:
    resume_id = os.environ.get("APIDECK_EXISTING_TICKET_ID")
    if resume_id:
        return resume_id.strip()
    if OUTPUT_LOG.exists():
        for line in OUTPUT_LOG.read_text(encoding="utf-8").splitlines():
            if line.startswith("Ticket ID:"):
                return line.split(":", 1)[1].strip()
    if PENDING_TICKET_FILE.exists():
        return PENDING_TICKET_FILE.read_text(encoding="utf-8").strip()
    return None


def main() -> int:
    ticket_id = existing_ticket_id()
    if not ticket_id:
        ticket_id = create_ticket()
        PENDING_TICKET_FILE.write_text(f"{ticket_id}\n", encoding="utf-8")

    update_ticket(ticket_id)
    OUTPUT_LOG.write_text(f"Ticket ID: {ticket_id}\n", encoding="utf-8")
    verify_ticket_state(ticket_id)
    if PENDING_TICKET_FILE.exists():
        PENDING_TICKET_FILE.unlink()
    print(f"Ticket ID: {ticket_id}")
    print(f"Wrote audit log to {OUTPUT_LOG}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
