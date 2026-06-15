# Organize OneDrive Files by Extension via Apideck File Storage

## Background
[Apideck](https://www.apideck.com/) exposes a unified File Storage API on top of providers such as OneDrive. The drive identified by the environment variable `APIDECK_FILE_STORAGE_DRIVE_NAME` already contains 6 pre-uploaded files at its root: 3 with extension `.txt` and 3 with extension `.md`. All 6 file names embed the current run id from `ZEALT_RUN_ID`.

Your job is to organize those existing files into two newly created folders, grouped by extension, using the Apideck `onedrive` connector.

## Requirements
- Read the run id from the `ZEALT_RUN_ID` environment variable.
- At the drive root, create two folders: one named `TXT-${ZEALT_RUN_ID}` and one named `MD-${ZEALT_RUN_ID}`.
- Without renaming or re-uploading any file, move every existing `.txt` file at the drive root into the `TXT-${ZEALT_RUN_ID}` folder, and every existing `.md` file at the drive root into the `MD-${ZEALT_RUN_ID}` folder.

## Implementation Hints
- The unified API base URL is `https://unify.apideck.com`. All requests must include `Authorization: Bearer $APIDECK_API_KEY`, `x-apideck-app-id`, `x-apideck-consumer-id`, and `x-apideck-service-id: onedrive`.
- Relevant endpoint documentation:
  - [List Files](https://developers.apideck.com/md/apis/file-storage/reference/files/filesAll.md)
  - [Create Folder](https://developers.apideck.com/md/apis/file-storage/reference/folders/foldersAdd.md)
  - [Rename or move File](https://developers.apideck.com/md/apis/file-storage/reference/files/filesUpdate.md)
- You may use the official `apideck-unify` Python SDK or call the REST endpoints directly with `requests`.

## Acceptance Criteria
- Project path: /home/user/myproject
- Ensure the real folder-create and file-move actions are executed against the live Apideck `onedrive` connector.
- Two folders must exist at the drive root: `TXT-${ZEALT_RUN_ID}` and `MD-${ZEALT_RUN_ID}`.
- Every pre-existing file whose name ends with `.txt` and contains `${ZEALT_RUN_ID}` must have the `TXT-${ZEALT_RUN_ID}` folder as its immediate parent folder, and every such `.md` file must have the `MD-${ZEALT_RUN_ID}` folder as its immediate parent folder.
- No `.txt` file matching that run id may end up inside the `MD-${ZEALT_RUN_ID}` folder, and no `.md` file matching that run id may end up inside the `TXT-${ZEALT_RUN_ID}` folder.
- The original file names must not be changed; only each file's parent folder is changed.

