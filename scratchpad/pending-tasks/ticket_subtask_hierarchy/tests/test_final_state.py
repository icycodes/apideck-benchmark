import os
import re
import time

import pytest
import requests

OUTPUT_LOG = "/home/user/apideck_task/output.log"
APIDECK_BASE_URL = "https://unify.apideck.com"
SERVICE_ID = "github"


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"Required environment variable {name} is not set in the verifier."
    return value


@pytest.fixture(scope="session")
def env_vars():
    return {
        "app_id": _require_env("APIDECK_APP_ID"),
        "api_key": _require_env("APIDECK_API_KEY"),
        "consumer_id": _require_env("APIDECK_CONSUMER_ID"),
        "collection_id": _require_env("APIDECK_ISSUE_TRACKING_COLLECTION_ID"),
        "run_id": _require_env("ZEALT_RUN_ID"),
    }


@pytest.fixture(scope="session")
def log_artifacts():
    assert os.path.isfile(OUTPUT_LOG), (
        f"Expected log artifact {OUTPUT_LOG} to exist after the task runs."
    )
    with open(OUTPUT_LOG, "r", encoding="utf-8") as f:
        content = f.read()

    prefix_match = re.search(r"^SUBJECT_PREFIX:\s*(.+)$", content, re.MULTILINE)
    parent_match = re.search(r"^PARENT_ID:\s*(\S+)\s*$", content, re.MULTILINE)
    children_match = re.search(r"^CHILD_IDS:\s*(\S+)\s*$", content, re.MULTILINE)

    assert prefix_match, (
        f"Could not find a line beginning with 'SUBJECT_PREFIX: ' in {OUTPUT_LOG}."
    )
    assert parent_match, (
        f"Could not find a line beginning with 'PARENT_ID: ' in {OUTPUT_LOG}."
    )
    assert children_match, (
        f"Could not find a line beginning with 'CHILD_IDS: ' in {OUTPUT_LOG}."
    )

    subject_prefix = prefix_match.group(1).strip()
    parent_id = parent_match.group(1).strip()
    child_ids_raw = children_match.group(1).strip()
    child_ids = [c.strip() for c in child_ids_raw.split(",") if c.strip()]

    assert subject_prefix, "SUBJECT_PREFIX value is empty."
    assert parent_id, "PARENT_ID value is empty."
    assert len(child_ids) == 3, (
        f"Expected exactly 3 child ids in CHILD_IDS line, got {len(child_ids)}: {child_ids}"
    )

    return {
        "subject_prefix": subject_prefix,
        "parent_id": parent_id,
        "child_ids": child_ids,
    }


@pytest.fixture(scope="session")
def matching_tickets(env_vars, log_artifacts):
    """Page through the collection and gather all tickets whose subject starts with the prefix."""
    headers = {
        "Authorization": f"Bearer {env_vars['api_key']}",
        "x-apideck-app-id": env_vars["app_id"],
        "x-apideck-consumer-id": env_vars["consumer_id"],
        "x-apideck-service-id": SERVICE_ID,
    }
    url = (
        f"{APIDECK_BASE_URL}/issue-tracking/collections/"
        f"{env_vars['collection_id']}/tickets"
    )
    prefix = log_artifacts["subject_prefix"]

    collected: list[dict] = []
    cursor: str | None = None
    # Allow GitHub-backed listings a bit of time to become consistent.
    deadline = time.time() + 60
    while True:
        params: dict = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        response = requests.get(url, headers=headers, params=params, timeout=60)
        assert response.status_code == 200, (
            f"List Tickets failed with status {response.status_code}: {response.text}"
        )
        payload = response.json()
        data = payload.get("data") or []
        for ticket in data:
            subject = ticket.get("subject") or ""
            if subject.startswith(prefix):
                collected.append(ticket)
        next_cursor = (
            (payload.get("meta") or {}).get("cursors", {}).get("next")
        )
        if not next_cursor:
            break
        if next_cursor == cursor:
            break
        cursor = next_cursor

    # If the listing hasn't caught up yet, retry briefly.
    while len(collected) < 4 and time.time() < deadline:
        time.sleep(5)
        collected = []
        cursor = None
        while True:
            params = {"limit": 200}
            if cursor:
                params["cursor"] = cursor
            response = requests.get(url, headers=headers, params=params, timeout=60)
            assert response.status_code == 200, (
                f"List Tickets failed with status {response.status_code}: {response.text}"
            )
            payload = response.json()
            data = payload.get("data") or []
            for ticket in data:
                subject = ticket.get("subject") or ""
                if subject.startswith(prefix):
                    collected.append(ticket)
            next_cursor = (
                (payload.get("meta") or {}).get("cursors", {}).get("next")
            )
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor

    return collected


