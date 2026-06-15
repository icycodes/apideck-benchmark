import os
import requests
import json

def main():
    # 1. Read environment variables
    zealt_run_id = os.environ.get("ZEALT_RUN_ID")
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    file_storage_service = os.environ.get("APIDECK_FILE_STORAGE_DRIVE_NAME", "onedrive")
    issue_tracking_collection_env = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID", "github")

    print("--- Environment Configuration ---")
    print(f"ZEALT_RUN_ID: {zealt_run_id}")
    print(f"File Storage Service ID: {file_storage_service}")
    print(f"Issue Tracking Collection Env: {issue_tracking_collection_env}")

    if not all([zealt_run_id, api_key, app_id, consumer_id]):
        print("Error: Missing required environment variables.")
        return

    # 2. Upload the three text files to OneDrive / Dropbox root
    filenames = [
        f"REPORT-{zealt_run_id}-A.txt",
        f"REPORT-{zealt_run_id}-B.txt",
        f"REPORT-{zealt_run_id}-C.txt"
    ]

    file_ids = []
    file_info = {}

    print("\n--- Uploading Files ---")
    for name in filenames:
        content = f"Report content for {name} with run ID {zealt_run_id}."
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "x-apideck-app-id": app_id,
            "x-apideck-consumer-id": consumer_id,
            "x-apideck-service-id": file_storage_service,
            "x-apideck-metadata": json.dumps({
                "name": name,
                "parent_folder_id": "root"
            }),
            "Content-Type": "text/plain"
        }

        url = "https://upload.apideck.com/file-storage/files"
        try:
            response = requests.post(url, headers=headers, data=content.encode('utf-8'))
            if response.status_code in [200, 201]:
                resp_json = response.json()
                file_id = resp_json.get("data", {}).get("id")
                print(f"Successfully uploaded {name} -> File ID: {file_id}")
                file_ids.append(file_id)
                file_info[name] = file_id
            else:
                print(f"Failed to upload {name}. Status: {response.status_code}")
                print(response.text)
                return
        except Exception as e:
            print(f"Error uploading {name}: {e}")
            return

    if len(file_ids) != 3:
        print("Error: Did not get exactly 3 file IDs.")
        return

    # Write uploaded files info to JSON file
    with open("/home/user/apideck_task/uploaded_files.json", "w") as f:
        json.dump(file_info, f, indent=2)

    # 3. Sort file IDs in ascending order
    sorted_file_ids = sorted(file_ids)
    description = "\n".join(sorted_file_ids)
    
    print("\n--- Sorted File IDs ---")
    print(description)

    # 4. Resolve the collection ID for issue tracking
    print("\n--- Resolving Issue Tracking Collection ID ---")
    issue_tracking_service = "REDACTED" # Default service ID for this environment
    
    # Let's list collections to find the matching collection ID
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
                    print(f"Resolved collection name '{issue_tracking_collection_env}' to ID: {resolved_collection_id}")
                    break
        else:
            print(f"Warning: Failed to list collections. Status: {col_response.status_code}")
    except Exception as e:
        print(f"Warning: Error listing collections: {e}")

    print(f"Using Collection ID: {resolved_collection_id}")

    # 5. Create the issue tracking ticket
    ticket_subject = f"[FILE-INDEX] - {zealt_run_id}"
    ticket_payload = {
        "subject": ticket_subject,
        "description": description
    }

    ticket_headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": issue_tracking_service,
        "Content-Type": "application/json"
    }

    ticket_url = f"https://unify.apideck.com/issue-tracking/collections/{resolved_collection_id}/tickets"

    print("\n--- Creating Ticket ---")
    try:
        ticket_response = requests.post(ticket_url, headers=ticket_headers, json=ticket_payload)
        if ticket_response.status_code in [200, 201]:
            ticket_data = ticket_response.json().get("data", {})
            print("Successfully created ticket!")
            print(f"Ticket ID: {ticket_data.get('id')}")
            print(f"Subject: {ticket_data.get('subject')}")
            print(f"Description:\n{ticket_data.get('description')}")
        else:
            print(f"Failed to create ticket. Status: {ticket_response.status_code}")
            print(ticket_response.text)
    except Exception as e:
        print(f"Error creating ticket: {e}")

if __name__ == "__main__":
    main()
