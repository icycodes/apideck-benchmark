import os
import sys
import json
import requests

def main():
    # 1. Read environment variables
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    collection_id = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    zealt_run_id = os.environ.get("ZEALT_RUN_ID")

    print("Checking environment variables...")
    missing = []
    for name, val in [
        ("APIDECK_API_KEY", api_key),
        ("APIDECK_APP_ID", app_id),
        ("APIDECK_CONSUMER_ID", consumer_id),
        ("APIDECK_ISSUE_TRACKING_COLLECTION_ID", collection_id),
        ("ZEALT_RUN_ID", zealt_run_id)
    ]:
        if not val:
            missing.append(name)
    
    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    print("Environment variables are set.")
    
    # 2. Prepare headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": "github",
        "Content-Type": "application/json"
    }

    base_url = "https://unify.apideck.com"

    # 3. Create a ticket (POST /issue-tracking/collections/{collection_id}/tickets)
    create_url = f"{base_url}/issue-tracking/collections/{collection_id}/tickets"
    initial_subject = f"[UPDATE-V1] Ticket for {zealt_run_id}"
    create_body = {
        "subject": initial_subject,
        "description": "Initial draft v1"
    }

    print(f"Creating ticket at {create_url}...")
    print(f"Request body: {json.dumps(create_body, indent=2)}")
    
    try:
        response = requests.post(create_url, headers=headers, json=create_body)
        print(f"Response status code: {response.status_code}")
        response_json = response.json()
        print(f"Response body: {json.dumps(response_json, indent=2)}")
        response.raise_for_status()
    except Exception as e:
        print(f"Error during ticket creation: {e}")
        if 'response' in locals() and response is not None:
            print(f"Response content: {response.text}")
        sys.exit(1)

    ticket_id = response_json.get("data", {}).get("id")
    if not ticket_id:
        print("Error: Could not extract ticket ID from response data.")
        sys.exit(1)
        
    print(f"Successfully created ticket with ID: {ticket_id}")

    # 4. Update the ticket (PATCH /issue-tracking/collections/{collection_id}/tickets/{ticket_id})
    update_url = f"{base_url}/issue-tracking/collections/{collection_id}/tickets/{ticket_id}"
    updated_subject = f"[UPDATE-V2] Ticket for {zealt_run_id}"
    
    # First attempt: Include ticket ID in the body as requested by the schema hint
    update_body_with_id = {
        "id": ticket_id,
        "subject": updated_subject,
        "description": "Revised draft v2"
    }

    print(f"Attempting to update ticket with ID in body at {update_url}...")
    print(f"Request body: {json.dumps(update_body_with_id, indent=2)}")

    update_success = False
    try:
        response = requests.patch(update_url, headers=headers, json=update_body_with_id)
        print(f"Response status code: {response.status_code}")
        response_json = response.json()
        print(f"Response body: {json.dumps(response_json, indent=2)}")
        if response.status_code == 200:
            print("Successfully updated ticket with ID in body.")
            update_success = True
        else:
            print(f"Failed with status code {response.status_code}. Error info: {response.text}")
    except Exception as e:
        print(f"Error during ticket update (with ID): {e}")

    # Second attempt: If first attempt failed, try without ID in body (since validator may reject it)
    if not update_success:
        print("Retrying ticket update WITHOUT ID in body...")
        update_body_without_id = {
            "subject": updated_subject,
            "description": "Revised draft v2"
        }
        print(f"Request body: {json.dumps(update_body_without_id, indent=2)}")
        try:
            response = requests.patch(update_url, headers=headers, json=update_body_without_id)
            print(f"Response status code: {response.status_code}")
            response_json = response.json()
            print(f"Response body: {json.dumps(response_json, indent=2)}")
            response.raise_for_status()
            print("Successfully updated ticket WITHOUT ID in body.")
            update_success = True
        except Exception as e:
            print(f"Error during ticket update (without ID): {e}")
            if 'response' in locals() and response is not None:
                print(f"Response content: {response.text}")
            sys.exit(1)

    # 5. Persist the ticket identifier to output.log
    log_dir = "/home/user/apideck_task"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "output.log")
    
    print(f"Writing ticket ID to {log_file_path}...")
    with open(log_file_path, "w") as f:
        f.write(f"Ticket ID: {ticket_id}\n")
    print("Write complete.")

    # 6. Verify and clean up other tickets in a single listing pass
    print("Verifying final ticket states in the collection (and cleaning up other runs)...")
    list_url = f"{base_url}/issue-tracking/collections/{collection_id}/tickets"
    
    tickets = []
    cursor = None
    
    while True:
        params = {}
        if cursor:
            params["cursor"] = cursor
            
        print(f"Fetching tickets from {list_url} (cursor: {cursor})...")
        try:
            response = requests.get(list_url, headers=headers, params=params)
            response.raise_for_status()
            res_data = response.json()
            
            page_tickets = res_data.get("data", [])
            tickets.extend(page_tickets)
            
            cursor = res_data.get("meta", {}).get("cursors", {}).get("next")
            if not cursor:
                break
        except Exception as e:
            print(f"Error listing tickets: {e}")
            break

    print(f"Found {len(tickets)} tickets in total.")
    
    v1_tickets = []
    v2_tickets = []
    
    for t in tickets:
        subj = t.get("subject", "")
        tid = t.get("id")
        desc = t.get("description", "")
        
        has_v1 = "[UPDATE-V1]" in subj and zealt_run_id in subj
        has_v2 = "[UPDATE-V2]" in subj and zealt_run_id in subj
        
        # If it's not our newly created ticket, but matches the run ID, we must clean it up
        if (has_v1 or has_v2) and (tid != ticket_id):
            print(f"Found duplicate/stale ticket {tid} with subject '{subj}'. Cleaning up...")
            clean_url = f"{base_url}/issue-tracking/collections/{collection_id}/tickets/{tid}"
            clean_body = {
                "subject": f"[CLEANED] Ticket for {zealt_run_id}",
                "description": "Cleaned up to avoid duplicates"
            }
            try:
                requests.patch(clean_url, headers=headers, json=clean_body).raise_for_status()
                print(f"Stale ticket {tid} cleaned up successfully.")
                # Update local variables to reflect the cleaned state
                subj = f"[CLEANED] Ticket for {zealt_run_id}"
                has_v1 = False
                has_v2 = False
            except Exception as e:
                print(f"Failed to clean up stale ticket {tid}: {e}")
                
        if has_v1:
            v1_tickets.append(t)
        if has_v2:
            v2_tickets.append(t)
            
        if has_v1 or has_v2 or tid == ticket_id:
            print(f"Matching Ticket ID: {tid} | Subject: {subj} | Description: {desc}")

    print("\n--- VERIFICATION RESULTS ---")
    print(f"Expected Ticket ID in log: {ticket_id}")
    print(f"Tickets containing [UPDATE-V1] and run ID: {len(v1_tickets)}")
    print(f"Tickets containing [UPDATE-V2] and run ID: {len(v2_tickets)}")
    
    # Check Acceptance Criteria
    success = True
    if len(v2_tickets) != 1:
        print(f"FAIL: Expected exactly 1 ticket with [UPDATE-V2] and run ID, found {len(v2_tickets)}")
        success = False
    else:
        print("PASS: Exactly 1 ticket exists with [UPDATE-V2] and run ID.")
        
    if len(v1_tickets) != 0:
        print(f"FAIL: Expected 0 tickets with [UPDATE-V1] and run ID, found {len(v1_tickets)}")
        success = False
    else:
        print("PASS: No tickets exist with [UPDATE-V1] and run ID.")
        
    # Check description of our ticket
    if ticket_id == ticket_id: # placeholder, we always check our ticket
        # Fetch our ticket state again just to be absolutely sure we have the latest description
        try:
            response = requests.get(f"{base_url}/issue-tracking/collections/{collection_id}/tickets/{ticket_id}", headers=headers)
            response.raise_for_status()
            our_ticket = response.json().get("data", {})
            desc = our_ticket.get("description", "")
            if "Revised draft v2" not in desc:
                print(f"FAIL: Ticket description '{desc}' does not contain 'Revised draft v2'.")
                success = False
            else:
                print(f"PASS: Ticket description contains 'Revised draft v2'.")
        except Exception as e:
            print(f"FAIL: Could not fetch final state of ticket {ticket_id}: {e}")
            success = False

    if success:
        print("ALL CRITERIA PASSED!")
    else:
        print("SOME CRITERIA FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()
