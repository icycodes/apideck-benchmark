import os
import re
from typing import Any

import pytest
import requests


PROJECT_DIR = "/home/user/apideck_task"
LOG_FILE = os.path.join(PROJECT_DIR, "output.log")
UNIFY_BASE = "https://unify.apideck.com"
SERVICE_ID = "github"
SUBJECT_MARKER = "[USER-ASSIGN]"


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    assert value, f"Environment variable {name} must be set for verification."
    return value


def _apideck_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": SERVICE_ID,
        "Accept": "application/json",
    }


def _paginate(url: str) -> list[dict[str, Any]]:
    """Walk Apideck cursor pagination and return all items in `data`."""
    items: list[dict[str, Any]] = []
    cursor: str | None = None
    seen_cursors: set[str] = set()
    for _ in range(50):  # hard safety cap
        params: dict[str, Any] = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(url, headers=_apideck_headers(), params=params, timeout=60)
        assert resp.status_code == 200, (
            f"GET {url} failed: status={resp.status_code}, body={resp.text[:500]}"
        )
        body = resp.json()
        data = body.get("data") or []
        assert isinstance(data, list), f"Expected list in 'data' from {url}, got {type(data)}"
        items.extend(data)
        next_cursor = (
            body.get("meta", {}).get("cursors", {}).get("next")
            if isinstance(body.get("meta"), dict)
            else None
        )
        if not next_cursor or next_cursor in seen_cursors:
            break
        seen_cursors.add(next_cursor)
        cursor = next_cursor
    return items


@pytest.fixture(scope="module")
def run_id() -> str:
    return _env("ZEALT_RUN_ID")


@pytest.fixture(scope="module")
def collection_id() -> str:
    return _env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")


@pytest.fixture(scope="module")
def logged_ticket_id() -> str:
    assert os.path.isfile(LOG_FILE), f"Log file {LOG_FILE} does not exist."
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"Ticket ID:\s*(\S+)", content)
    assert match, (
        f"Expected a line matching 'Ticket ID: <ticket_id>' in {LOG_FILE}, got:\n{content}"
    )
    return match.group(1).strip()


@pytest.fixture(scope="module")
def expected_assignee_id(collection_id: str) -> str:
    users = _paginate(f"{UNIFY_BASE}/issue-tracking/collections/{collection_id}/users")
    assert users, (
        "The Apideck Users endpoint returned no users for the configured collection; "
        "cannot determine the expected assignee."
    )
    ids = [str(u["id"]) for u in users if isinstance(u, dict) and u.get("id")]
    assert ids, f"No user objects with an 'id' field were returned. Raw users: {users[:3]}"
    return min(ids)


def test_log_file_records_ticket_id(logged_ticket_id: str):
    assert logged_ticket_id, "Logged ticket id must be a non-empty string."


def test_exactly_one_ticket_with_marker(
    collection_id: str, run_id: str, logged_ticket_id: str
):
    tickets = _paginate(
        f"{UNIFY_BASE}/issue-tracking/collections/{collection_id}/tickets"
    )
    matches = [
        t
        for t in tickets
        if isinstance(t, dict)
        and isinstance(t.get("subject"), str)
        and SUBJECT_MARKER in t["subject"]
        and run_id in t["subject"]
    ]
    assert len(matches) == 1, (
        f"Expected exactly 1 ticket whose subject contains both '{SUBJECT_MARKER}' "
        f"and ZEALT_RUN_ID='{run_id}', found {len(matches)}: "
        f"{[m.get('subject') for m in matches]}"
    )
    matched_id = str(matches[0].get("id"))
    assert matched_id == logged_ticket_id, (
        f"The matching ticket id ({matched_id}) does not equal the id recorded in "
        f"the log file ({logged_ticket_id})."
    )


def test_ticket_assignee_matches_directory_min(
    collection_id: str, logged_ticket_id: str, expected_assignee_id: str
):
    url = (
        f"{UNIFY_BASE}/issue-tracking/collections/{collection_id}/tickets/"
        f"{logged_ticket_id}"
    )
    resp = requests.get(url, headers=_apideck_headers(), timeout=60)
    assert resp.status_code == 200, (
        f"GET {url} failed: status={resp.status_code}, body={resp.text[:500]}"
    )
    data = resp.json().get("data") or {}
    assignees = data.get("assignees") or []
    assert isinstance(assignees, list), (
        f"Expected ticket.assignees to be a list, got {type(assignees)}: {assignees}"
    )
    assert len(assignees) == 1, (
        f"Expected exactly 1 assignee on the ticket, got {len(assignees)}: {assignees}"
    )
    actual_id = str(assignees[0].get("id"))
    assert actual_id == expected_assignee_id, (
        f"Ticket assignee id ({actual_id}) does not match the lexicographically "
        f"smallest user id from the directory ({expected_assignee_id})."
    )
