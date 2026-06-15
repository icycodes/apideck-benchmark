import os
import shutil


PROJECT_DIR = "/home/user/apideck_task"


def test_python3_available():
    assert shutil.which("python3") is not None, "python3 is not available in PATH."


def test_curl_available():
    assert shutil.which("curl") is not None, "curl is not available in PATH."


def test_requests_importable():
    import requests  # noqa: F401


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."


def test_apideck_env_vars_present():
    required = [
        "APIDECK_APP_ID",
        "APIDECK_API_KEY",
        "APIDECK_CONSUMER_ID",
        "APIDECK_FILE_STORAGE_DRIVE_NAME",
        "ZEALT_RUN_ID",
    ]
    missing = [name for name in required if not os.environ.get(name)]
    assert not missing, f"Missing required environment variables: {missing}"
