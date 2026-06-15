import os
import urllib.request
import json
import sys

def main():
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    collection_env = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    zealt_run_id = os.environ.get("ZEALT_RUN_ID")

    if not all([api_key, app_id, consumer_id, collection_env, zealt_run_id]):
        print("Missing required environment variables.")
        sys.exit(1)

    headers_base = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
    }

    # 1. Resolve service ID (by finding the enabled issue-tracking connection)
    print("Fetching connections to resolve service ID...")
    req = urllib.request.Request("https://unify.apideck.com/vault/connections", headers=headers_base, method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            connections_data = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print("Failed to fetch connections:", e)
        sys.exit(1)

    service_id = None
    for conn in connections_data.get("data", []):
        sid = conn.get("service_id")
        if conn.get("enabled") and sid != "REDACTED":
            service_id = sid
            break

    if not service_id:
        print("Could not resolve issue-tracking service ID from connections. Defaulting to REDACTED.")
        service_id = "REDACTED"
    else:
        print(f"Resolved service ID: {service_id}")

    headers_service = headers_base.copy()
    headers_service["x-apideck-service-id"] = service_id

    # 2. Resolve collection ID (by listing collections and matching name or id)
    print("Fetching collections to resolve collection ID...")
    req = urllib.request.Request("https://unify.apideck.com/issue-tracking/collections", headers=headers_service, method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            collections_data = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print("Failed to fetch collections:", e)
        sys.exit(1)

    collection_id = None
    for col in collections_data.get("data", []):
        col_id = str(col.get("id"))
        col_name = col.get("name")
        if collection_env in (col_id, col_name):
            collection_id = col_id
            break

    if not collection_id:
        print(f"Could not resolve collection matching {collection_env}. Using default.")
        collection_id = collection_env
    else:
        print(f"Resolved collection ID: {collection_id}")

    # 3. Fetch users and find the lexicographically smallest user ID
    users_url = f"https://unify.apideck.com/issue-tracking/collections/{collection_id}/users"
    print(f"Fetching users from {users_url}...")
    req = urllib.request.Request(users_url, headers=headers_service, method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            users_data = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print("Failed to fetch users:", e)
        sys.exit(1)

    users = users_data.get("data", [])
    if not users:
        print("No users found in collection.")
        sys.exit(1)

    user_ids = [str(u.get("id")) for u in users if u.get("id") is not None]
    if not user_ids:
        print("No valid user IDs found.")
        sys.exit(1)

    user_ids.sort()
    smallest_user_id = user_ids[0]
    print(f"Lexicographically smallest user ID: {smallest_user_id}")

    # 4. Clean up any existing tickets with the same run ID and [USER-ASSIGN] in their subject
    tickets_url = f"https://unify.apideck.com/issue-tracking/collections/{collection_id}/tickets"
    print(f"Checking for existing tickets with subject containing '[USER-ASSIGN]' and '{zealt_run_id}'...")
    req = urllib.request.Request(tickets_url, headers=headers_service, method="GET")
    existing_tickets = []
    try:
        with urllib.request.urlopen(req) as response:
            tickets_data = json.loads(response.read().decode("utf-8"))
            existing_tickets = tickets_data.get("data", [])
    except Exception as e:
        print("Failed to fetch existing tickets:", e)

    target_subject = f"[USER-ASSIGN] {zealt_run_id}"
    for ticket in existing_tickets:
        subj = ticket.get("subject", "")
        if "[USER-ASSIGN]" in subj and zealt_run_id in subj:
            tid = ticket.get("id")
            print(f"Deleting existing matching ticket ID: {tid} ('{subj}')...")
            del_url = f"{tickets_url}/{tid}"
            del_req = urllib.request.Request(del_url, headers=headers_service, method="DELETE")
            try:
                with urllib.request.urlopen(del_req) as del_res:
                    print(f"Deleted ticket ID {tid}. Status:", del_res.status)
            except Exception as e:
                print(f"Failed to delete ticket ID {tid}:", e)

    # 5. Create a new ticket
    payload = {
        "subject": target_subject,
        "description": "Created by automated integration script.",
        "assignees": [
            {
                "id": smallest_user_id
            }
        ]
    }
    
    print(f"Creating new ticket with payload:")
    print(json.dumps(payload, indent=2))
    
    data_bytes = json.dumps(payload).encode("utf-8")
    headers_post = headers_service.copy()
    headers_post["Content-Type"] = "application/json"
    
    req = urllib.request.Request(tickets_url, data=data_bytes, headers=headers_post, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            res_data = json.loads(res_body)
            new_ticket_id = res_data.get("data", {}).get("id")
            print(f"Successfully created ticket! ID: {new_ticket_id}")
    except urllib.error.HTTPError as e:
        print("HTTP Error creating ticket:", e.code, e.reason)
        print("Response:", e.read().decode("utf-8"))
        sys.exit(1)
    except Exception as e:
        print("Error creating ticket:", e)
        sys.exit(1)

    # 6. Write evidence to log file
    log_dir = "/home/user/apideck_task"
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "output.log")
    
    with open(log_path, "w") as f:
        f.write(f"Ticket ID: {new_ticket_id}\n")
    
    print(f"Successfully wrote to log file at {log_path}")

if __name__ == "__main__":
    main()
