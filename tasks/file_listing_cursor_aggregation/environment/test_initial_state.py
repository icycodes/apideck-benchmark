import os

import pytest
import requests

PROJECT_DIR = "/home/user/apideck_task"


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."


def test_required_env_vars_present():
    for var in (
        "APIDECK_APP_ID",
        "APIDECK_API_KEY",
        "APIDECK_CONSUMER_ID",
        "APIDECK_FILE_STORAGE_DRIVE_NAME",
        "ZEALT_RUN_ID",
    ):
        assert os.environ.get(var), f"Required environment variable {var} is not set."


def test_apideck_sdk_importable():
    # The apideck_unify SDK must be importable in the task environment.
    import apideck_unify  # noqa: F401


def test_requests_importable():
    assert requests is not None, "requests library must be importable."


def test_output_log_not_yet_created():
    log_path = os.path.join(PROJECT_DIR, "output.log")
    assert not os.path.exists(log_path), (
        f"Log file {log_path} must not exist before the task runs."
    )
