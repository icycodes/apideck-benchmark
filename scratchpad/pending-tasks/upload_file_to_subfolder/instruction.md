# Organize a Report File in OneDrive via the Apideck File Storage Unified API

## Background
Your SaaS app uses Apideck Unify to talk to multiple file-storage providers through a single canonical REST surface. For this task, the consumer has authorized **OneDrive** (Service ID: `onedrive`) and an empty drive has been provisioned for testing. You need to organize a new compliance report inside this drive by first creating a dedicated subfolder, then uploading the report into that subfolder, using the Apideck File Storage Unified API (`https://unify.apideck.com` for metadata, `https://upload.apideck.com` for the upload payload).

The following environment variables are already exported in the runtime:

- `APIDECK_APP_ID`
- `APIDECK_API_KEY`
- `APIDECK_CONSUMER_ID`
- `APIDECK_FILE_STORAGE_DRIVE_NAME` — display name of the OneDrive drive you must work in.
- `ZEALT_RUN_ID` — a unique run id matching `zr-[a-z0-9]+`. You **must** include it in every resource name to make the run isolated and retryable.

## Requirements
- Resolve the OneDrive drive whose `name` equals `APIDECK_FILE_STORAGE_DRIVE_NAME` via the unified Drives endpoint.
- Create a folder at the **root** of that drive named exactly `harbor-report-${ZEALT_RUN_ID}` (substitute the run id at runtime).
- Upload a UTF-8 text file named exactly `report-${ZEALT_RUN_ID}.txt` into the folder you just created. The file body must be exactly `Compliance report for run ${ZEALT_RUN_ID}\n` (single trailing newline, no other content).
- Use only the unified File Storage REST API or the official Apideck Unify SDK (`apideck-unify` Python package or `@apideck/unify` Node package). Do **not** call the underlying OneDrive/Microsoft Graph API directly.
- Write a log file at `/home/user/apideck_task/output.log` recording the IDs returned by Apideck so the verifier can locate the resources.

## Implementation Hints
- All metadata requests go to `https://unify.apideck.com`; the file upload itself must hit `https://upload.apideck.com/file-storage/files`. Every request needs the headers `Authorization: Bearer $APIDECK_API_KEY`, `x-apideck-app-id`, `x-apideck-consumer-id`, and `x-apideck-service-id: onedrive`.
- Direct uploads (≤100 MB) carry their metadata in the `x-apideck-metadata` header as JSON (with `name` and `parent_folder_id`) and the **raw binary body** of the file. Do **not** use multipart form data — it will silently fail.
- The unified Drives endpoint returns the drive `id` you should pass as `drive_id` when creating the folder. Use `parent_folder_id="root"` to anchor the folder at the drive root.
- The Apideck Python SDK exposes these via `apideck.file_storage.drives.list(...)`, `apideck.file_storage.folders.create(...)`, and `apideck.file_storage.files.upload(...)`.
- Refer to the Apideck docs at <https://developers.apideck.com/apis/file-storage/reference> and the [file upload guide](https://developers.apideck.com/guides/file-upload.md).

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the script is actually executed against the live Apideck Unify API and the OneDrive side effects exist.
- Log file: /home/user/apideck_task/output.log
- The log file must contain the following lines (each on its own line, in any order):
  - `Drive ID: <drive_id>`
  - `Folder ID: <folder_id>`
  - `File ID: <file_id>`
  Where `<drive_id>`, `<folder_id>`, `<file_id>` are the Apideck unified IDs returned by the API for the resolved drive, the created folder, and the uploaded file respectively.
- A folder with name `harbor-report-${ZEALT_RUN_ID}` must exist at the root of the drive named `APIDECK_FILE_STORAGE_DRIVE_NAME`.
- A file with name `report-${ZEALT_RUN_ID}.txt` must exist inside that folder. Its parent folder chain (from `GET /file-storage/files/<file_id>`) must include the created folder.
- `${ZEALT_RUN_ID}` must be read from the `ZEALT_RUN_ID` environment variable at runtime.

