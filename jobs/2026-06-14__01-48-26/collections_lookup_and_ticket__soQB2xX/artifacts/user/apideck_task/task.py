import os
import json
import sys
import requests

def main():
    print("Starting ApiDeck Collection Lookup and Ticket Creation Task...")

    # 1. Retrieve and validate environment variables
    api_key = os.environ.get('APIDECK_API_KEY')
    app_id = os.environ.get('APIDECK_APP_ID')
    consumer_id = os.environ.get('APIDECK_CONSUMER_ID')
    target_collection_id = os.environ.get('APIDECK_ISSUE_TRACKING_COLLECTION_ID')
    zealt_run_id = os.environ.get('ZEALT_RUN_ID')

    if not all([api_key, app_id, consumer_id, target_collection_id, zealt_run_id]):
        print("Error: Missing one or more required environment variables.", file=sys.stderr)
        print(f"APIDECK_API_KEY: {'Present' if api_key else 'Missing'}", file=sys.stderr)
        print(f"APIDECK_APP_ID: {'Present' if app_id else 'Missing'}", file=sys.stderr)
        print(f"APIDECK_CONSUMER_ID: {'Present' if consumer_id else 'Missing'}", file=sys.stderr)
        print(f"APIDECK_ISSUE_TRACKING_COLLECTION_ID: {'Present' if target_collection_id else 'Missing'}", file=sys.stderr)
        print(f"ZEALT_RUN_ID: {'Present' if zealt_run_id else 'Missing'}", file=sys.stderr)
        sys.exit(1)

    headers = {
        'Authorization': f'Bearer {api_key}',
        'x-apideck-app-id': app_id,
        'x-apideck-consumer-id': consumer_id,
        'x-apideck-service-id': 'REDACTED',
        'Content-Type': 'application/json'
    }

    # 2. Discover the collection
    collection_id = None
    collection_name = None

    print(f"Attempting direct lookup for collection ID/name: '{target_collection_id}'...")
    direct_url = f"https://unify.apideck.com/issue-tracking/collections/{target_collection_id}"
    try:
        r = requests.get(direct_url, headers=headers, timeout=30)
        if r.status_code == 200:
            res_json = r.json()
            data = res_json.get('data', {})
            if data:
                collection_id = data.get('id')
                collection_name = data.get('name')
                print(f"Direct lookup successful! Found collection '{collection_name}' with ID '{collection_id}'.")
    except Exception as e:
        print(f"Direct lookup encountered an exception: {e}", file=sys.stderr)

    if not collection_id:
        print("Direct lookup failed or returned no data. Falling back to listing collections...")
        # We will fetch collections using a standard list and a membership pass-through list
        collections_list = []
        
        # Standard list
        try:
            r = requests.get("https://unify.apideck.com/issue-tracking/collections", headers=headers, timeout=30)
            if r.status_code == 200:
                collections_list.extend(r.json().get('data', []))
        except Exception as e:
            print(f"Listing collections (standard) encountered an exception: {e}", file=sys.stderr)

        # Membership pass-through list
        try:
            r = requests.get("https://unify.apideck.com/issue-tracking/collections?pass_through[membership]=true", headers=headers, timeout=30)
            if r.status_code == 200:
                collections_list.extend(r.json().get('data', []))
        except Exception as e:
            print(f"Listing collections (membership) encountered an exception: {e}", file=sys.stderr)

        # Search for the target collection in the gathered list
        for col in collections_list:
            col_id = col.get('id')
            col_name = col.get('name')
            if col_id == target_collection_id or col_name == target_collection_id:
                collection_id = col_id
                collection_name = col_name
                print(f"Fallback lookup successful! Found collection '{collection_name}' with ID '{collection_id}'.")
                break

    if not collection_id or not collection_name:
        print(f"Error: Could not resolve collection for ID/name '{target_collection_id}'", file=sys.stderr)
        sys.exit(1)

    # 3. Clean up any existing tickets with the same target subject to ensure exactly one exists
    target_subject = f"COLLNAME-{zealt_run_id}-{collection_name}"
    print(f"Target subject: '{target_subject}'")
    print(f"Checking for existing tickets with subject '{target_subject}' in collection '{collection_id}'...")

    tickets_url = f"https://unify.apideck.com/issue-tracking/collections/{collection_id}/tickets"
    try:
        r = requests.get(tickets_url, headers=headers, timeout=30)
        if r.status_code == 200:
            tickets = r.json().get('data', [])
            for ticket in tickets:
                if ticket.get('subject') == target_subject:
                    t_id = ticket.get('id')
                    print(f"Found existing ticket with matching subject: ID '{t_id}'. Deleting...")
                    delete_url = f"https://unify.apideck.com/issue-tracking/collections/{collection_id}/tickets/{t_id}"
                    dr = requests.delete(delete_url, headers=headers, timeout=30)
                    if dr.status_code == 200:
                        print(f"Successfully deleted ticket '{t_id}'.")
                    else:
                        print(f"Failed to delete ticket '{t_id}': HTTP {dr.status_code} - {dr.text}", file=sys.stderr)
    except Exception as e:
        print(f"Error while checking/deleting existing tickets: {e}", file=sys.stderr)

    # 4. Create exactly one ticket with the target subject
    print(f"Creating a new ticket in collection '{collection_id}'...")
    create_payload = {
        'subject': target_subject,
        'description': f"Ticket auto-created for Zealt Run ID {zealt_run_id} in collection {collection_name}."
    }

    try:
        r = requests.post(tickets_url, headers=headers, json=create_payload, timeout=30)
        if r.status_code not in [200, 201]:
            print(f"Error: Failed to create ticket. HTTP {r.status_code} - {r.text}", file=sys.stderr)
            sys.exit(1)
        
        res_json = r.json()
        ticket_id = res_json.get('data', {}).get('id')
        if not ticket_id:
            print("Error: Ticket created but no ID returned in response.", file=sys.stderr)
            sys.exit(1)
        
        print(f"Successfully created ticket with ID '{ticket_id}'.")
    except Exception as e:
        print(f"Exception during ticket creation: {e}", file=sys.stderr)
        sys.exit(1)

    # 5. Record the discovered name and the created ticket's id in a JSON log file
    log_dir = "/home/user/apideck_task"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "output.log")

    output_data = {
        "collection_name": collection_name,
        "ticket_id": str(ticket_id)
    }

    try:
        with open(log_file_path, "w") as f:
            json.dump(output_data, f, indent=2)
            f.write("\n")
        print(f"Successfully wrote JSON log to '{log_file_path}'.")
        print("Log contents:")
        print(json.dumps(output_data, indent=2))
    except Exception as e:
        print(f"Error writing to log file: {e}", file=sys.stderr)
        sys.exit(1)

    print("Task completed successfully!")

if __name__ == '__main__':
    main()
