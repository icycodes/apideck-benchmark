import os
import re
from typing import Any, Dict, List, Optional

import pytest
import requests

UNIFY_BASE_URL = "https://unify.apideck.com"
LOG_FILE_PATH = "/home/user/apideck_task/output.log"
SERVICE_ID = "github"

MARKER_V1 = "[UPDATE-V1]"
MARKER_V2 = "[UPDATE-V2]"
EXPECTED_DESCRIPTION_SUBSTRING = "Revised draft v2"


def _required_env(var: str) -> str:
    value = os.environ.get(var)
    assert value is not None and value != "", (
        f"Environment variable {var} must be set for the verifier to run."
    )
    return value


def _apideck_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {_required_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _required_env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _required_env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": SERVICE_ID,
        "Accept": "application/json",
    }


def _list_all_tickets() -> List[Dict[str, Any]]:
    collection_id = _required_env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    url = f"{UNIFY_BASE_URL}/issue-tracking/collections/{collection_id}/tickets"
    headers = _apideck_headers()
    cursor: Optional[str] = None
    tickets: List[Dict[str, Any]] = []
    seen_cursors = set()
    for _ in range(50):  # hard pagination cap to avoid runaway loops
        params: Dict[str, Any] = {"limit": 200}
        if cursor is not None:
            params["cursor"] = cursor
        response = requests.get(url, headers=headers, params=params, timeout=60)
        assert response.status_code == 200, (
            f"List Tickets call failed: HTTP {response.status_code} — {response.text}"
        )
        payload = response.json()
        data = payload.get("data") or []
        assert isinstance(data, list), (
            f"List Tickets response `data` must be a list, got {type(data).__name__}: {payload}"
        )
        tickets.extend(data)
        meta = payload.get("meta") or {}
        cursors = meta.get("cursors") or {}
        next_cursor = cursors.get("next")
        if not next_cursor:
            break
        if next_cursor in seen_cursors:
            break
        seen_cursors.add(next_cursor)
        cursor = next_cursor
    return tickets


def _read_ticket_id_from_log() -> str:
    assert os.path.isfile(LOG_FILE_PATH), (
        f"Expected log file {LOG_FILE_PATH} to exist after the task is executed."
    )
    with open(LOG_FILE_PATH, "r", encoding="utf-8") as fh:
        content = fh.read()
    match = re.search(r"Ticket ID:\s*(\S+)", content)
    assert match is not None, (
        f"Log file {LOG_FILE_PATH} must contain a line matching `Ticket ID: <ticket_id>`. "
        f"Got:\n{content}"
    )
    ticket_id = match.group(1).strip().rstrip(",;")
    assert ticket_id, "Captured Ticket ID from the log file is empty."
    return ticket_id


def _subject_matches(subject: Optional[str], marker: str, run_id: str) -> bool:
    if not isinstance(subject, str):
        return False
    return marker in subject and run_id in subject


def test_log_file_contains_ticket_id():
    ticket_id = _read_ticket_id_from_log()
    assert ticket_id, "Ticket ID extracted from the log file must be non-empty."


def test_exactly_one_v2_ticket_exists_for_run():
    run_id = _required_env("ZEALT_RUN_ID")
    ticket_id_from_log = _read_ticket_id_from_log()
    tickets = _list_all_tickets()
    matching_v2 = [t for t in tickets if _subject_matches(t.get("subject"), MARKER_V2, run_id)]
    assert len(matching_v2) == 1, (
        f"Expected exactly one ticket whose subject contains both `{MARKER_V2}` and `{run_id}`, "
        f"got {len(matching_v2)}: {[t.get('subject') for t in matching_v2]}"
    )
    assert matching_v2[0].get("id") == ticket_id_from_log, (
        f"The single ticket bearing `{MARKER_V2}` and `{run_id}` must have id `{ticket_id_from_log}` "
        f"from the log; got `{matching_v2[0].get('id')}`."
    )


def test_no_v1_ticket_remains_for_run():
    run_id = _required_env("ZEALT_RUN_ID")
    tickets = _list_all_tickets()
    matching_v1 = [t for t in tickets if _subject_matches(t.get("subject"), MARKER_V1, run_id)]
    assert matching_v1 == [], (
        f"Expected no remaining ticket whose subject contains both `{MARKER_V1}` and `{run_id}` "
        f"after the update workflow, but found {len(matching_v1)}: "
        f"{[t.get('subject') for t in matching_v1]}"
    )


def test_ticket_subject_and_description_via_get():
    run_id = _required_env("ZEALT_RUN_ID")
    ticket_id = _read_ticket_id_from_log()
    collection_id = _required_env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    url = (
        f"{UNIFY_BASE_URL}/issue-tracking/collections/{collection_id}"
        f"/tickets/{ticket_id}"
    )
    response = requests.get(url, headers=_apideck_headers(), timeout=60)
    assert response.status_code == 200, (
        f"Get Ticket call for `{ticket_id}` failed: HTTP {response.status_code} — {response.text}"
    )
    payload = response.json()
    data = payload.get("data") or {}
    assert isinstance(data, dict), (
        f"Get Ticket response `data` must be an object, got {type(data).__name__}: {payload}"
    )
    subject = data.get("subject")
    assert _subject_matches(subject, MARKER_V2, run_id), (
        f"Ticket `{ticket_id}` subject must contain both `{MARKER_V2}` and `{run_id}`. "
        f"Got: {subject!r}"
    )
    description = data.get("description") or ""
    assert isinstance(description, str) and EXPECTED_DESCRIPTION_SUBSTRING in description, (
        f"Ticket `{ticket_id}` description must contain the substring "
        f"`{EXPECTED_DESCRIPTION_SUBSTRING}`. Got: {description!r}"
    )
