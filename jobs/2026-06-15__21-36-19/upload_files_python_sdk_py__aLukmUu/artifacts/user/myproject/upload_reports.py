#!/usr/bin/env python3
"""Upload two text reports to the configured OneDrive drive via Apideck."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

from apideck_unify import Apideck, models, utils
from apideck_unify._hooks import HookContext
from apideck_unify.utils import get_security_from_env

PROJECT_DIR = Path("/home/user/myproject")
OUTPUT_LOG = PROJECT_DIR / "output.log"
SERVICE_ID = os.getenv("APIDECK_FILE_STORAGE_SERVICE_ID", "onedrive")
PARENT_FOLDER_ID = "root"


def require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def to_plain(value: Any) -> Any:
    """Convert SDK response models to plain Python data for generic traversal."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {key: to_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_plain(item) for item in value]
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True, exclude_none=True)
    if hasattr(value, "dict"):
        return value.dict(by_alias=True, exclude_none=True)
    return value


def iter_response_ids(value: Any) -> Iterable[str]:
    """Yield string id values found in an SDK response payload."""
    value = to_plain(value)
    if isinstance(value, dict):
        candidate = value.get("id")
        if isinstance(candidate, str) and candidate:
            yield candidate
        for item in value.values():
            yield from iter_response_ids(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_response_ids(item)


def extract_first_id(response: Any, context: str) -> str:
    for file_id in iter_response_ids(response):
        return file_id
    raise RuntimeError(f"Could not read returned Apideck file id from {context} response")


def extract_uploaded_file_id(response: Any, context: str) -> str:
    """Prefer response.data.id-style file IDs, while remaining SDK-version tolerant."""
    for outer_attr in (
        "get_file_response",
        "create_file_response",
        "upload_file_response",
        "files_upload_response",
        "file_storage_files_upload_response",
        "response",
    ):
        outer = getattr(response, outer_attr, None)
        data = getattr(outer, "data", None) if outer is not None else None
        file_id = getattr(data, "id", None)
        if isinstance(file_id, str) and file_id:
            return file_id
    data = getattr(response, "data", None)
    file_id = getattr(data, "id", None)
    if isinstance(file_id, str) and file_id:
        return file_id
    return extract_first_id(response, context)


def resolve_drive_id(client: Apideck, drive_name: str) -> str:
    response = client.file_storage.drives.list(service_id=SERVICE_ID, limit=200)
    while response is not None:
        drives_response = getattr(response, "get_drives_response", None)
        for drive in getattr(drives_response, "data", []) or []:
            if getattr(drive, "name", None) == drive_name:
                drive_id = getattr(drive, "id", None)
                if isinstance(drive_id, str) and drive_id:
                    return drive_id
                raise RuntimeError(f"Drive named {drive_name!r} did not include an id")
        next_page = getattr(response, "next", None)
        response = next_page() if callable(next_page) else None
    raise RuntimeError(f"Drive named {drive_name!r} was not found for service {SERVICE_ID!r}")


def upload_file(client: Apideck, *, name: str, drive_id: str, payload: bytes) -> str:
    """Upload one small file using the SDK, including SDK transport fallback."""
    files_resource = client.file_storage.files
    direct_upload = getattr(files_resource, "upload", None)
    if callable(direct_upload):
        response = direct_upload(
            name=name,
            parent_folder_id=PARENT_FOLDER_ID,
            drive_id=drive_id,
            request_body=payload,
            service_id=SERVICE_ID,
        )
        return extract_uploaded_file_id(response, f"direct upload of {name}")

    # apideck-unify 0.31.x does not expose file_storage.files.upload as a
    # generated method, so use the SDK's configured transport/hook stack to call
    # the same direct upload operation without using requests/curl.
    metadata = {
        "name": name,
        "parent_folder_id": PARENT_FOLDER_ID,
        "drive_id": drive_id,
    }
    timeout_ms = files_resource.sdk_configuration.timeout_ms
    request = files_resource._build_request(
        method="POST",
        path="/file-storage/files",
        base_url="https://upload.apideck.com",
        url_variables=None,
        request=None,
        request_body_required=True,
        request_has_path_params=False,
        request_has_query_params=False,
        user_agent_header="user-agent",
        accept_header_value="application/json",
        _globals=models.FileStorageFilesAllGlobals(
            consumer_id=files_resource.sdk_configuration.globals.consumer_id,
            app_id=files_resource.sdk_configuration.globals.app_id,
        ),
        security=files_resource.sdk_configuration.security,
        timeout_ms=timeout_ms,
        get_serialized_body=lambda: utils.serialize_request_body(
            payload,
            nullable=False,
            optional=False,
            serialization_method="raw",
            request_body_type=bytes,
        ),
        http_headers={
            "x-apideck-service-id": SERVICE_ID,
            "x-apideck-metadata": json.dumps(metadata, separators=(",", ":")),
        },
    )
    http_response = files_resource.do_request(
        hook_ctx=HookContext(
            config=files_resource.sdk_configuration,
            base_url="https://upload.apideck.com",
            operation_id="fileStorage.filesUpload",
            oauth2_scopes=None,
            security_source=get_security_from_env(
                files_resource.sdk_configuration.security,
                models.Security,
            ),
        ),
        request=request,
        error_status_codes=["400", "401", "402", "404", "422", "4XX", "5XX"],
    )
    return extract_uploaded_file_id(http_response.json(), f"direct upload of {name}")


def main() -> int:
    api_key = require_env("APIDECK_API_KEY")
    app_id = require_env("APIDECK_APP_ID")
    consumer_id = require_env("APIDECK_CONSUMER_ID")
    drive_name = require_env("APIDECK_FILE_STORAGE_DRIVE_NAME")
    run_id = require_env("ZEALT_RUN_ID")

    client = Apideck(api_key=api_key, app_id=app_id, consumer_id=consumer_id)
    drive_id = resolve_drive_id(client, drive_name)

    alpha_name = f"report-{run_id}-alpha.txt"
    beta_name = f"report-{run_id}-beta.txt"

    alpha_id = upload_file(
        client,
        name=alpha_name,
        drive_id=drive_id,
        payload=f"alpha payload for {run_id}\n".encode("utf-8"),
    )
    beta_id = upload_file(
        client,
        name=beta_name,
        drive_id=drive_id,
        payload=f"beta payload for {run_id}\n".encode("utf-8"),
    )

    result = {
        "alpha": {"name": alpha_name, "id": alpha_id},
        "beta": {"name": beta_name, "id": beta_id},
    }
    OUTPUT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_LOG.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(result, ensure_ascii=False) + "\n")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - provide concise executor-visible failure.
        print(f"upload_reports.py failed: {exc}", file=sys.stderr)
        raise
