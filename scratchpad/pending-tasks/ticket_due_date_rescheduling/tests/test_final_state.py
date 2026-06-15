import os
import re
from datetime import datetime, timezone

import pytest
import requests

PROJECT_DIR = "/home/user/apideck_task"
LOG_FILE = os.path.join(PROJECT_DIR, "output.log")

EXPECTED_DUE_DATE_ISO = "2026-10-22T00:00:00.000Z"
TICKET_MARKER = "[DUE-DATE]"

UNIFY_BASE = "https://unify.apideck.com"


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    assert value != "", f"Required environment variable {name} is not set."
    return value


def _apideck_headers() -> dict:
    return {
        "Authorization": f"Bearer {_required_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _required_env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _required_env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": "github",
        "Accept": "application/json",
    }


def _parse_iso(value: str) -> datetime:
    # Normalize trailing Z to +00:00 so fromisoformat accepts it.
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _list_all_tickets(collection_id: str) -> list:
    """Page through GET tickets and return every ticket as a list of dicts."""
    url = f"{UNIFY_BASE}/issue-tracking/collections/{collection_id}/tickets"
    headers = _apideck_headers()
    tickets: list = []
    cursor: str | None = None
    seen_cursors: set[str] = set()

    for _ in range(50):  # hard safety cap
        params: dict = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(url, headers=headers, params=params, timeout=60)
        assert resp.status_code == 200, (
            f"List Tickets failed: status={resp.status_code}, body={resp.text}"
        )
        body = resp.json()
        data = body.get("data") or []
        assert isinstance(data, list), f"Expected 'data' to be a list, got: {type(data)}"
        tickets.extend(data)

        meta = body.get("meta") or {}
        cursors = meta.get("cursors") or {}
        next_cursor = cursors.get("next")
        if not next_cursor:
            break
        if next_cursor in seen_cursors:
            break
        seen_cursors.add(next_cursor)
        cursor = next_cursor

    return tickets


@pytest.fixture(scope="session")
def matching_tickets() -> list:
    collection_id = _required_env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    run_id = _required_env("ZEALT_RUN_ID")
    tickets = _list_all_tickets(collection_id)
    matches = [
        t
        for t in tickets
        if isinstance(t, dict)
        and isinstance(t.get("subject"), str)
        and run_id in t["subject"]
        and TICKET_MARKER in t["subject"]
    ]
    return matches


def test_log_file_exists():
    assert os.path.isfile(LOG_FILE), f"Log file {LOG_FILE} not found."


def test_log_file_contains_ticket_id():
    with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    match = re.search(r"^Ticket ID:\s*(\S+)\s*$", content, re.MULTILINE)
    assert match is not None, (
        "Log file must contain a line of the form 'Ticket ID: <ticket_id>'. "
        f"Content was:\n{content}"
    )
    ticket_id = match.group(1).strip()
    assert ticket_id != "", "Ticket ID logged in output.log is empty."


def test_exactly_one_matching_ticket(matching_tickets: list):
    assert len(matching_tickets) == 1, (
        "Expected exactly ONE ticket whose subject contains both ZEALT_RUN_ID and "
        f"'{TICKET_MARKER}', found {len(matching_tickets)}. "
        f"Subjects: {[t.get('subject') for t in matching_tickets]}"
    )


def test_matching_ticket_due_date_is_rescheduled(matching_tickets: list):
    assert len(matching_tickets) == 1, (
        "Cannot verify due_date: expected exactly one matching ticket, "
        f"found {len(matching_tickets)}."
    )
    ticket = matching_tickets[0]
    due_date_raw = ticket.get("due_date")
    assert isinstance(due_date_raw, str) and due_date_raw.strip() != "", (
        f"Matching ticket has no due_date set. Ticket: {ticket}"
    )
    actual = _parse_iso(due_date_raw)
    expected = _parse_iso(EXPECTED_DUE_DATE_ISO)
    assert actual == expected, (
        f"Ticket due_date mismatch. Expected {expected.isoformat()} "
        f"(from {EXPECTED_DUE_DATE_ISO}), got {actual.isoformat()} (raw {due_date_raw!r})."
    )


def test_logged_ticket_id_matches_remote_ticket(matching_tickets: list):
    assert len(matching_tickets) == 1, (
        "Cannot verify logged Ticket ID: expected exactly one matching ticket, "
        f"found {len(matching_tickets)}."
    )
    with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    match = re.search(r"^Ticket ID:\s*(\S+)\s*$", content, re.MULTILINE)
    assert match is not None, "Log file missing 'Ticket ID:' line."
    logged_id = match.group(1).strip()

    ticket = matching_tickets[0]
    remote_id = ticket.get("id")
    assert isinstance(remote_id, str) and remote_id != "", (
        f"Matching ticket missing 'id' field: {ticket}"
    )
    assert logged_id == remote_id, (
        f"Logged Ticket ID '{logged_id}' does not match remote ticket id '{remote_id}'."
    )
