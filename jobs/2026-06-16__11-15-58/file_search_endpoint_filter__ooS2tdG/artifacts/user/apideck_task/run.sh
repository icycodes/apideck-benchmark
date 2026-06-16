#!/usr/bin/env bash
set -euo pipefail

# ---- Config from environment ----
RUN_ID="${ZEALT_RUN_ID}"
APP_ID="${APIDECK_APP_ID}"
CONSUMER_ID="${APIDECK_CONSUMER_ID}"
API_KEY="${APIDECK_API_KEY}"
DRIVE_NAME="${APIDECK_FILE_STORAGE_DRIVE_NAME}"
LOG_FILE="/home/user/apideck_task/output.log"

UNIFY_BASE="https://unify.apideck.com"
UPLOAD_BASE="https://upload.apideck.com"
SERVICE_ID="onedrive"

echo "==> RUN_ID: ${RUN_ID}"
echo "==> DRIVE_NAME: ${DRIVE_NAME}"

# ---- Common headers ----
common_headers=(
  -H "Authorization: Bearer ${API_KEY}"
  -H "x-apideck-app-id: ${APP_ID}"
  -H "x-apideck-consumer-id: ${CONSUMER_ID}"
  -H "x-apideck-service-id: ${SERVICE_ID}"
)

# ---- Step 1: List drives and find the matching drive ID ----
echo "==> Listing drives..."
DRIVES_RESP=$(curl -s "${UNIFY_BASE}/file-storage/drives" \
  "${common_headers[@]}" \
  -H "Accept: application/json")

echo "Drives response: ${DRIVES_RESP}"

DRIVE_ID=$(echo "${DRIVES_RESP}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
drives = data.get('data', [])
drive_name = '${DRIVE_NAME}'
for d in drives:
    if d.get('name') == drive_name:
        print(d.get('id', ''))
        break
")

if [[ -z "${DRIVE_ID}" ]]; then
  echo "ERROR: Could not find drive with name '${DRIVE_NAME}'"
  echo "Full response: ${DRIVES_RESP}"
  exit 1
fi

echo "==> Found drive ID: ${DRIVE_ID}"

# ---- Step 2: Upload 4 files ----
upload_file() {
  local filename="$1"
  local content="$2"

  echo "==> Uploading ${filename}..."

  METADATA=$(python3 -c "
import json
m = {
  'name': '${filename}',
  'parent_folder_id': 'root',
  'drive_id': '${DRIVE_ID}'
}
print(json.dumps(m))
")

  UPLOAD_RESP=$(curl -s -X POST "${UPLOAD_BASE}/file-storage/files" \
    "${common_headers[@]}" \
    -H "Content-Type: text/plain" \
    -H "x-apideck-metadata: ${METADATA}" \
    --data-binary "${content}")

  echo "Upload response for ${filename}: ${UPLOAD_RESP}"
}

upload_file "KEEP-${RUN_ID}-1.txt" "keep file 1 run ${RUN_ID}"
upload_file "KEEP-${RUN_ID}-2.txt" "keep file 2 run ${RUN_ID}"
upload_file "SKIP-${RUN_ID}-1.txt" "skip file 1 run ${RUN_ID}"
upload_file "SKIP-${RUN_ID}-2.txt" "skip file 2 run ${RUN_ID}"

echo "==> All files uploaded."

# ---- Step 3: Search for KEEP files ----
echo "==> Searching for KEEP-${RUN_ID}..."

QUERY="KEEP-${RUN_ID}"
SEARCH_IDS=()

CURSOR=""
while true; do
  if [[ -z "${CURSOR}" ]]; then
    URL="${UNIFY_BASE}/file-storage/files/search"
  else
    URL="${UNIFY_BASE}/file-storage/files/search?cursor=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${CURSOR}', safe=''))")"
  fi

  SEARCH_RESP=$(curl -s -X POST "${URL}" \
    "${common_headers[@]}" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "{\"query\": \"${QUERY}\"}")

  echo "Search response: ${SEARCH_RESP}"

  # Extract IDs and next cursor
  READ_RESULT=$(echo "${SEARCH_RESP}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
files = data.get('data', [])
ids = [f.get('id','') for f in files]
print(json.dumps(ids))
cursor = ''
meta = data.get('meta', {})
cursors = meta.get('cursors', {})
if cursors.get('next'):
    cursor = cursors['next']
print(cursor)
")

  PAGE_IDS=$(echo "${READ_RESULT}" | head -1)
  NEXT_CURSOR=$(echo "${READ_RESULT}" | tail -1)

  # Append IDs from this page
  while IFS= read -r id; do
    if [[ -n "${id}" ]]; then
      SEARCH_IDS+=("${id}")
    fi
  done < <(echo "${PAGE_IDS}" | python3 -c "import sys, json; ids = json.load(sys.stdin); [print(i) for i in ids]")

  if [[ -z "${NEXT_CURSOR}" || "${NEXT_CURSOR}" == "None" || "${NEXT_CURSOR}" == "null" ]]; then
    break
  fi
  CURSOR="${NEXT_CURSOR}"
done

echo "==> Found IDs: ${SEARCH_IDS[*]}"

# ---- Step 4: Write output.log ----
python3 -c "
import json
ids = ${SEARCH_IDS[@]+"${SEARCH_IDS[@]}"}
" 2>/dev/null || true

# Build JSON array from collected IDs
python3 << PYEOF
import json

ids = []
raw = """$(for id in "${SEARCH_IDS[@]}"; do echo "${id}"; done)"""
for line in raw.strip().splitlines():
    line = line.strip()
    if line:
        ids.append(line)

result = {"search_result_ids": ids}
with open("${LOG_FILE}", "w") as f:
    f.write(json.dumps(result))
print("==> Written to ${LOG_FILE}:", json.dumps(result))
PYEOF
