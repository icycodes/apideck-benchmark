import os
import apideck_unify

def main():
    api_key = os.environ['APIDECK_API_KEY']
    consumer_id = os.environ['APIDECK_CONSUMER_ID']
    app_id = os.environ['APIDECK_APP_ID']
    drive_name = os.environ['APIDECK_FILE_STORAGE_DRIVE_NAME']

    sdk = apideck_unify.Apideck(
        api_key=api_key,
        consumer_id=consumer_id,
        app_id=app_id
    )

    # 1. Resolve drive id
    print("Listing drives...")
    drives_res = sdk.file_storage.drives.list(service_id='onedrive')
    drive_id = None
    for drive in drives_res.get_drives_response.data:
        if drive.name == drive_name:
            drive_id = drive.id
            break

    if not drive_id:
        print(f"Drive {drive_name} not found!")
        return

    print(f"Resolved drive ID: {drive_id}")

    # 2. Create upload session
    filename = "test_upload.txt"
    payload = b"hello world\n"
    size = len(payload)

    print(f"Creating upload session for {filename} (size: {size})...")
    try:
        session_res = sdk.file_storage.upload_sessions.create(
            name=filename,
            parent_folder_id='root',
            size=size,
            drive_id=drive_id,
            service_id='onedrive'
        )
        session_id = session_res.create_upload_session_response.data.id
        print(f"Session ID: {session_id}")
    except Exception as e:
        print("Error creating upload session:")
        print(e)
        if hasattr(e, 'http_res'):
            print("HTTP response status:", e.http_res.status_code)
            print("HTTP response body:", e.http_res.text)
        return

    # 3. Upload file part
    print("Uploading file part...")
    try:
        upload_res = sdk.file_storage.upload_sessions.upload(
            id=session_id,
            part_number=0,
            request_body=payload,
            service_id='onedrive'
        )
        print("Upload part response:", upload_res)
    except Exception as e:
        print("Error uploading file part:")
        print(e)
        if hasattr(e, 'http_res'):
            print("HTTP response status:", e.http_res.status_code)
            print("HTTP response body:", e.http_res.text)
        return

    # 4. Finish upload session
    print("Finishing upload session...")
    try:
        finish_res = sdk.file_storage.upload_sessions.finish(
            id=session_id,
            service_id='onedrive'
        )
        file_id = finish_res.get_file_response.data.id
        print(f"Finished! File ID: {file_id}")
    except Exception as e:
        print("Error finishing upload session:")
        print(e)
        if hasattr(e, 'http_res'):
            print("HTTP response status:", e.http_res.status_code)
            print("HTTP response body:", e.http_res.text)
        return

if __name__ == '__main__':
    main()
