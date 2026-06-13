import os
import re

import pytest
import requests


PROJECT_DIR = "/home/user/apideck_task"
LOG_FILE = os.path.join(PROJECT_DIR, "output.log")
UNIFY_BASE = "https://unify.apideck.com"
SERVICE_ID = "github"

EXPECTED_COMMENT_BODY = (
    "Reproduced and assigned to backend squad. Closing as duplicate of internal report."
)


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"Required environment variable {name} is not set in the verifier environment."
    return value


def _apideck_headers() -> dict:
    return {
        "Authorization": f"Bearer {_required_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _required_env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _required_env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": SERVICE_ID,
        "Accept": "application/json",
    }


@pytest.fixture(scope="session")
def run_id() -> str:
    return _required_env("ZEALT_RUN_ID")


@pytest.fixture(scope="session")
def collection_id() -> str:
    return _required_env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")


@pytest.fixture(scope="session")
def log_contents() -> str:
    assert os.path.isfile(LOG_FILE), (
        f"Expected log file at {LOG_FILE}; the task must write Ticket ID / Comment ID there."
    )
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="session")
def ids_from_log(log_contents: str) -> dict:
    patterns = {
        "ticket_id": re.compile(r"^Ticket ID:\s*(\S+)\s*$", re.MULTILINE),
        "comment_id": re.compile(r"^Comment ID:\s*(\S+)\s*$", re.MULTILINE),
    }
    extracted = {}
    for key, regex in patterns.items():
        match = regex.search(log_contents)
        assert match, (
            f"Could not find a line matching {regex.pattern!r} in the log file. "
            "Make sure the agent wrote `Ticket ID:` and `Comment ID:` lines to "
            "/home/user/apideck_task/output.log."
        )
        extracted[key] = match.group(1)
    return extracted


def test_log_contains_required_ids(ids_from_log):
    for key in ("ticket_id", "comment_id"):
        assert ids_from_log[key], f"{key} extracted from log is empty."


def test_ticket_has_expected_subject_and_status(ids_from_log, collection_id, run_id):
    ticket_id = ids_from_log["ticket_id"]
    url = f"{UNIFY_BASE}/issue-tracking/collections/{collection_id}/tickets/{ticket_id}"
    response = requests.get(url, headers=_apideck_headers(), timeout=30)
    assert response.status_code == 200, (
        f"Getting ticket {ticket_id!r} via Apideck failed: status={response.status_code}, "
        f"body={response.text}"
    )
    payload = response.json() or {}
    data = payload.get("data") or {}
    assert data.get("id") == ticket_id, (
        f"Expected the response data.id to equal {ticket_id!r}, got {data.get('id')!r}."
    )

    expected_subject = f"[triage] login button broken {run_id}"
    assert data.get("subject") == expected_subject, (
        f"Ticket subject mismatch: expected {expected_subject!r}, got {data.get('subject')!r}."
    )

    assert data.get("status") == "closed", (
        "Ticket status was not transitioned to 'closed' before verification; "
        f"got status={data.get('status')!r}."
    )


def test_comment_exists_with_expected_body(ids_from_log, collection_id):
    ticket_id = ids_from_log["ticket_id"]
    comment_id = ids_from_log["comment_id"]
    url = (
        f"{UNIFY_BASE}/issue-tracking/collections/{collection_id}"
        f"/tickets/{ticket_id}/comments"
    )

    cursor = None
    found = None
    for _ in range(10):  # at most 10 pages of 200 comments
        params = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        response = requests.get(
            url, headers=_apideck_headers(), params=params, timeout=30
        )
        assert response.status_code == 200, (
            f"List Comments call failed: status={response.status_code}, body={response.text}"
        )
        payload = response.json() or {}
        for item in payload.get("data") or []:
            if isinstance(item, dict) and item.get("id") == comment_id:
                found = item
                break
        if found is not None:
            break
        cursor = ((payload.get("meta") or {}).get("cursors") or {}).get("next")
        if not cursor:
            break

    assert found is not None, (
        f"Did not find comment id={comment_id!r} under ticket {ticket_id!r} via "
        "the List Comments endpoint."
    )
    assert found.get("body") == EXPECTED_COMMENT_BODY, (
        "Comment body mismatch: expected "
        f"{EXPECTED_COMMENT_BODY!r}, got {found.get('body')!r}."
    )
