#!/bin/bash

# Create the file to upload
FILE_NAME="apideck-curl-${ZEALT_RUN_ID}.txt"
FILE_PATH="/tmp/${FILE_NAME}"
echo -ne "Uploaded via Apideck File Storage direct upload curl test\n" > "${FILE_PATH}"

# Get the drives
DRIVES_RESPONSE=$(curl -s -X GET "https://unify.apideck.com/file-storage/drives" \
  -H "Authorization: Bearer ${APIDECK_API_KEY}" \
  -H "x-apideck-app-id: ${APIDECK_APP_ID}" \
  -H "x-apideck-consumer-id: ${APIDECK_CONSUMER_ID}" \
  -H "x-apideck-service-id: onedrive")

# Extract the drive ID matching APIDECK_FILE_STORAGE_DRIVE_NAME
DRIVE_ID=$(echo "${DRIVES_RESPONSE}" | jq -r ".data[] | select(.name == \"${APIDECK_FILE_STORAGE_DRIVE_NAME}\") | .id")

if [ -z "$DRIVE_ID" ] || [ "$DRIVE_ID" == "null" ]; then
  echo "Drive not found"
  echo "Drives response: ${DRIVES_RESPONSE}"
  exit 1
fi

# Prepare metadata
METADATA="{\"name\":\"${FILE_NAME}\",\"parent_folder_id\":\"root\",\"drive_id\":\"${DRIVE_ID}\"}"

# Upload the file
UPLOAD_RESPONSE=$(curl -s -X POST "https://upload.apideck.com/file-storage/files" \
  -H "Authorization: Bearer ${APIDECK_API_KEY}" \
  -H "x-apideck-app-id: ${APIDECK_APP_ID}" \
  -H "x-apideck-consumer-id: ${APIDECK_CONSUMER_ID}" \
  -H "x-apideck-service-id: onedrive" \
  -H "Content-Type: text/plain" \
  -H "x-apideck-metadata: ${METADATA}" \
  --data-binary "@${FILE_PATH}")

# Extract file ID
FILE_ID=$(echo "${UPLOAD_RESPONSE}" | jq -r ".data.id")

if [ -z "$FILE_ID" ] || [ "$FILE_ID" == "null" ]; then
  echo "File ID not found in response: ${UPLOAD_RESPONSE}"
  exit 1
fi

echo "${FILE_ID}" > /home/user/myproject/output.log
