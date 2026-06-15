import importlib
import os

import pytest
import requests


PROJECT_DIR = "/home/user/apideck_task"
UNIFY_BASE = "https://unify.apideck.com"
SERVICE_ID = "github"
PARTITION_MARKER = "[PARTITION]"
EXPECTED_TICKET_COUNT = 6


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    assert value, (
        f"Required environment variable {name} must be set before the task starts."
    )
    return value


def _apideck_headers() -> dict:
    return {
        "Authorization": f"Bearer {_required_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _required_env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _required_env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": SERVICE_ID,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _list_partition_tickets(collection_id: str, run_id: str) -> list:
    url = f"{UNIFY_BASE}/issue-tracking/collections/{collection_id}/tickets"
    cursor = None
    found = []
    for _ in range(20):
        params = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        response = requests.get(
            url, headers=_apideck_headers(), params=params, timeout=30
        )
        assert response.status_code == 200, (
            f"List Tickets failed during initial-state setup: "
            f"status={response.status_code}, body={response.text}"
        )
        payload = response.json() or {}
        for item in payload.get("data") or []:
            subject = item.get("subject") or ""
            if PARTITION_MARKER in subject and run_id in subject:
                found.append(item)
        cursor = ((payload.get("meta") or {}).get("cursors") or {}).get("next")
        if not cursor:
            break
    return found


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Expected project directory {PROJECT_DIR} to exist before the task starts."
    )


def test_apideck_sdk_importable():
    try:
        importlib.import_module("apideck_unify")
    except Exception as exc:  # pragma: no cover
        raise AssertionError(
            "The 'apideck_unify' Python SDK must be importable in the task "
            f"environment, but importing it raised: {exc!r}"
        )


def test_requests_library_available():
    try:
        importlib.import_module("requests")
    except Exception as exc:  # pragma: no cover
        raise AssertionError(
            "The 'requests' HTTP library must be importable so the agent can "
            f"call the Apideck REST API directly if desired, but got: {exc!r}"
        )


def test_required_env_vars_present():
    required = [
        "APIDECK_APP_ID",
        "APIDECK_API_KEY",
        "APIDECK_CONSUMER_ID",
        "APIDECK_ISSUE_TRACKING_COLLECTION_ID",
        "ZEALT_RUN_ID",
    ]
    missing = [name for name in required if not os.environ.get(name)]
    assert not missing, (
        "The following Apideck environment variables must be set before the "
        f"task starts: {missing}"
    )


def test_run_id_format():
    run_id = os.environ.get("ZEALT_RUN_ID", "")
    assert run_id.startswith("zr-") and len(run_id) > 3, (
        f"ZEALT_RUN_ID must match the 'zr-[a-z0-9]+' pattern, got: {run_id!r}"
    )


def test_log_file_not_yet_created():
    log_path = os.path.join(PROJECT_DIR, "output.log")
    assert not os.path.exists(log_path), (
        f"The output log {log_path} must not exist before the task runs; the "
        "agent is responsible for producing it."
    )


def test_seed_six_open_partition_tickets():
    """Seed exactly six `open` tickets with the `[PARTITION]` marker plus the
    current ZEALT_RUN_ID so the agent has a deterministic starting set.

    This setup is idempotent: if a previous attempt left tickets in place, we
    only create enough to bring the total to six. We do NOT delete tickets
    here, because the agent's responsibility is to transition (not delete)
    them.
    """
    collection_id = _required_env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    run_id = _required_env("ZEALT_RUN_ID")

    existing = _list_partition_tickets(collection_id, run_id)
    needed = EXPECTED_TICKET_COUNT - len(existing)
    assert needed >= 0, (
        f"Found more than {EXPECTED_TICKET_COUNT} pre-existing tickets with the "
        f"'[PARTITION]' marker for run {run_id}: {[t.get('id') for t in existing]}."
    )

    create_url = (
        f"{UNIFY_BASE}/issue-tracking/collections/{collection_id}/tickets"
    )
    for i in range(needed):
        payload = {
            "subject": f"{PARTITION_MARKER} {run_id} seed {i + 1}",
            "description": (
                f"Initial-state seed ticket {i + 1} for partition task "
                f"(run {run_id})."
            ),
            "status": "open",
        }
        response = requests.post(
            create_url,
            headers=_apideck_headers(),
            json=payload,
            timeout=60,
        )
        assert response.status_code in (200, 201), (
            f"Failed to seed initial-state ticket {i + 1}: "
            f"status={response.status_code}, body={response.text}"
        )

    final = _list_partition_tickets(collection_id, run_id)
    assert len(final) == EXPECTED_TICKET_COUNT, (
        f"After seeding, expected exactly {EXPECTED_TICKET_COUNT} '[PARTITION]' "
        f"tickets for run {run_id}, but found {len(final)}: "
        f"{[t.get('id') for t in final]}."
    )
    for ticket in final:
        assert ticket.get("status") == "open", (
            f"Seeded ticket {ticket.get('id')!r} must start in status 'open', "
            f"but got {ticket.get('status')!r}."
        )
