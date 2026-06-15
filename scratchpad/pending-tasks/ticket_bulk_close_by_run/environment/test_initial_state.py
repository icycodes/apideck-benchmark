"""Initial-state setup and verification for ticket_bulk_close_by_run.

Before the agent starts working, this test:
  1. Verifies that the Python HTTP client and the project directory are ready.
  2. Verifies that all Apideck environment variables are present.
  3. Seeds the Apideck Issue Tracking collection with exactly 5 open tickets whose
     subjects each contain ``ZEALT_RUN_ID`` and the ``[BULK-CLOSE]`` marker.
  4. Confirms those seeded tickets are visible via the API in ``open`` state.
"""

from __future__ import annotations

import os
import shutil
import time
from typing import Any

import pytest
import requests

PROJECT_DIR = "/home/user/apideck_task"
APIDECK_BASE_URL = "https://unify.apideck.com"
SERVICE_ID = "github"
MARKER = "[BULK-CLOSE]"
EXPECTED_TICKETS = 5


def _env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"Required environment variable {name} is not set."
    return value


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": SERVICE_ID,
        "Content-Type": "application/json",
    }


def _list_all_tickets() -> list[dict[str, Any]]:
    collection_id = _env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    url = (
        f"{APIDECK_BASE_URL}/issue-tracking/collections/{collection_id}/tickets"
    )
    tickets: list[dict[str, Any]] = []
    params: dict[str, Any] = {"limit": 200}
    while True:
        resp = requests.get(url, headers=_headers(), params=params, timeout=60)
        assert resp.status_code == 200, (
            f"List Tickets failed: status={resp.status_code}, body={resp.text}"
        )
        payload = resp.json()
        tickets.extend(payload.get("data", []) or [])
        next_cursor = (
            (payload.get("meta") or {}).get("cursors", {}).get("next")
        )
        if not next_cursor:
            break
        params = {"limit": 200, "cursor": next_cursor}
    return tickets


def _create_ticket(subject: str) -> str:
    collection_id = _env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    url = (
        f"{APIDECK_BASE_URL}/issue-tracking/collections/{collection_id}/tickets"
    )
    body = {
        "subject": subject,
        "description": (
            "Auto-generated bulk-close seed ticket. Close via PATCH when "
            "the run-id matches."
        ),
        "status": "open",
        "type": "task",
    }
    resp = requests.post(url, headers=_headers(), json=body, timeout=60)
    assert resp.status_code in (200, 201), (
        f"Create Ticket failed for subject={subject!r}: "
        f"status={resp.status_code}, body={resp.text}"
    )
    payload = resp.json()
    data = payload.get("data") or {}
    ticket_id = data.get("id")
    assert ticket_id, f"Create Ticket response missing data.id: {payload}"
    return ticket_id


def test_requests_library_available() -> None:
    assert requests is not None, "The requests library must be importable."


def test_curl_available() -> None:
    assert shutil.which("curl") is not None, "curl must be available in PATH."


def test_project_directory_exists() -> None:
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} must exist."
    )


def test_apideck_environment_present() -> None:
    for var in (
        "APIDECK_APP_ID",
        "APIDECK_API_KEY",
        "APIDECK_CONSUMER_ID",
        "APIDECK_ISSUE_TRACKING_COLLECTION_ID",
        "ZEALT_RUN_ID",
    ):
        assert os.environ.get(var), f"Environment variable {var} must be set."


def test_seed_open_tickets_for_run() -> None:
    """Create exactly 5 open tickets tagged with the current run id."""

    run_id = _env("ZEALT_RUN_ID")

    existing = _list_all_tickets()
    matching = [
        t
        for t in existing
        if isinstance(t.get("subject"), str) and run_id in t["subject"]
    ]
    # Idempotent re-runs: if seeds already exist, that's fine.
    if len(matching) >= EXPECTED_TICKETS:
        pytest.skip(
            f"{len(matching)} run-scoped tickets already exist; skipping seed."
        )

    needed = EXPECTED_TICKETS - len(matching)
    created_ids: list[str] = []
    for index in range(needed):
        subject = (
            f"{MARKER} bulk-close seed #{index + 1} run={run_id} "
            f"ts={int(time.time())}"
        )
        created_ids.append(_create_ticket(subject))

    assert len(created_ids) == needed, (
        f"Expected to create {needed} tickets, created {len(created_ids)}."
    )


def test_seeded_tickets_visible_and_open() -> None:
    run_id = _env("ZEALT_RUN_ID")
    tickets = _list_all_tickets()
    matching = [
        t
        for t in tickets
        if isinstance(t.get("subject"), str) and run_id in t["subject"]
    ]
    assert len(matching) == EXPECTED_TICKETS, (
        f"Expected exactly {EXPECTED_TICKETS} run-scoped tickets after seeding,"
        f" found {len(matching)}."
    )
    for ticket in matching:
        assert ticket.get("status") == "open", (
            f"Seeded ticket id={ticket.get('id')} should be open, "
            f"got status={ticket.get('status')!r}."
        )
