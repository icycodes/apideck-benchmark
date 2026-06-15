import os


PROJECT_DIR = "/home/user/apideck_task"


def test_apideck_sdk_importable():
    try:
        import apideck_unify  # noqa: F401
    except Exception as exc:  # pragma: no cover - import diagnostic
        raise AssertionError(
            f"apideck-unify SDK could not be imported: {exc}"
        )


def test_requests_available():
    try:
        import requests  # noqa: F401
    except Exception as exc:  # pragma: no cover - import diagnostic
        raise AssertionError(
            f"requests library could not be imported: {exc}"
        )


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_required_env_vars_present():
    for var in (
        "APIDECK_APP_ID",
        "APIDECK_API_KEY",
        "APIDECK_CONSUMER_ID",
        "APIDECK_FILE_STORAGE_DRIVE_NAME",
        "ZEALT_RUN_ID",
    ):
        value = os.environ.get(var)
        assert value, f"Environment variable {var} is not set."
