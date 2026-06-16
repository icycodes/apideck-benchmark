#!/usr/bin/env bash
set -euo pipefail

API_KEY="(*****SECRET_LEAK_DETECTED*****)"
APP_ID="605EzrgGklBBo5T9tcIgkHs4omRyk3ykcJVtcIg"
CONSUMER_ID="test-consumer"
RUN_ID="${ZEALT_RUN_ID:-zr-y3jhgm3}"
COLLECTION_ID="${APIDECK_ISSUE_TRACKING_COLLECTION_ID:-zealt-user-default-repo}"

# OneDrive drive root id (from drives listing, the "OneDrive" named drive)
DRIVE_ID="3ada079b78534ff1"

BASE_URL="https://unify.apideck.com"

echo "=== ZEALT_RUN_ID: $RUN_ID ==="
echo "=== COLLECTION_ID: $COLLECTION_ID ==="

upload_file() {
  local filename="$1"
  local content="$2"

  # Create a temp file
  local tmpfile
  tmpfile=$(mktemp /tmp/apideck_XXXXXX.txt)
  echo -n "$content" > "$tmpfile"

  echo "Uploading $filename ..."

  RESPONSE=$(curl -s -X POST "$BASE_URL/file-storage/files" \
    -H "Authorization: Bearer $API_KEY" \
    -H "x-apideck-app-id: $APP_ID" \
    -H "x-apideck-consumer-id: $CONSUMER_ID" \
    -H "x-apideck-service-id: onedrive" \
    -F "file=@${tmpfile};filename=${filename};type=text/plain" \
    -F "name=${filename}" \
    -F "parent_folder_id=root" \
    -F "drive_id=${DRIVE_ID}")

  rm -f "$tmpfile"

  echo "Response: $RESPONSE"
  FILE_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['id'])")
  echo "File ID: $FILE_ID"
  echo "$FILE_ID"
}

# Upload the three files
FILE_A=$(upload_file "REPORT-${RUN_ID}-A.txt" "Report A for run ${RUN_ID}")
FILE_B=$(upload_file "REPORT-${RUN_ID}-B.txt" "Report B for run ${RUN_ID}")
FILE_C=$(upload_file "REPORT-${RUN_ID}-C.txt" "Report C for run ${RUN_ID}")

echo "=== Uploaded file IDs ==="
echo "A: $FILE_A"
echo "B: $FILE_B"
echo "C: $FILE_C"

# Sort the IDs ascending
SORTED_IDS=$(printf '%s\n' "$FILE_A" "$FILE_B" "$FILE_C" | sort)
echo "=== Sorted IDs ==="
echo "$SORTED_IDS"

# Build description: newline-joined sorted IDs, nothing else
DESCRIPTION=$(printf '%s\n' "$FILE_A" "$FILE_B" "$FILE_C" | sort | tr '\n' '\n')
# Remove trailing newline issues by building it cleanly
LINE1=$(printf '%s\n' "$FILE_A" "$FILE_B" "$FILE_C" | sort | sed -n '1p')
LINE2=$(printf '%s\n' "$FILE_A" "$FILE_B" "$FILE_C" | sort | sed -n '2p')
LINE3=$(printf '%s\n' "$FILE_A" "$FILE_B" "$FILE_C" | sort | sed -n '3p')
DESCRIPTION="${LINE1}
${LINE2}
${LINE3}"

SUBJECT="[FILE-INDEX] ${RUN_ID} File Upload Report"

echo "=== Creating ticket ==="
echo "Subject: $SUBJECT"
echo "Description:"
echo "$DESCRIPTION"

TICKET_PAYLOAD=$(python3 -c "
import json
subject = '$SUBJECT'
description = '''${DESCRIPTION}'''
payload = {
    'subject': subject,
    'description': description,
    'status': 'open',
    'type': 'task'
}
print(json.dumps(payload))
")

echo "Payload: $TICKET_PAYLOAD"

TICKET_RESPONSE=$(curl -s -X POST "$BASE_URL/issue-tracking/collections/${COLLECTION_ID}/tickets" \
  -H "Authorization: Bearer $API_KEY" \
  -H "x-apideck-app-id: $APP_ID" \
  -H "x-apideck-consumer-id: $CONSUMER_ID" \
  -H "x-apideck-service-id: github" \
  -H "Content-Type: application/json" \
  -d "$TICKET_PAYLOAD")

echo "=== Ticket Response ==="
echo "$TICKET_RESPONSE" | python3 -m json.tool || echo "$TICKET_RESPONSE"

TICKET_ID=$(echo "$TICKET_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['id'])" 2>/dev/null || echo "ERROR")
echo "=== Ticket ID: $TICKET_ID ==="
