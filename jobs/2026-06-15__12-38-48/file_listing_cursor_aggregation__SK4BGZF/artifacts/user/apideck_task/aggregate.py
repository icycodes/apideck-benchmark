import os
import sys
import json
import urllib.request
import urllib.parse
import urllib.error
import time

def get_env_var(name):
    val = os.environ.get(name)
    if not val:
        print(f"Error: Environment variable '{name}' is missing.")
        sys.exit(1)
    return val

def main():
    # Read environment variables
    app_id = get_env_var("APIDECK_APP_ID")
    api_key = get_env_var("APIDECK_API_KEY")
    consumer_id = get_env_var("APIDECK_CONSUMER_ID")
    drive_name = get_env_var("APIDECK_FILE_STORAGE_DRIVE_NAME")
    run_id = get_env_var("ZEALT_RUN_ID")
    
    print("=== Environment configuration ===")
    print(f"App ID: {app_id}")
    print(f"API Key: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")
    print(f"Consumer ID: {consumer_id}")
    print(f"Target Drive Name: {drive_name}")
    print(f"Zealt Run ID: {run_id}")
    print("=================================\n")

    # Common headers for Apideck Unify API
    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": "onedrive"
    }

    # Step 1: Retrieve OneDrive drive ID
    print("Step 1: Listing drives to find target drive ID...")
    drives_url = "https://unify.apideck.com/file-storage/drives"
    req = urllib.request.Request(drives_url, headers=headers)
    drive_id = None
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode())
            for drive in res_data.get("data", []):
                if drive.get("name") == drive_name:
                    drive_id = drive.get("id")
                    break
    except Exception as e:
        print("Failed to list drives:", e)
        sys.exit(1)
        
    if not drive_id:
        print(f"Error: Drive '{drive_name}' not found!")
        sys.exit(1)
        
    print(f"Found target drive ID: {drive_id}\n")

    # Step 2: Upload 7 distinct small text files
    print("Step 2: Uploading 7 distinct text files to the drive root...")
    prefix = f"AGG-{run_id}-"
    uploaded_files = []
    
    for i in range(1, 8):
        filename = f"{prefix}{i}.txt"
        file_content = f"File {i} of 7 for aggregation run {run_id}.".encode("utf-8")
        
        metadata = {
            "name": filename,
            "parent_folder_id": "root",
            "drive_id": drive_id
        }
        
        upload_url = "https://upload.apideck.com/file-storage/files"
        upload_headers = headers.copy()
        upload_headers["x-apideck-metadata"] = json.dumps(metadata)
        upload_headers["Content-Type"] = "text/plain"
        
        print(f"Uploading file {i}/7: {filename}...")
        
        # Retry logic for upload in case of temporary network glitches
        for attempt in range(3):
            try:
                req = urllib.request.Request(upload_url, data=file_content, headers=upload_headers, method="POST")
                with urllib.request.urlopen(req) as response:
                    res_data = json.loads(response.read().decode())
                    file_info = res_data.get("data", {})
                    uploaded_files.append({
                        "name": filename,
                        "id": file_info.get("id")
                    })
                    print(f"Successfully uploaded {filename} (ID: {file_info.get('id')})")
                    break
            except urllib.error.HTTPError as e:
                print(f"HTTP Error {e.code} during upload of {filename}: {e.reason}")
                print(e.read().decode())
                if attempt < 2:
                    print("Retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    sys.exit(1)
            except Exception as e:
                print(f"Error uploading {filename}: {e}")
                if attempt < 2:
                    print("Retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    sys.exit(1)
                    
    print("\nAll 7 files uploaded successfully!\n")

    # Step 3: Walk the file listing using cursor pagination with a page size of 3
    print("Step 3: Walking file listing with cursor pagination (limit=3)...")
    
    aggregated_ids = []
    cursor = None
    page_num = 1
    
    while True:
        params = {
            "limit": 3,
            "filter[drive_id]": drive_id,
            "filter[folder_id]": "root"
        }
        if cursor:
            params["cursor"] = cursor
            
        query_string = urllib.parse.urlencode(params)
        list_url = f"https://unify.apideck.com/file-storage/files?{query_string}"
        
        print(f"Fetching page {page_num}...")
        req = urllib.request.Request(list_url, headers=headers)
        
        try:
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode())
                items = res_data.get("data", [])
                meta = res_data.get("meta", {})
                
                print(f"Page {page_num} returned {len(items)} items.")
                
                for item in items:
                    name = item.get("name", "")
                    item_id = item.get("id")
                    if name.startswith(prefix):
                        print(f" - Match: {name} (ID: {item_id})")
                        aggregated_ids.append(item_id)
                    else:
                        print(f" - Skip: {name}")
                        
                next_cursor = meta.get("cursors", {}).get("next")
                if not next_cursor:
                    print("No more pages to fetch (next cursor is empty).")
                    break
                
                cursor = next_cursor
                page_num += 1
                
        except urllib.error.HTTPError as e:
            print(f"HTTP Error {e.code} during listing: {e.reason}")
            print(e.read().decode())
            sys.exit(1)
        except Exception as e:
            print("Error during listing:", e)
            sys.exit(1)

    print(f"\nAggregation completed. Found {len(aggregated_ids)} files matching prefix '{prefix}'.")
    print("Aggregated IDs:", aggregated_ids)

    # Step 4: Write JSON summary to /home/user/apideck_task/output.log
    output_log_path = "/home/user/apideck_task/output.log"
    print(f"\nStep 4: Writing summary to {output_log_path}...")
    
    summary = {
        "count": len(aggregated_ids),
        "ids": aggregated_ids
    }
    
    try:
        with open(output_log_path, "w") as f:
            json.dump(summary, f)
        print("Summary written successfully.")
    except Exception as e:
        print("Failed to write output.log:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
