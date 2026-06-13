import importlib
import os


PROJECT_DIR = "/home/user/apideck_task"


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Expected project directory {PROJECT_DIR} to exist before the task starts."
    )


def test_apideck_sdk_importable():
    try:
        importlib.import_module("apideck_unify")
    except Exception as exc:  # pragma: no cover - import error path
        raise AssertionError(
            "The 'apideck_unify' Python SDK must be importable in the task "
            f"environment, but importing it raised: {exc!r}"
        )


def test_requests_library_available():
    try:
        importlib.import_module("requests")
    except Exception as exc:  # pragma: no cover - import error path
        raise AssertionError(
            "The 'requests' HTTP library must be importable so the agent can "
            f"call the Apideck REST API directly if desired, but got: {exc!r}"
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
        "The following Apideck environment variables must be set before the "
        f"task starts: {missing}"
    )


def test_run_id_format():
    run_id = os.environ.get("ZEALT_RUN_ID", "")
    assert run_id.startswith("zr-") and len(run_id) > 3, (
        f"ZEALT_RUN_ID must match the 'zr-[a-z0-9]+' pattern, got: {run_id!r}"
    )


def test_log_file_not_yet_created():
    log_path = os.path.join(PROJECT_DIR, "output.log")
    assert not os.path.exists(log_path), (
        f"The output log {log_path} must not exist before the task runs; the "
        "agent is responsible for producing it."
    )
