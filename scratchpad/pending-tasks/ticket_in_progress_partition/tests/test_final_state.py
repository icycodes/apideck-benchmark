import os
import re

import pytest
import requests


PROJECT_DIR = "/home/user/apideck_task"
LOG_FILE = os.path.join(PROJECT_DIR, "output.log")
UNIFY_BASE = "https://unify.apideck.com"
SERVICE_ID = "github"
PARTITION_MARKER = "[PARTITION]"
EXPECTED_TICKET_COUNT = 6
ALLOWED_STATUSES = {"in_progress", "closed"}

LOG_LINE_RE = re.compile(r"^Ticket (?P<ticket_id>\S+): (?P<status>in_progress|closed)$")


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    assert value, (
        f"Required environment variable {name} is not set in the verifier environment."
    )
    return value


def _apideck_headers() -> dict:
    return {
        "Authorization": f"Bearer {_required_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _required_env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _required_env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": SERVICE_ID,
        "Accept": "application/json",
    }


def _list_partition_tickets(collection_id: str, run_id: str) -> list:
    url = f"{UNIFY_BASE}/issue-tracking/collections/{collection_id}/tickets"
    cursor = None
    found = []
    for _ in range(20):
        params = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        response = requests.get(
            url, headers=_apideck_headers(), params=params, timeout=30
        )
        assert response.status_code == 200, (
            f"List Tickets failed: status={response.status_code}, body={response.text}"
        )
        payload = response.json() or {}
        for item in payload.get("data") or []:
            subject = item.get("subject") or ""
            if PARTITION_MARKER in subject and run_id in subject:
                found.append(item)
        cursor = ((payload.get("meta") or {}).get("cursors") or {}).get("next")
        if not cursor:
            break
    return found


@pytest.fixture(scope="session")
def run_id() -> str:
    return _required_env("ZEALT_RUN_ID")


@pytest.fixture(scope="session")
def collection_id() -> str:
    return _required_env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")


@pytest.fixture(scope="session")
def log_status_by_id() -> dict:
    assert os.path.isfile(LOG_FILE), (
        f"Expected log file at {LOG_FILE}; the task must write one "
        "`Ticket <id>: <status>` line per ticket."
    )
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        raw_lines = [line.rstrip("\n") for line in f.readlines()]

    nonempty = [line for line in raw_lines if line.strip()]
    assert len(nonempty) == EXPECTED_TICKET_COUNT, (
        f"Expected exactly {EXPECTED_TICKET_COUNT} non-empty lines in {LOG_FILE}, "
        f"got {len(nonempty)}: {nonempty!r}"
    )

    parsed: dict = {}
    for line in nonempty:
        match = LOG_LINE_RE.match(line)
        assert match, (
            f"Log line {line!r} does not match the required format "
            "'Ticket <ticket_id>: <in_progress|closed>'."
        )
        ticket_id = match.group("ticket_id")
        status = match.group("status")
        assert ticket_id not in parsed, (
            f"Ticket id {ticket_id!r} appears more than once in {LOG_FILE}."
        )
        parsed[ticket_id] = status

    return parsed


@pytest.fixture(scope="session")
def api_partition_tickets(collection_id: str, run_id: str) -> list:
    tickets = _list_partition_tickets(collection_id, run_id)
    return tickets


def test_exactly_six_partition_tickets_via_api(api_partition_tickets):
    ids = [t.get("id") for t in api_partition_tickets]
    assert len(api_partition_tickets) == EXPECTED_TICKET_COUNT, (
        f"Expected exactly {EXPECTED_TICKET_COUNT} tickets with subject containing "
        f"'{PARTITION_MARKER}' and the current ZEALT_RUN_ID, but found "
        f"{len(api_partition_tickets)}: {ids!r}."
    )


def test_log_ids_match_api_ids(api_partition_tickets, log_status_by_id):
    api_ids = {t.get("id") for t in api_partition_tickets}
    log_ids = set(log_status_by_id.keys())
    assert api_ids == log_ids, (
        "Ticket ids in the log file do not match the six '[PARTITION]' tickets "
        f"returned by the Apideck List Tickets API.\n"
        f"  Only in log:  {sorted(log_ids - api_ids)!r}\n"
        f"  Only in API:  {sorted(api_ids - log_ids)!r}"
    )


def test_status_partition_by_sorted_id(api_partition_tickets, log_status_by_id):
    sorted_tickets = sorted(api_partition_tickets, key=lambda t: t.get("id") or "")
    for index, ticket in enumerate(sorted_tickets, start=1):
        ticket_id = ticket.get("id")
        api_status = ticket.get("status")
        expected = "in_progress" if index % 2 == 1 else "closed"

        assert api_status == expected, (
            f"Ticket at sorted position {index} (id={ticket_id!r}) has API "
            f"status {api_status!r}, but expected {expected!r}."
        )
        log_status = log_status_by_id.get(ticket_id)
        assert log_status == expected, (
            f"Log file records status {log_status!r} for ticket id={ticket_id!r} "
            f"at sorted position {index}, but expected {expected!r}."
        )


def test_log_status_counts(log_status_by_id):
    in_progress = [tid for tid, s in log_status_by_id.items() if s == "in_progress"]
    closed = [tid for tid, s in log_status_by_id.items() if s == "closed"]
    assert len(in_progress) == 3, (
        f"Expected exactly 3 tickets logged with status 'in_progress', got "
        f"{len(in_progress)}: {in_progress!r}."
    )
    assert len(closed) == 3, (
        f"Expected exactly 3 tickets logged with status 'closed', got "
        f"{len(closed)}: {closed!r}."
    )
