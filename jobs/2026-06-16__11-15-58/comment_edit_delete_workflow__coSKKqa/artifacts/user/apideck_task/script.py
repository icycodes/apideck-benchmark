import os
import requests
import json
import time

def main():
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    collection_id = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    run_id = os.environ.get("ZEALT_RUN_ID", "default-run-id")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": "github",
        "Content-Type": "application/json"
    }
    
    base_url = "https://unify.apideck.com/issue-tracking"
    
    # 1. Create ticket
    ticket_subject = f"[COMMENT-EDIT-DELETE] {run_id}"
    ticket_payload = {"subject": ticket_subject}
    
    print(f"Creating ticket: {ticket_subject}")
    resp = requests.post(
        f"{base_url}/collections/{collection_id}/tickets",
        headers=headers,
        json=ticket_payload
    )
    resp.raise_for_status()
    ticket_id = resp.json()["data"]["id"]
    print(f"Ticket created: {ticket_id}")
    
    # Write to log
    with open("/home/user/apideck_task/output.log", "w") as f:
        f.write(f"Ticket ID: {ticket_id}\n")
        
    # 2. Add 4 comments
    # A, B, C, D
    bodies = [
        f"A-{run_id}",
        f"B-{run_id}",
        f"C-{run_id}",
        f"D-{run_id}"
    ]
    
    comment_ids = []
    for b in bodies:
        print(f"Adding comment: {b}")
        resp = requests.post(
            f"{base_url}/collections/{collection_id}/tickets/{ticket_id}/comments",
            headers=headers,
            json={"body": b}
        )
        resp.raise_for_status()
        c_id = resp.json()["data"]["id"]
        comment_ids.append(c_id)
        time.sleep(1) # sleep a bit to avoid rate limits or out of order
        
    # We want final to be: A, B-EDITED, D
    # So we edit B (index 1) and delete C (index 2)
    
    b_id = comment_ids[1]
    c_id = comment_ids[2]
    
    print(f"Editing comment {b_id}")
    resp = requests.patch(
        f"{base_url}/collections/{collection_id}/tickets/{ticket_id}/comments/{b_id}",
        headers=headers,
        json={"body": f"B-EDITED-{run_id}"}
    )
    resp.raise_for_status()
    
    print(f"Deleting comment {c_id}")
    resp = requests.delete(
        f"{base_url}/collections/{collection_id}/tickets/{ticket_id}/comments/{c_id}",
        headers=headers
    )
    resp.raise_for_status()
    
    print("Done!")

if __name__ == "__main__":
    main()
