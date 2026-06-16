#!/usr/bin/env bash
set -euo pipefail

# Read environment variables
API_KEY="${APIDECK_API_KEY}"
APP_ID="${APIDECK_APP_ID}"
CONSUMER_ID="${APIDECK_CONSUMER_ID}"
COLLECTION_ID="${APIDECK_ISSUE_TRACKING_COLLECTION_ID}"
RUN_ID="${ZEALT_RUN_ID}"

BASE_URL="https://unify.apideck.com"

# Common headers
HEADERS=(
  -H "Authorization: Bearer ${API_KEY}"
  -H "x-apideck-app-id: ${APP_ID}"
  -H "x-apideck-consumer-id: ${CONSUMER_ID}"
  -H "x-apideck-service-id: github"
  -H "Content-Type: application/json"
  -H "Accept: application/json"
)

LOG_FILE="/home/user/apideck_task/output.log"
> "${LOG_FILE}"

echo "=== Apideck Issue Tracking Comment Edit & Delete Workflow ===" | tee -a "${LOG_FILE}"
echo "Run ID: ${RUN_ID}" | tee -a "${LOG_FILE}"
echo "Collection ID: ${COLLECTION_ID}" | tee -a "${LOG_FILE}"
echo "" | tee -a "${LOG_FILE}"

# Step 1: Create a ticket
echo "--- Step 1: Creating ticket ---" | tee -a "${LOG_FILE}"
TICKET_SUBJECT="[COMMENT-EDIT-DELETE] ${RUN_ID}"
CREATE_TICKET_PAYLOAD=$(cat <<EOF
{
  "subject": "${TICKET_SUBJECT}",
  "description": "Ticket for comment edit/delete workflow - ${RUN_ID}",
  "status": "open"
}
EOF
)

RESPONSE=$(curl -s -X POST "${BASE_URL}/issue-tracking/collections/${COLLECTION_ID}/tickets" \
  "${HEADERS[@]}" \
  -d "${CREATE_TICKET_PAYLOAD}")

echo "Create ticket response: ${RESPONSE}" | tee -a "${LOG_FILE}"

# Extract ticket ID from response
TICKET_ID=$(echo "${RESPONSE}" | python3 -c "import sys,json; data=json.load(sys.stdin); print(data['data']['id'])")
echo "Ticket ID: ${TICKET_ID}" | tee -a "${LOG_FILE}"

# Step 2: Add 4 comments
echo "" | tee -a "${LOG_FILE}"
echo "--- Step 2: Adding 4 comments ---" | tee -a "${LOG_FILE}"

COMMENT_IDS=()

for LABEL in A B C D; do
  BODY="${LABEL}-${RUN_ID}"
  echo "Creating comment with body: ${BODY}" | tee -a "${LOG_FILE}"
  CREATE_COMMENT_PAYLOAD=$(cat <<EOF
{
  "body": "${BODY}"
}
EOF
)
  RESP=$(curl -s -X POST "${BASE_URL}/issue-tracking/collections/${COLLECTION_ID}/tickets/${TICKET_ID}/comments" \
    "${HEADERS[@]}" \
    -d "${CREATE_COMMENT_PAYLOAD}")
  echo "Response: ${RESP}" | tee -a "${LOG_FILE}"
  
  COMMENT_ID=$(echo "${RESP}" | python3 -c "import sys,json; data=json.load(sys.stdin); print(data['data']['id'])")
  COMMENT_IDS+=("${COMMENT_ID}")
  echo "Comment ${LABEL} ID: ${COMMENT_ID}" | tee -a "${LOG_FILE}"
done

# COMMENT_IDS array: index 0=A, 1=B, 2=C, 3=D
COMMENT_A_ID="${COMMENT_IDS[0]}"
COMMENT_B_ID="${COMMENT_IDS[1]}"
COMMENT_C_ID="${COMMENT_IDS[2]}"
COMMENT_D_ID="${COMMENT_IDS[3]}"

# Step 3: Edit comment B -> B-EDITED-{RUN_ID}
echo "" | tee -a "${LOG_FILE}"
echo "--- Step 3: Editing comment B to B-EDITED ---" | tee -a "${LOG_FILE}"
EDITED_BODY="B-EDITED-${RUN_ID}"
EDIT_PAYLOAD=$(cat <<EOF
{
  "body": "${EDITED_BODY}"
}
EOF
)
RESP=$(curl -s -X PATCH "${BASE_URL}/issue-tracking/collections/${COLLECTION_ID}/tickets/${TICKET_ID}/comments/${COMMENT_B_ID}" \
  "${HEADERS[@]}" \
  -d "${EDIT_PAYLOAD}")
echo "Edit response: ${RESP}" | tee -a "${LOG_FILE}"

# Step 4: Delete comment C
echo "" | tee -a "${LOG_FILE}"
echo "--- Step 4: Deleting comment C ---" | tee -a "${LOG_FILE}"
RESP=$(curl -s -X DELETE "${BASE_URL}/issue-tracking/collections/${COLLECTION_ID}/tickets/${TICKET_ID}/comments/${COMMENT_C_ID}" \
  "${HEADERS[@]}")
echo "Delete response: ${RESP}" | tee -a "${LOG_FILE}"

# Step 5: Verify final state - list all comments
echo "" | tee -a "${LOG_FILE}"
echo "--- Step 5: Verifying final state ---" | tee -a "${LOG_FILE}"

ALL_COMMENTS=""
CURSOR=""
while true; do
  if [ -z "${CURSOR}" ]; then
    RESP=$(curl -s -X GET "${BASE_URL}/issue-tracking/collections/${COLLECTION_ID}/tickets/${TICKET_ID}/comments" \
      "${HEADERS[@]}")
  else
    RESP=$(curl -s -X GET "${BASE_URL}/issue-tracking/collections/${COLLECTION_ID}/tickets/${TICKET_ID}/comments?cursor=${CURSOR}" \
      "${HEADERS[@]}")
  fi
  
  PAGE_COMMENTS=$(echo "${RESP}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
comments = data.get('data', [])
for c in comments:
    print(c.get('id', 'N/A') + ' | ' + c.get('body', 'N/A'))
" 2>/dev/null || echo "Error parsing comments")
  
  ALL_COMMENTS="${ALL_COMMENTS}${PAGE_COMMENTS}"$'\n'
  
  # Check for next cursor
  NEXT_CURSOR=$(echo "${RESP}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
meta = data.get('meta', {})
cursors = meta.get('cursors', {})
next_c = cursors.get('next', '')
print(next_c)
" 2>/dev/null || echo "")
  
  if [ -z "${NEXT_CURSOR}" ]; then
    break
  fi
  CURSOR="${NEXT_CURSOR}"
done

echo "Final comments on ticket:" | tee -a "${LOG_FILE}"
echo "${ALL_COMMENTS}" | tee -a "${LOG_FILE}"

echo "" | tee -a "${LOG_FILE}"
echo "=== Workflow Complete ===" | tee -a "${LOG_FILE}"