"""Seed 5 tickets and cursor-paginate the Apideck Issue Tracking API to collect them."""

import json
import os

from apideck_unify import Apideck

# ── configuration from the environment ──────────────────────────────────────
API_KEY = os.environ["APIDECK_API_KEY"]
APP_ID = os.environ["APIDECK_APP_ID"]
CONSUMER_ID = os.environ["APIDECK_CONSUMER_ID"]
COLLECTION_ID = os.environ["APIDECK_ISSUE_TRACKING_COLLECTION_ID"]
RUN_ID = os.environ["ZEALT_RUN_ID"]
SERVICE_ID = "github"
SEED_COUNT = 5
PAGE_LIMIT = 2

# ── instantiate the SDK ─────────────────────────────────────────────────────
client = Apideck(
    api_key=API_KEY,
    app_id=APP_ID,
    consumer_id=CONSUMER_ID,
)

tickets_api = client.issue_tracking.collection_tickets

# ── 1. Seed 5 tickets ──────────────────────────────────────────────────────
for i in range(1, SEED_COUNT + 1):
    subject = f"Pagination demo {i} - {RUN_ID}"
    description = f"Seeded by list_tickets_pagination_py for run {RUN_ID}"
    resp = tickets_api.create(
        collection_id=COLLECTION_ID,
        service_id=SERVICE_ID,
        subject=subject,
        description=description,
    )
    ticket_id = resp.create_ticket_response.data.id
    print(f"[seed] Created ticket {i}: id={ticket_id} subject={subject!r}")

# ── 2. Cursor-paginate with limit=2 ────────────────────────────────────────
all_tickets = []
page_count = 0

resp = tickets_api.list(
    collection_id=COLLECTION_ID,
    service_id=SERVICE_ID,
    limit=PAGE_LIMIT,
)

while resp is not None:
    page_count += 1
    data = resp.get_tickets_response
    if data is not None and data.data is not None:
        for ticket in data.data:
            all_tickets.append(ticket)
    print(f"[page {page_count}] fetched {len(data.data) if data and data.data else 0} tickets, "
          f"next cursor: {data.meta.cursors.next if data and data.meta else 'N/A'}")

    # Follow the cursor to the next page
    if resp.next is not None:
        resp = resp.next()
    else:
        resp = None

print(f"\nTotal pages traversed: {page_count}")
print(f"Total tickets collected: {len(all_tickets)}")

# ── 3. Filter to tickets from this run ─────────────────────────────────────
run_tickets = []
for t in all_tickets:
    subj = t.subject if t.subject else ""
    if RUN_ID in subj:
        run_tickets.append(t)

print(f"Tickets matching run_id '{RUN_ID}': {len(run_tickets)}")

# ── 4. Build the output JSON ───────────────────────────────────────────────
# Sort by extracting the index from the subject "Pagination demo {N} - ..."
def extract_index(ticket):
    subj = ticket.subject or ""
    # "Pagination demo N - RUN_ID"
    parts = subj.split(" - ")
    if parts:
        prefix = parts[0]  # "Pagination demo N"
        num_part = prefix.replace("Pagination demo ", "").strip()
        try:
            return int(num_part)
        except ValueError:
            return 9999
    return 9999

run_tickets.sort(key=extract_index)

output = {
    "run_id": RUN_ID,
    "collection_id": COLLECTION_ID,
    "page_count": page_count,
    "tickets": [
        {
            "index": idx,
            "id": t.id,
            "subject": t.subject,
        }
        for idx, t in enumerate(run_tickets, start=1)
    ],
}

out_path = "/home/user/myproject/tickets.json"
with open(out_path, "w") as f:
    json.dump(output, f, indent=2)

print(f"\nOutput written to {out_path}")
print(json.dumps(output, indent=2))
