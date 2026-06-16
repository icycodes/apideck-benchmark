import os
import json
import httpx
import apideck_unify

def main():
    # 1. Read environment variables
    api_key = os.environ.get('APIDECK_API_KEY')
    app_id = os.environ.get('APIDECK_APP_ID')
    consumer_id = os.environ.get('APIDECK_CONSUMER_ID')
    drive_name = os.environ.get('APIDECK_FILE_STORAGE_DRIVE_NAME')
    run_id = os.environ.get('ZEALT_RUN_ID')

    if not all([api_key, app_id, consumer_id, drive_name, run_id]):
        print("Missing required environment variables!")
        return

    # 2. Construct Apideck Client
    sdk = apideck_unify.Apideck(
        api_key=api_key,
        consumer_id=consumer_id,
        app_id=app_id
    )

    # 3. Resolve drive id
    print(f"Listing drives to find drive with name '{drive_name}'...")
    drives_res = sdk.file_storage.drives.list(service_id='onedrive')
    drive_id = None
    for drive in drives_res.get_drives_response.data:
        if drive.name == drive_name:
            drive_id = drive.id
            break

    if not drive_id:
        print(f"Drive '{drive_name}' not found!")
        return

    print(f"Resolved drive ID: {drive_id}")

    # 4. Define files and payloads
    alpha_filename = f"report-{run_id}-alpha.txt"
    beta_filename = f"report-{run_id}-beta.txt"

    alpha_content = f"alpha payload for {run_id}\n".encode('utf-8')
    beta_content = f"beta payload for {run_id}\n".encode('utf-8')

    results = {}

    # 5. Direct Upload Helper Function
    def upload_file(filename, content):
        print(f"Uploading {filename}...")
        headers = {
            'Authorization': f'Bearer {api_key}',
            'x-apideck-app-id': app_id,
            'x-apideck-consumer-id': consumer_id,
            'x-apideck-service-id': 'onedrive',
            'x-apideck-metadata': json.dumps({
                'name': filename,
                'parent_folder_id': 'root',
                'drive_id': drive_id
            }),
            'Content-Type': 'text/plain'
        }
        res = httpx.post('https://upload.apideck.com/file-storage/files', headers=headers, content=content)
        res.raise_for_status()
        res_data = res.json()
        file_id = res_data['data']['id']
        print(f"Successfully uploaded {filename}! File ID: {file_id}")
        return file_id

    # 6. Upload Alpha and Beta
    alpha_id = upload_file(alpha_filename, alpha_content)
    results['alpha'] = {
        'name': alpha_filename,
        'id': alpha_id
    }

    beta_id = upload_file(beta_filename, beta_content)
    results['beta'] = {
        'name': beta_filename,
        'id': beta_id
    }

    # 7. Write output JSON to /home/user/myproject/output.log
    output_log_path = '/home/user/myproject/output.log'
    print(f"Writing output to {output_log_path}...")
    with open(output_log_path, 'w') as f:
        f.write(json.dumps(results) + '\n')

    print("Done!")

if __name__ == '__main__':
    main()
