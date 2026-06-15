# Resolve a OneDrive Drive by Name and Plant a Probe Folder via the Apideck File Storage Unified API

## Background
Your platform team uses Apideck Unify to address multiple file-storage providers through a single canonical REST surface. The consumer has authorized **OneDrive** (Service ID: `onedrive`) and one of the drives that surface through Apideck has been chosen for testing; its display name is exposed to you via an environment variable. You must discover which Apideck drive `id` corresponds to that name and then drop a small "probe" folder at that drive's root so a downstream verifier can confirm you targeted the right drive.

The following environment variables are already exported in the runtime:

- `APIDECK_APP_ID`
- `APIDECK_API_KEY`
- `APIDECK_CONSUMER_ID`
- `APIDECK_FILE_STORAGE_DRIVE_NAME` — display name of the OneDrive drive you must work in.
- `ZEALT_RUN_ID` — a unique run id matching `zr-[a-z0-9]+`. You **must** include it in the probe folder name so concurrent runs do not collide.

## Requirements
- Use the Apideck File Storage Unified API at `https://unify.apideck.com` (or the official `apideck-unify` SDK). Do **not** call OneDrive / Microsoft Graph directly.
- Resolve the Apideck drive whose unified `name` field equals `APIDECK_FILE_STORAGE_DRIVE_NAME` and capture its unified `id`.
- Create exactly one folder at the **root** of that drive whose `name` is exactly `DRIVE-PROBE-${ZEALT_RUN_ID}` (substitute the run id at runtime). The Create Folder request **must** target that drive by passing the resolved `drive_id` in the request body; do not omit it.
- Persist the unified IDs returned by Apideck so the verifier can find both resources.

## Implementation Hints
- Every Apideck call needs the headers `Authorization: Bearer $APIDECK_API_KEY`, `x-apideck-app-id`, `x-apideck-consumer-id`, and `x-apideck-service-id: onedrive`.
- Drives are surfaced by `GET /file-storage/drives`; folders are created by `POST /file-storage/folders` with `name`, `parent_folder_id`, and `drive_id` in the JSON body. Use `parent_folder_id="root"` to anchor the folder at the drive root.
- Refer to the Apideck docs at <https://developers.apideck.com/apis/file-storage/reference>, the [List Drives](https://developers.apideck.com/md/apis/file-storage/reference/drives/drivesAll.md) page, and the [Create Folder](https://developers.apideck.com/md/apis/file-storage/reference/folders/foldersAdd.md) page.

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the script is actually executed against the live Apideck Unify API and the OneDrive side effect exists.
- Log file: /home/user/apideck_task/output.log
- The log file must be valid UTF-8 JSON (a single JSON object) with exactly two string fields:
  - `drive_id` — the Apideck unified `id` of the drive whose `name` equals `APIDECK_FILE_STORAGE_DRIVE_NAME`.
  - `folder_id` — the Apideck unified `id` returned by Create Folder for the probe folder.
- A folder named exactly `DRIVE-PROBE-${ZEALT_RUN_ID}` must exist at the root of the resolved drive, and its unified `id` must equal the `folder_id` value written to the log.
- `${ZEALT_RUN_ID}` must be read from the `ZEALT_RUN_ID` environment variable at runtime.

