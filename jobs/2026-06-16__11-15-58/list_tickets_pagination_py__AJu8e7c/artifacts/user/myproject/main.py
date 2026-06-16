#!/usr/bin/env python3
"""Seed tickets and walk them with cursor pagination using the apideck-unify SDK."""

import json
import os
from apideck_unify import Apideck

# Read environment variables
APIDECK_APP_ID = os.environ["APIDECK_APP_ID"]
APIDECK_API_KEY = os.environ["APIDECK_API_KEY"]
APIDECK_CONSUMER_ID = os.environ["APIDECK_CONSUMER_ID"]
APIDECK_ISSUE_TRACKING_COLLECTION_ID = os.environ["APIDECK_ISSUE_TRACKING_COLLECTION_ID"]
ZEALT_RUN_ID = os.environ["ZEALT_RUN_ID"]

SERVICE_ID = "github"
COLLECTION_ID = APIDECK_ISSUE_TRACKING_COLLECTION_ID

# Instantiate the SDK client
client = Apideck(
    api_key=APIDECK_API_KEY,
    app_id=APIDECK_APP_ID,
    consumer_id=APIDECK_CONSUMER_ID,
)

# ── Step 1: Seed 5 tickets ──────────────────────────────────────────────────

seeded_tickets = []

for n in range(1, 6):
    subject = f"Pagination demo {n} - {ZEALT_RUN_ID}"
    description = f"Seeded by list_tickets_pagination_py for run {ZEALT_RUN_ID}"

    add_response = client.issue_tracking.collection_tickets.create(
        collection_id=COLLECTION_ID,
        service_id=SERVICE_ID,
        subject=subject,
        description=description,
    )

    # The create response returns a UnifiedID containing the new ticket's id
    ticket_id = add_response.create_ticket_response.data.id
    print(f"Created ticket: id={ticket_id}, subject={subject}")
    seeded_tickets.append({
        "index": n,
        "id": str(ticket_id),
        "subject": subject,
    })

# Build a set of IDs we just seeded for precise filtering
seeded_ids = {t["id"] for t in seeded_tickets}

# ── Step 2: Walk the collection with cursor pagination (limit=2) ────────────

page_count = 0
all_matching_tickets = []
cursor = None  # first call has no cursor

while True:
    page_count += 1
    if cursor is None:
        list_response = client.issue_tracking.collection_tickets.list(
            collection_id=COLLECTION_ID,
            service_id=SERVICE_ID,
            limit=2,
        )
    else:
        list_response = client.issue_tracking.collection_tickets.list(
            collection_id=COLLECTION_ID,
            service_id=SERVICE_ID,
            limit=2,
            cursor=cursor,
        )

    tickets_data = list_response.get_tickets_response.data
    print(f"Page {page_count}: got {len(tickets_data)} tickets")

    # Filter for tickets matching the current run by ID
    for ticket in tickets_data:
        tid = str(ticket.id)
        if tid in seeded_ids:
            all_matching_tickets.append({
                "id": tid,
                "subject": ticket.subject,
            })

    # Check for next cursor
    meta = list_response.get_tickets_response.meta
    next_cursor = None
    if meta and meta.cursors and meta.cursors.next:
        next_cursor = meta.cursors.next

    if not next_cursor:
        print("No more pages.")
        break

    cursor = next_cursor

# ── Step 3: Build the output artifact ───────────────────────────────────────

# Map id -> index from seeded tickets
id_to_index = {t["id"]: t["index"] for t in seeded_tickets}

# Fill in index for matching tickets
for t in all_matching_tickets:
    t["index"] = id_to_index[t["id"]]

# Sort by index ascending
all_matching_tickets.sort(key=lambda t: t["index"])

output = {
    "run_id": ZEALT_RUN_ID,
    "collection_id": COLLECTION_ID,
    "page_count": page_count,
    "tickets": all_matching_tickets,
}

output_path = "/home/user/myproject/tickets.json"
with open(output_path, "w") as f:
    json.dump(output, f, indent=2)

print(f"\nArtifact written to {output_path}")
print(f"Page count: {page_count}")
print(f"Tickets found: {len(all_matching_tickets)}")