# Rename a File on OneDrive via Apideck File Storage

## Background
[Apideck](https://www.apideck.com/) is a unified API platform that exposes a single normalized REST surface for many third-party SaaS providers. The Apideck Unified File Storage API lets you manage files across providers such as OneDrive without having to learn the provider-specific API.

In this task, you will use the Apideck Unified File Storage API (with the preconfigured `onedrive` connector) to upload a small text file to OneDrive and then rename it through the unified `Rename or move File` endpoint.

## Requirements
- Read the `run-id` from the `ZEALT_RUN_ID` environment variable. All file names below must include this `run-id` to safely run concurrently with other trials.
- Upload a new text file to the root of the OneDrive drive identified by the environment variable `APIDECK_FILE_STORAGE_DRIVE_NAME`:
  - The file content must be the ASCII string `hello apideck` (no trailing newline) with MIME type `text/plain`.
  - The file must be uploaded with the name `original-${run-id}.txt`.
- After the upload succeeds, rename that same file to `renamed-${run-id}.txt` using the unified File Storage rename endpoint (do NOT delete and re-upload; the file's unified `id` must stay the same).
- Write the final unified file `id` (the `data.id` returned by Apideck for the uploaded file) and the final file name to a log file so the verifier can pick them up.

## Implementation Hints
- The Apideck base URL is `https://unify.apideck.com`, but direct file uploads must use the upload host `https://upload.apideck.com` (the rest of the API stays on `unify.apideck.com`). See the [file upload guide](https://developers.apideck.com/guides/file-upload.md).
- Every request needs these headers: `Authorization: Bearer $APIDECK_API_KEY`, `x-apideck-app-id: $APIDECK_APP_ID`, `x-apideck-consumer-id: $APIDECK_CONSUMER_ID`, and `x-apideck-service-id: onedrive`.
- For the upload, send the raw file bytes as the request body and pass file metadata in the `x-apideck-metadata` header as a JSON string with at least `name` and `parent_folder_id` (use `"root"` for the drive root). Do NOT use `multipart/form-data`.
- For the rename, use `PATCH /file-storage/files/{id}` with a JSON body that contains the new `name`.
- You may use the official Python SDK `apideck-unify` or call the REST endpoints directly (e.g., with `requests`).
- Endpoint documentation:
  - [Upload file](https://developers.apideck.com/md/apis/file-storage/reference/files/filesUpload.md)
  - [Rename or move File](https://developers.apideck.com/md/apis/file-storage/reference/files/filesUpdate.md)
  - [Get File](https://developers.apideck.com/md/apis/file-storage/reference/files/filesOne.md)

## Acceptance Criteria
- Project path: /home/user/myproject
- Ensure the real upload and rename actions are executed against the live Apideck `onedrive` connector and that the log artifact exists.
- Log file: /home/user/myproject/output.log
- The log file MUST contain two lines exactly matching these formats (no extra whitespace before the prefix):
  - `File ID: <unified_file_id>`
  - `File Name: <final_file_name>`
  where `<final_file_name>` must equal `renamed-${run-id}.txt` and `<unified_file_id>` is the Apideck unified `data.id` returned for the uploaded/renamed file.
- The file MUST be reachable via `GET https://unify.apideck.com/file-storage/files/<unified_file_id>` with the `onedrive` service id and respond `200`, where `data.name` equals `renamed-${run-id}.txt`.
- The original name `original-${run-id}.txt` MUST NOT appear in the `name` of any file returned by `GET /file-storage/files` for the configured drive.

