import os
import shutil

import pytest
import requests

PROJECT_DIR = "/home/user/apideck_task"
UNIFY_BASE = "https://unify.apideck.com"


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    assert value, f"Required environment variable {name} is not set."
    return value


def _apideck_headers() -> dict:
    return {
        "Authorization": f"Bearer {_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": "github",
        "Accept": "application/json",
    }


def test_apideck_sdk_importable():
    import apideck_unify  # noqa: F401


def test_requests_library_importable():
    assert requests is not None, "requests library must be importable."


def test_curl_available():
    assert shutil.which("curl") is not None, "curl binary not found in PATH."


def test_required_env_vars_set():
    for name in (
        "APIDECK_APP_ID",
        "APIDECK_API_KEY",
        "APIDECK_CONSUMER_ID",
        "APIDECK_ISSUE_TRACKING_COLLECTION_ID",
        "ZEALT_RUN_ID",
    ):
        assert os.environ.get(name, "").strip(), \
            f"Required environment variable {name} is not set."


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), \
        f"Project directory {PROJECT_DIR} does not exist."


def test_bench_prefix_tags_prerequisite():
    """The GitHub repo backing the configured collection must already have at
    least two labels whose name starts with `bench-`. ApiDeck cannot create
    labels, so this is a hard prerequisite for the task to be solvable."""
    collection_id = _env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    url = f"{UNIFY_BASE}/issue-tracking/collections/{collection_id}/tags"
    response = requests.get(url, headers=_apideck_headers(), params={"limit": 200}, timeout=30)
    assert response.status_code == 200, (
        f"List Tags request failed: {response.status_code} {response.text}"
    )
    payload = response.json()
    data = payload.get("data") or []
    bench_tags = [t for t in data if isinstance(t.get("name"), str) and t["name"].startswith("bench-")]
    if len(bench_tags) < 2:
        pytest.skip(
            "Prerequisite not met: the configured GitHub collection must have "
            "at least two labels whose name starts with 'bench-'. ApiDeck "
            "cannot create labels via the Issue Tracking API; create the "
            f"labels in GitHub first. Found: {[t.get('name') for t in bench_tags]}"
        )
