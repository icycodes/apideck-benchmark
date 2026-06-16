import os
import sys
import json
import base64
import requests

API_KEY = os.environ.get("APIDECK_API_KEY")
APP_ID = os.environ.get("APIDECK_APP_ID")
CONSUMER_ID = os.environ.get("APIDECK_CONSUMER_ID")

if not all([API_KEY, APP_ID, CONSUMER_ID]):
    print("Error: Missing required environment variables.", file=sys.stderr)
    sys.exit(1)

BASE_URL = "https://unify.apideck.com"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "x-apideck-app-id": APP_ID,
    "x-apideck-consumer-id": CONSUMER_ID,
    "x-apideck-service-id": "onedrive"
}

def decode_apideck_id(encoded_id):
    try:
        # Pad base64 if necessary
        padded = encoded_id + "=" * ((4 - len(encoded_id) % 4) % 4)
        decoded_bytes = base64.b64decode(padded)
        return json.loads(decoded_bytes.decode("utf-8"))
    except Exception as e:
        print(f"Failed to decode ID {encoded_id}: {e}", file=sys.stderr)
        return None

def ids_are_equivalent(id1, id2):
    if id1 == id2:
        return True
    
    obj1 = decode_apideck_id(id1)
    obj2 = decode_apideck_id(id2)
    
    if not obj1 or not obj2:
        return False
    
    # Compare fields case-insensitively
    item_id1 = obj1.get("id", "").lower()
    item_id2 = obj2.get("id", "").lower()
    
    drive_id1 = obj1.get("drive_id", "").lower()
    drive_id2 = obj2.get("drive_id", "").lower()
    
    return item_id1 == item_id2 and drive_id1 == drive_id2

def verify_file(file_id, expected_parent_id):
    url = f"{BASE_URL}/file-storage/files/{file_id}"
    print(f"Retrieving file: {url}")
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to retrieve file {file_id}: {response.status_code} {response.text}", file=sys.stderr)
        return False
    
    file_data = response.json().get("data", {})
    parent_folders = file_data.get("parent_folders", [])
    
    if not parent_folders:
        print(f"File has no parent folders list.", file=sys.stderr)
        return False
        
    parent_id = parent_folders[0].get("id")
    name = file_data.get("name")
    
    print(f"File Name: {name}")
    print(f"File Parent Folder ID: {parent_id}")
    print(f"Expected Parent Folder ID: {expected_parent_id}")
    
    if ids_are_equivalent(parent_id, expected_parent_id):
        print("Verification SUCCESS for this file!\n")
        return True
    else:
        print("Verification FAILURE for this file!\n", file=sys.stderr)
        return False

def main():
    log_path = "/home/user/apideck_task/output.log"
    if not os.path.exists(log_path):
        print(f"Error: Log path {log_path} does not exist.", file=sys.stderr)
        sys.exit(1)
        
    with open(log_path, "r") as f:
        log_data = json.loads(f.read().strip())
        
    folder_id = log_data.get("folder_id")
    file_ids = log_data.get("file_ids", [])
    
    all_ok = True
    for fid in file_ids:
        if not verify_file(fid, folder_id):
            all_ok = False
            
    if all_ok:
        print("All files verified successfully!")
    else:
        print("Some files failed verification.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
