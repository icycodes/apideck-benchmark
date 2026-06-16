import importlib
import os

import pytest

REQUIRED_ENV_VARS = [
    "APIDECK_APP_ID",
    "APIDECK_API_KEY",
    "APIDECK_CONSUMER_ID",
    "APIDECK_ISSUE_TRACKING_COLLECTION_ID",
    "ZEALT_RUN_ID",
]


def test_requests_library_available():
    try:
        importlib.import_module("requests")
    except ImportError as exc:  # pragma: no cover - defensive
        pytest.fail(f"`requests` library is not importable in the environment: {exc}")


@pytest.mark.parametrize("env_var", REQUIRED_ENV_VARS)
def test_required_env_var_is_set(env_var: str):
    value = os.environ.get(env_var)
    assert value is not None and value != "", (
        f"Environment variable {env_var} must be set and non-empty before the task runs."
    )


def test_run_id_format():
    run_id = os.environ.get("ZEALT_RUN_ID", "")
    assert run_id.startswith("zr-"), (
        "ZEALT_RUN_ID must start with the prefix `zr-` so that task side effects are isolated per run."
    )
