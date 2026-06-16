import json
import os
import time

import pytest
import requests

PROJECT_DIR = "/home/user/apideck_task"
LOG_PATH = os.path.join(PROJECT_DIR, "output.log")
UNIFY_BASE = "https://unify.apideck.com"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {os.environ['APIDECK_API_KEY']}",
        "x-apideck-app-id": os.environ["APIDECK_APP_ID"],
        "x-apideck-consumer-id": os.environ["APIDECK_CONSUMER_ID"],
        "x-apideck-service-id": "onedrive",
        "Accept": "application/json",
    }


def _list_files_paginated(limit: int = 3) -> list[dict]:
    """Walk the File Storage List Files endpoint using cursor pagination."""
    collected: list[dict] = []
    cursor: str | None = None
    # Guard against infinite loops if a connector misbehaves.
    for _ in range(500):
        params: dict[str, str | int] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        # Tolerate transient 5xx responses with a brief retry.
        last_exc: Exception | None = None
        for attempt in range(4):
            try:
                resp = requests.get(
                    f"{UNIFY_BASE}/file-storage/files",
                    headers=_headers(),
                    params=params,
                    timeout=60,
                )
                if resp.status_code >= 500:
                    raise RuntimeError(f"server error {resp.status_code}: {resp.text}")
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                time.sleep(2 * (attempt + 1))
        else:
            raise AssertionError(
                f"List Files failed after retries: {last_exc!r}"
            )
        assert resp.status_code == 200, (
            f"List Files returned {resp.status_code}: {resp.text}"
        )
        body = resp.json()
        data = body.get("data") or []
        assert isinstance(data, list), (
            f"List Files response 'data' must be a list, got: {type(data).__name__}"
        )
        collected.extend(data)
        cursors = ((body.get("meta") or {}).get("cursors")) or {}
        next_cursor = cursors.get("next")
        if not next_cursor:
            return collected
        cursor = next_cursor
    raise AssertionError("List Files pagination did not terminate within 500 pages.")


@pytest.fixture(scope="module")
def run_id() -> str:
    value = os.environ.get("ZEALT_RUN_ID")
    assert value, "ZEALT_RUN_ID environment variable must be set."
    return value


@pytest.fixture(scope="module")
def log_payload() -> dict:
    assert os.path.isfile(LOG_PATH), f"Expected log file at {LOG_PATH}, but it is missing."
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        text = f.read().strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"output.log must contain a single JSON object; failed to parse: {exc}\nContent:\n{text!r}"
        )
    assert isinstance(payload, dict), (
        f"output.log JSON must be an object, got: {type(payload).__name__}"
    )
    assert "count" in payload and "ids" in payload, (
        f"output.log JSON must contain keys 'count' and 'ids', got keys: {sorted(payload.keys())}"
    )
    assert isinstance(payload["count"], int) and not isinstance(payload["count"], bool), (
        f"output.log 'count' must be an integer, got: {type(payload['count']).__name__}"
    )
    assert isinstance(payload["ids"], list) and all(isinstance(i, str) for i in payload["ids"]), (
        "output.log 'ids' must be an array of strings."
    )
    return payload


@pytest.fixture(scope="module")
def remote_matches(run_id: str) -> list[dict]:
    prefix = f"AGG-{run_id}-"
    all_files = _list_files_paginated(limit=3)
    matches = [f for f in all_files if isinstance(f.get("name"), str) and f["name"].startswith(prefix)]
    return matches


def test_remote_has_exactly_seven_matching_files(remote_matches: list[dict], run_id: str) -> None:
    prefix = f"AGG-{run_id}-"
    names = sorted(str(f.get("name")) for f in remote_matches)
    expected_names = sorted(f"{prefix}{i}.txt" for i in range(1, 8))
    assert len(remote_matches) == 7, (
        f"Expected exactly 7 files matching prefix {prefix!r}, found {len(remote_matches)}: {names}"
    )
    assert names == expected_names, (
        f"Expected file names {expected_names}, got {names}"
    )


def test_log_count_equals_seven(log_payload: dict) -> None:
    assert log_payload["count"] == 7, (
        f"Expected output.log 'count' to be 7, got {log_payload['count']}"
    )


def test_log_ids_match_remote_ids(log_payload: dict, remote_matches: list[dict]) -> None:
    remote_ids = {str(f["id"]) for f in remote_matches if f.get("id") is not None}
    log_ids = {str(i) for i in log_payload["ids"]}
    assert log_ids == remote_ids, (
        "output.log 'ids' set must equal the set of ids the verifier discovered via cursor-paginated List Files.\n"
        f"Only in log: {sorted(log_ids - remote_ids)}\n"
        f"Only in remote: {sorted(remote_ids - log_ids)}"
    )
    assert len(log_payload["ids"]) == len(log_ids), (
        f"output.log 'ids' must not contain duplicates: {log_payload['ids']}"
    )
