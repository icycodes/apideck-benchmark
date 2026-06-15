import os

PROJECT_DIR = "/home/user/apideck_task"


def test_python3_available():
    import shutil
    assert shutil.which("python3") is not None, "python3 binary not found in PATH."


def test_requests_importable():
    try:
        import requests  # noqa: F401
    except ImportError as e:
        raise AssertionError(f"Python 'requests' library is not importable: {e}")


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Expected project directory {PROJECT_DIR} to exist before evaluation."
    )


def test_apideck_env_vars_present():
    for key in (
        "APIDECK_APP_ID",
        "APIDECK_API_KEY",
        "APIDECK_CONSUMER_ID",
        "APIDECK_ISSUE_TRACKING_COLLECTION_ID",
        "ZEALT_RUN_ID",
    ):
        assert os.environ.get(key), f"Required environment variable {key} is not set."
