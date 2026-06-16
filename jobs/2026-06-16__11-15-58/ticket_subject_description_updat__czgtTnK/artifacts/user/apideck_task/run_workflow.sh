#!/usr/bin/env bash
set -euo pipefail

# ── Credentials & config ────────────────────────────────────────────────────
API_KEY="${APIDECK_API_KEY}"
APP_ID="${APIDECK_APP_ID}"
CONSUMER_ID="${APIDECK_CONSUMER_ID}"
COLLECTION_ID="${APIDECK_ISSUE_TRACKING_COLLECTION_ID}"
RUN_ID="${ZEALT_RUN_ID}"

BASE_URL="https://unify.apideck.com"
LOG_FILE="$(dirname "$0")/output.log"

# Common headers helper
auth_headers() {
  echo -n \
    "-H 'Authorization: Bearer ${API_KEY}'" \
    "-H 'x-apideck-app-id: ${APP_ID}'" \
    "-H 'x-apideck-consumer-id: ${CONSUMER_ID}'" \
    "-H 'x-apideck-service-id: github'"
}

# ── Step 1: Create ticket with [UPDATE-V1] subject ──────────────────────────
echo "[INFO] Creating ticket with subject containing [UPDATE-V1] and run_id=${RUN_ID}..."

CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST "${BASE_URL}/issue-tracking/collections/${COLLECTION_ID}/tickets" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "x-apideck-app-id: ${APP_ID}" \
  -H "x-apideck-consumer-id: ${CONSUMER_ID}" \
  -H "x-apideck-service-id: github" \
  -H "Content-Type: application/json" \
  -d "{
    \"subject\": \"[UPDATE-V1] ${RUN_ID}\",
    \"description\": \"Initial draft v1\"
  }")

HTTP_STATUS=$(echo "${CREATE_RESPONSE}" | tail -n1)
CREATE_BODY=$(echo "${CREATE_RESPONSE}" | head -n -1)

echo "[INFO] Create response (HTTP ${HTTP_STATUS}): ${CREATE_BODY}"

if [[ "${HTTP_STATUS}" != "201" && "${HTTP_STATUS}" != "200" ]]; then
  echo "[ERROR] Failed to create ticket. HTTP status: ${HTTP_STATUS}"
  echo "[ERROR] Response: ${CREATE_BODY}"
  exit 1
fi

# Extract ticket ID from response
TICKET_ID=$(echo "${CREATE_BODY}" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['data']['id'])")

if [[ -z "${TICKET_ID}" ]]; then
  echo "[ERROR] Could not extract ticket ID from response: ${CREATE_BODY}"
  exit 1
fi

echo "[INFO] Ticket created with ID: ${TICKET_ID}"

# ── Step 2: Update ticket with [UPDATE-V2] subject and new description ───────
echo "[INFO] Updating ticket ${TICKET_ID} with [UPDATE-V2] subject and 'Revised draft v2' description..."

UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X PATCH "${BASE_URL}/issue-tracking/collections/${COLLECTION_ID}/tickets/${TICKET_ID}" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "x-apideck-app-id: ${APP_ID}" \
  -H "x-apideck-consumer-id: ${CONSUMER_ID}" \
  -H "x-apideck-service-id: github" \
  -H "Content-Type: application/json" \
  -d "{
    \"subject\": \"[UPDATE-V2] ${RUN_ID}\",
    \"description\": \"Revised draft v2\"
  }")

HTTP_STATUS_UPDATE=$(echo "${UPDATE_RESPONSE}" | tail -n1)
UPDATE_BODY=$(echo "${UPDATE_RESPONSE}" | head -n -1)

echo "[INFO] Update response (HTTP ${HTTP_STATUS_UPDATE}): ${UPDATE_BODY}"

if [[ "${HTTP_STATUS_UPDATE}" != "200" ]]; then
  echo "[ERROR] Failed to update ticket. HTTP status: ${HTTP_STATUS_UPDATE}"
  echo "[ERROR] Response: ${UPDATE_BODY}"
  exit 1
fi

# ── Step 3: Verify updated state ─────────────────────────────────────────────
echo "[INFO] Verifying ticket ${TICKET_ID} final state..."

GET_RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X GET "${BASE_URL}/issue-tracking/collections/${COLLECTION_ID}/tickets/${TICKET_ID}" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "x-apideck-app-id: ${APP_ID}" \
  -H "x-apideck-consumer-id: ${CONSUMER_ID}" \
  -H "x-apideck-service-id: github")

HTTP_STATUS_GET=$(echo "${GET_RESPONSE}" | tail -n1)
GET_BODY=$(echo "${GET_RESPONSE}" | head -n -1)

echo "[INFO] Get response (HTTP ${HTTP_STATUS_GET}): ${GET_BODY}"

FINAL_SUBJECT=$(echo "${GET_BODY}" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['data'].get('subject',''))" 2>/dev/null || echo "")
FINAL_DESC=$(echo "${GET_BODY}" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['data'].get('description',''))" 2>/dev/null || echo "")

echo "[INFO] Final subject  : ${FINAL_SUBJECT}"
echo "[INFO] Final description: ${FINAL_DESC}"

# ── Step 4: Write audit log ──────────────────────────────────────────────────
{
  echo "Run ID   : ${RUN_ID}"
  echo "Ticket ID: ${TICKET_ID}"
  echo "Subject  : ${FINAL_SUBJECT}"
  echo "Description: ${FINAL_DESC}"
  echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
} > "${LOG_FILE}"

echo "[INFO] Log written to ${LOG_FILE}"
echo "[SUCCESS] Workflow complete. Ticket ID: ${TICKET_ID}"
