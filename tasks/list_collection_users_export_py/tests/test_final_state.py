import json
import os
import re

import pytest
import requests

PROJECT_DIR = "/home/user/myproject"
USERS_JSON = os.path.join(PROJECT_DIR, "users.json")
LOG_FILE = os.path.join(PROJECT_DIR, "output.log")

APIDECK_BASE = "https://unify.apideck.com"
SERVICE_ID = "github"


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    assert value, f"Required environment variable {name} is not set."
    return value


def _apideck_headers() -> dict:
    return {
        "Authorization": f"Bearer {_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": SERVICE_ID,
        "Accept": "application/json",
    }


def _list_all_users_via_api() -> list:
    """Independently fetch every user via the Apideck Issue Tracking List Users endpoint."""
    collection_id = _env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    url = (
        f"{APIDECK_BASE}/issue-tracking/collections/{collection_id}/users"
    )
    headers = _apideck_headers()

    aggregated: list = []
    cursor = None
    # Hard cap on pagination iterations to avoid infinite loops on misbehaving cursors.
    for _ in range(50):
        params: dict = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(url, headers=headers, params=params, timeout=60)
        assert resp.status_code == 200, (
            "Failed to list users via Apideck API: "
            f"status={resp.status_code} body={resp.text[:500]}"
        )
        body = resp.json()
        data = body.get("data") or []
        assert isinstance(data, list), (
            f"Expected 'data' to be a list in Apideck response, got: {type(data).__name__}"
        )
        aggregated.extend(data)

        meta = body.get("meta") or {}
        cursors = meta.get("cursors") or {}
        next_cursor = cursors.get("next")
        if not next_cursor:
            break
        cursor = next_cursor
    else:  # pragma: no cover - guard against runaway pagination
        pytest.fail(
            "Apideck pagination did not terminate after 50 pages; cursor handling may be broken."
        )

    return aggregated


@pytest.fixture(scope="module")
def users_artifact() -> dict:
    assert os.path.isfile(USERS_JSON), (
        f"Expected the users export artifact at {USERS_JSON}, but it does not exist."
    )
    with open(USERS_JSON, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            pytest.fail(f"{USERS_JSON} is not valid JSON: {exc}")
    assert isinstance(data, dict), (
        f"{USERS_JSON} must contain a JSON object at the top level, "
        f"got {type(data).__name__}."
    )
    return data


@pytest.fixture(scope="module")
def expected_users() -> list:
    return _list_all_users_via_api()


def test_users_json_top_level_shape(users_artifact: dict):
    for key in ("collection_id", "service_id", "users"):
        assert key in users_artifact, (
            f"{USERS_JSON} is missing required top-level key '{key}'. "
            f"Found keys: {sorted(users_artifact.keys())}"
        )
    assert users_artifact["collection_id"] == _env("APIDECK_ISSUE_TRACKING_COLLECTION_ID"), (
        "users.json 'collection_id' does not match APIDECK_ISSUE_TRACKING_COLLECTION_ID. "
        f"Got: {users_artifact.get('collection_id')!r}"
    )
    assert users_artifact["service_id"] == SERVICE_ID, (
        f"users.json 'service_id' must equal {SERVICE_ID!r}, "
        f"got: {users_artifact.get('service_id')!r}"
    )
    assert isinstance(users_artifact["users"], list), (
        "users.json 'users' field must be a JSON array, "
        f"got: {type(users_artifact['users']).__name__}"
    )


def test_each_user_entry_has_expected_field_types(users_artifact: dict):
    for index, user in enumerate(users_artifact["users"]):
        assert isinstance(user, dict), (
            f"users[{index}] must be a JSON object, got: {type(user).__name__}"
        )
        user_id = user.get("id")
        assert isinstance(user_id, str) and user_id.strip(), (
            f"users[{index}].id must be a non-empty string, got: {user_id!r}"
        )
        for optional_field in ("name", "first_name", "last_name", "email"):
            assert optional_field in user, (
                f"users[{index}] is missing field '{optional_field}'. "
                f"Found keys: {sorted(user.keys())}"
            )
            value = user[optional_field]
            assert value is None or isinstance(value, str), (
                f"users[{index}].{optional_field} must be a string or null, "
                f"got: {type(value).__name__}"
            )


def test_user_ids_match_apideck_api(users_artifact: dict, expected_users: list):
    actual_ids = {u["id"] for u in users_artifact["users"]}
    expected_ids = {u.get("id") for u in expected_users if u.get("id")}
    assert actual_ids == expected_ids, (
        "User IDs in users.json do not match the Apideck List Users API.\n"
        f"Missing from users.json: {sorted(expected_ids - actual_ids)}\n"
        f"Unexpected in users.json: {sorted(actual_ids - expected_ids)}"
    )


def test_output_log_records_user_count(users_artifact: dict):
    assert os.path.isfile(LOG_FILE), (
        f"Expected log file at {LOG_FILE}, but it does not exist."
    )
    with open(LOG_FILE, "r", encoding="utf-8") as fh:
        log_content = fh.read()

    matches = re.findall(r"^User count: (\d+)$", log_content, flags=re.MULTILINE)
    assert matches, (
        "output.log must contain a line matching 'User count: <integer>'. "
        f"Log contents (truncated): {log_content[:500]!r}"
    )
    logged_count = int(matches[-1])
    expected_count = len(users_artifact["users"])
    assert logged_count == expected_count, (
        "Logged user count does not match the number of users in users.json. "
        f"Logged: {logged_count}, users.json count: {expected_count}"
    )
