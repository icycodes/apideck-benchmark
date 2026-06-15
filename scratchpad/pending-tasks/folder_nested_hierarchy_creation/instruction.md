# Build a 4-Level Nested Folder Tree in OneDrive via ApiDeck

## Background
Use the ApiDeck **File Storage** unified API (OneDrive connector) to provision a deep folder hierarchy that downstream tasks can rely on for organizing per-run artifacts. The target drive is identified by its name (`APIDECK_FILE_STORAGE_DRIVE_NAME`), not by id.

## Requirements
- Resolve the OneDrive drive whose name matches `APIDECK_FILE_STORAGE_DRIVE_NAME`.
- Inside that drive, create a chain of **exactly four nested folders** starting at the drive root, in the following parent → child order: `LEVEL1` → `LEVEL2` → `LEVEL3` → `LEVEL4`.
- Each child folder's `parent_folder_id` must reference the id returned for its immediate parent. The top-level folder's parent must be the drive root.
- Persist the four returned folder ids into a JSON log file the verifier will read.

## Implementation Hints
- Authenticate with the standard headers (`Authorization`, `x-apideck-app-id`, `x-apideck-consumer-id`) and target the OneDrive connector with `x-apideck-service-id: onedrive`.
- Use `GET /file-storage/drives` to find the drive id whose `name` equals `APIDECK_FILE_STORAGE_DRIVE_NAME`.
- Use `POST /file-storage/folders` four times, supplying `name`, `parent_folder_id`, and `drive_id`. Use the literal string `root` as the `parent_folder_id` of the top-level folder.
- Read `ZEALT_RUN_ID` from the environment and embed it in the top-level folder name only.

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the script is executed and the real folders are created on OneDrive.
- Log file: /home/user/apideck_task/output.log
- Naming convention (exactly this convention, no other variation accepted):
  - Top-level folder name MUST equal `LEVEL1-${ZEALT_RUN_ID}` where `${ZEALT_RUN_ID}` is read from the environment.
  - The remaining three folder names MUST be exactly `LEVEL2`, `LEVEL3`, and `LEVEL4` (no run-id suffix).
- Parent relationships (verified via List Files / Get File only):
  - `LEVEL1-${ZEALT_RUN_ID}` is created at the drive root.
  - `LEVEL2`'s immediate parent is `LEVEL1-${ZEALT_RUN_ID}`.
  - `LEVEL3`'s immediate parent is `LEVEL2`.
  - `LEVEL4`'s immediate parent is `LEVEL3`.
  - All four resources must have `type` = `folder` and live inside the drive resolved from `APIDECK_FILE_STORAGE_DRIVE_NAME`.
- Output log content: `output.log` MUST contain a single JSON object with exactly the keys `level1_id`, `level2_id`, `level3_id`, `level4_id`, each mapped to the corresponding folder id returned by ApiDeck.

