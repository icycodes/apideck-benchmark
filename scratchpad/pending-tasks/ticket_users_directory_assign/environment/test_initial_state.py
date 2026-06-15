import os

import pytest
import requests


PROJECT_DIR = "/home/user/apideck_task"


def test_requests_importable():
    # The target task uses the Apideck REST API over HTTPS. Verify a baseline
    # HTTP client library is available.
    assert requests is not None, "The `requests` library must be importable."


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} must exist."


@pytest.mark.parametrize(
    "var_name",
    [
        "APIDECK_APP_ID",
        "APIDECK_API_KEY",
        "APIDECK_CONSUMER_ID",
        "APIDECK_ISSUE_TRACKING_COLLECTION_ID",
        "ZEALT_RUN_ID",
    ],
)
def test_required_env_vars_present(var_name: str):
    value = os.environ.get(var_name, "").strip()
    assert value, f"Environment variable {var_name} must be set and non-empty."
