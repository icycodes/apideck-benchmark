import os
import sys
import json
import requests

def main():
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    service_id = os.environ.get("APIDECK_FILE_STORAGE_DRIVE_NAME", "onedrive")
    zealt_run_id = os.environ.get("ZEALT_RUN_ID")

    if not all([api_key, app_id, consumer_id, zealt_run_id]):
        print("Error: Missing required environment variables.", file=sys.stderr)
        sys.exit(1)

    print(f"Starting folder reorganization for run ID: {zealt_run_id}")
    print(f"Using service ID: {service_id}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": service_id,
        "Content-Type": "application/json"
    }

    outer_name = f"OUTER-{zealt_run_id}"
    inner_name = f"INNER-{zealt_run_id}"
    inner_renamed_name = f"INNER-RENAMED-{zealt_run_id}"

    # Step 1: Create OUTER folder at root
    print(f"Creating OUTER folder: {outer_name}")
    payload = {
        "name": outer_name,
        "parent_folder_id": "root"
    }
    res = requests.post("https://unify.apideck.com/file-storage/folders", headers=headers, json=payload)
    if res.status_code not in (200, 201):
        print(f"Error creating OUTER folder: {res.status_code} - {res.text}", file=sys.stderr)
        sys.exit(1)
    outer_id = res.json()["data"]["id"]
    print(f"Successfully created OUTER folder (ID: {outer_id})")

    # Step 2: Create INNER folder at root
    print(f"Creating INNER folder: {inner_name}")
    payload = {
        "name": inner_name,
        "parent_folder_id": "root"
    }
    res = requests.post("https://unify.apideck.com/file-storage/folders", headers=headers, json=payload)
    if res.status_code not in (200, 201):
        print(f"Error creating INNER folder: {res.status_code} - {res.text}", file=sys.stderr)
        sys.exit(1)
    inner_id = res.json()["data"]["id"]
    print(f"Successfully created INNER folder (ID: {inner_id})")

    # Step 3: Rename and move INNER folder via PATCH
    print(f"Renaming and moving INNER folder (ID: {inner_id}) to {inner_renamed_name} inside OUTER folder (ID: {outer_id})...")
    payload = {
        "name": inner_renamed_name,
        "parent_folder_id": outer_id
    }
    res = requests.patch(f"https://unify.apideck.com/file-storage/folders/{inner_id}", headers=headers, json=payload)
    if res.status_code not in (200, 201):
        print(f"Error renaming/moving INNER folder: {res.status_code} - {res.text}", file=sys.stderr)
        sys.exit(1)
    print("Successfully renamed and moved INNER folder.")

    # Step 4: Verify the final state of OUTER folder
    print("Verifying OUTER folder...")
    res = requests.get(f"https://unify.apideck.com/file-storage/folders/{outer_id}", headers=headers)
    if res.status_code != 200:
        print(f"Error fetching OUTER folder: {res.status_code} - {res.text}", file=sys.stderr)
        sys.exit(1)
    outer_info = res.json().get("data", {})
    print(f"OUTER folder verified: {outer_info.get('name')} (ID: {outer_info.get('id')})")

    # Step 5: Verify the final state of INNER-RENAMED folder
    print("Verifying INNER-RENAMED folder...")
    res = requests.get(f"https://unify.apideck.com/file-storage/folders/{inner_id}", headers=headers)
    if res.status_code != 200:
        print(f"Error fetching INNER-RENAMED folder: {res.status_code} - {res.text}", file=sys.stderr)
        sys.exit(1)
    
    inner_info = res.json().get("data", {})
    actual_name = inner_info.get("name")
    parent_folders = inner_info.get("parent_folders", [])
    
    print(f"INNER-RENAMED folder verified: Name={actual_name}, Parents={parent_folders}")
    
    if actual_name != inner_renamed_name:
        print(f"Error: Expected name '{inner_renamed_name}', got '{actual_name}'", file=sys.stderr)
        sys.exit(1)

    # Step 6: Write output log
    log_data = {
        "outer_id": outer_id,
        "inner_id": inner_id
    }
    
    log_path = "/home/user/apideck_task/output.log"
    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2)
    
    print(f"Successfully wrote log to {log_path}")
    print(json.dumps(log_data, indent=2))

if __name__ == "__main__":
    main()
