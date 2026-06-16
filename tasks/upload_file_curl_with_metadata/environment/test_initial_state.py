import os
import shutil

PROJECT_DIR = "/home/user/myproject"


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Expected project directory {PROJECT_DIR} to exist before the task starts."
    )


def test_curl_binary_available():
    assert shutil.which("curl") is not None, (
        "The `curl` CLI must be available in PATH; the task requires using curl for the upload."
    )


def test_required_environment_variables_present():
    required_vars = [
        "APIDECK_APP_ID",
        "APIDECK_API_KEY",
        "APIDECK_CONSUMER_ID",
        "APIDECK_FILE_STORAGE_DRIVE_NAME",
        "ZEALT_RUN_ID",
    ]
    missing = [name for name in required_vars if not os.environ.get(name)]
    assert not missing, (
        f"The following required environment variables are missing or empty: {missing}."
    )


def test_output_log_not_yet_created():
    output_log = os.path.join(PROJECT_DIR, "output.log")
    assert not os.path.exists(output_log), (
        f"Expected {output_log} to not exist before the task runs; it is an artifact the executor must create."
    )
