#!/usr/bin/env python3
"""
Seed 5 tickets and paginate the collection using cursor-based pagination.
Writes the result to /home/user/myproject/tickets.json.
"""

import json
import os
import sys
import time

from apideck_unify import Apideck

# ── env ────────────────────────────────────────────────────────────────────────
API_KEY       = os.environ["APIDECK_API_KEY"]
APP_ID        = os.environ["APIDECK_APP_ID"]
CONSUMER_ID   = os.environ["APIDECK_CONSUMER_ID"]
COLLECTION_ID = os.environ["APIDECK_ISSUE_TRACKING_COLLECTION_ID"]
RUN_ID        = os.environ["ZEALT_RUN_ID"]

SERVICE_ID    = "github"
TICKET_COUNT  = 5
PAGE_LIMIT    = 2

# ── SDK client ─────────────────────────────────────────────────────────────────
sdk = Apideck(
    api_key=API_KEY,
    app_id=APP_ID,
    consumer_id=CONSUMER_ID,
)

# ── 1. Seed tickets ────────────────────────────────────────────────────────────
print(f"Seeding {TICKET_COUNT} tickets for run {RUN_ID} …")
seeded_ids = []

for n in range(1, TICKET_COUNT + 1):
    subject     = f"Pagination demo {n} - {RUN_ID}"
    description = f"Seeded by list_tickets_pagination_py for run {RUN_ID}"

    resp = sdk.issue_tracking.collection_tickets.create(
        collection_id=COLLECTION_ID,
        service_id=SERVICE_ID,
        subject=subject,
        description=description,
    )

    ticket_id = resp.create_ticket_response.data.id
    seeded_ids.append(ticket_id)
    print(f"  [{n}] Created ticket id={ticket_id!r}  subject={subject!r}")
    # small back-off to stay friendly with rate limits
    time.sleep(0.3)

print(f"Seeded {len(seeded_ids)} tickets.")

# ── 2. Paginate the collection ─────────────────────────────────────────────────
print(f"\nPaginating collection {COLLECTION_ID!r} with limit={PAGE_LIMIT} …")

all_tickets = []
page_count  = 0

res = sdk.issue_tracking.collection_tickets.list(
    collection_id=COLLECTION_ID,
    service_id=SERVICE_ID,
    limit=PAGE_LIMIT,
)

while res is not None:
    page_count += 1
    tickets_page = res.get_tickets_response.data if res.get_tickets_response else []
    print(f"  Page {page_count}: received {len(tickets_page)} ticket(s)")
    all_tickets.extend(tickets_page)
    res = res.next()

print(f"Pagination complete: {page_count} page(s), {len(all_tickets)} total tickets retrieved.")

# ── 3. Filter to this run's tickets ───────────────────────────────────────────
run_tickets = [t for t in all_tickets if RUN_ID in (t.subject or "")]
print(f"\nTickets belonging to run {RUN_ID!r}: {len(run_tickets)}")

# Sort by the numeric index embedded in the subject ("Pagination demo N - …")
def _index(ticket):
    try:
        return int(ticket.subject.split(" ")[2])
    except Exception:
        return 0

run_tickets.sort(key=_index)

if len(run_tickets) != TICKET_COUNT:
    print(f"WARNING: expected {TICKET_COUNT} run-scoped tickets but found {len(run_tickets)}", file=sys.stderr)

# ── 4. Write artifact ──────────────────────────────────────────────────────────
artifact = {
    "run_id":        RUN_ID,
    "collection_id": COLLECTION_ID,
    "page_count":    page_count,
    "tickets": [
        {
            "index":   i + 1,
            "id":      t.id,
            "subject": t.subject,
        }
        for i, t in enumerate(run_tickets)
    ],
}

out_path = "/home/user/myproject/tickets.json"
with open(out_path, "w") as fh:
    json.dump(artifact, fh, indent=2)

print(f"\nArtifact written to {out_path}")
print(json.dumps(artifact, indent=2))
