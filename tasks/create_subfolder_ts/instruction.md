# Create a Nested Folder Structure in OneDrive via Apideck (TypeScript SDK)

## Background
You are building a workspace organizer for a SaaS product that uses [Apideck](https://www.apideck.com/) to talk to multiple cloud file storage providers through a single Unified File Storage API. The current environment is configured with a single connector — OneDrive (`service_id: onedrive`) — and a pre-configured drive whose name is provided as `APIDECK_FILE_STORAGE_DRIVE_NAME`.

Your job is to create a two-level folder hierarchy inside that drive using the official Apideck TypeScript / Node.js SDK (`@apideck/unify`): a parent folder created at the drive root, and a child folder created **inside** that parent folder by referencing its `id` as the new folder's `parent_folder_id`.

## Requirements
- Read all credentials and configuration from environment variables: `APIDECK_APP_ID`, `APIDECK_API_KEY`, `APIDECK_CONSUMER_ID`, `APIDECK_FILE_STORAGE_DRIVE_NAME`, and `ZEALT_RUN_ID`.
- Use the `@apideck/unify` TypeScript / Node.js SDK to talk to Apideck (do not call `unify.apideck.com` with raw `fetch`/`axios`).
- Resolve the target drive: list drives in OneDrive and pick the one whose `name` exactly matches `APIDECK_FILE_STORAGE_DRIVE_NAME`. Use its `id` as `drive_id` when creating folders.
- Create a **parent folder** named `apideck-parent-${ZEALT_RUN_ID}` at the drive's root (`parent_folder_id: "root"`).
- Create a **child folder** named `apideck-child-${ZEALT_RUN_ID}` whose `parent_folder_id` is the `id` returned by the parent-folder create call (not `"root"` and not a literal path string).
- Write a JSON log file with the IDs and names of both folders so the verifier can confirm the hierarchy.

## Implementation Hints
- Install `@apideck/unify` with npm and run TypeScript via a runner of your choice (e.g. `ts-node`, `tsx`, or compile with `tsc` then run with `node`).
- Initialize the SDK with the API key, app ID, and consumer ID, and pass `serviceId: "onedrive"` on each call so Apideck routes to the OneDrive connector.
- The drives listing endpoint returns a paginated iterable — make sure you walk pages until you find the matching drive name, or use a `filter` if convenient.
- `parent_folder_id` for a root-level item is the literal string `"root"`; for the nested folder it must be the parent folder's `id` returned by the create response.
- Refer to: [Create Folder](https://developers.apideck.com/md/apis/file-storage/reference/folders/foldersAdd.md), [List Drives](https://developers.apideck.com/md/apis/file-storage/reference/drives/drivesAll.md), and the [TypeScript / Node.js SDK](https://developers.apideck.com/sdks/node.md).

## Acceptance Criteria
- Project path: /home/user/myproject
- Ensure the real folder-creation actions are executed against Apideck/OneDrive and the log artifact exists.
- Log file: /home/user/myproject/output.log
- The log file MUST be valid JSON with at least these top-level fields:
  - `drive_id` (string) — id of the drive resolved from `APIDECK_FILE_STORAGE_DRIVE_NAME`.
  - `parent_folder_id` (string) — id returned when creating the parent folder.
  - `parent_folder_name` (string) — `apideck-parent-${ZEALT_RUN_ID}`.
  - `child_folder_id` (string) — id returned when creating the child folder.
  - `child_folder_name` (string) — `apideck-child-${ZEALT_RUN_ID}`.
- The two folders MUST be discoverable via the Apideck File Storage API:
  - A folder named `apideck-parent-${ZEALT_RUN_ID}` exists in the configured drive.
  - A folder named `apideck-child-${ZEALT_RUN_ID}` exists in the configured drive and lists the parent folder in its `parent_folders` chain (i.e. its `parent_folders[*].id` includes `parent_folder_id`).
- The TypeScript / Node.js SDK (`@apideck/unify`) MUST be present in the project's `package.json` dependencies.

