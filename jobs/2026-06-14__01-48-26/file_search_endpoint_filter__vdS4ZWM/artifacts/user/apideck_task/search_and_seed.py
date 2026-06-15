import os
import requests
import json
import time

def main():
    # 1. Read environment variables
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    run_id = os.environ.get("ZEALT_RUN_ID")
    drive_name = os.environ.get("APIDECK_FILE_STORAGE_DRIVE_NAME")

    if not all([api_key, app_id, consumer_id, run_id]):
        print("Missing required environment variables.")
        return

    # 2. Resolve the service ID dynamically by listing connections
    print("Listing connections to find file-storage service...")
    service_id = "REDACTED"  # fallback default
    try:
        r = requests.get(
            "https://unify.apideck.com/vault/connections",
            headers={
                "Authorization": f"Bearer {api_key}",
                "x-apideck-app-id": app_id,
                "x-apideck-consumer-id": consumer_id,
            }
        )
        if r.status_code == 200:
            connections = r.json().get("data", [])
            for conn in connections:
                if conn.get("unified_api") == "file-storage" and conn.get("integration_state") == "configured":
                    service_id = conn.get("service_id")
                    print(f"Found active file-storage service: {service_id}")
                    break
        else:
            print(f"Failed to list connections: {r.status_code} - {r.text}")
    except Exception as e:
        print("Error listing connections:", e)

    # 3. Resolve drive ID if drives are supported by the service
    print(f"Attempting to resolve drive ID for drive name: '{drive_name}'...")
    drive_id = None
    try:
        r = requests.get(
            "https://unify.apideck.com/file-storage/drives",
            headers={
                "Authorization": f"Bearer {api_key}",
                "x-apideck-app-id": app_id,
                "x-apideck-consumer-id": consumer_id,
                "x-apideck-service-id": service_id,
            }
        )
        if r.status_code == 200:
            drives = r.json().get("data", [])
            for d in drives:
                if d.get("name") == drive_name:
                    drive_id = d.get("id")
                    print(f"Found matching drive: '{drive_name}' with ID: {drive_id}")
                    break
            if not drive_id:
                print(f"No drive found matching name '{drive_name}'. Available drives: {[d.get('name') for d in drives]}")
        else:
            print(f"Listing drives returned status {r.status_code}: {r.text}")
    except Exception as e:
        print("Error listing drives:", e)

    # 4. Upload exactly four files
    files_to_upload = [
        (f"KEEP-{run_id}-1.txt", "Keep file 1 content"),
        (f"KEEP-{run_id}-2.txt", "Keep file 2 content"),
        (f"SKIP-{run_id}-1.txt", "Skip file 1 content"),
        (f"SKIP-{run_id}-2.txt", "Skip file 2 content"),
    ]

    uploaded_ids = {}
    for filename, content in files_to_upload:
        print(f"Uploading file: {filename}...")
        metadata = {
            "name": filename,
            "parent_folder_id": "root"
        }
        if drive_id:
            metadata["drive_id"] = drive_id

        headers = {
            "Authorization": f"Bearer {api_key}",
            "x-apideck-app-id": app_id,
            "x-apideck-consumer-id": consumer_id,
            "x-apideck-service-id": service_id,
            "x-apideck-metadata": json.dumps(metadata),
            "Content-Type": "text/plain",
        }

        try:
            r = requests.post(
                "https://upload.apideck.com/file-storage/files",
                headers=headers,
                data=content.encode('utf-8')
            )
            if r.status_code in (200, 201):
                file_id = r.json().get("data", {}).get("id")
                print(f"Successfully uploaded {filename}. ID: {file_id}")
                uploaded_ids[filename] = file_id
            else:
                print(f"Failed to upload {filename}: {r.status_code} - {r.text}")
        except Exception as e:
            print(f"Exception during upload of {filename}:", e)

    # 5. Search files with query KEEP-{run-id}
    # We will poll/retry to allow for indexing propagation, ensuring we find both KEEP files.
    print(f"Searching for files with query 'KEEP-{run_id}'...")
    search_result_ids = []
    
    # We poll up to 10 times, sleeping between attempts
    for attempt in range(1, 11):
        print(f"Search attempt {attempt}/10...")
        current_attempt_ids = []
        cursor = None
        search_failed = False
        
        while True:
            params = {}
            if cursor:
                params["cursor"] = cursor

            headers = {
                "Authorization": f"Bearer {api_key}",
                "x-apideck-app-id": app_id,
                "x-apideck-consumer-id": consumer_id,
                "x-apideck-service-id": service_id,
                "Content-Type": "application/json",
            }
            body = {
                "query": f"KEEP-{run_id}"
            }

            try:
                r = requests.post(
                    "https://unify.apideck.com/file-storage/files/search",
                    headers=headers,
                    params=params,
                    json=body
                )
                if r.status_code == 200:
                    res_json = r.json()
                    data = res_json.get("data", [])
                    for file_info in data:
                        name = file_info.get("name")
                        if name in (f"KEEP-{run_id}-1.txt", f"KEEP-{run_id}-2.txt"):
                            file_id = file_info.get("id")
                            if file_id not in current_attempt_ids:
                                current_attempt_ids.append(file_id)
                    
                    next_cursor = res_json.get("meta", {}).get("cursors", {}).get("next")
                    if next_cursor:
                        cursor = next_cursor
                    else:
                        break
                else:
                    print(f"Search API returned {r.status_code}: {r.text}")
                    search_failed = True
                    break
            except Exception as e:
                print("Exception during search:", e)
                search_failed = True
                break
        
        if not search_failed and len(current_attempt_ids) == 2:
            print(f"Successfully found both KEEP files in search! IDs: {current_attempt_ids}")
            search_result_ids = current_attempt_ids
            break
        else:
            print(f"Only found {len(current_attempt_ids)} of 2 files. Retrying in 5 seconds...")
            time.sleep(5)

    # 6. Persist JSON object to output log file
    log_dir = "/home/user/apideck_task"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "output.log")
    
    output_data = {
        "search_result_ids": search_result_ids
    }
    
    print(f"Writing result to {log_file_path}...")
    with open(log_file_path, "w") as f:
        f.write(json.dumps(output_data) + "\n")
    
    print("Done!")

if __name__ == "__main__":
    main()
