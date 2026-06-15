# ApiDeck File Storage — Verify Byte-Exact Upload Size

## Background
ApiDeck's File Storage Unified API exposes a `size` field (bytes) on file metadata. You will upload a small text file to the connected OneDrive drive root via the ApiDeck unified File Storage API and confirm that the uploaded file's reported `size` matches the exact byte length of the payload you sent.

## Requirements
- Read the current `run-id` from the `ZEALT_RUN_ID` environment variable.
- Upload exactly one file at the drive root with the name `SIZED-${run-id}.txt`.
- The file's content (the raw byte body) MUST be the ASCII string `ApiDeck-${run-id}-payload-line\n` (where `\n` is a single LF byte, `0x0A`) repeated EXACTLY 100 times, with no leading bytes, no trailing bytes, and no other modifications.
- After uploading, the file's metadata `size` reported by ApiDeck MUST equal the exact byte length of the payload you sent.

## Implementation Hints
- File Storage uploads use the upload host (`upload.apideck.com`), not the unify host.
- The upload endpoint expects the file metadata (`name`, `parent_folder_id`) inside the `x-apideck-metadata` request header as a JSON string, and the request body must be the raw binary bytes of the file (not multipart/form-data).
- Use `parent_folder_id` `"root"` to place the file at the drive root.
- The connector for File Storage is OneDrive — set the `x-apideck-service-id` header accordingly.
- Required ApiDeck headers: `Authorization: Bearer $APIDECK_API_KEY`, `x-apideck-app-id`, `x-apideck-consumer-id`, `x-apideck-service-id`.

## Acceptance Criteria
- Project path: /home/user/apideck_task
- Ensure the upload is actually performed against ApiDeck (no mocking) and the artifact log exists.
- Log file: /home/user/apideck_task/output.log
- Read `run-id` from the `ZEALT_RUN_ID` environment variable.
- Exactly one file named `SIZED-${run-id}.txt` exists at the root of the configured OneDrive drive.
- The reported `size` (bytes) on the file's ApiDeck metadata equals the exact byte length of the payload sent.
- The file's `mime_type` is NOT asserted by the verifier (connectors may normalize it differently); you do not need to control it.
- The log file must contain the uploaded file's ApiDeck id in the format: `File ID: <file_id>`.

