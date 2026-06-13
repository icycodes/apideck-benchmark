import os

import pytest
import requests


PROJECT_DIR = "/home/user/myproject"


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_requests_importable():
    # `requests` is the recommended HTTP client for calling Apideck REST endpoints.
    assert requests is not None, "requests library is not importable."


def test_apideck_unify_sdk_importable():
    # The Apideck Python SDK should be preinstalled so the executor can choose
    # either the SDK or raw HTTP calls.
    pytest.importorskip(
        "apideck_unify",
        reason="The 'apideck-unify' Python SDK should be installed in the environment.",
    )


def test_apideck_env_vars_present():
    required = [
        "APIDECK_APP_ID",
        "APIDECK_API_KEY",
        "APIDECK_CONSUMER_ID",
        "APIDECK_FILE_STORAGE_DRIVE_NAME",
        "ZEALT_RUN_ID",
    ]
    missing = [name for name in required if not os.environ.get(name)]
    assert not missing, (
        f"Required Apideck environment variables are not set: {missing}"
    )
