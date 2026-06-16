import os
import requests
import sys

def main():
    api_key = os.environ.get('APIDECK_API_KEY')
    app_id = os.environ.get('APIDECK_APP_ID')
    consumer_id = os.environ.get('APIDECK_CONSUMER_ID')
    drive_name = os.environ.get('APIDECK_FILE_STORAGE_DRIVE_NAME')
    run_id = os.environ.get('ZEALT_RUN_ID')

    if not all([api_key, app_id, consumer_id, drive_name, run_id]):
        print("Missing required environment variables")
        sys.exit(1)

    headers = {
        'Authorization': f'Bearer {api_key}',
        'x-apideck-app-id': app_id,
        'x-apideck-consumer-id': consumer_id,
        'x-apideck-service-id': 'onedrive',
        'Content-Type': 'application/json'
    }

    base_url = 'https://unify.apideck.com/file-storage'

    # 1. List drives
    print("Listing drives...")
    resp = requests.get(f'{base_url}/drives', headers=headers)
    resp.raise_for_status()
    drives = resp.json().get('data', [])
    
    drive_id = None
    for d in drives:
        if d.get('name') == drive_name:
            drive_id = d.get('id')
            break
    
    if not drive_id:
        print(f"Drive with name '{drive_name}' not found.")
        sys.exit(1)
        
    print(f"Found drive ID: {drive_id}")

    # 2. Create folder
    folder_name = f'harbor-delete-{run_id}'
    create_payload = {
        "name": folder_name,
        "parent_folder_id": "root",
        "drive_id": drive_id
    }
    print(f"Creating folder '{folder_name}'...")
    # It might be POST /file-storage/folders
    resp = requests.post(f'{base_url}/folders', headers=headers, json=create_payload)
    resp.raise_for_status()
    created_folder = resp.json().get('data', {})
    folder_id = created_folder.get('id')
    
    if not folder_id:
        print("Failed to get folder ID from creation response")
        sys.exit(1)
        
    print(f"Created folder ID: {folder_id}")

    # 3. Delete folder
    print(f"Deleting folder ID: {folder_id}...")
    resp = requests.delete(f'{base_url}/folders/{folder_id}', headers=headers)
    resp.raise_for_status()
    print("Folder deleted.")

    # 4. Write log file
    log_content = f"Drive ID: {drive_id}\nCreated folder ID: {folder_id}\nDeleted folder ID: {folder_id}\n"
    with open('/home/user/myproject/output.log', 'a') as f:
        f.write(log_content)
    print("Log written to /home/user/myproject/output.log")

if __name__ == '__main__':
    main()
