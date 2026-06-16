import importlib.util
import os

PROJECT_DIR = "/home/user/myproject"
TICKETS_JSON = os.path.join(PROJECT_DIR, "tickets.json")


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Expected project directory {PROJECT_DIR} to exist before the task starts."
    )


def test_apideck_unify_sdk_available():
    assert importlib.util.find_spec("apideck_unify") is not None, (
        "Expected the `apideck_unify` Python SDK to be importable; the task requires using it."
    )


def test_required_environment_variables_present():
    required_vars = [
        "APIDECK_APP_ID",
        "APIDECK_API_KEY",
        "APIDECK_CONSUMER_ID",
        "APIDECK_ISSUE_TRACKING_COLLECTION_ID",
        "ZEALT_RUN_ID",
    ]
    missing = [name for name in required_vars if not os.environ.get(name)]
    assert not missing, (
        f"The following required environment variables are missing or empty: {missing}."
    )


def test_tickets_json_not_yet_created():
    assert not os.path.exists(TICKETS_JSON), (
        f"Expected {TICKETS_JSON} to not exist before the task runs; it is an artifact the executor must create."
    )
