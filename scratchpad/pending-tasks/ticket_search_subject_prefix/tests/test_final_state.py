import json
import os
from typing import Any

import pytest
import requests


PROJECT_DIR = "/home/user/apideck_task"
LOG_FILE = os.path.join(PROJECT_DIR, "output.log")
APIDECK_BASE_URL = "https://unify.apideck.com"
SERVICE_ID = "github"
PAGE_LIMIT = 200
MAX_PAGES = 50  # safety guard for cursor pagination


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    assert value, f"Required environment variable {name} is not set."
    return value


def _apideck_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": SERVICE_ID,
        "Accept": "application/json",
    }


def _list_all_tickets() -> list[dict[str, Any]]:
    collection_id = _env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    url = f"{APIDECK_BASE_URL}/issue-tracking/collections/{collection_id}/tickets"
    headers = _apideck_headers()
    params: dict[str, Any] = {"limit": PAGE_LIMIT}
    tickets: list[dict[str, Any]] = []
    seen_cursors: set[str] = set()

    for _ in range(MAX_PAGES):
        response = requests.get(url, headers=headers, params=params, timeout=60)
        assert response.status_code == 200, (
            f"List Tickets failed with status {response.status_code}: {response.text}"
        )
        payload = response.json()
        data = payload.get("data") or []
        tickets.extend(data)
        cursors = (payload.get("meta") or {}).get("cursors") or {}
        next_cursor = cursors.get("next")
        if not next_cursor or next_cursor in seen_cursors:
            break
        seen_cursors.add(next_cursor)
        params = {"limit": PAGE_LIMIT, "cursor": next_cursor}
    else:
        pytest.fail(
            f"Exceeded {MAX_PAGES} cursor pages while listing tickets; aborting to avoid infinite loop."
        )

    return tickets


@pytest.fixture(scope="module")
def log_payload() -> dict[str, Any]:
    assert os.path.isfile(LOG_FILE), f"Log file {LOG_FILE} does not exist."
    with open(LOG_FILE, "r", encoding="utf-8") as fh:
        raw = fh.read().strip()
    assert raw, f"Log file {LOG_FILE} is empty."
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        pytest.fail(f"Log file {LOG_FILE} does not contain valid JSON: {exc}")
    assert isinstance(data, dict), f"Log JSON must be an object, got: {type(data).__name__}"
    return data


@pytest.fixture(scope="module")
def all_tickets() -> list[dict[str, Any]]:
    return _list_all_tickets()


def test_log_has_expected_shape(log_payload: dict[str, Any]):
    assert set(log_payload.keys()) == {"matching_ids", "other_ids"}, (
        f"Log JSON must have exactly keys 'matching_ids' and 'other_ids', got: {sorted(log_payload.keys())}"
    )
    matching_ids = log_payload["matching_ids"]
    other_ids = log_payload["other_ids"]
    assert isinstance(matching_ids, list) and all(isinstance(x, str) for x in matching_ids), (
        "'matching_ids' must be a list of strings."
    )
    assert isinstance(other_ids, list) and all(isinstance(x, str) for x in other_ids), (
        "'other_ids' must be a list of strings."
    )
    assert len(matching_ids) == 4, f"Expected 4 matching_ids, got {len(matching_ids)}: {matching_ids}"
    assert len(other_ids) == 2, f"Expected 2 other_ids, got {len(other_ids)}: {other_ids}"
    assert len(set(matching_ids)) == 4, f"matching_ids contains duplicates: {matching_ids}"
    assert len(set(other_ids)) == 2, f"other_ids contains duplicates: {other_ids}"
    assert set(matching_ids).isdisjoint(set(other_ids)), (
        f"matching_ids and other_ids must be disjoint. matching_ids={matching_ids}, other_ids={other_ids}"
    )


def test_apideck_state_matches_log(log_payload: dict[str, Any], all_tickets: list[dict[str, Any]]):
    run_id = _env("ZEALT_RUN_ID")
    match_prefix = f"SEARCH-MATCH-{run_id}-"
    other_prefix = f"SEARCH-OTHER-{run_id}-"

    actual_matching = {
        str(t["id"])
        for t in all_tickets
        if isinstance(t.get("subject"), str)
        and t["subject"].startswith(match_prefix)
        and t.get("id") is not None
    }
    actual_other = {
        str(t["id"])
        for t in all_tickets
        if isinstance(t.get("subject"), str)
        and t["subject"].startswith(other_prefix)
        and t.get("id") is not None
    }

    assert len(actual_matching) == 4, (
        f"Expected exactly 4 tickets whose subject starts with {match_prefix!r}, found {len(actual_matching)}: {sorted(actual_matching)}"
    )
    assert len(actual_other) == 2, (
        f"Expected exactly 2 tickets whose subject starts with {other_prefix!r}, found {len(actual_other)}: {sorted(actual_other)}"
    )

    expected_matching = {str(x) for x in log_payload["matching_ids"]}
    expected_other = {str(x) for x in log_payload["other_ids"]}

    assert expected_matching == actual_matching, (
        f"Logged matching_ids do not match ApiDeck state. logged={sorted(expected_matching)}, actual={sorted(actual_matching)}"
    )
    assert expected_other == actual_other, (
        f"Logged other_ids do not match ApiDeck state. logged={sorted(expected_other)}, actual={sorted(actual_other)}"
    )
