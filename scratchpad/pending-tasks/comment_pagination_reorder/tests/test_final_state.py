import os
import re

import pytest
import requests

PROJECT_DIR = "/home/user/apideck_task"
LOG_FILE = os.path.join(PROJECT_DIR, "output.log")

PAGE_LINE_RE = re.compile(r"^PAGE\s+(\d+)\s+items=(\d+)\s*$", re.MULTILINE)


def _headers():
    return {
        "Authorization": f"Bearer {os.environ['APIDECK_API_KEY']}",
        "x-apideck-app-id": os.environ["APIDECK_APP_ID"],
        "x-apideck-consumer-id": os.environ["APIDECK_CONSUMER_ID"],
        "x-apideck-service-id": "github",
        "Accept": "application/json",
    }


def _list_all_tickets():
    collection_id = os.environ["APIDECK_ISSUE_TRACKING_COLLECTION_ID"]
    url = f"https://unify.apideck.com/issue-tracking/collections/{collection_id}/tickets"
    cursor = None
    tickets = []
    for _ in range(50):
        params = {"limit": 50}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(url, headers=_headers(), params=params, timeout=60)
        assert resp.status_code == 200, (
            f"List Tickets failed with status {resp.status_code}: {resp.text}"
        )
        payload = resp.json()
        tickets.extend(payload.get("data", []) or [])
        cursor = (payload.get("meta") or {}).get("cursors", {}).get("next")
        if not cursor:
            break
    return tickets


def _find_target_ticket():
    run_id = os.environ["ZEALT_RUN_ID"]
    matches = [
        t
        for t in _list_all_tickets()
        if isinstance(t, dict) and run_id in (t.get("subject") or "")
    ]
    assert len(matches) == 1, (
        f"Expected exactly one ticket whose subject contains '{run_id}', "
        f"found {len(matches)}."
    )
    return matches[0]


def _list_all_comments_paginated(ticket_id, page_limit=5):
    """List comments using cursor pagination and return (comments, page_count)."""
    collection_id = os.environ["APIDECK_ISSUE_TRACKING_COLLECTION_ID"]
    url = (
        f"https://unify.apideck.com/issue-tracking/collections/"
        f"{collection_id}/tickets/{ticket_id}/comments"
    )
    cursor = None
    comments = []
    page_count = 0
    for _ in range(50):
        params = {"limit": page_limit}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(url, headers=_headers(), params=params, timeout=60)
        assert resp.status_code == 200, (
            f"List Comments failed with status {resp.status_code}: {resp.text}"
        )
        payload = resp.json()
        data = payload.get("data", []) or []
        comments.extend(data)
        page_count += 1
        cursor = (payload.get("meta") or {}).get("cursors", {}).get("next")
        if not cursor:
            break
    return comments, page_count


def test_log_file_exists():
    assert os.path.isfile(LOG_FILE), f"Log file {LOG_FILE} not found."


def test_log_file_contains_pagination_lines():
    with open(LOG_FILE) as f:
        content = f.read()
    matches = PAGE_LINE_RE.findall(content)
    assert len(matches) >= 2, (
        "Expected log file to contain at least two 'PAGE <n> items=<count>' "
        f"lines proving multi-page pagination, got matches: {matches}\n"
        f"Log content:\n{content}"
    )


def test_target_ticket_has_twelve_run_id_comments():
    run_id = os.environ["ZEALT_RUN_ID"]
    ticket = _find_target_ticket()
    ticket_id = ticket.get("id")
    assert ticket_id, f"Target ticket has no id: {ticket}"

    comments, page_count = _list_all_comments_paginated(ticket_id, page_limit=5)
    assert page_count >= 2, (
        f"Cursor pagination with limit=5 returned only {page_count} page(s); "
        "expected multiple pages."
    )

    expected_bodies = {f"COMMENT-{run_id}-{n}" for n in range(1, 13)}
    bodies = [
        (c.get("body") or "")
        for c in comments
        if isinstance(c, dict)
    ]

    body_counts = {}
    for b in bodies:
        if b in expected_bodies:
            body_counts[b] = body_counts.get(b, 0) + 1

    missing = sorted(expected_bodies - set(body_counts.keys()))
    assert not missing, (
        f"Missing expected comment bodies: {missing}. "
        f"Found bodies: {bodies}"
    )

    duplicates = {b: c for b, c in body_counts.items() if c != 1}
    assert not duplicates, (
        f"Each expected body should appear exactly once. Duplicates: {duplicates}"
    )


def test_comments_have_unique_ids():
    ticket = _find_target_ticket()
    ticket_id = ticket.get("id")
    assert ticket_id, f"Target ticket has no id: {ticket}"
    comments, _ = _list_all_comments_paginated(ticket_id, page_limit=5)
    ids = [c.get("id") for c in comments if isinstance(c, dict) and c.get("id")]
    assert len(ids) == len(set(ids)), (
        f"Comment IDs are not unique: {ids}"
    )
