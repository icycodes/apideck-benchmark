import os
import requests
import json

def verify():
    zealt_run_id = os.environ.get("ZEALT_RUN_ID")
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    file_storage_service = os.environ.get("APIDECK_FILE_STORAGE_DRIVE_NAME", "onedrive")
    issue_tracking_collection_env = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID", "github")
    issue_tracking_service = "REDACTED"

    print("=== Verification Script ===")
    
    # Load expected files from local JSON
    json_path = "/home/user/apideck_task/uploaded_files.json"
    if not os.path.exists(json_path):
        print(f"FAILURE: {json_path} does not exist. Run the task script first.")
        return
        
    with open(json_path, "r") as f:
        uploaded_files = json.load(f)

    # 1. Verify File Storage
    print("\n1. Verifying File Storage...")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": file_storage_service
    }
    
    all_files_exist = True
    for name, file_id in uploaded_files.items():
        url = f"https://unify.apideck.com/file-storage/files/{file_id}"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json().get("data", {})
                print(f"SUCCESS: File {name} exists with ID {file_id}. Path: {data.get('path')}")
            else:
                print(f"FAILURE: File {name} with ID {file_id} could not be retrieved. Status: {response.status_code}")
                all_files_exist = False
        except Exception as e:
            print(f"Error checking file {name}: {e}")
            all_files_exist = False

    if all_files_exist:
        print("SUCCESS: All 3 files verified successfully in file storage!")
    else:
        print("FAILURE: File verification failed.")

    # 2. Verify Issue Tracking
    print("\n2. Verifying Issue Tracking...")
    # List collections to find ID
    collections_url = "https://unify.apideck.com/issue-tracking/collections"
    collections_headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": issue_tracking_service
    }

    resolved_collection_id = issue_tracking_collection_env
    try:
        col_response = requests.get(collections_url, headers=collections_headers)
        if col_response.status_code == 200:
            collections = col_response.json().get("data", [])
            for col in collections:
                if col.get("name") == issue_tracking_collection_env or col.get("id") == issue_tracking_collection_env:
                    resolved_collection_id = col.get("id")
                    break
    except Exception as e:
        print(f"Error listing collections: {e}")

    tickets_url = f"https://unify.apideck.com/issue-tracking/collections/{resolved_collection_id}/tickets"
    tickets_headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": issue_tracking_service
    }

    try:
        response = requests.get(tickets_url, headers=tickets_headers)
        if response.status_code == 200:
            tickets_data = response.json().get("data", [])
            matching_tickets = []
            for t in tickets_data:
                subject = t.get("subject", "")
                if "[FILE-INDEX]" in subject and zealt_run_id in subject:
                    matching_tickets.append(t)
            
            print(f"Found {len(matching_tickets)} matching tickets in collection {resolved_collection_id}.")
            if len(matching_tickets) == 1:
                ticket = matching_tickets[0]
                print(f"SUCCESS: Exactly one matching ticket found!")
                print(f"Subject: {ticket.get('subject')}")
                print(f"Description:\n{ticket.get('description')}")
                
                # Check description matches sorted uploaded files
                sorted_fids = sorted(list(uploaded_files.values()))
                expected_desc = "\n".join(sorted_fids)
                
                actual_desc_lines = [line.strip() for line in ticket.get("description", "").split("\n") if line.strip()]
                actual_desc = "\n".join(actual_desc_lines)
                
                if actual_desc == expected_desc:
                    print("SUCCESS: Ticket description matches sorted file IDs exactly!")
                else:
                    print("FAILURE: Ticket description does not match sorted file IDs.")
                    print(f"Expected:\n{expected_desc}")
                    print(f"Actual:\n{actual_desc}")
            else:
                print("FAILURE: Did not find exactly one matching ticket.")
        else:
            print(f"Error listing tickets: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error during ticket verification: {e}")

if __name__ == "__main__":
    verify()
