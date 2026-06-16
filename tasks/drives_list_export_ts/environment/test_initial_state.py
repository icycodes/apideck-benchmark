import os
import shutil

PROJECT_DIR = "/home/user/myproject"


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_node_binary_available():
    assert shutil.which("node") is not None, "node binary not found in PATH."


def test_npm_binary_available():
    assert shutil.which("npm") is not None, "npm binary not found in PATH."


def test_npx_binary_available():
    assert shutil.which("npx") is not None, "npx binary not found in PATH."


def test_apideck_app_id_env_present():
    assert os.environ.get("APIDECK_APP_ID"), (
        "APIDECK_APP_ID environment variable must be set."
    )


def test_apideck_api_key_env_present():
    assert os.environ.get("APIDECK_API_KEY"), (
        "APIDECK_API_KEY environment variable must be set."
    )


def test_apideck_consumer_id_env_present():
    assert os.environ.get("APIDECK_CONSUMER_ID"), (
        "APIDECK_CONSUMER_ID environment variable must be set."
    )


def test_apideck_file_storage_drive_name_env_present():
    assert os.environ.get("APIDECK_FILE_STORAGE_DRIVE_NAME"), (
        "APIDECK_FILE_STORAGE_DRIVE_NAME environment variable must be set."
    )


def test_zealt_run_id_env_present():
    assert os.environ.get("ZEALT_RUN_ID"), (
        "ZEALT_RUN_ID environment variable must be set."
    )
