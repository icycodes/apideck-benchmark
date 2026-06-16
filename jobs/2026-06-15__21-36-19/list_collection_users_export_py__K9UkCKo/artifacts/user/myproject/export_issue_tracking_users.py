#!/usr/bin/env python3
"""Export all Apideck Issue Tracking collection users to users.json."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Iterable

from apideck_unify import Apideck

try:
    from apideck_unify.types import UNSET
except ImportError:  # pragma: no cover - compatibility with older SDK versions
    UNSET = object()


PROJECT_DIR = Path(__file__).resolve().parent
USERS_JSON = PROJECT_DIR / "users.json"
OUTPUT_LOG = PROJECT_DIR / "output.log"
SERVICE_ID = "github"


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_field(obj: Any, field: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(field)
    return getattr(obj, field, None)


def to_plain_object(obj: Any) -> Any:
    """Convert SDK model objects to Python containers where possible."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, list):
        return [to_plain_object(item) for item in obj]
    if isinstance(obj, tuple):
        return [to_plain_object(item) for item in obj]
    if isinstance(obj, dict):
        return {key: to_plain_object(value) for key, value in obj.items()}
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return {
            key: to_plain_object(value)
            for key, value in vars(obj).items()
            if not key.startswith("_")
        }
    return obj


def is_unset(value: Any) -> bool:
    return value is UNSET or repr(value) == "Unset()"


def normalize_optional_string(value: Any) -> str | None:
    if value is None or is_unset(value):
        return None
    if isinstance(value, str):
        return value if value else None
    return str(value)


def normalize_user(user: Any) -> dict[str, str | None]:
    user_id = normalize_optional_string(get_field(user, "id"))
    if not user_id:
        raise RuntimeError(f"Encountered user without a non-empty id: {to_plain_object(user)!r}")

    return {
        "id": user_id,
        "name": normalize_optional_string(get_field(user, "name")),
        "first_name": normalize_optional_string(get_field(user, "first_name")),
        "last_name": normalize_optional_string(get_field(user, "last_name")),
        "email": normalize_optional_string(get_field(user, "email")),
    }


def page_data(page: Any) -> Iterable[Any]:
    data = get_field(page, "data")
    if data is None:
        response_body = get_field(page, "get_collection_users_response")
        data = get_field(response_body, "data")
    if data is None:
        return []
    return data


def configure_logging() -> None:
    logging.basicConfig(
        filename=OUTPUT_LOG,
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def main() -> int:
    configure_logging()

    api_key = require_env("APIDECK_API_KEY")
    app_id = require_env("APIDECK_APP_ID")
    consumer_id = require_env("APIDECK_CONSUMER_ID")
    collection_id = require_env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")

    apideck = Apideck(
        api_key=api_key,
        app_id=app_id,
        consumer_id=consumer_id,
    )

    users: list[dict[str, str | None]] = []
    page = apideck.issue_tracking.collection_users.list(
        collection_id=collection_id,
        service_id=SERVICE_ID,
    )

    while page is not None:
        users.extend(normalize_user(user) for user in page_data(page))
        page = page.next()

    artifact = {
        "collection_id": collection_id,
        "service_id": SERVICE_ID,
        "users": users,
    }

    USERS_JSON.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    logging.info("User count: %d", len(users))
    print(f"Exported {len(users)} users to {USERS_JSON}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        logging.exception("Export failed")
        print(f"Export failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
