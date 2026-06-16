import os
import json
from apideck_unify import Apideck

def main():
    # Load environment variables
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    collection_id = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    run_id = os.environ.get("ZEALT_RUN_ID")

    if not all([api_key, app_id, consumer_id, collection_id, run_id]):
        print("Error: Missing one or more required environment variables.")
        return

    # Instantiate Apideck client
    sdk = Apideck(api_key=api_key, app_id=app_id, consumer_id=consumer_id)

    # Step 1: Query existing tickets to see what is already seeded for this run
    print("Checking existing tickets in the collection...")
    existing_tickets = {}
    
    # We do a preliminary walk to check existing tickets for this run
    res = sdk.issue_tracking.collection_tickets.list(
        collection_id=collection_id,
        service_id="github",
        limit=20
    )
    
    current_page = res
    while current_page is not None:
        tickets = current_page.get_tickets_response.data or []
        for t in tickets:
            if t.subject and run_id in t.subject:
                # Parse index from subject: "Pagination demo {N} - {ZEALT_RUN_ID}"
                prefix = "Pagination demo "
                suffix = f" - {run_id}"
                if t.subject.startswith(prefix) and t.subject.endswith(suffix):
                    try:
                        idx_str = t.subject[len(prefix):-len(suffix)]
                        idx = int(idx_str)
                        existing_tickets[idx] = t.id
                    except ValueError:
                        pass
        current_page = current_page.next()

    print(f"Found existing tickets for run {run_id}: {existing_tickets}")

    # Step 2: Seed exactly 5 tickets. If any index from 1 to 5 is missing, create it.
    for n in range(1, 6):
        if n not in existing_tickets:
            subject = f"Pagination demo {n} - {run_id}"
            description = f"Seeded by list_tickets_pagination_py for run {run_id}"
            print(f"Seeding ticket {n}: '{subject}'")
            create_res = sdk.issue_tracking.collection_tickets.create(
                collection_id=collection_id,
                service_id="github",
                subject=subject,
                description=description
            )
            ticket_id = create_res.create_ticket_response.data.id
            existing_tickets[n] = ticket_id
            print(f"Ticket {n} seeded successfully with ID: {ticket_id}")
        else:
            print(f"Ticket {n} already exists with ID: {existing_tickets[n]}")

    # Step 3: Walk the entire collection with limit=2 using cursor pagination
    print("Performing full pagination walk with limit=2...")
    page_count = 0
    all_tickets = []
    
    res = sdk.issue_tracking.collection_tickets.list(
        collection_id=collection_id,
        service_id="github",
        limit=2
    )
    
    current_page = res
    while current_page is not None:
        page_count += 1
        tickets = current_page.get_tickets_response.data or []
        all_tickets.extend(tickets)
        current_page = current_page.next()

    print(f"Completed pagination walk. Total pages traversed: {page_count}")

    # Step 4: Filter and sort the tickets for the current run
    run_tickets = []
    for t in all_tickets:
        if t.subject and run_id in t.subject:
            prefix = "Pagination demo "
            suffix = f" - {run_id}"
            if t.subject.startswith(prefix) and t.subject.endswith(suffix):
                try:
                    idx_str = t.subject[len(prefix):-len(suffix)]
                    idx = int(idx_str)
                    if 1 <= idx <= 5:
                        run_tickets.append({
                            "index": idx,
                            "id": t.id,
                            "subject": t.subject
                        })
                except ValueError:
                    pass

    # Sort by index ascending
    run_tickets.sort(key=lambda x: x["index"])

    # Verify we have exactly 5 tickets
    if len(run_tickets) != 5:
        print(f"Warning: Found {len(run_tickets)} tickets instead of 5.")
        # If we have duplicates or missing, let's make sure we unique them by index and only keep the 5 we care about
        unique_tickets = {}
        for rt in run_tickets:
            unique_tickets[rt["index"]] = rt
        run_tickets = [unique_tickets[i] for i in sorted(unique_tickets.keys()) if 1 <= i <= 5]

    # Step 5: Write the JSON artifact
    artifact = {
        "run_id": run_id,
        "collection_id": collection_id,
        "page_count": page_count,
        "tickets": run_tickets
    }

    artifact_path = "/home/user/myproject/tickets.json"
    print(f"Writing artifact to {artifact_path}...")
    with open(artifact_path, "w") as f:
        json.dump(artifact, f, indent=2)

    print("Artifact written successfully:")
    print(json.dumps(artifact, indent=2))

if __name__ == "__main__":
    main()
