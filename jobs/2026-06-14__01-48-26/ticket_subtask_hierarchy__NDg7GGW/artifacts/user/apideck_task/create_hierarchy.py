import os
import sys
import requests
import json

def main():
    # 1. Read environment variables
    app_id = os.environ.get("APIDECK_APP_ID")
    api_key = os.environ.get("APIDECK_API_KEY")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    env_collection_id = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    run_id = os.environ.get("ZEALT_RUN_ID")

    if not all([app_id, api_key, consumer_id, env_collection_id, run_id]):
        print("Error: Missing one or more required environment variables.")
        print(f"APIDECK_APP_ID: {app_id}")
        print(f"APIDECK_API_KEY: {'set' if api_key else 'not set'}")
        print(f"APIDECK_CONSUMER_ID: {consumer_id}")
        print(f"APIDECK_ISSUE_TRACKING_COLLECTION_ID: {env_collection_id}")
        print(f"ZEALT_RUN_ID: {run_id}")
        sys.exit(1)

    print(f"Starting ticket hierarchy creation for run: {run_id}")

    # 2. Determine the service ID dynamically from Vault connections
    vault_headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
    }
    
    service_id = None
    try:
        connections_url = "https://unify.apideck.com/vault/connections"
        response = requests.get(connections_url, headers=vault_headers)
        if response.status_code == 200:
            connections = response.json().get("data", [])
            for conn in connections:
                if conn.get("unified_api") == "issue-tracking" and conn.get("enabled"):
                    service_id = conn.get("service_id")
                    print(f"Found active issue-tracking connection: {service_id}")
                    break
        else:
            print(f"Warning: Failed to fetch connections (status {response.status_code}): {response.text}")
    except Exception as e:
        print(f"Warning: Exception while fetching connections: {e}")

    if not service_id:
        # Fallback logic
        if env_collection_id == "REDACTED":
            service_id = "REDACTED"
        else:
            service_id = "github"
        print(f"Fallback: Using service_id '{service_id}'")

    # 3. Set up headers for API calls
    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": service_id,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # 4. Resolve the collection ID
    resolved_collection_id = env_collection_id
    try:
        collections_url = "https://unify.apideck.com/issue-tracking/collections"
        response = requests.get(collections_url, headers=headers)
        if response.status_code == 200:
            collections = response.json().get("data", [])
            for col in collections:
                if col.get("id") == env_collection_id or col.get("name") == env_collection_id:
                    resolved_collection_id = col.get("id")
                    print(f"Resolved collection ID from '{env_collection_id}' to '{resolved_collection_id}'")
                    break
        else:
            print(f"Warning: Failed to fetch collections (status {response.status_code}): {response.text}")
    except Exception as e:
        print(f"Warning: Exception while resolving collection: {e}")

    print(f"Using collection ID: {resolved_collection_id}")

    # 5. Choose a prefix
    prefix = f"epic-hierarchy-{run_id}"
    print(f"Chosen subject prefix: {prefix}")

    # 6. Create the parent ticket
    tickets_url = f"https://unify.apideck.com/issue-tracking/collections/{resolved_collection_id}/tickets"
    parent_data = {
        "subject": f"{prefix} - Parent Epic",
        "description": f"This is the parent epic ticket for run {run_id}"
    }

    print("Creating parent ticket...")
    try:
        response = requests.post(tickets_url, headers=headers, json=parent_data)
        if response.status_code not in (200, 201):
            print(f"Error creating parent ticket (status {response.status_code}): {response.text}")
            sys.exit(1)
        
        parent_ticket = response.json().get("data", {})
        parent_id = parent_ticket.get("id")
        if not parent_id:
            print(f"Error: Parent ticket ID not found in response: {response.text}")
            sys.exit(1)
        
        print(f"Successfully created parent ticket. ID: {parent_id}")
    except Exception as e:
        print(f"Exception while creating parent ticket: {e}")
        sys.exit(1)

    # 7. Create exactly three child tickets
    child_ids = []
    for i in range(1, 4):
        child_data = {
            "subject": f"{prefix} - Child Task {i}",
            "description": f"This is child task {i} for run {run_id}",
            "parent_id": parent_id
        }
        print(f"Creating child ticket {i}...")
        try:
            response = requests.post(tickets_url, headers=headers, json=child_data)
            if response.status_code not in (200, 201):
                print(f"Error creating child ticket {i} (status {response.status_code}): {response.text}")
                sys.exit(1)
            
            child_ticket = response.json().get("data", {})
            child_id = child_ticket.get("id")
            if not child_id:
                print(f"Error: Child ticket ID not found in response: {response.text}")
                sys.exit(1)
            
            child_ids.append(child_id)
            print(f"Successfully created child ticket {i}. ID: {child_id}")
        except Exception as e:
            print(f"Exception while creating child ticket {i}: {e}")
            sys.exit(1)

    # 8. Write the log artifact
    log_dir = "/home/user/apideck_task"
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "output.log")
    
    child_ids_str = ",".join(child_ids)
    
    log_content = (
        f"SUBJECT_PREFIX: {prefix}\n"
        f"PARENT_ID: {parent_id}\n"
        f"CHILD_IDS: {child_ids_str}\n"
    )
    
    try:
        with open(log_path, "w") as f:
            f.write(log_content)
        print(f"Successfully wrote log artifact to {log_path}")
        print("Log content:")
        print(log_content)
    except Exception as e:
        print(f"Error writing log artifact: {e}")
        sys.exit(1)

    print("All tasks completed successfully!")

if __name__ == "__main__":
    main()
