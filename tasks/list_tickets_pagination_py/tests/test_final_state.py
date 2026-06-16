import json
import os
import re
from pathlib import Path
from typing import Optional

import pytest
import requests

PROJECT_DIR = "/home/user/myproject"
TICKETS_JSON = os.path.join(PROJECT_DIR, "tickets.json")
UNIFY_BASE_URL = "https://unify.apideck.com"
SERVICE_ID = "github"
REQUEST_TIMEOUT = 60
SEED_COUNT = 5


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"Required environment variable {name} is not set in the verifier environment."
    return value


@pytest.fixture(scope="module")
def env_config() -> dict:
    return {
        "app_id": _required_env("APIDECK_APP_ID"),
        "api_key": _required_env("APIDECK_API_KEY"),
        "consumer_id": _required_env("APIDECK_CONSUMER_ID"),
        "collection_id": _required_env("APIDECK_ISSUE_TRACKING_COLLECTION_ID"),
        "run_id": _required_env("ZEALT_RUN_ID"),
    }


@pytest.fixture(scope="module")
def apideck_headers(env_config: dict) -> dict:
    return {
        "Authorization": f"Bearer {env_config['api_key']}",
        "x-apideck-app-id": env_config["app_id"],
        "x-apideck-consumer-id": env_config["consumer_id"],
        "x-apideck-service-id": SERVICE_ID,
        "Accept": "application/json",
    }


