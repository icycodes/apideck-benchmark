#!/usr/bin/env bash
set -euo pipefail

# Read environment variables
APP_ID="${APIDECK_APP_ID}"
API_KEY="${APIDECK_API_KEY}"
CONSUMER_ID="${APIDECK_CONSUMER_ID}"
DRIVE_NAME="${APIDECK_FILE_STORAGE_DRIVE_NAME}"
RUN_ID="${ZEALT_RUN_ID}"

FILE_NAME="apideck-curl-${RUN_ID}.txt"
CONTENT_TYPE="text/plain"

# Step 1: Discover the target drive ID
echo "Discovering drive ID for: ${DRIVE_NAME}..."
DRIVES_RESPONSE=$(curl -s -X GET "https://unify.apideck.com/file-storage/drives" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "x-apideck-app-id: ${APP_ID}" \
  -H "x-apideck-consumer-id: ${CONSUMER_ID}" \
  -H "x-apideck-service-id: onedrive" \
  -H "Content-Type: application/json")

DRIVE_ID=$(echo "${DRIVES_RESPONSE}" | python3 -c "
import json, sys, os
data = json.load(sys.stdin)
drive_name = os.environ['APIDECK_FILE_STORAGE_DRIVE_NAME']
for drive in data['data']:
    if drive['name'] == drive_name:
        print(drive['id'])
        break
else:
    print('DRIVE_NOT_FOUND', file=sys.stderr)
    sys.exit(1)
")

echo "Target drive ID: ${DRIVE_ID}"

# Step 2: Prepare file content (exact 58 bytes: single line terminated by \n)
TMPFILE=$(mktemp)
printf 'Uploaded via Apideck File Storage direct upload curl test\n' > "${TMPFILE}"

# Step 3: Build metadata JSON
METADATA=$(python3 -c "
import json
print(json.dumps({
    'name': '${FILE_NAME}',
    'parent_folder_id': 'root',
    'drive_id': '${DRIVE_ID}'
}))
")

echo "Upload metadata: ${METADATA}"

# Step 4: Upload via curl to upload.apideck.com (NOT unify.apideck.com)
UPLOAD_RESPONSE=$(curl -s -X POST "https://upload.apideck.com/file-storage/files" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "x-apideck-app-id: ${APP_ID}" \
  -H "x-apideck-consumer-id: ${CONSUMER_ID}" \
  -H "x-apideck-service-id: onedrive" \
  -H "x-apideck-metadata: ${METADATA}" \
  -H "Content-Type: ${CONTENT_TYPE}" \
  --data-binary "@${TMPFILE}")

echo "Upload response: ${UPLOAD_RESPONSE}"

# Step 5: Extract file ID and write to output.log
FILE_ID=$(echo "${UPLOAD_RESPONSE}" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data['data']['id'])
")

echo "Uploaded file ID: ${FILE_ID}"

# Write the file ID to output.log (single non-empty line)
mkdir -p /home/user/myproject
echo "${FILE_ID}" > /home/user/myproject/output.log

# Clean up temp file
rm -f "${TMPFILE}"

echo "Done. File ID written to /home/user/myproject/output.log"