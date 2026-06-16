import os
import re

import pytest
import requests

PROJECT_DIR = "/home/user/apideck_task"
LOG_FILE = os.path.join(PROJECT_DIR, "output.log")

APIDECK_BASE_URL = "https://unify.apideck.com"
MARKER = "[COMMENT-EDIT-DELETE]"


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    assert value, f"Required environment variable {name} is not set."
    return value


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": "github",
        "Accept": "application/json",
    }


def _get_paginated(url: str) -> list:
    items: list = []
    cursor = None
    seen_cursors: set = set()
    while True:
        params = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        response = requests.get(url, headers=_headers(), params=params, timeout=60)
        assert response.status_code == 200, (
            f"GET {url} returned {response.status_code}: {response.text}"
        )
        payload = response.json()
        items.extend(payload.get("data", []) or [])
        next_cursor = (
            (payload.get("meta") or {}).get("cursors", {}).get("next")
        )
        if not next_cursor or next_cursor in seen_cursors:
            break
        seen_cursors.add(next_cursor)
        cursor = next_cursor
    return items


@pytest.fixture(scope="session")
def run_id() -> str:
    return _env("ZEALT_RUN_ID")


@pytest.fixture(scope="session")
def collection_id() -> str:
    return _env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")


@pytest.fixture(scope="session")
def ticket_id_from_log() -> str:
    assert os.path.isfile(LOG_FILE), f"Log file {LOG_FILE} does not exist."
    with open(LOG_FILE, "r", encoding="utf-8") as fh:
        content = fh.read()
    match = re.search(r"Ticket ID:\s*(\S+)", content)
    assert match, (
        f"Log file {LOG_FILE} must contain a line like 'Ticket ID: <ticket_id>'."
    )
    return match.group(1).strip()


@pytest.fixture(scope="session")
def matching_ticket(run_id: str, collection_id: str, ticket_id_from_log: str) -> dict:
    url = f"{APIDECK_BASE_URL}/issue-tracking/collections/{collection_id}/tickets"
    tickets = _get_paginated(url)
    matches = [
        t
        for t in tickets
        if isinstance(t.get("subject"), str)
        and MARKER in t["subject"]
        and run_id in t["subject"]
    ]
    assert len(matches) == 1, (
        f"Expected exactly 1 ticket with marker '{MARKER}' and run id '{run_id}', "
        f"got {len(matches)}: subjects={[t.get('subject') for t in matches]}"
    )
    ticket = matches[0]
    assert ticket.get("id") == ticket_id_from_log, (
        f"Ticket id from log ({ticket_id_from_log}) does not match the discovered "
        f"ticket id ({ticket.get('id')})."
    )
    return ticket


def test_log_file_has_ticket_id(ticket_id_from_log: str):
    assert ticket_id_from_log, "Ticket ID missing from log file."


def test_exactly_one_marked_ticket(matching_ticket: dict):
    assert matching_ticket.get("id"), "Matching ticket has no id."


def test_final_comment_bodies(
    matching_ticket: dict, collection_id: str, run_id: str
):
    ticket_id = matching_ticket["id"]
    url = (
        f"{APIDECK_BASE_URL}/issue-tracking/collections/{collection_id}"
        f"/tickets/{ticket_id}/comments"
    )
    comments = _get_paginated(url)
    bodies = [c.get("body") for c in comments]

    assert len(comments) == 3, (
        f"Expected exactly 3 comments on the ticket, got {len(comments)}: bodies={bodies}"
    )

    expected = {
        f"A-{run_id}",
        f"B-EDITED-{run_id}",
        f"D-{run_id}",
    }
    actual = set(bodies)
    assert actual == expected, (
        f"Final comment body set mismatch. Expected {expected}, got {actual}."
    )

    forbidden = {f"B-{run_id}", f"C-{run_id}"}
    leftover = forbidden.intersection(actual)
    assert not leftover, (
        f"Forbidden original comment bodies still present: {leftover}"
    )
