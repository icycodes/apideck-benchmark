"""Final-state verification for ticket_bulk_close_by_run.

After the agent runs, we expect:
  * Exactly 5 tickets in the Apideck Issue Tracking collection have a subject
    that contains ``ZEALT_RUN_ID``.
  * Every one of those tickets is in status ``closed``.
  * The output log lists the closed ticket ids on a ``Closed ticket ids:`` line.
"""

from __future__ import annotations

import os
import re
from typing import Any

import pytest
import requests

PROJECT_DIR = "/home/user/apideck_task"
LOG_FILE = os.path.join(PROJECT_DIR, "output.log")
APIDECK_BASE_URL = "https://unify.apideck.com"
SERVICE_ID = "github"
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
    pages = 0
    while True:
        pages += 1
        assert pages <= 50, (
            "List Tickets pagination exceeded 50 pages; aborting."
        )
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


@pytest.fixture(scope="module")
def run_scoped_tickets() -> list[dict[str, Any]]:
    run_id = _env("ZEALT_RUN_ID")
    all_tickets = _list_all_tickets()
    matching = [
        t
        for t in all_tickets
        if isinstance(t.get("subject"), str) and run_id in t["subject"]
    ]
    return matching


def test_output_log_exists_and_lists_closed_ids() -> None:
    assert os.path.isfile(LOG_FILE), (
        f"Expected output log at {LOG_FILE}, but it was not found."
    )
    with open(LOG_FILE, "r", encoding="utf-8") as fh:
        content = fh.read()
    match = re.search(r"Closed ticket ids:\s*([^\n]*)", content)
    assert match, (
        "Output log must contain a line of the form "
        "'Closed ticket ids: <comma_separated_ids>'."
    )
    ids_part = match.group(1).strip()
    reported_ids = [
        token.strip()
        for token in re.split(r"[,\s]+", ids_part)
        if token.strip()
    ]
    assert reported_ids, (
        "The 'Closed ticket ids:' log line must list at least one ticket id."
    )


def test_exactly_five_run_scoped_tickets_exist(
    run_scoped_tickets: list[dict[str, Any]],
) -> None:
    assert len(run_scoped_tickets) == EXPECTED_TICKETS, (
        f"Expected exactly {EXPECTED_TICKETS} tickets whose subject contains "
        f"ZEALT_RUN_ID, found {len(run_scoped_tickets)}. The agent must not "
        "create new run-scoped tickets."
    )


def test_all_run_scoped_tickets_are_closed(
    run_scoped_tickets: list[dict[str, Any]],
) -> None:
    not_closed = [
        {"id": t.get("id"), "status": t.get("status")}
        for t in run_scoped_tickets
        if t.get("status") != "closed"
    ]
    assert not not_closed, (
        "All run-scoped tickets must have status 'closed' after the agent "
        f"runs; still open/other: {not_closed}."
    )


def test_log_reports_every_closed_ticket(
    run_scoped_tickets: list[dict[str, Any]],
) -> None:
    with open(LOG_FILE, "r", encoding="utf-8") as fh:
        content = fh.read()
    match = re.search(r"Closed ticket ids:\s*([^\n]*)", content)
    assert match, "Missing 'Closed ticket ids:' line in output log."
    reported_ids = {
        token.strip()
        for token in re.split(r"[,\s]+", match.group(1))
        if token.strip()
    }
    expected_ids = {str(t.get("id")) for t in run_scoped_tickets}
    missing = expected_ids - reported_ids
    assert not missing, (
        "The output log's 'Closed ticket ids:' line must mention every "
        f"run-scoped ticket id. Missing: {sorted(missing)}."
    )
