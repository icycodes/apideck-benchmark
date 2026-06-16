import os

PROJECT_DIR = "/home/user/apideck_task"


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Expected project directory {PROJECT_DIR} to exist."


def test_requests_importable():
    import requests  # noqa: F401


def test_apideck_app_id_env():
    assert os.environ.get("APIDECK_APP_ID"), "APIDECK_APP_ID env var is not set."


def test_apideck_api_key_env():
    assert os.environ.get("APIDECK_API_KEY"), "APIDECK_API_KEY env var is not set."


def test_apideck_consumer_id_env():
    assert os.environ.get("APIDECK_CONSUMER_ID"), "APIDECK_CONSUMER_ID env var is not set."


def test_apideck_collection_id_env():
    assert os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID"), (
        "APIDECK_ISSUE_TRACKING_COLLECTION_ID env var is not set."
    )


def test_zealt_run_id_env():
    assert os.environ.get("ZEALT_RUN_ID"), "ZEALT_RUN_ID env var is not set."
