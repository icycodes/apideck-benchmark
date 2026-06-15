# OneDrive Folder Rename and Move via Apideck File Storage

## Background
Apideck's File Storage Unified API exposes folder lifecycle operations across providers. The `onedrive` connector is configured for File Storage on this account. You will reorganize folders on the configured OneDrive drive by first creating two sibling folders at the drive root, then renaming one of them and moving it inside the other using folder-update operations.

## Requirements
- Read `ZEALT_RUN_ID` from the environment and derive a unique folder name suffix for this run.
- Create two folders at the drive root.
- Rename one of the folders and reparent it so it becomes a child of the other folder.
- The rename and the move must both be performed through Apideck's folder-update endpoint (no delete-and-recreate).
- Persist the resulting folder identifiers to a JSON log file.

## Implementation Hints
- All requests live under `https://unify.apideck.com` and require `Authorization: Bearer <APIDECK_API_KEY>`, `x-apideck-app-id`, `x-apideck-consumer-id`, and the File Storage service id for OneDrive.
- Use `POST /file-storage/folders` to create folders; supply `"parent_folder_id": "root"` to place a folder at the drive root.
- Use `PATCH /file-storage/folders/{id}` to mutate a folder. The same endpoint accepts updates to `name`, `parent_folder_id`, or both.
- Capture the `data.id` from create/update responses so you can reference the same resource across calls and emit it in the log.
- You can verify with `GET /file-storage/folders/{id}` or `GET /file-storage/files` (folders appear with `type="folder"` and a `parent_folders` array).

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the real Apideck calls are executed and the artifacts exist on OneDrive.
- Log file: /home/user/apideck_task/output.log
- The log file MUST contain a single JSON object with exactly these keys: `outer_id` and `inner_id`. Each value is the Apideck folder id (string) of the corresponding folder after all operations complete.
- Read `ZEALT_RUN_ID` from the environment; use its raw value as the run-id suffix below.
- After execution, the following state MUST hold on the configured OneDrive drive:
  - A folder named exactly `OUTER-${ZEALT_RUN_ID}` exists at the drive root (its `parent_folders` is empty or only contains the drive root).
  - No folder named `INNER-${ZEALT_RUN_ID}` exists anywhere on the drive.
  - Exactly one folder named `INNER-RENAMED-${ZEALT_RUN_ID}` exists on the drive, and its immediate parent is `OUTER-${ZEALT_RUN_ID}` (not the drive root).
- The `inner_id` recorded in the log MUST equal the folder id returned by `GET /file-storage/folders/{inner_id}` for the `INNER-RENAMED-${ZEALT_RUN_ID}` folder, proving the folder was renamed and moved via PATCH rather than deleted and recreated.

