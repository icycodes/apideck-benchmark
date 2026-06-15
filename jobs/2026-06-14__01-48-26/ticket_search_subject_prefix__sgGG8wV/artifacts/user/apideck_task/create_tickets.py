import os
import sys
import json
import requests

def resolve_service_and_collection():
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    collection_env = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
    }
    
    r = requests.get("https://unify.apideck.com/vault/connections", headers=headers)
    r.raise_for_status()
    connections = r.json().get("data", [])
    
    service_id = None
    for conn in connections:
        if conn.get("unified_api") == "issue-tracking" and conn.get("state") == "callable":
            service_id = conn.get("service_id")
            break
            
    if not service_id:
        for conn in connections:
            if conn.get("unified_api") == "issue-tracking":
                service_id = conn.get("service_id")
                break
        if not service_id:
            service_id = "github"
            
    print(f"Resolved service_id: {service_id}")
    
    headers["x-apideck-service-id"] = service_id
    r = requests.get("https://unify.apideck.com/issue-tracking/collections", headers=headers)
    r.raise_for_status()
    collections = r.json().get("data", [])
    
    collection_id = None
    for col in collections:
        if col.get("id") == collection_env:
            collection_id = col.get("id")
            break
    if not collection_id:
        for col in collections:
            if col.get("name") == collection_env:
                collection_id = col.get("id")
                break
                
    if not collection_id:
        collection_id = collection_env
        
    print(f"Resolved collection_id: {collection_id}")
    return service_id, collection_id

def create_tickets():
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    zealt_run_id = os.environ.get("ZEALT_RUN_ID")

    if not all([api_key, app_id, consumer_id, zealt_run_id]):
        print("Error: Missing required environment variables.")
        sys.exit(1)

    service_id, collection_id = resolve_service_and_collection()

    url = f"https://unify.apideck.com/issue-tracking/collections/{collection_id}/tickets"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": service_id,
        "accept": "application/json",
        "content-type": "application/json"
    }

    matching_ids = []
    other_ids = []

    # Exactly 4 matching tickets
    for i in range(1, 5):
        subject = f"SEARCH-MATCH-{zealt_run_id}-{i}"
        payload = {
            "subject": subject,
            "description": f"Matching ticket {i} for run {zealt_run_id}"
        }
        print(f"Creating matching ticket {i}: {subject}...")
        r = requests.post(url, json=payload, headers=headers)
        if r.status_code != 201:
            print(f"Failed to create matching ticket {i}. Status: {r.status_code}. Response: {r.text}")
            sys.exit(1)
        
        ticket_id = r.json()["data"]["id"]
        print(f"Successfully created matching ticket {i} with ID: {ticket_id}")
        matching_ids.append(ticket_id)

    # Exactly 2 other tickets
    for i in range(1, 3):
        subject = f"SEARCH-OTHER-{zealt_run_id}-{i}"
        payload = {
            "subject": subject,
            "description": f"Other ticket {i} for run {zealt_run_id}"
        }
        print(f"Creating other ticket {i}: {subject}...")
        r = requests.post(url, json=payload, headers=headers)
        if r.status_code != 201:
            print(f"Failed to create other ticket {i}. Status: {r.status_code}. Response: {r.text}")
            sys.exit(1)
            
        ticket_id = r.json()["data"]["id"]
        print(f"Successfully created other ticket {i} with ID: {ticket_id}")
        other_ids.append(ticket_id)

    # Prepare output JSON
    output = {
        "matching_ids": matching_ids,
        "other_ids": other_ids
    }

    output_path = "/home/user/apideck_task/output.log"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
        f.write("\n")

    print(f"Successfully wrote output to {output_path}")
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    create_tickets()
