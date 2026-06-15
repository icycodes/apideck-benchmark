import os
import sys
import json
import requests

def main():
    # 1. Read environment variables
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    run_id = os.environ.get("ZEALT_RUN_ID")
    env_service = os.environ.get("APIDECK_FILE_STORAGE_DRIVE_NAME")

    if not all([api_key, app_id, consumer_id, run_id]):
        print("Error: Missing required environment variables.", file=sys.stderr)
        print(f"APIDECK_API_KEY: {'set' if api_key else 'missing'}", file=sys.stderr)
        print(f"APIDECK_APP_ID: {'set' if app_id else 'missing'}", file=sys.stderr)
        print(f"APIDECK_CONSUMER_ID: {'set' if consumer_id else 'missing'}", file=sys.stderr)
        print(f"ZEALT_RUN_ID: {'set' if run_id else 'missing'}", file=sys.stderr)
        sys.exit(1)

    # 2. Determine the service ID
    # Use APIDECK_FILE_STORAGE_DRIVE_NAME if set, otherwise try to detect, default to onedrive
    service_id = env_service if env_service else "onedrive"
    print(f"Using service_id: {service_id}")

    # Set up common headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": service_id
    }

    # 3. Generate payload
    filename = f"SIZED-{run_id}.txt"
    line = f"ApiDeck-{run_id}-payload-line\n"
    payload = line.encode("ascii") * 100
    expected_size = len(payload)
    print(f"Generated payload for filename: {filename}")
    print(f"Single line: {repr(line)}")
    print(f"Expected size of payload: {expected_size} bytes")

    # 4. Clean up any existing file with the same name
    print("Checking for existing files using search...")
    try:
        search_body = {
            "query": f"SIZED-{run_id}"
        }
        response = requests.post("https://unify.apideck.com/file-storage/files/search", headers=headers, json=search_body)
        if response.status_code == 200:
            files_data = response.json().get("data", [])
            for f in files_data:
                if f.get("name").startswith(f"SIZED-{run_id}"):
                    file_id = f.get("id")
                    print(f"Found existing file: {f.get('name')} (ID: {file_id}). Deleting it...")
                    del_response = requests.delete(f"https://unify.apideck.com/file-storage/files/{file_id}", headers=headers)
                    print(f"Delete response status: {del_response.status_code}")
                    if del_response.status_code not in [200, 204]:
                        print(f"Warning: Failed to delete existing file. Body: {del_response.text}")
        else:
            print(f"Warning: Could not search files for cleanup. Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        print(f"Warning: Error during cleanup: {e}")

    # 5. Upload the file
    print("Uploading file...")
    metadata = {
        "name": filename,
        "parent_folder_id": "root"
    }
    upload_headers = headers.copy()
    upload_headers["x-apideck-metadata"] = json.dumps(metadata)
    upload_headers["Content-Type"] = "application/octet-stream"

    try:
        # Note: upload host is upload.apideck.com
        upload_response = requests.post(
            "https://upload.apideck.com/file-storage/files",
            headers=upload_headers,
            data=payload
        )
        print(f"Upload response status: {upload_response.status_code}")
        if upload_response.status_code not in [200, 201]:
            print(f"Error: Upload failed. Body: {upload_response.text}", file=sys.stderr)
            sys.exit(1)
        
        upload_data = upload_response.json()
        print("Upload Response Body:")
        print(json.dumps(upload_data, indent=2))
    except Exception as e:
        print(f"Error: Exception during upload: {e}", file=sys.stderr)
        sys.exit(1)

    # 6. Retrieve uploaded file's details to verify size
    file_info = upload_data.get("data", {})
    uploaded_file_id = file_info.get("id")
    if not uploaded_file_id:
        print("Error: Upload response did not contain file ID.", file=sys.stderr)
        sys.exit(1)

    print(f"Uploaded File ID: {uploaded_file_id}")

    # Let's fetch file metadata again to be absolutely sure we have the latest status from ApiDeck
    print("Fetching file metadata to verify size...")
    try:
        get_response = requests.get(f"https://unify.apideck.com/file-storage/files/{uploaded_file_id}", headers=headers)
        print(f"Get file metadata status: {get_response.status_code}")
        if get_response.status_code == 200:
            file_info = get_response.json().get("data", {})
            print("Fetched File Metadata:")
            print(json.dumps(file_info, indent=2))
        else:
            print(f"Warning: Could not fetch file metadata. Status: {get_response.status_code}, Body: {get_response.text}")
    except Exception as e:
        print(f"Warning: Error fetching file metadata: {e}")

    reported_size = file_info.get("size")
    print(f"Reported size: {reported_size} bytes")
    print(f"Expected size: {expected_size} bytes")

    if reported_size != expected_size:
        print(f"Error: Reported size ({reported_size}) does not match expected size ({expected_size})!", file=sys.stderr)
        sys.exit(1)

    print("Success: File size matches perfectly!")

    # 7. Write to log file
    log_path = "/home/user/apideck_task/output.log"
    print(f"Writing result to log file: {log_path}")
    try:
        with open(log_path, "w") as log_file:
            log_file.write(f"File ID: {uploaded_file_id}\n")
            log_file.write(f"Filename: {filename}\n")
            log_file.write(f"Expected Size: {expected_size}\n")
            log_file.write(f"Reported Size: {reported_size}\n")
            log_file.write("Status: SUCCESS\n")
        print("Log file written successfully.")
    except Exception as e:
        print(f"Error: Could not write to log file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
