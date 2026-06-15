# Move a File Between Two Folders via Apideck File Storage (OneDrive)

## Background
You are working with the Apideck Unified File Storage API connected to a OneDrive drive. Implement a small one-off automation that organizes a freshly uploaded file by relocating it from a staging folder to a destination folder using the unified API.

## Requirements
- Use the Apideck File Storage API against the configured OneDrive connector to perform a three-step organize operation in a single run:
  1. Create a staging folder and a destination folder at the drive root.
  2. Upload a small text file into the staging folder.
  3. Move that file into the destination folder (the file's name must NOT change).
- Persist a structured log line describing the resulting resource ids.

## Implementation Hints
- Read the `ZEALT_RUN_ID`, `APIDECK_APP_ID`, `APIDECK_API_KEY`, and `APIDECK_CONSUMER_ID` environment variables before issuing any request.
- Apideck normalizes File Storage. Required headers on every call: `Authorization: Bearer`, `x-apideck-app-id`, `x-apideck-consumer-id`, `x-apideck-service-id`.
- The Unify base URL `https://unify.apideck.com` is used for folder, file metadata, list, and patch calls. File binary uploads use a different host.
- Folder creation accepts a `parent_folder_id` of `"root"` to target the drive root.
- The unified "move" operation for a file is a PATCH on the file resource that updates the file's parent.
- Avoid renaming the file when moving it.

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the script is executed and the artifacts exist (the verifier does not re-run the move).
- Log file: /home/user/apideck_task/output.log
- Service id used for File Storage calls: `onedrive`.
- The drive root must contain a folder named `SRC-${ZEALT_RUN_ID}` and a folder named `DST-${ZEALT_RUN_ID}`.
- Exactly one file named `MOVE-${ZEALT_RUN_ID}.txt` must exist in the configured drive after the run, and it must reside in the destination folder (its `parent_folders` references the destination folder id, not the source folder id).
- The file name `MOVE-${ZEALT_RUN_ID}.txt` must be preserved across the move (no rename).
- The log file must contain a single JSON object on its last non-empty line with the keys `file_id`, `src_folder_id`, and `dst_folder_id`, each mapped to the corresponding Apideck unified resource id strings.

