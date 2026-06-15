import os
import re

import pytest
import requests

PROJECT_DIR = "/home/user/apideck_task"
LOG_FILE = os.path.join(PROJECT_DIR, "output.log")
UNIFY_BASE = "https://unify.apideck.com"
BENCH_TAG_PREFIX = "bench-"
MARKER = "[TAGS-APPLY]"


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    assert value, f"Required environment variable {name} is not set."
    return value


def _apideck_headers() -> dict:
    return {
        "Authorization": f"Bearer {_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": "github",
        "Accept": "application/json",
    }


def _collection_id() -> str:
    return _env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")


def _list_all_tags() -> list:
    url = f"{UNIFY_BASE}/issue-tracking/collections/{_collection_id()}/tags"
    headers = _apideck_headers()
    tags: list = []
    cursor = None
    for _ in range(20):
        params = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        response = requests.get(url, headers=headers, params=params, timeout=30)
        assert response.status_code == 200, (
            f"List Tags request failed: {response.status_code} {response.text}"
        )
        payload = response.json()
        data = payload.get("data") or []
        tags.extend(data)
        cursor = (payload.get("meta") or {}).get("cursors", {}).get("next")
        if not cursor:
            break
    return tags


def _list_all_tickets() -> list:
    url = f"{UNIFY_BASE}/issue-tracking/collections/{_collection_id()}/tickets"
    headers = _apideck_headers()
    tickets: list = []
    cursor = None
    for _ in range(50):
        params = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        response = requests.get(url, headers=headers, params=params, timeout=30)
        assert response.status_code == 200, (
            f"List Tickets request failed: {response.status_code} {response.text}"
        )
        payload = response.json()
        data = payload.get("data") or []
        tickets.extend(data)
        cursor = (payload.get("meta") or {}).get("cursors", {}).get("next")
        if not cursor:
            break
    return tickets


@pytest.fixture(scope="module")
def run_id() -> str:
    return _env("ZEALT_RUN_ID")


@pytest.fixture(scope="module")
def expected_tag_ids() -> set:
    tags = _list_all_tags()
    bench_tags = [
        t for t in tags
        if isinstance(t.get("name"), str) and t["name"].startswith(BENCH_TAG_PREFIX)
    ]
    if len(bench_tags) < 2:
        pytest.skip(
            "Prerequisite not met: fewer than two tags with prefix "
            f"'{BENCH_TAG_PREFIX}' exist in the configured collection. "
            "ApiDeck cannot create labels via the Issue Tracking API."
        )
    ids = {t["id"] for t in bench_tags if t.get("id")}
    assert len(ids) == len(bench_tags), (
        "Resolved bench- tags must all expose a unique id."
    )
    return ids


@pytest.fixture(scope="module")
def matching_ticket(run_id):
    tickets = _list_all_tickets()
    matched = [
        t for t in tickets
        if isinstance(t.get("subject"), str)
        and MARKER in t["subject"]
        and run_id in t["subject"]
    ]
    assert len(matched) == 1, (
        f"Expected exactly one ticket whose subject contains '{MARKER}' and "
        f"'{run_id}', found {len(matched)}: "
        f"{[t.get('subject') for t in matched]}"
    )
    return matched[0]


def test_ticket_subject_marker_and_run_id(matching_ticket, run_id):
    subject = matching_ticket.get("subject") or ""
    assert MARKER in subject, (
        f"Ticket subject must contain marker '{MARKER}', got: {subject!r}"
    )
    assert run_id in subject, (
        f"Ticket subject must contain run-id '{run_id}', got: {subject!r}"
    )


def test_ticket_tag_ids_match_bench_prefix_set(matching_ticket, expected_tag_ids):
    actual_tag_ids = {
        t.get("id") for t in (matching_ticket.get("tags") or [])
        if isinstance(t, dict) and t.get("id")
    }
    assert actual_tag_ids == expected_tag_ids, (
        "Ticket tags must equal the set of tag ids whose name starts with "
        f"'{BENCH_TAG_PREFIX}'. Expected: {sorted(expected_tag_ids)}, "
        f"got: {sorted(actual_tag_ids)}"
    )


def test_log_file_records_ticket_id(matching_ticket):
    assert os.path.isfile(LOG_FILE), f"Log file {LOG_FILE} does not exist."
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    ticket_id = matching_ticket.get("id")
    assert ticket_id, "Matching ticket must have an id."
    pattern = rf"Ticket ID:\s*{re.escape(str(ticket_id))}\b"
    assert re.search(pattern, content), (
        f"Log file must contain a line matching 'Ticket ID: {ticket_id}'. "
        f"Log contents: {content!r}"
    )
