import os

import pytest
import requests

PROJECT_DIR = "/home/user/apideck_task"

REQUIRED_ENV_VARS = [
    "APIDECK_APP_ID",
    "APIDECK_API_KEY",
    "APIDECK_CONSUMER_ID",
    "APIDECK_ISSUE_TRACKING_COLLECTION_ID",
    "ZEALT_RUN_ID",
]


def test_requests_library_importable():
    assert requests is not None, "Python requests library is not importable."


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."


@pytest.mark.parametrize("var_name", REQUIRED_ENV_VARS)
def test_required_env_vars_present(var_name: str):
    value = os.environ.get(var_name, "")
    assert value.strip() != "", f"Required environment variable {var_name} is not set."
