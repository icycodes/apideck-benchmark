import os
import sys
import json
import requests

# Retrieve configuration from environment variables
API_KEY = os.environ.get("APIDECK_API_KEY")
APP_ID = os.environ.get("APIDECK_APP_ID")
CONSUMER_ID = os.environ.get("APIDECK_CONSUMER_ID")
RUN_ID = os.environ.get("ZEALT_RUN_ID")
DRIVE_NAME = os.environ.get("APIDECK_FILE_STORAGE_DRIVE_NAME")

if not all([API_KEY, APP_ID, CONSUMER_ID, RUN_ID, DRIVE_NAME]):
    print("Error: Missing one or more required environment variables.", file=sys.stderr)
    print(f"API_KEY: {'set' if API_KEY else 'missing'}", file=sys.stderr)
    print(f"APP_ID: {'set' if APP_ID else 'missing'}", file=sys.stderr)
    print(f"CONSUMER_ID: {'set' if CONSUMER_ID else 'missing'}", file=sys.stderr)
    print(f"RUN_ID: {'set' if RUN_ID else 'missing'}", file=sys.stderr)
    print(f"DRIVE_NAME: {'set' if DRIVE_NAME else 'missing'}", file=sys.stderr)
    sys.exit(1)

BASE_URL = "https://unify.apideck.com"
UPLOAD_URL = "https://upload.apideck.com"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "x-apideck-app-id": APP_ID,
    "x-apideck-consumer-id": CONSUMER_ID,
    "x-apideck-service-id": "onedrive"
}

def list_drives():
    url = f"{BASE_URL}/file-storage/drives"
    print(f"Listing drives: {url}")
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to list drives: {response.status_code} {response.text}", file=sys.stderr)
        sys.exit(1)
    return response.json()

def resolve_drive_id(drives_response, name):
    drives = drives_response.get("data", [])
    for d in drives:
        if d.get("name") == name:
            return d.get("id")
    print(f"Error: Drive named '{name}' not found.", file=sys.stderr)
    sys.exit(1)

def create_folder(drive_id, folder_name):
    url = f"{BASE_URL}/file-storage/folders"
    print(f"Creating folder '{folder_name}' in drive '{drive_id}'...")
    payload = {
        "name": folder_name,
        "parent_folder_id": "root",
        "drive_id": drive_id
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code not in (200, 201):
        print(f"Failed to create folder: {response.status_code} {response.text}", file=sys.stderr)
        sys.exit(1)
    res_json = response.json()
    folder_id = res_json.get("data", {}).get("id")
    if not folder_id:
        print(f"Failed to extract folder_id from response: {res_json}", file=sys.stderr)
        sys.exit(1)
    print(f"Created folder successfully. ID: {folder_id}")
    return folder_id

def upload_file(drive_id, parent_folder_id, filename, content):
    url = f"{UPLOAD_URL}/file-storage/files"
    print(f"Uploading file '{filename}' to folder '{parent_folder_id}' in drive '{drive_id}'...")
    
    metadata = {
        "name": filename,
        "parent_folder_id": parent_folder_id,
        "drive_id": drive_id
    }
    
    upload_headers = headers.copy()
    upload_headers["Content-Type"] = "text/plain"
    upload_headers["x-apideck-metadata"] = json.dumps(metadata)
    
    response = requests.post(url, headers=upload_headers, data=content.encode("utf-8"))
    if response.status_code not in (200, 201):
        print(f"Failed to upload file {filename}: {response.status_code} {response.text}", file=sys.stderr)
        sys.exit(1)
    
    res_json = response.json()
    file_id = res_json.get("data", {}).get("id")
    if not file_id:
        print(f"Failed to extract file_id from response for {filename}: {res_json}", file=sys.stderr)
        sys.exit(1)
    print(f"Uploaded file successfully. ID: {file_id}")
    return file_id

def main():
    drives_res = list_drives()
    drive_id = resolve_drive_id(drives_res, DRIVE_NAME)
    print(f"Resolved drive ID: {drive_id}")
    
    folder_name = f"FOLDER-{RUN_ID}"
    folder_id = create_folder(drive_id, folder_name)
    
    file_ids = []
    for i in range(1, 4):
        filename = f"NOTE-{RUN_ID}-{i}.txt"
        content = f"This is note {i} for run {RUN_ID}.\nTimestamp and run scoped notes placeholder content."
        file_id = upload_file(drive_id, folder_id, filename, content)
        file_ids.append(file_id)
        
    # Write output log
    log_dir = "/home/user/apideck_task"
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "output.log")
    
    log_data = {
        "folder_id": folder_id,
        "file_ids": file_ids
    }
    
    with open(log_path, "w") as f:
        f.write(json.dumps(log_data) + "\n")
        
    print(f"Log written to {log_path}: {json.dumps(log_data)}")

if __name__ == "__main__":
    main()
