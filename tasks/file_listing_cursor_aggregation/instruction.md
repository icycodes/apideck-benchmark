# Aggregate Files With Cursor Pagination (Apideck File Storage)

## Background
Use the Apideck unified File Storage API (connected to OneDrive) to upload a fixed set of files, then walk the file listing using cursor pagination to aggregate identifiers across pages.

## Requirements
- Upload 7 distinct small text files at the drive root of the OneDrive drive named in `APIDECK_FILE_STORAGE_DRIVE_NAME`.
- After uploading, use cursor pagination with a page size of 3 to walk the file listing and aggregate every file whose name matches the run-scoped prefix.
- Emit a JSON summary of the aggregation to a log file.

## Implementation Hints
- Read `APIDECK_APP_ID`, `APIDECK_API_KEY`, `APIDECK_CONSUMER_ID`, `APIDECK_FILE_STORAGE_DRIVE_NAME`, and `ZEALT_RUN_ID` from the environment.
- File uploads must hit the upload host; listing happens on the unify host. The service id for OneDrive is `onedrive`.
- Each List Files response exposes a `meta.cursors.next` value; pass it back as the `cursor` query parameter to fetch the next page. Stop only once `next` is empty.
- The aggregation must include only files whose names start with the run-scoped prefix, regardless of which page they appear on.

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the real Apideck uploads are executed and the log artifact exists.
- Log file: /home/user/apideck_task/output.log
- After the task runs, exactly 7 files must exist at the drive root with names matching the prefix `AGG-${ZEALT_RUN_ID}-`. The seven file names are `AGG-${ZEALT_RUN_ID}-1.txt` through `AGG-${ZEALT_RUN_ID}-7.txt`.
- The log file must contain a single JSON object with two keys:
  - `count`: integer equal to 7.
  - `ids`: array of strings, each being the Apideck file id of a file matching the prefix. The set of ids must equal the set of ids the verifier discovers via cursor-paginated List Files.
- The listing walk used to populate `ids` must use cursor pagination with `limit=3`.

