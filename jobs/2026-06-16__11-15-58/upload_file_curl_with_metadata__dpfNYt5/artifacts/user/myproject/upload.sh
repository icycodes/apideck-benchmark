#!/usr/bin/env bash
set -euo pipefail

# ── Environment variables ──────────────────────────────────────────────────
APIDECK_APP_ID="${APIDECK_APP_ID}"
APIDECK_API_KEY="${APIDECK_API_KEY}"
APIDECK_CONSUMER_ID="${APIDECK_CONSUMER_ID}"
APIDECK_FILE_STORAGE_DRIVE_NAME="${APIDECK_FILE_STORAGE_DRIVE_NAME}"
ZEALT_RUN_ID="${ZEALT_RUN_ID}"

OUTPUT_LOG="/home/user/myproject/output.log"
UPLOAD_FILE="/tmp/apideck-upload-${ZEALT_RUN_ID}.txt"

# ── Create the file to upload ──────────────────────────────────────────────
printf 'Uploaded via Apideck File Storage direct upload curl test\n' > "${UPLOAD_FILE}"
echo "File created: ${UPLOAD_FILE} ($(wc -c < "${UPLOAD_FILE}") bytes)"

# ── Step 1: Discover drives and find the target drive ID ───────────────────
echo "Fetching drives from Apideck..."
DRIVES_RESPONSE=$(curl --silent --fail \
  -X GET "https://unify.apideck.com/file-storage/drives" \
  -H "Authorization: Bearer ${APIDECK_API_KEY}" \
  -H "x-apideck-app-id: ${APIDECK_APP_ID}" \
  -H "x-apideck-consumer-id: ${APIDECK_CONSUMER_ID}" \
  -H "x-apideck-service-id: onedrive" \
  -H "Accept: application/json")

echo "Drives response received"

# Extract the drive id whose name matches APIDECK_FILE_STORAGE_DRIVE_NAME
DRIVE_ID=$(echo "${DRIVES_RESPONSE}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
drives = data.get('data', [])
target = '${APIDECK_FILE_STORAGE_DRIVE_NAME}'
for d in drives:
    if d.get('name') == target:
        print(d['id'])
        break
else:
    print('NOT_FOUND')
")

if [[ "${DRIVE_ID}" == "NOT_FOUND" || -z "${DRIVE_ID}" ]]; then
  echo "ERROR: Could not find drive named '${APIDECK_FILE_STORAGE_DRIVE_NAME}'"
  echo "Available drives:"
  echo "${DRIVES_RESPONSE}" | python3 -c "import sys,json; [print(d.get('name'), '->', d.get('id')) for d in json.load(sys.stdin).get('data',[])]"
  exit 1
fi

echo "Found drive '${APIDECK_FILE_STORAGE_DRIVE_NAME}' with ID: ${DRIVE_ID}"

# ── Step 2: Build file name ────────────────────────────────────────────────
FILE_NAME="apideck-curl-${ZEALT_RUN_ID}.txt"
echo "Uploading file: ${FILE_NAME}"

# ── Step 3: Upload the file via direct upload endpoint ────────────────────
# Note: host is upload.apideck.com, NOT unify.apideck.com
# Metadata is passed in x-apideck-metadata header as JSON
# Body is raw binary content via --data-binary
METADATA="{\"name\":\"${FILE_NAME}\",\"parent_folder_id\":\"root\",\"drive_id\":\"${DRIVE_ID}\"}"

echo "Sending upload request to upload.apideck.com..."
UPLOAD_RESPONSE=$(curl --silent --fail \
  -X POST "https://upload.apideck.com/file-storage/files" \
  -H "Authorization: Bearer ${APIDECK_API_KEY}" \
  -H "x-apideck-app-id: ${APIDECK_APP_ID}" \
  -H "x-apideck-consumer-id: ${APIDECK_CONSUMER_ID}" \
  -H "x-apideck-service-id: onedrive" \
  -H "Content-Type: text/plain" \
  -H "x-apideck-metadata: ${METADATA}" \
  --data-binary "@${UPLOAD_FILE}")

echo "Upload response received:"
echo "${UPLOAD_RESPONSE}"

# ── Step 4: Extract and save the file ID ──────────────────────────────────
FILE_ID=$(echo "${UPLOAD_RESPONSE}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
fid = data.get('data', {}).get('id', '')
print(fid)
")

if [[ -z "${FILE_ID}" ]]; then
  echo "ERROR: Could not extract file ID from upload response"
  exit 1
fi

echo "Uploaded successfully. File ID: ${FILE_ID}"

# Write only the file ID to output.log (single non-empty line)
printf '%s\n' "${FILE_ID}" > "${OUTPUT_LOG}"
echo "Written to ${OUTPUT_LOG}"
