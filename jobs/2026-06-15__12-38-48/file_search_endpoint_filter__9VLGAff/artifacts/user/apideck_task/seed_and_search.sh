#!/usr/bin/env bash
set -euo pipefail

# --- Config from environment ---
RUN_ID="${ZEALT_RUN_ID:?ZEALT_RUN_ID not set}"
DRIVE_NAME="${APIDECK_FILE_STORAGE_DRIVE_NAME:?APIDECK_FILE_STORAGE_DRIVE_NAME not set}"
APP_ID="${APIDECK_APP_ID:?APIDECK_APP_ID not set}"
CONSUMER_ID="${APIDECK_CONSUMER_ID:?APIDECK_CONSUMER_ID not set}"
API_KEY="${APIDECK_API_KEY:?APIDECK_API_KEY not set}"

UNIFY_HOST="https://unify.apideck.com"
UPLOAD_HOST="https://upload.apideck.com"

AUTH_HEADERS=(
  -H "Authorization: Bearer ${API_KEY}"
  -H "x-apideck-app-id: ${APP_ID}"
  -H "x-apideck-consumer-id: ${CONSUMER_ID}"
  -H "x-apideck-service-id: onedrive"
)

OUTPUT_LOG="/home/user/apideck_task/output.log"

echo "=== RUN_ID: ${RUN_ID} ==="
echo "=== DRIVE_NAME: ${DRIVE_NAME} ==="

# -------------------------------------------------------------------
# Step 1: List drives and find the drive id matching DRIVE_NAME
# -------------------------------------------------------------------
echo "=== Listing drives ==="
DRIVES_RESP=$(curl -sS "${UNIFY_HOST}/file-storage/drives" "${AUTH_HEADERS[@]}")
echo "Drives response: ${DRIVES_RESP}" | head -c 2000

# Extract the drive id for the matching drive name
DRIVE_ID=$(echo "${DRIVES_RESP}" | python3 -c "
import json, sys, os
data = json.load(sys.stdin)
drives = data.get('data', [])
target = os.environ['APIDECK_FILE_STORAGE_DRIVE_NAME']
for d in drives:
    if d.get('name') == target:
        print(d['id'])
        sys.exit(0)
print('', end='')
")

if [ -z "${DRIVE_ID}" ]; then
  echo "ERROR: Could not find drive with name '${DRIVE_NAME}'"
  echo "Full response: ${DRIVES_RESP}"
  exit 1
fi

echo "=== Found drive id: ${DRIVE_ID} ==="

# -------------------------------------------------------------------
# Step 2: Upload four marker files
# -------------------------------------------------------------------
FILES=(
  "KEEP-${RUN_ID}-1.txt"
  "KEEP-${RUN_ID}-2.txt"
  "SKIP-${RUN_ID}-1.txt"
  "SKIP-${RUN_ID}-2.txt"
)

for FILENAME in "${FILES[@]}"; do
  echo "=== Uploading: ${FILENAME} ==="

  # Build metadata JSON: name and parent_folder_id (use "root" for root folder)
  METADATA=$(python3 -c "
import json, os
meta = {
    'name': '${FILENAME}',
    'parent_folder_id': 'root'
}
print(json.dumps(meta))
")

  # Upload with raw body and metadata header
  UPLOAD_RESP=$(curl -sS -X POST "${UPLOAD_HOST}/file-storage/files" \
    "${AUTH_HEADERS[@]}" \
    -H "x-apideck-metadata: ${METADATA}" \
    -H "Content-Type: application/octet-stream" \
    --data-binary "marker file content for ${FILENAME} - run ${RUN_ID}")

  echo "Upload response: ${UPLOAD_RESP}" | head -c 1000
  echo ""
done

# -------------------------------------------------------------------
# Step 3: Search for KEEP-* files
# -------------------------------------------------------------------
echo "=== Searching for KEEP-${RUN_ID} ==="

SEARCH_BODY=$(python3 -c "
import json
print(json.dumps({'query': 'KEEP-${RUN_ID}'}))
")

SEARCH_RESP=$(curl -sS -X POST "${UNIFY_HOST}/file-storage/files/search" \
  "${AUTH_HEADERS[@]}" \
  -H "Content-Type: application/json" \
  -d "${SEARCH_BODY}")

echo "Search response: ${SEARCH_RESP}" | head -c 3000

# -------------------------------------------------------------------
# Step 4: Extract matching file IDs and handle pagination
# -------------------------------------------------------------------
MATCHING_IDS=$(echo "${SEARCH_RESP}" | python3 -c "
import json, sys

resp = json.load(sys.stdin)
ids = []

# Collect from first page
data = resp.get('data', [])
for f in data:
    ids.append(f['id'])

# Check for cursor-based pagination
cursor = resp.get('meta', {}).get('cursors', {}).get('next')
print('Found {} files on first page'.format(len(data)), file=sys.stderr)
if cursor:
    print('Cursor present: {}'.format(cursor), file=sys.stderr)

# Output just the ids so far
print(json.dumps(ids))
")

echo "Matching IDs (first page): ${MATCHING_IDS}"

# Handle pagination if cursor is present
CURSOR=$(echo "${SEARCH_RESP}" | python3 -c "
import json, sys
resp = json.load(sys.stdin)
c = resp.get('meta', {}).get('cursors', {}).get('next')
print(c if c else '')
")

while [ -n "${CURSOR}" ]; do
  echo "=== Fetching next page with cursor: ${CURSOR} ==="
  CURSOR_BODY=$(python3 -c "import json; print(json.dumps({'cursor': '${CURSOR}'}))")
  
  PAGE_RESP=$(curl -sS -X POST "${UNIFY_HOST}/file-storage/files/search" \
    "${AUTH_HEADERS[@]}" \
    -H "Content-Type: application/json" \
    -d "${CURSOR_BODY}")

  echo "Page response: ${PAGE_RESP}" | head -c 2000

  PAGE_IDS=$(echo "${PAGE_RESP}" | python3 -c "
import json, sys
resp = json.load(sys.stdin)
ids = [f['id'] for f in resp.get('data', [])]
print(json.dumps(ids))
")

  # Merge page ids into MATCHING_IDS
  MATCHING_IDS=$(python3 -c "
import json
existing = json.loads('${MATCHING_IDS}')
new = json.loads('${PAGE_IDS}')
existing.extend(new)
print(json.dumps(existing))
")

  CURSOR=$(echo "${PAGE_RESP}" | python3 -c "
import json, sys
resp = json.load(sys.stdin)
c = resp.get('meta', {}).get('cursors', {}).get('next')
print(c if c else '')
")
done

# -------------------------------------------------------------------
# Step 5: Write output log
# -------------------------------------------------------------------
echo "=== Final matching IDs: ${MATCHING_IDS} ==="

python3 -c "
import json
ids = json.loads('${MATCHING_IDS}')
result = {'search_result_ids': ids}
with open('${OUTPUT_LOG}', 'w') as f:
    f.write(json.dumps(result) + '\n')
print('Wrote output to ${OUTPUT_LOG}')
"

echo "=== Done ==="
cat "${OUTPUT_LOG}"
