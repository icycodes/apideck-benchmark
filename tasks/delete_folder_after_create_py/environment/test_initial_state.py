import importlib
import os
import shutil

PROJECT_DIR = "/home/user/myproject"


def test_python3_available():
    assert shutil.which("python3") is not None, "python3 binary not found in PATH."


def test_apideck_unify_sdk_importable():
    try:
        importlib.import_module("apideck_unify")
    except ImportError as exc:
        raise AssertionError(
            f"apideck_unify Python SDK is not importable: {exc}. "
            "Install it with `pip install apideck-unify`."
        )


def test_requests_library_importable():
    try:
        importlib.import_module("requests")
    except ImportError as exc:
        raise AssertionError(
            f"requests Python package is not importable: {exc}. "
            "Install it with `pip install requests`."
        )


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist before the task starts."
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
        f"Required environment variables are missing or empty: {missing}. "
        "These must be provided by the task runtime."
    )


def test_output_log_absent_initially():
    log_path = os.path.join(PROJECT_DIR, "output.log")
    assert not os.path.exists(log_path), (
        f"Log file {log_path} must not exist before the task runs; "
        "the executor is responsible for creating it."
    )
