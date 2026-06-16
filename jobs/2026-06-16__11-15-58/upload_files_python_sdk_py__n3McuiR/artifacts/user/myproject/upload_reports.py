"""Upload two report files to OneDrive via the Apideck Unify SDK."""

import json
import os

from apideck_unify import Apideck


def main() -> None:
    # Read configuration from environment variables
    api_key = os.environ["APIDECK_API_KEY"]
    app_id = os.environ["APIDECK_APP_ID"]
    consumer_id = os.environ["APIDECK_CONSUMER_ID"]
    drive_name = os.environ["APIDECK_FILE_STORAGE_DRIVE_NAME"]
    run_id = os.environ["ZEALT_RUN_ID"]

    service_id = "microsoftonedrive"

    # Initialise the SDK client
    sdk = Apideck(
        api_key=api_key,
        app_id=app_id,
        consumer_id=consumer_id,
    )

    # --- Resolve the drive id by name ---
    drives_response = sdk.file_storage.drives.list(
        service_id=service_id,
    )

    if drives_response.get_drives_response is None:
        raise RuntimeError("No drives response received")

    drive_id = None
    for drive in drives_response.get_drives_response.data:
        if drive.name == drive_name:
            drive_id = drive.id
            break

    if drive_id is None:
        raise RuntimeError(f"Drive named '{drive_name}' not found")

    # --- Helper: upload a single file ---
    def upload_file(filename: str, content: bytes) -> str:
        # 1. Create an upload session
        create_resp = sdk.file_storage.upload_sessions.create(
            name=filename,
            parent_folder_id="root",
            size=len(content),
            service_id=service_id,
            drive_id=drive_id,
        )

        session = create_resp.create_upload_session_response
        if session is None:
            raise RuntimeError(f"Failed to create upload session for {filename}")

        session_id = session.data.id

        # 2. Upload the file content
        sdk.file_storage.upload_sessions.upload(
            id=session_id,
            part_number=1,
            request_body=content,
            service_id=service_id,
        )

        # 3. Finish the upload session
        finish_resp = sdk.file_storage.upload_sessions.finish(
            id=session_id,
            service_id=service_id,
        )

        file_resp = finish_resp.get_file_response
        if file_resp is None:
            raise RuntimeError(f"Finish did not return file info for {filename}")

        return file_resp.data.id

    # --- Upload alpha and beta files ---
    alpha_name = f"report-{run_id}-alpha.txt"
    beta_name = f"report-{run_id}-beta.txt"

    alpha_content = f"alpha payload for {run_id}\n".encode("utf-8")
    beta_content = f"beta payload for {run_id}\n".encode("utf-8")

    alpha_id = upload_file(alpha_name, alpha_content)
    beta_id = upload_file(beta_name, beta_content)

    # --- Write the output log ---
    result = {
        "alpha": {"name": alpha_name, "id": alpha_id},
        "beta": {"name": beta_name, "id": beta_id},
    }

    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output.log")
    with open(log_path, "a") as f:
        f.write(json.dumps(result) + "\n")


if __name__ == "__main__":
    main()