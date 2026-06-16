import os
import sys
import json
import time
import requests

def main():
    # 1. Read environment variables
    run_id = os.environ.get("ZEALT_RUN_ID")
    drive_name = os.environ.get("APIDECK_FILE_STORAGE_DRIVE_NAME")
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    service_id = "onedrive"

    print(f"ZEALT_RUN_ID: {run_id}")
    print(f"APIDECK_FILE_STORAGE_DRIVE_NAME: {drive_name}")
    print(f"APIDECK_APP_ID: {app_id}")
    print(f"APIDECK_CONSUMER_ID: {consumer_id}")

    if not all([run_id, drive_name, api_key, app_id, consumer_id]):
        print("Error: Missing one or more required environment variables.")
        sys.exit(1)

    # 2. Resolve Drive ID
    print("\nResolving drive ID...")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": service_id
    }
    
    drives_url = "https://unify.apideck.com/file-storage/drives"
    try:
        r = requests.get(drives_url, headers=headers)
        r.raise_for_status()
        drives_data = r.json()
    except Exception as e:
        print(f"Error fetching drives: {e}")
        if 'r' in locals():
            print(f"Response: {r.text}")
        sys.exit(1)

    drive_id = None
    for drive in drives_data.get("data", []):
        if drive.get("name") == drive_name:
            drive_id = drive.get("id")
            break

    if not drive_id:
        print(f"Error: Drive named '{drive_name}' not found.")
        sys.exit(1)

    print(f"Resolved Drive ID for '{drive_name}': {drive_id}")

    # 3. Check if files are already uploaded
    files_to_upload = [
        f"KEEP-{run_id}-1.txt",
        f"KEEP-{run_id}-2.txt",
        f"SKIP-{run_id}-1.txt",
        f"SKIP-{run_id}-2.txt"
    ]

    print("\nChecking if files are already uploaded...")
    existing_files = {}
    cursor = None
    files_url = "https://unify.apideck.com/file-storage/files"
    
    try:
        while True:
            params = {"filter[drive_id]": drive_id}
            if cursor:
                params["cursor"] = cursor
            r = requests.get(files_url, headers=headers, params=params)
            r.raise_for_status()
            data = r.json()
            for f in data.get("data", []):
                name = f.get("name")
                if name in files_to_upload:
                    existing_files[name] = f.get("id")
            cursor = data.get("meta", {}).get("cursors", {}).get("next")
            if not cursor:
                break
    except Exception as e:
        print(f"Warning: Error listing files to check existence: {e}")

    all_exist = all(fname in existing_files for fname in files_to_upload)

    if all_exist:
        print("All four files already exist on the drive. Skipping upload!")
        uploaded_files = existing_files
    else:
        print("Not all files exist. Uploading missing files...")
        uploaded_files = existing_files
        upload_url = "https://upload.apideck.com/file-storage/files"

        for fname in files_to_upload:
            if fname in uploaded_files:
                print(f"File {fname} already exists, skipping upload.")
                continue
                
            metadata = {
                "name": fname,
                "parent_folder_id": "root",
                "drive_id": drive_id
            }
            upload_headers = {
                "Authorization": f"Bearer {api_key}",
                "x-apideck-app-id": app_id,
                "x-apideck-consumer-id": consumer_id,
                "x-apideck-service-id": service_id,
                "x-apideck-metadata": json.dumps(metadata),
                "Content-Type": "text/plain"
            }
            file_content = f"Content of {fname} with run_id {run_id}."
            
            try:
                print(f"Uploading {fname}...")
                r = requests.post(upload_url, headers=upload_headers, data=file_content.encode('utf-8'))
                r.raise_for_status()
                res_json = r.json()
                file_id = res_json.get("data", {}).get("id")
                uploaded_files[fname] = file_id
                print(f"Successfully uploaded {fname} -> ID: {file_id}")
            except Exception as e:
                print(f"Error uploading {fname}: {e}")
                if 'r' in locals():
                    print(f"Response: {r.text}")
                sys.exit(1)

    # 4. Search for KEEP files with polling
    print("\nSearching for KEEP files...")
    search_url = "https://unify.apideck.com/file-storage/files/search"
    search_query = f"KEEP-{run_id}"

    target_files = [f"KEEP-{run_id}-1.txt", f"KEEP-{run_id}-2.txt"]
    found_ids = {}

    max_attempts = 60  # Wait up to 10 minutes (60 * 10 seconds)
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        print(f"Search attempt {attempt}/{max_attempts}...")
        
        current_attempt_found = {}
        cursor = None
        
        while True:
            params = {
                "filter[drive_id]": drive_id
            }
            if cursor:
                params["cursor"] = cursor
                
            body = {
                "query": search_query
            }
            
            try:
                r = requests.post(search_url, headers=headers, params=params, json=body)
                r.raise_for_status()
                res_data = r.json()
            except Exception as e:
                print(f"Error searching files: {e}")
                if 'r' in locals():
                    print(f"Response: {r.text}")
                break
            
            for file_item in res_data.get("data", []):
                name = file_item.get("name")
                fid = file_item.get("id")
                if name in target_files:
                    current_attempt_found[name] = fid
            
            cursor = res_data.get("meta", {}).get("cursors", {}).get("next")
            if not cursor:
                break
        
        print(f"Found on this attempt: {list(current_attempt_found.keys())}")
        
        if len(current_attempt_found) == 2:
            found_ids = current_attempt_found
            print("Successfully found both target KEEP files!")
            break
            
        print("Waiting 10 seconds for indexing before retrying...")
        time.sleep(10)

    if len(found_ids) != 2:
        print("Error: Could not find both target KEEP files in search results after maximum attempts.")
        sys.exit(1)

    # 5. Persist matching KEEP file IDs to log file
    output_log_path = "/home/user/apideck_task/output.log"
    os.makedirs(os.path.dirname(output_log_path), exist_ok=True)
    
    result_ids = [found_ids[f"KEEP-{run_id}-1.txt"], found_ids[f"KEEP-{run_id}-2.txt"]]
    output_data = {
        "search_result_ids": result_ids
    }
    
    with open(output_log_path, "w") as f:
        json.dump(output_data, f)
        f.write("\n")
        
    print(f"\nSuccessfully wrote search results to {output_log_path}")
    print(json.dumps(output_data))

if __name__ == "__main__":
    main()
