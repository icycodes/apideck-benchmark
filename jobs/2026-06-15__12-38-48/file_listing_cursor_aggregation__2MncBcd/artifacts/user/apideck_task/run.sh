#!/usr/bin/env bash
set -euo pipefail

# ── Configuration from environment ──────────────────────────────────────────
APP_ID="${APIDECK_APP_ID:?}"
API_KEY="${APIDECK_API_KEY:?}"
CONSUMER_ID="${APIDECK_CONSUMER_ID:?}"
DRIVE_NAME="${APIDECK_FILE_STORAGE_DRIVE_NAME:?}"
RUN_ID="${ZEALT_RUN_ID:?}"

SERVICE_ID="onedrive"
PREFIX="AGG-${RUN_ID}-"
UPLOAD_HOST="https://upload.apideck.com"
UNIFY_HOST="https://unify.apideck.com"
LOG_FILE="/home/user/apideck_task/output.log"

# ── Upload 7 text files ─────────────────────────────────────────────────────
echo "=== Uploading 7 files ==="
declare -a FILE_IDS=()

for i in $(seq 1 7); do
    FILENAME="${PREFIX}${i}.txt"
    CONTENT="File number ${i} for run ${RUN_ID}"

    echo "Uploading ${FILENAME} ..."

    response=$(echo -n "$CONTENT" | curl -sS --connect-timeout 15 -X POST "${UPLOAD_HOST}/file-storage/files" \
        -H "Authorization: Bearer ${API_KEY}" \
        -H "Content-Type: text/plain" \
        -H "x-apideck-app-id: ${APP_ID}" \
        -H "x-apideck-consumer-id: ${CONSUMER_ID}" \
        -H "x-apideck-metadata: {\"name\": \"${FILENAME}\", \"parent_folder_id\": \"root\"}" \
        -H "x-apideck-service-id: ${SERVICE_ID}" \
        --data-binary @- \
        -w '\n%{http_code}' 2>&1)

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [[ "$http_code" -eq 201 ]]; then
        file_id=$(echo "$body" | jq -r '.data.id // empty')
        if [[ -n "$file_id" ]]; then
            echo "  -> Uploaded: ${file_id}"
            FILE_IDS+=("$file_id")
        else
            echo "  -> Upload OK but no id in response. Body: $body"
        fi
    else
        echo "  -> Upload FAILED (HTTP ${http_code}): $body"
        exit 1
    fi
done

echo "Uploaded ${#FILE_IDS[@]} files."
echo ""

# ── Walk file listing with cursor pagination (limit=3) ─────────────────────
echo "=== Walking file listing with cursor pagination (limit=3) ==="
ids_array_json="[]"
cursor=""
page=0

while true; do
    page=$((page + 1))
    echo "--- Page ${page} ---"

    if [[ -z "$cursor" ]]; then
        url="${UNIFY_HOST}/file-storage/files?limit=3&drive_id=${DRIVE_NAME}"
    else
        url="${UNIFY_HOST}/file-storage/files?limit=3&drive_id=${DRIVE_NAME}&cursor=${cursor}"
    fi

    response=$(curl -sS --connect-timeout 15 -X GET "$url" \
        -H "Authorization: Bearer ${API_KEY}" \
        -H "x-apideck-app-id: ${APP_ID}" \
        -H "x-apideck-consumer-id: ${CONSUMER_ID}" \
        -w '\n%{http_code}' 2>&1)

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [[ "$http_code" -ge 200 && "$http_code" -lt 300 ]]; then
        # Extract file ids whose names start with PREFIX
        matching=$(echo "$body" | jq --arg prefix "$PREFIX" '
            [.data[] | select(.name | startswith($prefix)) | .id]
        ')

        # Merge into the aggregate
        ids_array_json=$(echo "$ids_array_json" "$matching" | jq -s '.[0] + .[1]')

        echo "  Matching on this page: $(echo "$matching" | jq 'length')"

        # Check cursor for next page
        next_cursor=$(echo "$body" | jq -r '.meta.cursors.next // empty')
        echo "  Next cursor: ${next_cursor:-"(empty - done)"}"

        if [[ -z "$next_cursor" ]]; then
            echo "  No next cursor. Pagination complete."
            break
        fi
        cursor="$next_cursor"
    else
        echo "  -> List FAILED (HTTP ${http_code}): $body"
        exit 1
    fi
done

# ── Write JSON summary to log file ─────────────────────────────────────────
count=$(echo "$ids_array_json" | jq 'length')
result=$(jq -n --argjson count "$count" --argjson ids "$ids_array_json" \
    '{count: $count, ids: $ids}')

echo "$result" | jq '.' > "$LOG_FILE"
echo ""
echo "=== Result written to ${LOG_FILE} ==="
jq '.' "$LOG_FILE"
