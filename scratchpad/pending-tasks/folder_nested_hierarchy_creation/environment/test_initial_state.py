import os

import pytest


PROJECT_DIR = "/home/user/apideck_task"


def test_requests_importable():
    try:
        import requests  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        pytest.fail(f"requests library is not installed: {exc}")


def test_apideck_unify_importable():
    try:
        import apideck_unify  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        pytest.fail(f"apideck_unify SDK is not installed: {exc}")


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_apideck_env_vars_present():
    for name in (
        "APIDECK_APP_ID",
        "APIDECK_API_KEY",
        "APIDECK_CONSUMER_ID",
        "APIDECK_FILE_STORAGE_DRIVE_NAME",
        "ZEALT_RUN_ID",
    ):
        value = os.environ.get(name)
        assert value, f"Environment variable {name} must be set before evaluation."
