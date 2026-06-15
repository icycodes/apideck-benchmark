import importlib
import os

import pytest

PROJECT_DIR = "/home/user/apideck_task"

REQUIRED_ENV_VARS = [
    "APIDECK_APP_ID",
    "APIDECK_API_KEY",
    "APIDECK_CONSUMER_ID",
    "APIDECK_ISSUE_TRACKING_COLLECTION_ID",
    "ZEALT_RUN_ID",
]


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_requests_library_importable():
    try:
        importlib.import_module("requests")
    except ImportError as exc:  # pragma: no cover - defensive
        pytest.fail(f"requests library is not importable: {exc}")


def test_apideck_sdk_importable():
    try:
        importlib.import_module("apideck_unify")
    except ImportError as exc:  # pragma: no cover - defensive
        pytest.fail(f"apideck_unify SDK is not importable: {exc}")


@pytest.mark.parametrize("var_name", REQUIRED_ENV_VARS)
def test_required_env_vars_present(var_name):
    value = os.environ.get(var_name)
    assert value, f"Required environment variable {var_name} is not set."
