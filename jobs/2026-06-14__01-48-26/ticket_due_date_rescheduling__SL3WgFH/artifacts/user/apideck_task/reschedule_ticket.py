import os
import sys
import requests
import json

def log_message(msg):
    print(msg)
    sys.stdout.flush()

def main():
    # 1. Load environment variables
    api_key = os.getenv("APIDECK_API_KEY")
    app_id = os.getenv("APIDECK_APP_ID")
    consumer_id = os.getenv("APIDECK_CONSUMER_ID")
    collection_env = os.getenv("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    run_id = os.getenv("ZEALT_RUN_ID")

    if not all([api_key, app_id, consumer_id, collection_env, run_id]):
        log_message("Error: Missing required environment variables.")
        log_message(f"APIDECK_API_KEY: {'set' if api_key else 'not set'}")
        log_message(f"APIDECK_APP_ID: {'set' if app_id else 'not set'}")
        log_message(f"APIDECK_CONSUMER_ID: {'set' if consumer_id else 'not set'}")
        log_message(f"APIDECK_ISSUE_TRACKING_COLLECTION_ID: {collection_env}")
        log_message(f"ZEALT_RUN_ID: {run_id}")
        sys.exit(1)

    # 2. Determine service ID from Vault connections
    headers_base = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "Content-Type": "application/json"
    }

    service_id = "github" # Default fallback
    try:
        url = "https://unify.apideck.com/vault/connections"
        response = requests.get(url, headers=headers_base)
        if response.status_code == 200:
            connections = response.json().get("data", [])
            issue_tracking_services = [
                c["service_id"] for c in connections 
                if c.get("unified_api") == "issue-tracking" and c.get("enabled")
            ]
            if issue_tracking_services:
                # If there's REDACTED and github, prefer github if mentioned in prompt, otherwise use what's enabled
                if "github" in issue_tracking_services:
                    service_id = "github"
                else:
                    service_id = issue_tracking_services[0]
            log_message(f"Detected issue-tracking service ID: {service_id}")
        else:
            log_message(f"Warning: Failed to fetch connections (status {response.status_code}). Using default service ID: {service_id}")
    except Exception as e:
        log_message(f"Warning: Exception while fetching connections: {e}. Using default service ID: {service_id}")

    # Set headers with x-apideck-service-id
    headers = headers_base.copy()
    headers["x-apideck-service-id"] = service_id

    # 3. Resolve collection ID
    resolved_collection_id = collection_env
    try:
        url = "https://unify.apideck.com/issue-tracking/collections"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            collections = response.json().get("data", [])
            for col in collections:
                if col.get("id") == collection_env or col.get("name") == collection_env:
                    resolved_collection_id = col.get("id")
                    break
            log_message(f"Resolved collection ID from '{collection_env}' to '{resolved_collection_id}'")
        else:
            log_message(f"Warning: Failed to fetch collections (status {response.status_code}). Using collection ID directly: {resolved_collection_id}")
    except Exception as e:
        log_message(f"Warning: Exception while resolving collection: {e}. Using collection ID directly: {resolved_collection_id}")

    # 4. Check if ticket already exists (idempotency)
    existing_ticket_id = None
    try:
        url = f"https://unify.apideck.com/issue-tracking/collections/{resolved_collection_id}/tickets"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            tickets = response.json().get("data", [])
            for ticket in tickets:
                subj = ticket.get("subject", "")
                if run_id in subj and "[DUE-DATE]" in subj:
                    existing_ticket_id = ticket.get("id")
                    log_message(f"Found existing ticket with subject matching run ID and [DUE-DATE]: ID {existing_ticket_id}")
                    break
    except Exception as e:
        log_message(f"Warning: Exception while searching for existing tickets: {e}")

    # 5. Create or retrieve the ticket
    if existing_ticket_id:
        ticket_id = existing_ticket_id
    else:
        log_message(f"Creating a new ticket with initial due date '2026-09-15T00:00:00.000Z'...")
        create_payload = {
            "subject": f"Release Task {run_id} [DUE-DATE]",
            "description": f"Release task initially scheduled for 2026-09-15. ZEALT_RUN_ID={run_id}",
            "due_date": "2026-09-15T00:00:00.000Z",
            "status": "open"
        }
        url = f"https://unify.apideck.com/issue-tracking/collections/{resolved_collection_id}/tickets"
        response = requests.post(url, headers=headers, json=create_payload)
        if response.status_code not in [200, 201]:
            log_message(f"Error: Failed to create ticket. Status code: {response.status_code}")
            log_message(f"Response: {response.text}")
            sys.exit(1)
        
        ticket_data = response.json().get("data", {})
        ticket_id = ticket_data.get("id")
        log_message(f"Successfully created ticket. ID: {ticket_id}")

    # 6. Reschedule the ticket to new due date
    log_message(f"Rescheduling ticket {ticket_id} to due date '2026-10-22T00:00:00.000Z'...")
    patch_payload = {
        "due_date": "2026-10-22T00:00:00.000Z"
    }
    patch_url = f"https://unify.apideck.com/issue-tracking/collections/{resolved_collection_id}/tickets/{ticket_id}"
    response = requests.patch(patch_url, headers=headers, json=patch_payload)
    if response.status_code not in [200, 204]:
        log_message(f"Error: Failed to reschedule ticket. Status code: {response.status_code}")
        log_message(f"Response: {response.text}")
        sys.exit(1)

    log_message(f"Successfully rescheduled ticket.")

    # 7. Confirm rescheduled value
    log_message(f"Fetching ticket {ticket_id} to confirm rescheduled due date...")
    get_url = f"https://unify.apideck.com/issue-tracking/collections/{resolved_collection_id}/tickets/{ticket_id}"
    response = requests.get(get_url, headers=headers)
    if response.status_code == 200:
        ticket_data = response.json().get("data", {})
        confirmed_due_date = ticket_data.get("due_date")
        log_message(f"Confirmed Ticket due_date: {confirmed_due_date}")
    else:
        log_message(f"Warning: Failed to fetch ticket for confirmation (status {response.status_code}).")

    # 8. Write log file
    log_dir = "/home/user/apideck_task"
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "output.log")
    
    with open(log_path, "w") as f:
        f.write(f"Ticket ID: {ticket_id}\n")
        f.write(f"Subject: Release Task {run_id} [DUE-DATE]\n")
        f.write(f"Rescheduled Due Date: 2026-10-22T00:00:00.000Z\n")
        if 'confirmed_due_date' in locals():
            f.write(f"Confirmed Due Date from API: {confirmed_due_date}\n")
    
    log_message(f"Wrote output log to {log_path}")

if __name__ == "__main__":
    main()
