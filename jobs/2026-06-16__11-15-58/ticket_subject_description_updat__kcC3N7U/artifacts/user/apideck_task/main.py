import os
import requests
import sys
import json

def main():
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    collection_id = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    run_id = os.environ.get("ZEALT_RUN_ID")

    if not all([api_key, app_id, consumer_id, collection_id, run_id]):
        print("Missing required environment variables")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": "github",
        "Content-Type": "application/json"
    }

    base_url = "https://unify.apideck.com/issue-tracking/collections"

    # 1. Create ticket
    create_url = f"{base_url}/{collection_id}/tickets"
    create_payload = {
        "subject": f"[UPDATE-V1] {run_id}",
        "description": "Initial draft"
    }

    print(f"Creating ticket at {create_url}")
    resp = requests.post(create_url, headers=headers, json=create_payload)
    if resp.status_code not in (200, 201):
        print(f"Failed to create ticket: {resp.status_code} {resp.text}")
        sys.exit(1)

    data = resp.json()
    ticket_id = data.get("data", {}).get("id")

    if not ticket_id:
        print("Failed to get ticket ID from response")
        sys.exit(1)

    print(f"Created ticket ID: {ticket_id}")

    # 2. Update ticket
    update_url = f"{base_url}/{collection_id}/tickets/{ticket_id}"
    update_payload = {
        "subject": f"[UPDATE-V2] {run_id}",
        "description": "Revised draft v2"
    }

    print(f"Updating ticket at {update_url}")
    resp = requests.patch(update_url, headers=headers, json=update_payload)
    if resp.status_code not in (200, 201):
        print(f"Failed to update ticket: {resp.status_code} {resp.text}")
        sys.exit(1)

    print("Updated ticket successfully")

    # 3. Write output log
    os.makedirs("/home/user/apideck_task", exist_ok=True)
    with open("/home/user/apideck_task/output.log", "w") as f:
        f.write(f"Ticket ID: {ticket_id}\n")

if __name__ == "__main__":
    main()
