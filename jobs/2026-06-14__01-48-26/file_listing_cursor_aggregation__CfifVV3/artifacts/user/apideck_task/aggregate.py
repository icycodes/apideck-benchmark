import os
import sys
import json
import requests
import time

def main():
    # 1. Read environment variables
    app_id = os.getenv("APIDECK_APP_ID")
    api_key = os.getenv("APIDECK_API_KEY")
    consumer_id = os.getenv("APIDECK_CONSUMER_ID")
    drive_name = os.getenv("APIDECK_FILE_STORAGE_DRIVE_NAME")
    run_id = os.getenv("ZEALT_RUN_ID")

    if not all([app_id, api_key, consumer_id, drive_name, run_id]):
        print("Error: Missing one or more required environment variables.")
        sys.exit(1)

    print(f"Starting aggregation task for run: {run_id}")

    # 2. Query Vault connections to find the active file-storage service
    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id
    }

    try:
        conn_res = requests.get("https://unify.apideck.com/vault/connections", headers=headers)
        conn_res.raise_for_status()
        connections = conn_res.json().get("data", [])
    except Exception as e:
        print(f"Error fetching Vault connections: {e}")
        sys.exit(1)

    # Find the active file-storage service
    file_storage_conns = [c for c in connections if c.get("unified_api") == "file-storage" and c.get("enabled")]
    if not file_storage_conns:
        print("Error: No enabled file-storage connection found.")
        sys.exit(1)

    # If there are multiple, let's see if one matches the drive_name (e.g. REDACTED) or if onedrive/REDACTED is present
    service_id = None
    for conn in file_storage_conns:
        s_id = conn.get("service_id")
        if s_id == drive_name or s_id == "onedrive" or s_id == "REDACTED":
            service_id = s_id
            break
    if not service_id:
        service_id = file_storage_conns[0].get("service_id")

    print(f"Using file-storage service: {service_id}")

    # Headers for file-storage API calls
    fs_headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": service_id
    }

    # 3. If service is onedrive, find the drive_id
    drive_id = None
    if service_id == "onedrive":
        try:
            drives_res = requests.get("https://unify.apideck.com/file-storage/drives", headers=fs_headers)
            drives_res.raise_for_status()
            drives = drives_res.json().get("data", [])
            for d in drives:
                if d.get("name") == drive_name:
                    drive_id = d.get("id")
                    break
            if not drive_id:
                print(f"Warning: Drive matching '{drive_name}' not found. Available drives: {[d.get('name') for d in drives]}")
                # Fallback to first drive or raise error
                if drives:
                    drive_id = drives[0].get("id")
                    print(f"Falling back to first drive: {drives[0].get('name')} (ID: {drive_id})")
        except Exception as e:
            print(f"Error fetching drives: {e}")
            sys.exit(1)
        print(f"Resolved drive ID: {drive_id}")

    # 4. Clean up any pre-existing files with the same prefix to ensure exact 7 files
    prefix = f"AGG-{run_id}-"
    print(f"Cleaning up pre-existing files with prefix: {prefix}")
    
    # Let's list files to find any pre-existing ones
    cursor = None
    files_to_delete = []
    while True:
        params = {
            "filter[folder_id]": "root"
        }
        if drive_id:
            params["filter[drive_id]"] = drive_id
        if cursor:
            params["cursor"] = cursor
        
        try:
            list_res = requests.get("https://unify.apideck.com/file-storage/files", headers=fs_headers, params=params)
            list_res.raise_for_status()
            page_data = list_res.json()
            for item in page_data.get("data", []):
                if item.get("type") == "file" and item.get("name", "").startswith(prefix):
                    files_to_delete.append(item.get("id"))
            
            # Check next cursor
            cursor = page_data.get("meta", {}).get("cursors", {}).get("next")
            if not cursor:
                break
        except Exception as e:
            print(f"Error listing files for cleanup: {e}")
            break

    if files_to_delete:
        print(f"Found {len(files_to_delete)} matching files to delete.")
        for fid in files_to_delete:
            try:
                del_res = requests.delete(f"https://unify.apideck.com/file-storage/files/{fid}", headers=fs_headers)
                if del_res.status_code == 200:
                    print(f"Deleted old file ID: {fid}")
                else:
                    print(f"Failed to delete file ID {fid}: {del_res.status_code}")
            except Exception as e:
                print(f"Error deleting file ID {fid}: {e}")

    # 5. Upload 7 distinct small text files
    print("Uploading 7 files...")
    for i in range(1, 8):
        filename = f"{prefix}{i}.txt"
        content = f"Content of file {i} for run {run_id}."
        
        metadata = {
            "name": filename,
            "parent_folder_id": "root"
        }
        if drive_id:
            metadata["drive_id"] = drive_id

        upload_headers = {
            "Authorization": f"Bearer {api_key}",
            "x-apideck-app-id": app_id,
            "x-apideck-consumer-id": consumer_id,
            "x-apideck-service-id": service_id,
            "Content-Type": "text/plain",
            "x-apideck-metadata": json.dumps(metadata)
        }

        try:
            upload_res = requests.post("https://upload.apideck.com/file-storage/files", headers=upload_headers, data=content)
            upload_res.raise_for_status()
            res_json = upload_res.json()
            file_id = res_json.get("data", {}).get("id")
            print(f"Uploaded {filename} successfully. ID: {file_id}")
        except Exception as e:
            print(f"Error uploading {filename}: {e}")
            sys.exit(1)

    # 6. Walk the file listing using cursor pagination with page size of 3
    # We will retry the entire walk if we don't find exactly 7 files, up to 5 times, to handle eventual consistency.
    max_attempts = 5
    aggregated_ids = []
    for attempt in range(1, max_attempts + 1):
        print(f"Aggregating file IDs using cursor pagination with limit=3 (Attempt {attempt}/{max_attempts})...")
        aggregated_ids = []
        cursor = None
        page_num = 1
        success = True
        
        while True:
            params = {
                "filter[folder_id]": "root",
                "limit": 3
            }
            if drive_id:
                params["filter[drive_id]"] = drive_id
            if cursor:
                params["cursor"] = cursor

            try:
                list_res = requests.get("https://unify.apideck.com/file-storage/files", headers=fs_headers, params=params)
                list_res.raise_for_status()
                page_data = list_res.json()
                
                items = page_data.get("data", [])
                print(f"Page {page_num}: Retrieved {len(items)} items.")
                
                for item in items:
                    name = item.get("name", "")
                    if item.get("type") == "file" and name.startswith(prefix):
                        fid = item.get("id")
                        if fid not in aggregated_ids:
                            aggregated_ids.append(fid)
                            print(f"  Matched: {name} (ID: {fid})")
                
                # Check next cursor
                cursor = page_data.get("meta", {}).get("cursors", {}).get("next")
                if not cursor:
                    break
                else:
                    page_num += 1
            except Exception as e:
                print(f"Error during paginated file listing: {e}")
                success = False
                break
        
        if success and len(aggregated_ids) == 7:
            print(f"Success! Found exactly 7 matching files.")
            break
        else:
            print(f"Found {len(aggregated_ids)} matching files. Expected 7.")
            if attempt < max_attempts:
                print("Waiting 3 seconds before retrying listing walk...")
                time.sleep(3)
            else:
                print("Error: Could not find exactly 7 matching files after maximum attempts.")
                sys.exit(1)

    # 7. Write the JSON summary to output.log
    output_dir = "/home/user/apideck_task"
    os.makedirs(output_dir, exist_ok=True)
    log_file_path = os.path.join(output_dir, "output.log")
    
    summary = {
        "count": len(aggregated_ids),
        "ids": aggregated_ids
    }
    
    try:
        with open(log_file_path, "w") as f:
            json.dump(summary, f)
        print(f"Successfully wrote summary to {log_file_path}")
        print(json.dumps(summary, indent=2))
    except Exception as e:
        print(f"Error writing log file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
