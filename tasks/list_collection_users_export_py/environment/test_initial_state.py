import os

PROJECT_DIR = "/home/user/myproject"


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_apideck_unify_importable():
    try:
        import apideck_unify  # noqa: F401
    except Exception as exc:  # pragma: no cover - import error reported via assert
        raise AssertionError(
            "apideck_unify Python SDK must be importable in the task environment, "
            f"but importing it failed with: {exc!r}"
        )


def test_apideck_env_vars_present():
    required = [
        "APIDECK_API_KEY",
        "APIDECK_APP_ID",
        "APIDECK_CONSUMER_ID",
        "APIDECK_ISSUE_TRACKING_COLLECTION_ID",
    ]
    missing = [name for name in required if not os.environ.get(name)]
    assert not missing, (
        "The following Apideck environment variables must be set for this task: "
        f"{missing}"
    )


def test_users_json_not_created_yet():
    artifact = os.path.join(PROJECT_DIR, "users.json")
    assert not os.path.exists(artifact), (
        f"{artifact} must not exist before the task is executed."
    )


def test_output_log_not_created_yet():
    log_path = os.path.join(PROJECT_DIR, "output.log")
    assert not os.path.exists(log_path), (
        f"{log_path} must not exist before the task is executed."
    )
