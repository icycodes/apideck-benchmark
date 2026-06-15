import os
import sys
import json
import requests

def main():
    print("Starting Apideck File Upload and Rename task...")

    # Read environment variables
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    run_id = os.environ.get("ZEALT_RUN_ID")
    drive_name = os.environ.get("APIDECK_FILE_STORAGE_DRIVE_NAME")

    if not all([api_key, app_id, consumer_id, run_id]):
        print("Error: Missing required environment variables.", file=sys.stderr)
        print(f"APIDECK_API_KEY: {'set' if api_key else 'not set'}", file=sys.stderr)
        print(f"APIDECK_APP_ID: {'set' if app_id else 'not set'}", file=sys.stderr)
        print(f"APIDECK_CONSUMER_ID: {'set' if consumer_id else 'not set'}", file=sys.stderr)
        print(f"ZEALT_RUN_ID: {'set' if run_id else 'not set'}", file=sys.stderr)
        sys.exit(1)

    print(f"ZEALT_RUN_ID: {run_id}")
    print(f"Drive Name: {drive_name}")

    original_filename = f"ORIGINAL-{run_id}.txt"
    renamed_filename = f"RENAMED-{run_id}.txt"
    file_content = f"This is a small text file uploaded for Zealt run ID: {run_id}."

    # Step 1: Upload the file
    print(f"\n--- Uploading file: {original_filename} ---")
    upload_url = "https://upload.apideck.com/file-storage/files"
    
    upload_headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": "onedrive",
        "x-apideck-metadata": json.dumps({
            "name": original_filename,
            "parent_folder_id": "root"
        }),
        "Content-Type": "text/plain"
    }

    print(f"POST URL: {upload_url}")
    print("Headers (excluding Authorization):")
    for k, v in upload_headers.items():
        if k != "Authorization":
            print(f"  {k}: {v}")

    try:
        response = requests.post(upload_url, headers=upload_headers, data=file_content.encode('utf-8'))
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code not in [200, 201]:
            print(f"Upload failed with status code {response.status_code}", file=sys.stderr)
            sys.exit(1)

        upload_data = response.json()
        file_id = upload_data.get("data", {}).get("id")
        if not file_id:
            print("Error: Could not retrieve file ID from upload response.", file=sys.stderr)
            sys.exit(1)

        print(f"Successfully uploaded file. Unified File ID: {file_id}")

    except Exception as e:
        print(f"Exception during upload: {e}", file=sys.stderr)
        sys.exit(1)

    # Step 2: Rename the file
    print(f"\n--- Renaming file to: {renamed_filename} ---")
    rename_url = f"https://unify.apideck.com/file-storage/files/{file_id}"
    
    rename_headers = {
        "Authorization": f"Bearer {api_key}",
        "x-apideck-app-id": app_id,
        "x-apideck-consumer-id": consumer_id,
        "x-apideck-service-id": "onedrive",
        "Content-Type": "application/json"
    }

    rename_body = {
        "name": renamed_filename,
        "parent_folder_id": "root"
    }

    print(f"PATCH URL: {rename_url}")
    print("Headers (excluding Authorization):")
    for k, v in rename_headers.items():
        if k != "Authorization":
            print(f"  {k}: {v}")
    print(f"Request Body: {json.dumps(rename_body)}")

    try:
        response = requests.patch(rename_url, headers=rename_headers, json=rename_body)
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")

        if response.status_code != 200:
            print(f"Rename failed with status code {response.status_code}", file=sys.stderr)
            sys.exit(1)

        rename_data = response.json()
        renamed_file_id = rename_data.get("data", {}).get("id")
        print(f"Successfully renamed file. Unified File ID after rename: {renamed_file_id}")

        if renamed_file_id != file_id:
            print(f"Warning: File ID changed from {file_id} to {renamed_file_id}", file=sys.stderr)

    except Exception as e:
        print(f"Exception during rename: {e}", file=sys.stderr)
        sys.exit(1)

    # Step 3: Write output log
    log_dir = "/home/user/apideck_task"
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "output.log")
    
    with open(log_path, "w") as f:
        f.write(f"File ID: {file_id}\n")

    print(f"\nSuccessfully wrote log to {log_path}")
    print(f"Log content: File ID: {file_id}")

if __name__ == "__main__":
    main()
