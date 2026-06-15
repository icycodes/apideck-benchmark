import os

import pytest
import requests

PROJECT_DIR = "/home/user/apideck_task"

REQUIRED_ENV_VARS = [
    "APIDECK_API_KEY",
    "APIDECK_APP_ID",
    "APIDECK_CONSUMER_ID",
    "APIDECK_ISSUE_TRACKING_COLLECTION_ID",
    "ZEALT_RUN_ID",
]


def _headers():
    return {
        "Authorization": f"Bearer {os.environ['APIDECK_API_KEY']}",
        "x-apideck-app-id": os.environ["APIDECK_APP_ID"],
        "x-apideck-consumer-id": os.environ["APIDECK_CONSUMER_ID"],
        "x-apideck-service-id": "github",
        "Accept": "application/json",
        "Content-Type": "application/json",
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


def _create_initial_ticket(run_id):
    collection_id = os.environ["APIDECK_ISSUE_TRACKING_COLLECTION_ID"]
    url = f"https://unify.apideck.com/issue-tracking/collections/{collection_id}/tickets"
    body = {
        "subject": f"comment-pagination-{run_id}",
        "description": (
            f"Initial ticket for comment_pagination_reorder run {run_id}. "
            "The agent should add 12 comments and list them via cursor pagination."
        ),
        "status": "open",
    }
    resp = requests.post(url, headers=_headers(), json=body, timeout=60)
    assert resp.status_code in (200, 201), (
        f"Failed to create initial ticket: status={resp.status_code} body={resp.text}"
    )


def test_apideck_sdk_importable():
    try:
        import apideck_unify  # noqa: F401
    except ImportError as exc:
        pytest.fail(f"apideck-unify SDK is not importable: {exc}")


def test_requests_importable():
    import requests as _r  # noqa: F401


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_required_env_vars_present():
    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    assert not missing, f"Missing required environment variables: {missing}"


def test_initial_target_ticket_exists():
    """Ensure exactly one ticket containing ZEALT_RUN_ID exists. Create if missing."""
    run_id = os.environ["ZEALT_RUN_ID"]
    tickets = _list_all_tickets()
    matches = [
        t for t in tickets if isinstance(t, dict) and run_id in (t.get("subject") or "")
    ]
    if len(matches) == 0:
        _create_initial_ticket(run_id)
        tickets = _list_all_tickets()
        matches = [
            t
            for t in tickets
            if isinstance(t, dict) and run_id in (t.get("subject") or "")
        ]
    assert len(matches) == 1, (
        f"Expected exactly one initial ticket whose subject contains '{run_id}', "
        f"found {len(matches)}."
    )