@pytest.fixture(scope="module")
def tickets_payload(env_config: dict) -> dict:
    assert os.path.isfile(TICKETS_JSON), (
        f"Expected the executor to produce {TICKETS_JSON}, but the file is missing."
    )
    try:
        with open(TICKETS_JSON, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except json.JSONDecodeError as exc:
        pytest.fail(f"{TICKETS_JSON} is not valid JSON: {exc}")
    assert isinstance(payload, dict), (
        f"Expected the top-level JSON in {TICKETS_JSON} to be an object, got {type(payload).__name__}."
    )
    return payload


@pytest.fixture(scope="module")
def expected_subjects(env_config: dict) -> dict:
    return {
        i: f"Pagination demo {i} - {env_config['run_id']}"
        for i in range(1, SEED_COUNT + 1)
    }


def test_top_level_run_and_collection_ids_match(tickets_payload: dict, env_config: dict):
    assert tickets_payload.get("run_id") == env_config["run_id"], (
        f"tickets.json run_id={tickets_payload.get('run_id')!r}; "
        f"expected {env_config['run_id']!r} (value of ZEALT_RUN_ID)."
    )
    assert tickets_payload.get("collection_id") == env_config["collection_id"], (
        f"tickets.json collection_id={tickets_payload.get('collection_id')!r}; "
        f"expected {env_config['collection_id']!r} (value of APIDECK_ISSUE_TRACKING_COLLECTION_ID)."
    )


def test_page_count_is_positive_integer(tickets_payload: dict):
    page_count = tickets_payload.get("page_count")
    assert isinstance(page_count, int) and not isinstance(page_count, bool), (
        f"tickets.json page_count must be an integer; got {page_count!r} (type {type(page_count).__name__})."
    )
    assert page_count >= 1, (
        f"tickets.json page_count must be >= 1; got {page_count}."
    )


def test_tickets_array_shape_and_subjects(tickets_payload: dict, expected_subjects: dict):
    tickets = tickets_payload.get("tickets")
    assert isinstance(tickets, list), (
        f"tickets.json `tickets` must be a list; got {type(tickets).__name__}."
    )
    assert len(tickets) == SEED_COUNT, (
        f"tickets.json `tickets` must contain exactly {SEED_COUNT} entries; got {len(tickets)}."
    )

    sorted_tickets = sorted(
        tickets,
        key=lambda entry: entry.get("index") if isinstance(entry, dict) else -1,
    )
    seen_ids: list[str] = []
    for entry in sorted_tickets:
        assert isinstance(entry, dict), (
            f"Each entry in `tickets` must be an object; got {entry!r}."
        )
        for key in ("index", "id", "subject"):
            assert key in entry, (
                f"Each ticket entry must contain key {key!r}; got {entry!r}."
            )
        idx = entry["index"]
        assert isinstance(idx, int) and not isinstance(idx, bool), (
            f"Ticket entry `index` must be an integer; got {idx!r} in {entry!r}."
        )
        assert idx in expected_subjects, (
            f"Ticket entry has unexpected `index`={idx}; expected one of {sorted(expected_subjects)}."
        )
        ticket_id = entry["id"]
        assert isinstance(ticket_id, str) and ticket_id.strip(), (
            f"Ticket entry `id` must be a non-empty string; got {ticket_id!r} in {entry!r}."
        )
        seen_ids.append(ticket_id)
        subject = entry["subject"]
        assert subject == expected_subjects[idx], (
            f"Ticket entry at index {idx} has subject {subject!r}; "
            f"expected {expected_subjects[idx]!r}."
        )

    indices = sorted(entry["index"] for entry in tickets if isinstance(entry, dict))
    assert indices == list(range(1, SEED_COUNT + 1)), (
        f"Ticket entry indices must be exactly {list(range(1, SEED_COUNT + 1))}; got {indices}."
    )
    assert len(set(seen_ids)) == SEED_COUNT, (
        f"Ticket IDs must be distinct; got duplicates among {seen_ids}."
    )


def test_each_ticket_retrievable_via_get_ticket(
    tickets_payload: dict,
    env_config: dict,
    apideck_headers: dict,
    expected_subjects: dict,
):
    tickets = tickets_payload.get("tickets") or []
    for entry in tickets:
        assert isinstance(entry, dict), f"Bad ticket entry shape: {entry!r}"
        ticket_id = entry["id"]
        idx = entry["index"]
        url = (
            f"{UNIFY_BASE_URL}/issue-tracking/collections/"
            f"{env_config['collection_id']}/tickets/{ticket_id}"
        )
        response = requests.get(url, headers=apideck_headers, timeout=REQUEST_TIMEOUT)
        assert response.status_code == 200, (
            f"GET {url} returned status {response.status_code}: {response.text}"
        )
        body = response.json()
        data = body.get("data")
        assert isinstance(data, dict), (
            f"Unexpected response shape from {url}: {body!r}"
        )
        assert data.get("id") == ticket_id, (
            f"Get Ticket id mismatch: requested {ticket_id!r}, got data.id={data.get('id')!r}."
        )
        assert data.get("subject") == expected_subjects[idx], (
            f"Ticket {ticket_id!r} (index {idx}) has server subject "
            f"{data.get('subject')!r}; expected {expected_subjects[idx]!r}."
        )


def test_seeded_tickets_appear_in_list_tickets(
    tickets_payload: dict,
    env_config: dict,
    apideck_headers: dict,
    expected_subjects: dict,
):
    tickets = tickets_payload.get("tickets") or []
    expected_by_id = {
        entry["id"]: expected_subjects[entry["index"]]
        for entry in tickets
        if isinstance(entry, dict)
    }

    url = (
        f"{UNIFY_BASE_URL}/issue-tracking/collections/"
        f"{env_config['collection_id']}/tickets"
    )
    params: dict[str, str] = {"limit": "200"}
    next_cursor: Optional[str] = None
    matched: dict[str, str] = {}
    for _ in range(50):
        if next_cursor:
            params["cursor"] = next_cursor
        else:
            params.pop("cursor", None)
        response = requests.get(url, headers=apideck_headers, params=params, timeout=REQUEST_TIMEOUT)
        assert response.status_code == 200, (
            f"GET {url} returned status {response.status_code}: {response.text}"
        )
        body = response.json()
        data = body.get("data") or []
        assert isinstance(data, list), (
            f"Expected list at data, got {type(data).__name__}: {body!r}"
        )
        for entry in data:
            if not isinstance(entry, dict):
                continue
            entry_id = entry.get("id")
            if entry_id in expected_by_id and entry_id not in matched:
                matched[entry_id] = entry.get("subject", "")
        if set(matched) >= set(expected_by_id):
            break
        next_cursor = (((body.get("meta") or {}).get("cursors") or {}).get("next"))
        if not next_cursor:
            break

    missing = set(expected_by_id) - set(matched)
    assert not missing, (
        f"The following seeded ticket IDs were not found when paginating List Tickets: {sorted(missing)}."
    )
    for ticket_id, expected_subject in expected_by_id.items():
        observed_subject = matched[ticket_id]
        assert observed_subject == expected_subject, (
            f"List Tickets entry for {ticket_id!r} has subject {observed_subject!r}; "
            f"expected {expected_subject!r}."
        )


def test_solution_uses_apideck_unify_sdk_and_not_raw_http():
    project_path = Path(PROJECT_DIR)
    assert project_path.is_dir(), f"Project directory {PROJECT_DIR} is missing."

    interesting_suffixes = {".py", ".sh", ".bash", ".js", ".mjs", ".ts"}
    sources: list[tuple[Path, str]] = []
    for path in project_path.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in interesting_suffixes and path.name != "Makefile":
            continue
        try:
            sources.append((path, path.read_text(encoding="utf-8", errors="ignore")))
        except OSError:
            continue

    assert sources, (
        f"Expected at least one persisted solution file under {PROJECT_DIR} that performs the task."
    )

    sdk_import_pattern = re.compile(
        r"(?:from\s+apideck_unify\b|import\s+apideck_unify\b)"
    )
    raw_http_against_apideck = re.compile(
        r"(?:requests|httpx)\.(?:get|post|put|patch|delete|request)\s*\([^)]*apideck\.com",
        re.IGNORECASE | re.DOTALL,
    )
    curl_against_apideck = re.compile(
        r"\bcurl\b[^\n]*apideck\.com",
        re.IGNORECASE,
    )
    node_sdk_pattern = re.compile(r"@apideck/unify")

    sdk_user_found = False
    for source_file, text in sources:
        if sdk_import_pattern.search(text):
            sdk_user_found = True
        assert not raw_http_against_apideck.search(text), (
            f"{source_file} appears to call the Apideck REST API directly with requests/httpx, "
            "but the task requires using the `apideck-unify` Python SDK."
        )
        assert not curl_against_apideck.search(text), (
            f"{source_file} appears to call the Apideck API with `curl`, but the task "
            "requires using the `apideck-unify` Python SDK."
        )
        assert not node_sdk_pattern.search(text), (
            f"{source_file} appears to use the `@apideck/unify` Node SDK, but the task "
            "requires using the `apideck-unify` Python SDK."
        )

    assert sdk_user_found, (
        "No persisted file under /home/user/myproject imports `apideck_unify`; "
        "the task requires using the Apideck Python SDK."
    )
