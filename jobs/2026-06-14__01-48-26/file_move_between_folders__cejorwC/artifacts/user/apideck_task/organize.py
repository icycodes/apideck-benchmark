import os
import sys
import json
import requests

def cleanup_resource(name, resource_type, headers):
    print(f"Checking if {resource_type} '{name}' already exists...")
    search_payload = {
        "query": name
    }
    search_resp = requests.post(
        "https://unify.apideck.com/file-storage/files/search",
        json=search_payload,
        headers=headers
    )
    if search_resp.status_code == 200:
        results = search_resp.json().get("data", [])
        for item in results:
            if item.get("name") == name and item.get("type") == resource_type:
                item_id = item.get("id")
                print(f"Found existing {resource_type} '{name}' with ID: {item_id}. Deleting...")
                if resource_type == "folder":
                    del_url = f"https://unify.apideck.com/file-storage/folders/{item_id}"
                else:
                    del_url = f"https://unify.apideck.com/file-storage/files/{item_id}"
                
                del_resp = requests.delete(del_url, headers=headers)
                if del_resp.status_code == 200:
                    print(f"Successfully deleted {resource_type} '{name}'")
                else:
                    print(f"Failed to delete {resource_type} '{name}'. Status: {del_resp.status_code}")

def main():
    # 1. Read environment variables
    zealt_run_id = os.environ.get("ZEALT_RUN_ID")
    apideck_app_id = os.environ.get("APIDECK_APP_ID")
    apideck_api_key = os.environ.get("APIDECK_API_KEY")
    apideck_consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    service_id = os.environ.get("APIDECK_FILE_STORAGE_DRIVE_NAME", "onedrive")

    print("Checking environment variables...")
    missing_vars = []
    if not zealt_run_id:
        missing_vars.append("ZEALT_RUN_ID")
    if not apideck_app_id:
        missing_vars.append("APIDECK_APP_ID")
    if not apideck_api_key:
        missing_vars.append("APIDECK_API_KEY")
    if not apideck_consumer_id:
        missing_vars.append("APIDECK_CONSUMER_ID")

    if missing_vars:
        print(f"Error: Missing environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    print(f"ZEALT_RUN_ID: {zealt_run_id}")
    print(f"APIDECK_APP_ID: {apideck_app_id}")
    print(f"APIDECK_CONSUMER_ID: {apideck_consumer_id}")
    print(f"Using Service ID: {service_id}")

    # Set up common headers
    headers = {
        "Authorization": f"Bearer {apideck_api_key}",
        "x-apideck-app-id": apideck_app_id,
        "x-apideck-consumer-id": apideck_consumer_id,
        "x-apideck-service-id": service_id
    }

    src_folder_name = f"SRC-{zealt_run_id}"
    dst_folder_name = f"DST-{zealt_run_id}"
    file_name = f"MOVE-{zealt_run_id}.txt"

    # Cleanup existing resources to ensure clean run
    cleanup_resource(src_folder_name, "folder", headers)
    cleanup_resource(dst_folder_name, "folder", headers)
    cleanup_resource(file_name, "file", headers)

    # Step 1: Create a staging folder and a destination folder at the drive root
    # Create SRC folder
    print(f"Creating source folder: {src_folder_name}...")
    src_payload = {
        "name": src_folder_name,
        "parent_folder_id": "root"
    }
    src_resp = requests.post(
        "https://unify.apideck.com/file-storage/folders",
        json=src_payload,
        headers=headers
    )
    if src_resp.status_code not in (200, 201):
        print(f"Failed to create source folder. Status: {src_resp.status_code}, Response: {src_resp.text}")
        sys.exit(1)
    
    src_data = src_resp.json()
    src_folder_id = src_data.get("data", {}).get("id")
    if not src_folder_id:
        print(f"Could not extract source folder ID from response: {src_data}")
        sys.exit(1)
    print(f"Source folder created successfully with ID: {src_folder_id}")

    # Create DST folder
    print(f"Creating destination folder: {dst_folder_name}...")
    dst_payload = {
        "name": dst_folder_name,
        "parent_folder_id": "root"
    }
    dst_resp = requests.post(
        "https://unify.apideck.com/file-storage/folders",
        json=dst_payload,
        headers=headers
    )
    if dst_resp.status_code not in (200, 201):
        print(f"Failed to create destination folder. Status: {dst_resp.status_code}, Response: {dst_resp.text}")
        sys.exit(1)
    
    dst_data = dst_resp.json()
    dst_folder_id = dst_data.get("data", {}).get("id")
    if not dst_folder_id:
        print(f"Could not extract destination folder ID from response: {dst_data}")
        sys.exit(1)
    print(f"Destination folder created successfully with ID: {dst_folder_id}")

    # Step 2: Upload a small text file into the staging folder
    file_content = f"This is a test file for ZEALT_RUN_ID: {zealt_run_id}".encode("utf-8")

    print(f"Uploading file '{file_name}' to source folder '{src_folder_id}'...")
    upload_headers = headers.copy()
    upload_headers["Content-Type"] = "text/plain"
    upload_headers["x-apideck-metadata"] = json.dumps({
        "name": file_name,
        "parent_folder_id": src_folder_id
    })

    upload_resp = requests.post(
        "https://upload.apideck.com/file-storage/files",
        data=file_content,
        headers=upload_headers
    )
    if upload_resp.status_code not in (200, 201):
        print(f"Failed to upload file. Status: {upload_resp.status_code}, Response: {upload_resp.text}")
        sys.exit(1)
    
    upload_data = upload_resp.json()
    file_id = upload_data.get("data", {}).get("id")
    if not file_id:
        print(f"Could not extract file ID from upload response: {upload_data}")
        sys.exit(1)
    print(f"File uploaded successfully with ID: {file_id}")

    # Step 3: Move that file into the destination folder (the file's name must NOT change)
    print(f"Moving file '{file_id}' to destination folder '{dst_folder_id}'...")
    move_payload = {
        "parent_folder_id": dst_folder_id
    }
    
    # We use PATCH /file-storage/files/{id} to move/rename
    move_resp = requests.patch(
        f"https://unify.apideck.com/file-storage/files/{file_id}",
        json=move_payload,
        headers=headers
    )
    if move_resp.status_code not in (200, 201):
        print(f"Failed to move file. Status: {move_resp.status_code}, Response: {move_resp.text}")
        sys.exit(1)
    
    print("File moved successfully!")

    # Write output to log file
    log_file_path = "/home/user/apideck_task/output.log"
    log_data = {
        "file_id": file_id,
        "src_folder_id": src_folder_id,
        "dst_folder_id": dst_folder_id
    }

    print(f"Writing log to {log_file_path}...")
    with open(log_file_path, "w") as f:
        f.write(json.dumps(log_data) + "\n")

    print("Success! Process completed.")

if __name__ == "__main__":
    main()
