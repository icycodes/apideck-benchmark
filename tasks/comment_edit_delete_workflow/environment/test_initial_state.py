import os

PROJECT_DIR = "/home/user/apideck_task"


def test_python_requests_importable():
    import requests  # noqa: F401


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."


def test_required_env_vars_present():
    required = [
        "APIDECK_APP_ID",
        "APIDECK_API_KEY",
        "APIDECK_CONSUMER_ID",
        "APIDECK_ISSUE_TRACKING_COLLECTION_ID",
        "ZEALT_RUN_ID",
    ]
    missing = [name for name in required if not os.environ.get(name)]
    assert not missing, f"Missing required environment variables: {missing}"
