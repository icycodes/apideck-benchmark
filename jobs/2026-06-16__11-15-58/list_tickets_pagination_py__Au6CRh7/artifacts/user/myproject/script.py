import os
import json
from apideck_unify import Apideck

def main():
    app_id = os.environ.get("APIDECK_APP_ID")
    api_key = os.environ.get("APIDECK_API_KEY")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    collection_id = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    run_id = os.environ.get("ZEALT_RUN_ID")

    apideck = Apideck(
        api_key=api_key,
        app_id=app_id,
        consumer_id=consumer_id
    )

    print("Seeding tickets...")
    # 1. Seed tickets
    for i in range(1, 6):
        subject = f"Pagination demo {i} - {run_id}"
        description = f"Seeded by list_tickets_pagination_py for run {run_id}"
        
        apideck.issue_tracking.collection_tickets.create(
            service_id="github",
            collection_id=collection_id,
            subject=subject,
            description=description
        )
    print("Tickets seeded.")

    # 2. Paginate tickets
    limit = 2
    page_count = 0
    collected_tickets = []

    print("Listing tickets...")
    res = apideck.issue_tracking.collection_tickets.list(
        service_id="github",
        collection_id=collection_id,
        limit=limit
    )
    
    while res is not None:
        page_count += 1
        print(f"Page {page_count}")
        
        if not res.get_tickets_response or not res.get_tickets_response.data:
            break
            
        for ticket in res.get_tickets_response.data:
            if ticket.subject and run_id in ticket.subject:
                parts = ticket.subject.split(" - ")
                prefix = parts[0]
                index = int(prefix.replace("Pagination demo ", ""))
                collected_tickets.append({
                    "index": index,
                    "id": ticket.id,
                    "subject": ticket.subject
                })
        
        meta = res.get_tickets_response.meta
        if meta and meta.cursors and meta.cursors.next:
            print(f"Next cursor: {meta.cursors.next}")
            try:
                res = res.next()
            except Exception as e:
                print(f"Error using .next(): {e}")
                res = apideck.issue_tracking.collection_tickets.list(
                    service_id="github",
                    collection_id=collection_id,
                    limit=limit,
                    cursor=meta.cursors.next
                )
        else:
            break

    print("Done listing.")
    # Sort tickets
    collected_tickets.sort(key=lambda x: x["index"])

    output = {
        "run_id": run_id,
        "collection_id": collection_id,
        "page_count": page_count,
        "tickets": collected_tickets
    }

    with open("/home/user/myproject/tickets.json", "w") as f:
        json.dump(output, f, indent=2)

if __name__ == "__main__":
    main()