def test_subject_prefix_contains_run_id(env_vars, log_artifacts):
    prefix = log_artifacts["subject_prefix"]
    run_id = env_vars["run_id"]
    assert run_id in prefix, (
        f"SUBJECT_PREFIX '{prefix}' must contain ZEALT_RUN_ID '{run_id}'."
    )


def test_parent_and_child_ids_are_distinct(log_artifacts):
    parent_id = log_artifacts["parent_id"]
    child_ids = log_artifacts["child_ids"]
    all_ids = [parent_id] + child_ids
    assert len(set(all_ids)) == len(all_ids), (
        f"Parent id and child ids must all be distinct, got: {all_ids}"
    )


def test_matching_tickets_count(matching_tickets):
    assert len(matching_tickets) >= 4, (
        "Expected at least 4 tickets with the announced subject prefix "
        f"(1 parent + 3 children); got {len(matching_tickets)}."
    )


def test_parent_ticket_properties(env_vars, log_artifacts, matching_tickets):
    parent_id = log_artifacts["parent_id"]
    prefix = log_artifacts["subject_prefix"]
    run_id = env_vars["run_id"]

    parent = next((t for t in matching_tickets if t.get("id") == parent_id), None)
    assert parent is not None, (
        f"Parent ticket with id '{parent_id}' was not found among tickets "
        f"with subject prefix '{prefix}'."
    )
    subject = parent.get("subject") or ""
    assert subject.startswith(prefix), (
        f"Parent ticket subject '{subject}' must start with prefix '{prefix}'."
    )
    assert run_id in subject, (
        f"Parent ticket subject '{subject}' must contain ZEALT_RUN_ID '{run_id}'."
    )
    parent_parent_id = parent.get("parent_id")
    assert parent_parent_id in (None, "",), (
        f"Parent ticket parent_id must be empty/null, got: {parent_parent_id!r}."
    )


def test_child_ticket_properties(env_vars, log_artifacts, matching_tickets):
    parent_id = log_artifacts["parent_id"]
    child_ids = log_artifacts["child_ids"]
    prefix = log_artifacts["subject_prefix"]
    run_id = env_vars["run_id"]

    by_id = {t.get("id"): t for t in matching_tickets}
    for child_id in child_ids:
        child = by_id.get(child_id)
        assert child is not None, (
            f"Child ticket with id '{child_id}' was not found among tickets "
            f"with subject prefix '{prefix}'."
        )
        subject = child.get("subject") or ""
        assert subject.startswith(prefix), (
            f"Child ticket {child_id} subject '{subject}' must start with prefix '{prefix}'."
        )
        assert run_id in subject, (
            f"Child ticket {child_id} subject '{subject}' must contain ZEALT_RUN_ID '{run_id}'."
        )
        assert child.get("parent_id") == parent_id, (
            f"Child ticket {child_id} parent_id must equal parent id '{parent_id}', "
            f"got: {child.get('parent_id')!r}."
        )


def test_hierarchy_counts(log_artifacts, matching_tickets):
    parent_id = log_artifacts["parent_id"]

    parents = [
        t for t in matching_tickets if (t.get("parent_id") in (None, ""))
    ]
    children = [t for t in matching_tickets if t.get("parent_id") == parent_id]

    assert len(parents) == 1, (
        "Exactly 1 ticket with an empty/null parent_id is expected among tickets "
        f"sharing the announced prefix; got {len(parents)}."
    )
    assert len(children) == 3, (
        "Exactly 3 tickets must reference the parent via parent_id; "
        f"got {len(children)}."
    )
