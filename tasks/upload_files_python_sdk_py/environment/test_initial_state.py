import importlib.util
import os

PROJECT_DIR = "/home/user/myproject"


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_apideck_unify_sdk_importable():
    spec = importlib.util.find_spec("apideck_unify")
    assert spec is not None, (
        "Python package 'apideck_unify' is not installed in the environment."
    )


def test_required_env_vars_present():
    required = [
        "APIDECK_APP_ID",
        "APIDECK_API_KEY",
        "APIDECK_CONSUMER_ID",
        "APIDECK_FILE_STORAGE_DRIVE_NAME",
        "ZEALT_RUN_ID",
    ]
    missing = [name for name in required if not os.environ.get(name)]
    assert not missing, (
        f"Required environment variables are missing or empty: {missing}"
    )


def test_output_log_not_yet_created():
    log_path = os.path.join(PROJECT_DIR, "output.log")
    assert not os.path.exists(log_path), (
        f"{log_path} should not exist before the executor runs the task."
    )


def test_upload_script_not_yet_created():
    script_path = os.path.join(PROJECT_DIR, "upload_reports.py")
    assert not os.path.exists(script_path), (
        f"{script_path} should not exist before the executor runs the task."
    )
