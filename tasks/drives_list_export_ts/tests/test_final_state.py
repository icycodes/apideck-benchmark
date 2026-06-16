import json
import os
import re

import pytest
import requests

PROJECT_DIR = "/home/user/myproject"
DRIVE_JSON_PATH = os.path.join(PROJECT_DIR, "drive.json")
LOG_FILE_PATH = os.path.join(PROJECT_DIR, "output.log")
PACKAGE_JSON_PATH = os.path.join(PROJECT_DIR, "package.json")
NODE_MODULE_PATH = os.path.join(
    PROJECT_DIR, "node_modules", "@apideck", "unify", "package.json"
)

UNIFY_BASE_URL = "https://unify.apideck.com"


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"Environment variable {name} must be set for verification."
    return value


@pytest.fixture(scope="module")
def drive_record() -> dict:
    assert os.path.isfile(DRIVE_JSON_PATH), (
        f"Expected drive metadata file at {DRIVE_JSON_PATH}, but it does not exist."
    )
    with open(DRIVE_JSON_PATH, "r", encoding="utf-8") as f:
        try:
            record = json.load(f)
        except json.JSONDecodeError as exc:
            pytest.fail(f"{DRIVE_JSON_PATH} is not valid JSON: {exc}")
    assert isinstance(record, dict), (
        f"{DRIVE_JSON_PATH} must contain a JSON object, got: {type(record).__name__}"
    )
    return record


def test_drive_json_has_matching_name(drive_record: dict):
    expected_name = _required_env("APIDECK_FILE_STORAGE_DRIVE_NAME")
    actual_name = drive_record.get("name")
    assert actual_name == expected_name, (
        f"drive.json 'name' must equal APIDECK_FILE_STORAGE_DRIVE_NAME "
        f"({expected_name!r}), got {actual_name!r}."
    )


def test_drive_json_has_non_empty_id(drive_record: dict):
    drive_id = drive_record.get("id")
    assert isinstance(drive_id, str) and drive_id.strip(), (
        f"drive.json 'id' must be a non-empty string, got: {drive_id!r}"
    )


def test_output_log_contains_run_id_and_drive_id(drive_record: dict):
    run_id = _required_env("ZEALT_RUN_ID")
    drive_id = drive_record.get("id")
    assert isinstance(drive_id, str) and drive_id.strip(), (
        "drive.json must contain a non-empty 'id' before checking the log file."
    )

    assert os.path.isfile(LOG_FILE_PATH), (
        f"Expected log file at {LOG_FILE_PATH}, but it does not exist."
    )
    with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
        log_content = f.read()

    run_id_pattern = re.compile(rf"^Run ID:\s*{re.escape(run_id)}\s*$", re.MULTILINE)
    assert run_id_pattern.search(log_content), (
        f"Expected a line matching 'Run ID: {run_id}' in {LOG_FILE_PATH}.\n"
        f"Got:\n{log_content}"
    )

    drive_id_pattern = re.compile(
        rf"^Drive ID:\s*{re.escape(drive_id)}\s*$", re.MULTILINE
    )
    assert drive_id_pattern.search(log_content), (
        f"Expected a line matching 'Drive ID: {drive_id}' in {LOG_FILE_PATH}.\n"
        f"Got:\n{log_content}"
    )


def test_package_json_declares_apideck_unify():
    assert os.path.isfile(PACKAGE_JSON_PATH), (
        f"Expected package.json at {PACKAGE_JSON_PATH}, but it does not exist."
    )
    with open(PACKAGE_JSON_PATH, "r", encoding="utf-8") as f:
        try:
            pkg = json.load(f)
        except json.JSONDecodeError as exc:
            pytest.fail(f"{PACKAGE_JSON_PATH} is not valid JSON: {exc}")
    deps = {}
    for key in ("dependencies", "devDependencies"):
        section = pkg.get(key) or {}
        if isinstance(section, dict):
            deps.update(section)
    assert "@apideck/unify" in deps, (
        f"Expected '@apideck/unify' to be declared in dependencies or "
        f"devDependencies of {PACKAGE_JSON_PATH}, got: {sorted(deps.keys())}"
    )


def test_apideck_unify_installed_in_node_modules():
    assert os.path.isfile(NODE_MODULE_PATH), (
        f"Expected @apideck/unify SDK to be installed at {NODE_MODULE_PATH}, "
        "but it was not found. Run 'npm install' in the project directory."
    )


def test_drive_is_listed_via_apideck_api(drive_record: dict):
    """Confirm via a fresh List Drives call that the recorded drive really exists."""
    expected_name = _required_env("APIDECK_FILE_STORAGE_DRIVE_NAME")
    drive_id = drive_record.get("id")
    assert isinstance(drive_id, str) and drive_id, (
        "drive.json must contain a non-empty 'id' before calling Apideck."
    )

    api_key = _required_env("APIDECK_API_KEY")
    app_id = _required_env("APIDECK_APP_ID")
    consumer_id = _required_env("APIDECK_CONSUMER_ID")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": "onedrive",
        "Accept": "application/json",
    }

    collected: list[dict] = []
    cursor: str | None = None
    # Walk cursor pagination until we either find the drive or exhaust pages.
    for _ in range(20):  # safety bound on pagination loops
        params: dict[str, str] = {"limit": "200"}
        if cursor:
            params["cursor"] = cursor
        response = requests.get(
            f"{UNIFY_BASE_URL}/file-storage/drives",
            headers=headers,
            params=params,
            timeout=60,
        )
        assert response.status_code == 200, (
            f"Apideck List Drives returned status {response.status_code}: "
            f"{response.text}"
        )
        payload = response.json()
        data = payload.get("data") or []
        assert isinstance(data, list), (
            f"Expected 'data' to be a list in List Drives response, got: {type(data).__name__}"
        )
        collected.extend(data)
        if any(
            isinstance(item, dict) and item.get("id") == drive_id for item in data
        ):
            break
        cursor = (
            ((payload.get("meta") or {}).get("cursors") or {}).get("next")
            if isinstance(payload.get("meta"), dict)
            else None
        )
        if not cursor:
            break

    matching = [
        item
        for item in collected
        if isinstance(item, dict) and item.get("id") == drive_id
    ]
    assert matching, (
        f"Drive with id {drive_id!r} (from drive.json) was not returned by "
        f"GET /file-storage/drives. Returned drives: "
        f"{[d.get('id') for d in collected if isinstance(d, dict)]}"
    )
    assert matching[0].get("name") == expected_name, (
        f"Drive {drive_id!r} returned by Apideck has name "
        f"{matching[0].get('name')!r}, expected {expected_name!r}."
    )
