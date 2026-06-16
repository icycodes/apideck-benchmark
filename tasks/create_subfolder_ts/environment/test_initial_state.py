import os
import shutil

PROJECT_DIR = "/home/user/myproject"


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_node_available():
    assert shutil.which("node") is not None, (
        "node binary not found in PATH; Node.js runtime is required to run the TypeScript SDK."
    )


def test_npm_available():
    assert shutil.which("npm") is not None, (
        "npm binary not found in PATH; npm is required to install @apideck/unify."
    )


def test_apideck_app_id_env():
    assert os.environ.get("APIDECK_APP_ID"), (
        "APIDECK_APP_ID environment variable is not set."
    )


def test_apideck_api_key_env():
    assert os.environ.get("APIDECK_API_KEY"), (
        "APIDECK_API_KEY environment variable is not set."
    )


def test_apideck_consumer_id_env():
    assert os.environ.get("APIDECK_CONSUMER_ID"), (
        "APIDECK_CONSUMER_ID environment variable is not set."
    )


def test_apideck_file_storage_drive_name_env():
    assert os.environ.get("APIDECK_FILE_STORAGE_DRIVE_NAME"), (
        "APIDECK_FILE_STORAGE_DRIVE_NAME environment variable is not set."
    )


def test_zealt_run_id_env():
    assert os.environ.get("ZEALT_RUN_ID"), (
        "ZEALT_RUN_ID environment variable is not set."
    )
