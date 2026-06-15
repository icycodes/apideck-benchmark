import json
import os
import time

import pytest
import requests

PROJECT_DIR = "/home/user/apideck_task"
LOG_FILE = os.path.join(PROJECT_DIR, "output.log")

APIDECK_BASE = "https://unify.apideck.com"
SERVICE_ID = "github"


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    assert value, f"Required environment variable {name} is not set."
    return value


def _apideck_headers() -> dict:
    return {
        "Authorization": f"Bearer {_required_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _required_env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _required_env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": SERVICE_ID,
        "Accept": "application/json",
    }


def _request_with_retries(method: str, url: str, **kwargs):
    last_exc = None
    for attempt in range(4):
        try:
            response = requests.request(method, url, timeout=60, **kwargs)
            if response.status_code < 500:
                return response
            last_exc = AssertionError(
                f"{method} {url} returned server error {response.status_code}: {response.text}"
            )
        except requests.RequestException as exc:
            last_exc = exc
        time.sleep(2 ** attempt)
    raise AssertionError(f"Request to {url} failed after retries: {last_exc}")


@pytest.fixture(scope="module")
def collection_id() -> str:
    return _required_env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")


@pytest.fixture(scope="module")
def run_id() -> str:
    return _required_env("ZEALT_RUN_ID")


@pytest.fixture(scope="module")
def expected_collection_name(collection_id: str) -> str:
    response = _request_with_retries(
        "GET",
        f"{APIDECK_BASE}/issue-tracking/collections",
        headers=_apideck_headers(),
        params={"limit": 200},
    )
    assert response.status_code == 200, (
        f"Listing collections failed with {response.status_code}: {response.text}"
    )
    body = response.json()
    data = body.get("data", [])
    assert isinstance(data, list) and data, (
        f"Expected non-empty 'data' array from List Collections, got: {body!r}"
    )
    match = next((c for c in data if c.get("id") == collection_id), None)
    assert match is not None, (
        f"Configured collection id {collection_id!r} not found in List Collections response. "
        f"Returned ids: {[c.get('id') for c in data]!r}"
    )
    name = match.get("name")
    assert isinstance(name, str) and name.strip(), (
        f"Collection {collection_id!r} did not expose a non-empty 'name'. Object: {match!r}"
    )
    return name


@pytest.fixture(scope="module")
def output_log() -> dict:
    assert os.path.isfile(LOG_FILE), f"Expected log file {LOG_FILE} to exist."
    with open(LOG_FILE) as f:
        raw = f.read().strip()
    assert raw, f"Log file {LOG_FILE} is empty."
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"Log file {LOG_FILE} is not valid JSON: {exc}; contents: {raw!r}"
        )
    assert isinstance(payload, dict), (
        f"Log file {LOG_FILE} must contain a JSON object, got: {type(payload).__name__}"
    )
    for key in ("collection_name", "ticket_id"):
        assert key in payload, f"Log file {LOG_FILE} is missing required field '{key}'."
        assert isinstance(payload[key], str) and payload[key].strip(), (
            f"Log field '{key}' must be a non-empty string, got: {payload[key]!r}"
        )
    return payload


def test_collection_name_matches_lookup(output_log: dict, expected_collection_name: str):
    assert output_log["collection_name"] == expected_collection_name, (
        f"Logged collection_name {output_log['collection_name']!r} does not match "
        f"the name returned by ApiDeck ({expected_collection_name!r})."
    )


def test_exactly_one_matching_ticket(
    output_log: dict,
    expected_collection_name: str,
    collection_id: str,
    run_id: str,
):
    expected_subject = f"COLLNAME-{run_id}-{expected_collection_name}"

    headers = _apideck_headers()
    url = f"{APIDECK_BASE}/issue-tracking/collections/{collection_id}/tickets"

    matches: list[dict] = []
    cursor: str | None = None
    seen_cursors: set[str] = set()

    while True:
        params: dict = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        response = _request_with_retries("GET", url, headers=headers, params=params)
        assert response.status_code == 200, (
            f"Listing tickets failed with {response.status_code}: {response.text}"
        )
        body = response.json()
        for ticket in body.get("data", []) or []:
            if ticket.get("subject") == expected_subject:
                matches.append(ticket)

        next_cursor = (
            (body.get("meta") or {}).get("cursors", {}).get("next")
        )
        if not next_cursor or next_cursor in seen_cursors:
            break
        seen_cursors.add(next_cursor)
        cursor = next_cursor

    assert len(matches) == 1, (
        f"Expected exactly one ticket with subject {expected_subject!r} in collection "
        f"{collection_id!r}, found {len(matches)}: {[m.get('id') for m in matches]!r}"
    )
    assert matches[0].get("id") == output_log["ticket_id"], (
        f"Logged ticket_id {output_log['ticket_id']!r} does not match the id of the "
        f"matching ticket ({matches[0].get('id')!r})."
    )
