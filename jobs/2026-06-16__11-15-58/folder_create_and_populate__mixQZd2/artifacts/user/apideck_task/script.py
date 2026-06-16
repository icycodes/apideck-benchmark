import os
import json
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError

def main():
    run_id = os.environ.get("ZEALT_RUN_ID")
    drive_name = os.environ.get("APIDECK_FILE_STORAGE_DRIVE_NAME")
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    
    if not all([run_id, drive_name, api_key, app_id, consumer_id]):
        print("Missing required environment variables")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": "onedrive"
    }

    # 1. Get drives
    req = urllib.request.Request("https://unify.apideck.com/file-storage/drives", headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode())
    except HTTPError as e:
        print(f"Error getting drives: {e.read().decode()}")
        return

    drive_id = None
    for drive in res_data.get("data", []):
        if drive.get("name") == drive_name:
            drive_id = drive.get("id")
            break
            
    if not drive_id:
        print(f"Drive {drive_name} not found")
        return

    # 2. Create folder
    folder_name = f"FOLDER-{run_id}"
    folder_payload = json.dumps({
        "name": folder_name,
        "parent_folder_id": "root",
        "drive_id": drive_id
    }).encode()
    
    folder_headers = headers.copy()
    folder_headers["Content-Type"] = "application/json"
    
    req = urllib.request.Request("https://unify.apideck.com/file-storage/folders", data=folder_payload, headers=folder_headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            folder_res = json.loads(response.read().decode())
            folder_id = folder_res["data"]["id"]
    except HTTPError as e:
        print(f"Error creating folder: {e.read().decode()}")
        return

    # 3. Upload files
    file_ids = []
    for i in range(1, 4):
        file_name = f"NOTE-{run_id}-{i}.txt"
        file_content = f"Content of {file_name}".encode()
        
        metadata = json.dumps({
            "name": file_name,
            "parent_folder_id": folder_id,
            "drive_id": drive_id
        })
        
        upload_headers = headers.copy()
        upload_headers["Content-Type"] = "text/plain"
        upload_headers["x-apideck-metadata"] = metadata
        
        req = urllib.request.Request("https://upload.apideck.com/file-storage/files", data=file_content, headers=upload_headers, method="POST")
        try:
            with urllib.request.urlopen(req) as response:
                file_res = json.loads(response.read().decode())
                file_ids.append(file_res["data"]["id"])
        except HTTPError as e:
            print(f"Error uploading file {file_name}: {e.read().decode()}")
            return

    # 4. Write log
    log_data = {
        "folder_id": folder_id,
        "file_ids": file_ids
    }
    
    with open("/home/user/apideck_task/output.log", "w") as f:
        f.write(json.dumps(log_data) + "\n")
        
    print("Success!")

if __name__ == "__main__":
    main()
