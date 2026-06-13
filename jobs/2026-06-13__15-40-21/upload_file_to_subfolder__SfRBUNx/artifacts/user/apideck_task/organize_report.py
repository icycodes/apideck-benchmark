import os
import sys
import json
import requests

def main():
    # 1. Retrieve and validate environment variables
    api_key = os.getenv("APIDECK_API_KEY")
    app_id = os.getenv("APIDECK_APP_ID")
    consumer_id = os.getenv("APIDECK_CONSUMER_ID")
    drive_name = os.getenv("APIDECK_FILE_STORAGE_DRIVE_NAME")
    run_id = os.getenv("ZEALT_RUN_ID")

    if not all([api_key, app_id, consumer_id, drive_name, run_id]):
        print("Error: Missing one or more required environment variables.", file=sys.stderr)
        print(f"APIDECK_API_KEY: {'Set' if api_key else 'Missing'}", file=sys.stderr)
        print(f"APIDECK_APP_ID: {'Set' if app_id else 'Missing'}", file=sys.stderr)
        print(f"APIDECK_CONSUMER_ID: {'Set' if consumer_id else 'Missing'}", file=sys.stderr)
        print(f"APIDECK_FILE_STORAGE_DRIVE_NAME: {'Set' if drive_name else 'Missing'}", file=sys.stderr)
        print(f"ZEALT_RUN_ID: {'Set' if run_id else 'Missing'}", file=sys.stderr)
        sys.exit(1)

    print(f"Using ZEALT_RUN_ID: {run_id}")
    print(f"Target Drive Name: {drive_name}")

    # Base headers for metadata requests
    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": "onedrive"
    }

    # 2. Resolve the OneDrive drive whose name matches APIDECK_FILE_STORAGE_DRIVE_NAME
    print("Listing drives to resolve target drive...")
    drives_url = "https://unify.apideck.com/file-storage/drives"
    response = requests.get(drives_url, headers=headers)
    if response.status_code != 200:
        print(f"Error listing drives: {response.status_code} - {response.text}", file=sys.stderr)
        sys.exit(1)

    drives_data = response.json().get("data", [])
    drive_id = None
    for d in drives_data:
        if d.get("name") == drive_name:
            drive_id = d.get("id")
            break

    if not drive_id:
        print(f"Error: Could not find drive with name '{drive_name}'", file=sys.stderr)
        sys.exit(1)

    print(f"Resolved Drive ID: {drive_id}")

    # 3. Create a folder at the root of that drive named harbor-report-${ZEALT_RUN_ID}
    folder_name = f"harbor-report-{run_id}"
    print(f"Creating folder '{folder_name}' at the root of drive {drive_id}...")
    folders_url = "https://unify.apideck.com/file-storage/folders"
    folder_payload = {
        "name": folder_name,
        "parent_folder_id": "root",
        "drive_id": drive_id
    }
    
    # We need application/json content type for folder creation
    folder_headers = headers.copy()
    folder_headers["Content-Type"] = "application/json"
    
    response = requests.post(folders_url, headers=folder_headers, json=folder_payload)
    if response.status_code not in (200, 201):
        print(f"Error creating folder: {response.status_code} - {response.text}", file=sys.stderr)
        sys.exit(1)

    folder_id = response.json().get("data", {}).get("id")
    if not folder_id:
        print(f"Error: Folder created but no ID returned. Response: {response.text}", file=sys.stderr)
        sys.exit(1)

    print(f"Created Folder ID: {folder_id}")

    # 4. Upload report-${ZEALT_RUN_ID}.txt into the folder
    file_name = f"report-{run_id}.txt"
    file_content = f"Compliance report for run {run_id}\n"
    print(f"Uploading file '{file_name}' to folder '{folder_id}'...")

    upload_url = "https://upload.apideck.com/file-storage/files"
    
    # Metadata as JSON in x-apideck-metadata header
    metadata = {
        "name": file_name,
        "parent_folder_id": folder_id,
        "drive_id": drive_id
    }
    
    upload_headers = headers.copy()
    upload_headers["x-apideck-metadata"] = json.dumps(metadata)
    upload_headers["Content-Type"] = "text/plain; charset=utf-8"

    response = requests.post(upload_url, headers=upload_headers, data=file_content.encode("utf-8"))
    if response.status_code not in (200, 201):
        print(f"Error uploading file: {response.status_code} - {response.text}", file=sys.stderr)
        sys.exit(1)

    file_id = response.json().get("data", {}).get("id")
    if not file_id:
        print(f"Error: File uploaded but no ID returned. Response: {response.text}", file=sys.stderr)
        sys.exit(1)

    print(f"Uploaded File ID: {file_id}")

    # 5. Write log file to /home/user/apideck_task/output.log
    log_path = "/home/user/apideck_task/output.log"
    print(f"Writing output log to {log_path}...")
    
    # Ensure the parent directory exists (it should, but good practice)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"Drive ID: {drive_id}\n")
        f.write(f"Folder ID: {folder_id}\n")
        f.write(f"File ID: {file_id}\n")

    print("Task completed successfully!")

if __name__ == "__main__":
    main()
