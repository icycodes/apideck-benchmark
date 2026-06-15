# Rename a Root-Level OneDrive File In Place via Apideck PATCH

## Background
[Apideck](https://www.apideck.com/) exposes a Unified File Storage API over many providers. In this environment the `onedrive` connector is preconfigured against the drive named in `APIDECK_FILE_STORAGE_DRIVE_NAME`. Your job is to upload a file at the drive root and then rename it in place through the unified PATCH endpoint, preserving the file's unified identifier.

## Requirements
- Read the trial id from the `ZEALT_RUN_ID` environment variable.
- Upload a single small text file at the drive root with the exact name `ORIGINAL-${ZEALT_RUN_ID}.txt` (uppercase prefix, case-sensitive).
- Rename that uploaded file in place to `RENAMED-${ZEALT_RUN_ID}.txt` using the unified File Storage PATCH endpoint. The rename MUST keep the file's unified `id` stable and keep the file at the drive root.
- Record the resulting unified `id` so the verifier can correlate the renamed file with the original upload.

## Implementation Hints
- All Apideck calls require the standard auth/app/consumer headers plus the OneDrive service id; uploads use the dedicated upload host, while metadata/rename calls use the main unified host.
- The rename is a `PATCH` operation on the single file, not a delete-then-create. The verifier explicitly checks that the id from before the rename still resolves to the renamed file.
- See the [File Storage API reference](https://developers.apideck.com/apis/file-storage/reference) for endpoint shapes and the [file upload guide](https://developers.apideck.com/guides/file-upload.md) for upload mechanics.

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the real upload and rename actions are executed against the live Apideck `onedrive` connector and that the log artifact exists.
- Log file: /home/user/apideck_task/output.log
- The log file MUST contain a line of the exact format `File ID: <unified_file_id>`, where `<unified_file_id>` is the unified `data.id` returned by Apideck for the uploaded file (which is also the id of the renamed file).
- After the task finishes, exactly zero files named `ORIGINAL-${ZEALT_RUN_ID}.txt` exist in the configured OneDrive drive.
- After the task finishes, exactly one file named `RENAMED-${ZEALT_RUN_ID}.txt` exists, and its unified id equals the id recorded in the log file.
- The renamed file's parent location is the drive root (i.e., it has no nested parent folder besides the drive root itself).

