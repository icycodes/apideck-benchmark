import os
import time

import pytest
import requests

UNIFY_BASE_URL = "https://unify.apideck.com"
FILE_STORAGE_SERVICE_ID = "onedrive"
ISSUE_TRACKING_SERVICE_ID = "github"
TICKET_MARKER = "[FILE-INDEX]"


def _get_env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"Environment variable {name} is not set."
    return value


def _common_headers(service_id: str) -> dict:
    return {
        "Authorization": f"Bearer {_get_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _get_env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _get_env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": service_id,
        "Accept": "application/json",
    }


def _paginate(url: str, headers: dict, params: dict | None = None) -> list[dict]:
    items: list[dict] = []
    cursor: str | None = None
    seen_cursors: set[str] = set()
    for _ in range(100):
        q = dict(params or {})
        q["limit"] = 200
        if cursor:
            q["cursor"] = cursor
        for attempt in range(3):
            resp = requests.get(url, headers=headers, params=q, timeout=60)
            if resp.status_code == 200:
                break
            if resp.status_code in (429, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            raise AssertionError(
                f"GET {url} failed with status {resp.status_code}: {resp.text}"
            )
        else:
            raise AssertionError(f"GET {url} kept failing after retries.")
        payload = resp.json()
        data = payload.get("data") or []
        items.extend(data)
        next_cursor = (
            (payload.get("meta") or {}).get("cursors", {}).get("next")
        )
        if not next_cursor or next_cursor in seen_cursors:
            break
        seen_cursors.add(next_cursor)
        cursor = next_cursor
    return items


@pytest.fixture(scope="module")
def run_id() -> str:
    return _get_env("ZEALT_RUN_ID")


@pytest.fixture(scope="module")
def expected_file_names(run_id: str) -> list[str]:
    return [
        f"REPORT-{run_id}-A.txt",
        f"REPORT-{run_id}-B.txt",
        f"REPORT-{run_id}-C.txt",
    ]


@pytest.fixture(scope="module")
def matching_files(run_id: str) -> list[dict]:
    headers = _common_headers(FILE_STORAGE_SERVICE_ID)
    all_files = _paginate(f"{UNIFY_BASE_URL}/file-storage/files", headers)
    prefix = f"REPORT-{run_id}-"
    matches: list[dict] = []
    for item in all_files:
        if (item.get("type") == "file") and isinstance(item.get("name"), str) and item["name"].startswith(prefix):
            matches.append(item)
    return matches


@pytest.fixture(scope="module")
def matching_tickets(run_id: str) -> list[dict]:
    collection_id = _get_env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    headers = _common_headers(ISSUE_TRACKING_SERVICE_ID)
    url = f"{UNIFY_BASE_URL}/issue-tracking/collections/{collection_id}/tickets"
    tickets = _paginate(url, headers)
    matches: list[dict] = []
    for t in tickets:
        subject = t.get("subject") or ""
        if run_id in subject and TICKET_MARKER in subject:
            matches.append(t)
    return matches


def test_exactly_three_report_files_exist(matching_files, expected_file_names):
    actual_names = sorted(f.get("name", "") for f in matching_files)
    assert actual_names == sorted(expected_file_names), (
        f"Expected exactly the three files {sorted(expected_file_names)} at the OneDrive root, "
        f"got {actual_names}."
    )


def test_exactly_one_matching_ticket_exists(matching_tickets, run_id):
    assert len(matching_tickets) == 1, (
        f"Expected exactly 1 ticket whose subject contains both '{TICKET_MARKER}' and "
        f"ZEALT_RUN_ID '{run_id}', got {len(matching_tickets)}."
    )


def test_ticket_description_lists_sorted_file_ids(matching_tickets, matching_files):
    assert len(matching_tickets) == 1, (
        "Cannot verify description without exactly one matching ticket."
    )
    assert len(matching_files) == 3, (
        "Cannot verify description without exactly three matching files."
    )
    expected_ids = sorted(f["id"] for f in matching_files)
    description = matching_tickets[0].get("description") or ""
    actual_lines = [line.strip() for line in description.split("\n") if line.strip()]
    assert actual_lines == expected_ids, (
        "Ticket description, when split by newlines and stripped of empty lines, "
        f"must equal the ascending-sorted file ids {expected_ids}, got {actual_lines}."
    )
