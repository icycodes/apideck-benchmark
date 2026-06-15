import os

import pytest


PROJECT_DIR = "/home/user/apideck_task"

REQUIRED_ENV_VARS = [
    "APIDECK_API_KEY",
    "APIDECK_APP_ID",
    "APIDECK_CONSUMER_ID",
    "APIDECK_ISSUE_TRACKING_COLLECTION_ID",
    "ZEALT_RUN_ID",
]


def test_requests_importable():
    try:
        import requests  # noqa: F401
    except Exception as exc:  # pragma: no cover - defensive
        pytest.fail(f"`requests` is required to call the ApiDeck API but is not importable: {exc}")


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."


@pytest.mark.parametrize("var", REQUIRED_ENV_VARS)
def test_required_env_var_is_set(var: str):
    value = os.environ.get(var, "")
    assert value, f"Required environment variable {var} is not set."
