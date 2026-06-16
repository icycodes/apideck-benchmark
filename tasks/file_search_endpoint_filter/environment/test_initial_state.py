import os

import pytest

PROJECT_DIR = "/home/user/apideck_task"


def test_apideck_sdk_importable():
    try:
        import apideck_unify  # noqa: F401
    except Exception as exc:
        pytest.fail(f"apideck_unify SDK is not importable: {exc}")


def test_requests_importable():
    try:
        import requests  # noqa: F401
    except Exception as exc:
        pytest.fail(f"requests is not importable: {exc}")


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."


def test_required_env_vars_present():
    required = [
        "APIDECK_APP_ID",
        "APIDECK_API_KEY",
        "APIDECK_CONSUMER_ID",
        "APIDECK_FILE_STORAGE_DRIVE_NAME",
        "ZEALT_RUN_ID",
    ]
    missing = [name for name in required if not os.environ.get(name)]
    assert not missing, f"Missing required environment variables: {missing}"
