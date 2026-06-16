#!/usr/bin/env python3
"""Seed Apideck Issue Tracking tickets and collect them via cursor pagination."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from apideck_unify import Apideck
from apideck_unify.types import UNSET

SERVICE_ID = "github"
PAGE_LIMIT = 2
TICKET_COUNT = 5
ARTIFACT_PATH = Path("/home/user/myproject/tickets.json")


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def is_cursor(value: Any) -> bool:
    return value is not None and value is not UNSET and str(value) != ""


def response_tickets(response: Any) -> list[Any]:
    payload = getattr(response, "get_tickets_response", None)
    if payload is None:
        unexpected = getattr(response, "unexpected_error_response", None)
        raise RuntimeError(f"List Tickets did not return a ticket payload: {unexpected!r}")
    return list(payload.data or [])


def response_next_cursor(response: Any) -> str | None:
    payload = getattr(response, "get_tickets_response", None)
    if payload is None or payload.meta is None or payload.meta.cursors is None:
        return None
    next_cursor = payload.meta.cursors.next
    return str(next_cursor) if is_cursor(next_cursor) else None


def create_ticket(client: Apideck, collection_id: str, index: int, run_id: str) -> str:
    subject = f"Pagination demo {index} - {run_id}"
    description = f"Seeded by list_tickets_pagination_py for run {run_id}"
    response = client.issue_tracking.collection_tickets.create(
        service_id=SERVICE_ID,
        collection_id=collection_id,
        subject=subject,
        description=description,
    )
    payload = getattr(response, "create_ticket_response", None)
    if payload is None or payload.data is None or not getattr(payload.data, "id", None):
        unexpected = getattr(response, "unexpected_error_response", None)
        raise RuntimeError(f"Create Ticket failed for {subject!r}: {unexpected!r}")
    return payload.data.id


def list_all_tickets(client: Apideck, collection_id: str) -> tuple[int, list[Any]]:
    page_count = 0
    all_tickets: list[Any] = []
    cursor: str | None = None

    while True:
        kwargs: dict[str, Any] = {
            "service_id": SERVICE_ID,
            "collection_id": collection_id,
            "limit": PAGE_LIMIT,
        }
        if cursor is not None:
            kwargs["cursor"] = cursor

        response = client.issue_tracking.collection_tickets.list(**kwargs)
        if response is None:
            raise RuntimeError("List Tickets returned no response")

        page_count += 1
        all_tickets.extend(response_tickets(response))

        cursor = response_next_cursor(response)
        if cursor is None:
            break

    return page_count, all_tickets


def ticket_index(subject: str, run_id: str) -> int | None:
    prefix = "Pagination demo "
    suffix = f" - {run_id}"
    if not subject.startswith(prefix) or not subject.endswith(suffix):
        return None
    raw_index = subject[len(prefix) : -len(suffix)]
    try:
        index = int(raw_index)
    except ValueError:
        return None
    return index if 1 <= index <= TICKET_COUNT else None


def main() -> None:
    app_id = required_env("APIDECK_APP_ID")
    api_key = required_env("APIDECK_API_KEY")
    consumer_id = required_env("APIDECK_CONSUMER_ID")
    collection_id = required_env("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    run_id = required_env("ZEALT_RUN_ID")

    client = Apideck(api_key=api_key, app_id=app_id, consumer_id=consumer_id)

    # Seed exactly five new tickets for this run before walking the collection.
    created_ids_by_index = {
        index: create_ticket(client, collection_id, index, run_id)
        for index in range(1, TICKET_COUNT + 1)
    }

    page_count, all_tickets = list_all_tickets(client, collection_id)

    tickets_by_index: dict[int, dict[str, Any]] = {}
    for ticket in all_tickets:
        subject = getattr(ticket, "subject", None)
        ticket_id = getattr(ticket, "id", None)
        if not subject or not ticket_id or run_id not in subject:
            continue
        index = ticket_index(subject, run_id)
        if index is None:
            continue
        if ticket_id == created_ids_by_index[index]:
            tickets_by_index[index] = {
                "index": index,
                "id": ticket_id,
                "subject": subject,
            }

    missing = [index for index in range(1, TICKET_COUNT + 1) if index not in tickets_by_index]
    if missing:
        raise RuntimeError(
            "Seeded tickets were not found during cursor pagination: "
            + ", ".join(str(index) for index in missing)
        )

    artifact = {
        "run_id": run_id,
        "collection_id": collection_id,
        "page_count": page_count,
        "tickets": [tickets_by_index[index] for index in range(1, TICKET_COUNT + 1)],
    }

    ARTIFACT_PATH.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
