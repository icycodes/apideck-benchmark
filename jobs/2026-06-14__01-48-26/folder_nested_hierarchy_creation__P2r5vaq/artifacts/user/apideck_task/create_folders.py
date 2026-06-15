import os
import json
import requests

def main():
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    drive_name_target = os.environ.get("APIDECK_FILE_STORAGE_DRIVE_NAME")
    run_id = os.environ.get("ZEALT_RUN_ID")

    if not all([api_key, app_id, consumer_id, drive_name_target, run_id]):
        print("Error: Missing required environment variables.")
        return

    print("--- Environment Variables ---")
    print(f"API Key: {api_key[:10]}...")
    print(f"App ID: {app_id}")
    print(f"Consumer ID: {consumer_id}")
    print(f"Drive Name Target: {drive_name_target}")
    print(f"Run ID: {run_id}")
    print("-----------------------------")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "Content-Type": "application/json"
    }

    base_url = "https://unify.apideck.com"

    # Step 1: Detect the active service ID for file-storage
    active_service = None
    conn_url = f"{base_url}/vault/connections"
    try:
        conn_resp = requests.get(conn_url, headers=headers)
        if conn_resp.status_code == 200:
            conns = conn_resp.json().get("data", [])
            active_file_storage = [
                c for c in conns 
                if c.get("unified_api") == "file-storage" and c.get("state") == "callable"
            ]
            if active_file_storage:
                # If onedrive is active, prefer it. Otherwise, use the first active file-storage service.
                onedrive_active = [c for c in active_file_storage if c.get("service_id") == "onedrive"]
                if onedrive_active:
                    active_service = "onedrive"
                else:
                    active_service = active_file_storage[0].get("service_id")
    except Exception as e:
        print(f"Error checking active connections: {e}")

    # Fallback to onedrive if auto-detection failed
    if not active_service:
        active_service = "onedrive"

    print(f"Using service ID: {active_service}")
    headers["x-apideck-service-id"] = active_service

    # Step 2: Resolve the drive ID if the service supports drives
    drive_id = None
    try:
        drives_url = f"{base_url}/file-storage/drives"
        drives_resp = requests.get(drives_url, headers=headers)
        if drives_resp.status_code == 200:
            drives_data = drives_resp.json().get("data", [])
            for d in drives_data:
                if d.get("name") == drive_name_target:
                    drive_id = d.get("id")
                    print(f"Resolved drive ID for '{drive_name_target}': {drive_id}")
                    break
            if not drive_id and drives_data:
                drive_id = drives_data[0].get("id")
                print(f"Drive '{drive_name_target}' not found. Falling back to first drive ID: {drive_id}")
        else:
            print(f"Drives endpoint returned status {drives_resp.status_code}. Skipping drive_id resolution.")
    except Exception as e:
        print(f"Error resolving drive ID: {e}")

    # Step 3: Create the 4-level nested folder tree
    folder_names = [
        f"LEVEL1-{run_id}",
        "LEVEL2",
        "LEVEL3",
        "LEVEL4"
    ]

    folder_ids = []
    parent_folder_id = "root"

    for i, name in enumerate(folder_names):
        print(f"Creating folder '{name}' with parent '{parent_folder_id}'...")
        url = f"{base_url}/file-storage/folders"
        payload = {
            "name": name,
            "parent_folder_id": parent_folder_id
        }
        if drive_id:
            payload["drive_id"] = drive_id

        response = requests.post(url, headers=headers, json=payload)
        print(f"POST {url} status: {response.status_code}")
        if response.status_code not in [200, 201]:
            print("Response:", response.text)
            response.raise_for_status()

        resp_data = response.json()
        folder_id = resp_data.get("data", {}).get("id")
        if not folder_id:
            raise ValueError(f"No folder ID returned in response for '{name}'")
        
        print(f"Successfully created '{name}' with ID: {folder_id}")
        folder_ids.append(folder_id)
        parent_folder_id = folder_id

    # Step 4: Persist the folder IDs to output.log
    output_log_path = "/home/user/apideck_task/output.log"
    output_data = {
        "level1_id": folder_ids[0],
        "level2_id": folder_ids[1],
        "level3_id": folder_ids[2],
        "level4_id": folder_ids[3]
    }

    with open(output_log_path, "w") as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Successfully saved folder IDs to {output_log_path}")
    print(json.dumps(output_data, indent=2))

if __name__ == "__main__":
    main()
