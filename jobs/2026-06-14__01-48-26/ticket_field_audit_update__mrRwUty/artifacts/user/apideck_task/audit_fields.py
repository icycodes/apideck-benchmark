import os
import sys
import json
import requests

def main():
    # 1. Read environment variables
    zealt_run_id = os.environ.get("ZEALT_RUN_ID")
    apideck_app_id = os.environ.get("APIDECK_APP_ID")
    apideck_api_key = os.environ.get("APIDECK_API_KEY")
    apideck_consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    collection_env = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID")

    print("Checking environment variables:")
    print(f"  ZEALT_RUN_ID: {zealt_run_id}")
    print(f"  APIDECK_APP_ID: {apideck_app_id}")
    print(f"  APIDECK_CONSUMER_ID: {apideck_consumer_id}")
    print(f"  APIDECK_ISSUE_TRACKING_COLLECTION_ID: {collection_env}")
    print(f"  APIDECK_API_KEY present: {bool(apideck_api_key)}")

    if not all([zealt_run_id, apideck_app_id, apideck_api_key, apideck_consumer_id, collection_env]):
        print("Error: Missing required environment variables.", file=sys.stderr)
        sys.exit(1)

    # 2. Determine active service_id and resolve collection_id
    # We will query Vault connections to find the active issue-tracking connection.
    vault_headers = {
        "Authorization": f"Bearer {apideck_api_key}",
        "x-apideck-app-id": apideck_app_id,
        "x-apideck-consumer-id": apideck_consumer_id,
        "Content-Type": "application/json"
    }

    try:
        connections_res = requests.get("https://unify.apideck.com/vault/connections", headers=vault_headers)
        connections_res.raise_for_status()
        connections_data = connections_res.json().get("data", [])
    except Exception as e:
        print(f"Error fetching connections: {e}", file=sys.stderr)
        sys.exit(1)

    # Find the issue-tracking connection
    issue_tracking_connections = [
        conn for conn in connections_data 
        if conn.get("unified_api") == "issue-tracking" and conn.get("state") == "callable"
    ]

    if not issue_tracking_connections:
        print("Error: No callable issue-tracking connection found.", file=sys.stderr)
        sys.exit(1)

    # Use the first active one, or github if it's there (though github won't be there based on test_connections)
    active_conn = issue_tracking_connections[0]
    service_id = active_conn.get("service_id")
    print(f"Selected active service_id: {service_id}")

    # Now let's list collections for this service to resolve collection_id if needed
    service_headers = {
        "Authorization": f"Bearer {apideck_api_key}",
        "x-apideck-app-id": apideck_app_id,
        "x-apideck-consumer-id": apideck_consumer_id,
        "x-apideck-service-id": service_id,
        "Content-Type": "application/json"
    }

    resolved_collection_id = collection_env
    try:
        collections_res = requests.get("https://unify.apideck.com/issue-tracking/collections", headers=service_headers)
        collections_res.raise_for_status()
        collections_list = collections_res.json().get("data", [])
        
        # Try to find a collection matching collection_env by ID or Name
        matched_collection = None
        for col in collections_list:
            if str(col.get("id")) == collection_env or col.get("name") == collection_env:
                matched_collection = col
                break
        
        if matched_collection:
            resolved_collection_id = str(matched_collection.get("id"))
            print(f"Resolved collection ID from '{collection_env}' to '{resolved_collection_id}' (name: {matched_collection.get('name')})")
        else:
            print(f"Could not find matching collection in list. Using collection_env '{collection_env}' directly.")
    except Exception as e:
        print(f"Warning: Failed to list collections, using collection_env directly. Error: {e}")

    # 3. Setup standard request headers for ticket operations
    headers = {
        "Authorization": f"Bearer {apideck_api_key}",
        "x-apideck-app-id": apideck_app_id,
        "x-apideck-consumer-id": apideck_consumer_id,
        "x-apideck-service-id": service_id,
        "Content-Type": "application/json"
    }

    # 4. Define the values
    initial_subject = f"INITIAL-SUBJECT-{zealt_run_id}-[FIELD-AUDIT]"
    intermediate_subject = f"INTERMEDIATE-SUBJECT-{zealt_run_id}-[FIELD-AUDIT]"
    final_subject = f"FINAL-SUBJECT-{zealt_run_id}-[FIELD-AUDIT]"

    initial_description = f"INITIAL-DESCRIPTION-{zealt_run_id}"
    intermediate_description = f"INTERMEDIATE-DESCRIPTION-{zealt_run_id}"
    final_description = f"FINAL-DESCRIPTION-{zealt_run_id}"

    # 5. Create ONE ticket
    create_url = f"https://unify.apideck.com/issue-tracking/collections/{resolved_collection_id}/tickets"
    create_payload = {
        "subject": initial_subject,
        "description": initial_description
    }

    print(f"Creating ticket at URL: {create_url}")
    print(f"Payload: {json.dumps(create_payload, indent=2)}")

    response = requests.post(create_url, headers=headers, json=create_payload)
    print(f"Create response status code: {response.status_code}")
    print(f"Create response text: {response.text}")

    if response.status_code not in (200, 201):
        print(f"Error: Failed to create ticket. Status: {response.status_code}", file=sys.stderr)
        sys.exit(1)

    response_json = response.json()
    if "data" in response_json and isinstance(response_json["data"], dict):
        ticket_id = response_json["data"].get("id")
    else:
        ticket_id = response_json.get("id")

    if not ticket_id:
        print("Error: Could not extract ticket_id from response.", file=sys.stderr)
        sys.exit(1)

    print(f"Successfully created ticket with ID: {ticket_id}")

    # 6. Perform sequential PATCH updates
    patch_url = f"https://unify.apideck.com/issue-tracking/collections/{resolved_collection_id}/tickets/{ticket_id}"

    # Subject PATCH 1 (intermediate)
    print(f"Updating subject to intermediate: {intermediate_subject}")
    sub_patch1_res = requests.patch(patch_url, headers=headers, json={"subject": intermediate_subject})
    print(f"Status: {sub_patch1_res.status_code}, Body: {sub_patch1_res.text}")

    # Subject PATCH 2 (final)
    print(f"Updating subject to final: {final_subject}")
    sub_patch2_res = requests.patch(patch_url, headers=headers, json={"subject": final_subject})
    print(f"Status: {sub_patch2_res.status_code}, Body: {sub_patch2_res.text}")

    # Description PATCH 1 (intermediate)
    print(f"Updating description to intermediate: {intermediate_description}")
    desc_patch1_res = requests.patch(patch_url, headers=headers, json={"description": intermediate_description})
    print(f"Status: {desc_patch1_res.status_code}, Body: {desc_patch1_res.text}")

    # Description PATCH 2 (final)
    print(f"Updating description to final: {final_description}")
    desc_patch2_res = requests.patch(patch_url, headers=headers, json={"description": final_description})
    print(f"Status: {desc_patch2_res.status_code}, Body: {desc_patch2_res.text}")

    # 7. Verify final state via a GET request
    get_url = f"https://unify.apideck.com/issue-tracking/collections/{resolved_collection_id}/tickets/{ticket_id}"
    print(f"Verifying ticket state via GET: {get_url}")
    get_res = requests.get(get_url, headers=headers)
    print(f"GET status: {get_res.status_code}")
    if get_res.status_code == 200:
        get_json = get_res.json()
        ticket_data = get_json.get("data", {})
        print(f"Verified Final Subject: {ticket_data.get('subject')}")
        print(f"Verified Final Description: {ticket_data.get('description')}")
    else:
        print(f"Warning: Failed to fetch ticket details. Status: {get_res.status_code}")

    # 8. Write the output.log
    output_log_path = "/home/user/apideck_task/output.log"
    log_data = {
        "ticket_id": ticket_id,
        "subjects": [initial_subject, intermediate_subject, final_subject],
        "descriptions": [initial_description, intermediate_description, final_description],
        "patch_statuses": {
            "subject": [sub_patch1_res.status_code, sub_patch2_res.status_code],
            "description": [desc_patch1_res.status_code, desc_patch2_res.status_code]
        }
    }

    with open(output_log_path, "w") as f:
        json.dump(log_data, f, indent=2)

    print(f"Successfully wrote artifact log to {output_log_path}")

if __name__ == "__main__":
    main()
