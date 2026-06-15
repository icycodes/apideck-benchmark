import os

import pytest


PROJECT_DIR = "/home/user/apideck_task"


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_log_file_not_yet_created():
    log_path = os.path.join(PROJECT_DIR, "output.log")
    assert not os.path.exists(log_path), (
        f"Log file {log_path} should not exist before the task runs."
    )


def test_requests_available():
    try:
        import requests  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        pytest.fail(f"requests library is not importable: {exc}")


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
