import json
import os

import pytest
import requests


PROJECT_DIR = "/home/user/apideck_task"
LOG_FILE = os.path.join(PROJECT_DIR, "output.log")
UNIFY_BASE = "https://unify.apideck.com"
SERVICE_ID = "github"


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    assert value, f"Required environment variable {name} is not set."
    return value


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": SERVICE_ID,
        "Accept": "application/json",
    }


@pytest.fixture(scope="module")
def artifact() -> dict:
    assert os.path.isfile(LOG_FILE), f"Artifact log {LOG_FILE} does not exist."
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Artifact log {LOG_FILE} is not valid JSON: {exc}")
    assert isinstance(data, dict), "Artifact log must be a JSON object."
    for key in ("ticket_id", "subjects", "descriptions", "patch_statuses"):
        assert key in data, f"Artifact log missing required key: {key}"
    assert isinstance(data["ticket_id"], str) and data["ticket_id"], \
        "Artifact ticket_id must be a non-empty string."
    return data


def test_artifact_log_is_valid(artifact):
    assert isinstance(artifact["subjects"], list) and len(artifact["subjects"]) >= 1, \
        "Artifact 'subjects' must be a non-empty list."
    assert isinstance(artifact["descriptions"], list) and len(artifact["descriptions"]) >= 1, \
        "Artifact 'descriptions' must be a non-empty list."
    statuses = artifact["patch_statuses"]
    assert isinstance(statuses, dict), "patch_statuses must be an object."
    for key in ("subject", "description"):
        assert key in statuses and isinstance(statuses[key], list), \
            f"patch_statuses.{key} must be a list."


def test_final_subject_and_description_match(artifact):
    run_id = _env("ZEALT_RUN_ID")
    collection_id = _env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    ticket_id = artifact["ticket_id"]
    expected_subject = f"FINAL-SUBJECT-{run_id}-[FIELD-AUDIT]"
    expected_description = f"FINAL-DESCRIPTION-{run_id}"

    url = f"{UNIFY_BASE}/issue-tracking/collections/{collection_id}/tickets/{ticket_id}"
    response = requests.get(url, headers=_headers(), timeout=60)
    assert response.status_code == 200, \
        f"GET ticket failed: status={response.status_code}, body={response.text}"
    body = response.json()
    data = body.get("data") or {}
    assert data.get("subject") == expected_subject, (
        f"Final subject mismatch: expected {expected_subject!r}, "
        f"got {data.get('subject')!r}"
    )
    assert data.get("description") == expected_description, (
        f"Final description mismatch: expected {expected_description!r}, "
        f"got {data.get('description')!r}"
    )


def _iter_all_tickets(collection_id: str):
    url = f"{UNIFY_BASE}/issue-tracking/collections/{collection_id}/tickets"
    params = {"limit": 200}
    seen_cursors = set()
    while True:
        response = requests.get(url, headers=_headers(), params=params, timeout=60)
        assert response.status_code == 200, \
            f"List tickets failed: status={response.status_code}, body={response.text}"
        payload = response.json()
        for item in payload.get("data") or []:
            yield item
        meta = payload.get("meta") or {}
        cursors = meta.get("cursors") or {}
        next_cursor = cursors.get("next")
        if not next_cursor or next_cursor in seen_cursors:
            break
        seen_cursors.add(next_cursor)
        params = {"limit": 200, "cursor": next_cursor}


def test_exactly_one_field_audit_ticket_exists(artifact):
    run_id = _env("ZEALT_RUN_ID")
    collection_id = _env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    matches = []
    for ticket in _iter_all_tickets(collection_id):
        subject = ticket.get("subject") or ""
        if "[FIELD-AUDIT]" in subject and run_id in subject:
            matches.append(ticket)
    assert len(matches) == 1, (
        f"Expected exactly one ticket with subject containing both '[FIELD-AUDIT]' "
        f"and ZEALT_RUN_ID {run_id!r}, found {len(matches)}: "
        f"{[m.get('id') for m in matches]}"
    )
    assert matches[0].get("id") == artifact["ticket_id"], (
        f"Matching ticket id {matches[0].get('id')!r} does not equal "
        f"artifact ticket_id {artifact['ticket_id']!r}"
    )
