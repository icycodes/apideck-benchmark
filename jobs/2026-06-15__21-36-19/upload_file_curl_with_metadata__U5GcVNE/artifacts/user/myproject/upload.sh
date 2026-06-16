#!/bin/bash
set -euo pipefail

# Verify environment variables
if [ -z "${APIDECK_API_KEY:-}" ] || [ -z "${APIDECK_APP_ID:-}" ] || [ -z "${APIDECK_CONSUMER_ID:-}" ] || [ -z "${APIDECK_FILE_STORAGE_DRIVE_NAME:-}" ] || [ -z "${ZEALT_RUN_ID:-}" ]; then
  echo "Error: Missing required environment variables." >&2
  exit 1
fi

echo "All environment variables verified."

# 1. Fetch drives to find the drive ID matching APIDECK_FILE_STORAGE_DRIVE_NAME
echo "Fetching drives..."
DRIVES_JSON=$(curl -s -X GET "https://unify.apideck.com/file-storage/drives" \
  -H "Authorization: Bearer $APIDECK_API_KEY" \
  -H "x-apideck-app-id: $APIDECK_APP_ID" \
  -H "x-apideck-consumer-id: $APIDECK_CONSUMER_ID" \
  -H "x-apideck-service-id: onedrive")

DRIVE_ID=$(echo "$DRIVES_JSON" | jq -r '.data[] | select(.name == "'"$APIDECK_FILE_STORAGE_DRIVE_NAME"'") | .id')

if [ -z "$DRIVE_ID" ] || [ "$DRIVE_ID" = "null" ]; then
  echo "Error: Could not find drive with name '$APIDECK_FILE_STORAGE_DRIVE_NAME'." >&2
  echo "Response was: $DRIVES_JSON" >&2
  exit 1
fi

echo "Found target drive '$APIDECK_FILE_STORAGE_DRIVE_NAME' with ID: $DRIVE_ID"

# 2. Create local file to upload
FILE_NAME="apideck-curl-${ZEALT_RUN_ID}.txt"
FILE_PATH="/home/user/myproject/${FILE_NAME}"

echo -ne "Uploaded via Apideck File Storage direct upload curl test\n" > "$FILE_PATH"

# Verify file size is exactly 58 bytes
FILE_SIZE=$(wc -c < "$FILE_PATH")
if [ "$FILE_SIZE" -ne 58 ]; then
  echo "Error: Created file size is $FILE_SIZE bytes, expected 58 bytes." >&2
  exit 1
fi

echo "Created local file: $FILE_PATH ($FILE_SIZE bytes)"

# 3. Construct metadata and perform raw direct upload via curl
METADATA=$(jq -c -n \
  --arg name "$FILE_NAME" \
  --arg parent_folder_id "root" \
  --arg drive_id "$DRIVE_ID" \
  '{name: $name, parent_folder_id: $parent_folder_id, drive_id: $drive_id}')

echo "Uploading file via Apideck File Storage direct upload..."
UPLOAD_RESPONSE=$(curl -s -X POST "https://upload.apideck.com/file-storage/files" \
  -H "Authorization: Bearer $APIDECK_API_KEY" \
  -H "Content-Type: text/plain" \
  -H "x-apideck-app-id: $APIDECK_APP_ID" \
  -H "x-apideck-consumer-id: $APIDECK_CONSUMER_ID" \
  -H "x-apideck-service-id: onedrive" \
  -H "x-apideck-metadata: $METADATA" \
  --data-binary "@$FILE_PATH")

echo "Upload response received."

# 4. Parse response and write file ID to output.log
FILE_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.data.id // empty')

if [ -z "$FILE_ID" ] || [ "$FILE_ID" = "null" ]; then
  echo "Error: Upload failed or file ID not returned in response." >&2
  echo "Upload response: $UPLOAD_RESPONSE" >&2
  exit 1
fi

echo "Uploaded successfully! Unified File ID: $FILE_ID"

# Write the ID as the only non-empty line in output.log
echo "$FILE_ID" > "/home/user/myproject/output.log"
echo "Wrote file ID to /home/user/myproject/output.log"

# 5. Verification
echo "Verifying file retrieval..."
VERIFY_RESPONSE=$(curl -s -X GET "https://unify.apideck.com/file-storage/files/$FILE_ID" \
  -H "Authorization: Bearer $APIDECK_API_KEY" \
  -H "x-apideck-app-id: $APIDECK_APP_ID" \
  -H "x-apideck-consumer-id: $APIDECK_CONSUMER_ID" \
  -H "x-apideck-service-id: onedrive")

VERIFY_NAME=$(echo "$VERIFY_RESPONSE" | jq -r '.data.name // empty')
VERIFY_TYPE=$(echo "$VERIFY_RESPONSE" | jq -r '.data.type // empty')

if [ "$VERIFY_NAME" = "$FILE_NAME" ] && [ "$VERIFY_TYPE" = "file" ]; then
  echo "Verification Succeeded! File name: $VERIFY_NAME, File type: $VERIFY_TYPE"
else
  echo "Verification Failed! Received: name=$VERIFY_NAME, type=$VERIFY_TYPE" >&2
  echo "Response: $VERIFY_RESPONSE" >&2
  exit 1
fi
