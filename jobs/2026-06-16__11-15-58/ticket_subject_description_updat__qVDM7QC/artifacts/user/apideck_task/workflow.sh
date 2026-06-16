#!/usr/bin/env bash
set -euo pipefail

API_KEY="${APIDECK_API_KEY}"
APP_ID="${APIDECK_APP_ID}"
CONSUMER_ID="${APIDECK_CONSUMER_ID}"
COLLECTION_ID="${APIDECK_ISSUE_TRACKING_COLLECTION_ID}"
RUN_ID="${ZEALT_RUN_ID}"
BASE_URL="https://unify.apideck.com"

COMMON_HEADERS=(
  -H "Authorization: Bearer ${API_KEY}"
  -H "x-apideck-app-id: ${APP_ID}"
  -H "x-apideck-consumer-id: ${CONSUMER_ID}"
  -H "x-apideck-service-id: github"
  -H "Content-Type: application/json"
)

SUBJECT_V1="[UPDATE-V1] ${RUN_ID}"
SUBJECT_V2="[UPDATE-V2] ${RUN_ID}"
DESCRIPTION_V2="Revised draft v2"

echo "=== Step 1: Create ticket with subject containing [UPDATE-V1] ==="
CREATE_RESPONSE=$(curl -s -X POST \
  "${BASE_URL}/issue-tracking/collections/${COLLECTION_ID}/tickets" \
  "${COMMON_HEADERS[@]}" \
  -d "{\"subject\": \"${SUBJECT_V1}\", \"description\": \"Initial draft\"}")

echo "Create response: ${CREATE_RESPONSE}"

TICKET_ID=$(echo "${CREATE_RESPONSE}" | python3 -c "import sys,json; data=json.load(sys.stdin); print(data['data']['id'])")

echo "Extracted Ticket ID: ${TICKET_ID}"

echo "=== Step 2: Update ticket with [UPDATE-V2] subject and revised description ==="
UPDATE_RESPONSE=$(curl -s -X PATCH \
  "${BASE_URL}/issue-tracking/collections/${COLLECTION_ID}/tickets/${TICKET_ID}" \
  "${COMMON_HEADERS[@]}" \
  -d "{\"id\": \"${TICKET_ID}\", \"subject\": \"${SUBJECT_V2}\", \"description\": \"${DESCRIPTION_V2}\"}")

echo "Update response: ${UPDATE_RESPONSE}"

echo "=== Step 3: Log ticket ID ==="
echo "Ticket ID: ${TICKET_ID}" > /home/user/apideck_task/output.log

echo "=== Workflow complete. Ticket ID logged. ==="
cat /home/user/apideck_task/output.log