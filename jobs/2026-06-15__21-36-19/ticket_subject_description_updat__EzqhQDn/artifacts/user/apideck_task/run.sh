#!/usr/bin/env bash
set -euo pipefail

# ── Environment ──────────────────────────────────────────────────────────────
API_KEY="${APIDECK_API_KEY:?}"
APP_ID="${APIDECK_APP_ID:?}"
CONSUMER_ID="${APIDECK_CONSUMER_ID:?}"
SERVICE_ID="github"
COLLECTION_ID="${APIDECK_ISSUE_TRACKING_COLLECTION_ID:?}"
RUN_ID="${ZEALT_RUN_ID:?}"

BASE_URL="https://unify.apideck.com/issue-tracking/collections/${COLLECTION_ID}/tickets"
LOG_FILE="/home/user/apideck_task/output.log"

# Clear previous log
> "$LOG_FILE"

# ── Helpers ──────────────────────────────────────────────────────────────────
log() {
  echo "$@" | tee -a "$LOG_FILE"
}

api_call() {
  local method="$1"
  local url="$2"
  local data="$3"
  local tmpfile
  tmpfile=$(mktemp)

  local http_code
  http_code=$(curl -s -o "$tmpfile" -w "%{http_code}" \
    -X "$method" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "x-apideck-app-id: ${APP_ID}" \
    -H "x-apideck-consumer-id: ${CONSUMER_ID}" \
    -H "x-apideck-service-id: ${SERVICE_ID}" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "$data" \
    "$url")

  local body
  body=$(cat "$tmpfile")
  rm -f "$tmpfile"

  echo "${http_code}"
  echo "${body}"
}

# ── Step 1: Create ticket ────────────────────────────────────────────────────
log "=== Creating ticket with subject [UPDATE-V1] ${RUN_ID} ==="

CREATE_PAYLOAD=$(cat <<EOF
{
  "subject": "[UPDATE-V1] ${RUN_ID}",
  "description": "Initial draft v1"
}
EOF
)

CREATE_OUT=$(api_call "POST" "${BASE_URL}" "$CREATE_PAYLOAD")
CREATE_HTTP=$(echo "$CREATE_OUT" | head -1)
CREATE_BODY=$(echo "$CREATE_OUT" | tail -n +2)

log "Create HTTP status: ${CREATE_HTTP}"
log "Create response: ${CREATE_BODY}"

if [[ "$CREATE_HTTP" != "201" ]]; then
  log "ERROR: Create failed with status ${CREATE_HTTP}"
  exit 1
fi

TICKET_ID=$(echo "$CREATE_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")
log "Ticket ID: ${TICKET_ID}"

# ── Step 2: Update ticket ────────────────────────────────────────────────────
log ""
log "=== Updating ticket ${TICKET_ID} with subject [UPDATE-V2] ${RUN_ID} ==="

UPDATE_PAYLOAD=$(cat <<EOF
{
  "subject": "[UPDATE-V2] ${RUN_ID}",
  "description": "Revised draft v2"
}
EOF
)

UPDATE_OUT=$(api_call "PATCH" "${BASE_URL}/${TICKET_ID}" "$UPDATE_PAYLOAD")
UPDATE_HTTP=$(echo "$UPDATE_OUT" | head -1)
UPDATE_BODY=$(echo "$UPDATE_OUT" | tail -n +2)

log "Update HTTP status: ${UPDATE_HTTP}"
log "Update response: ${UPDATE_BODY}"

if [[ "$UPDATE_HTTP" != "200" ]]; then
  log "ERROR: Update failed with status ${UPDATE_HTTP}"
  exit 1
fi

# ── Step 3: Verify final state via List Tickets ──────────────────────────────
log ""
log "=== Verifying final state ==="

LIST_OUT=$(api_call "GET" "${BASE_URL}?limit=200" "")
LIST_HTTP=$(echo "$LIST_OUT" | head -1)
LIST_BODY=$(echo "$LIST_OUT" | tail -n +2)

log "List HTTP status: ${LIST_HTTP}"

# Check for [UPDATE-V1] tickets with this run ID
V1_COUNT=$(echo "$LIST_BODY" | python3 -c "
import sys, json
data = json.load(sys.stdin)
tickets = data.get('data', [])
count = sum(1 for t in tickets if '[UPDATE-V1]' in t.get('subject','') and '${RUN_ID}' in t.get('subject',''))
print(count)
")

# Check for [UPDATE-V2] tickets with this run ID
V2_COUNT=$(echo "$LIST_BODY" | python3 -c "
import sys, json
data = json.load(sys.stdin)
tickets = data.get('data', [])
count = sum(1 for t in tickets if '[UPDATE-V2]' in t.get('subject','') and '${RUN_ID}' in t.get('subject',''))
print(count)
")

# Verify the created ticket has the correct description
TICKET_DESC=$(echo "$LIST_BODY" | python3 -c "
import sys, json
data = json.load(sys.stdin)
tickets = data.get('data', [])
for t in tickets:
    if t.get('id') == '${TICKET_ID}':
        print(t.get('description',''))
        break
")

log ""
log "V1 tickets remaining: ${V1_COUNT}"
log "V2 tickets found: ${V2_COUNT}"
log "Ticket ${TICKET_ID} description matches: $(echo "$TICKET_DESC" | grep -c 'Revised draft v2')"

if [[ "$V1_COUNT" -eq 0 && "$V2_COUNT" -eq 1 && "$TICKET_DESC" == *"Revised draft v2"* ]]; then
  log "SUCCESS: All acceptance criteria met."
else
  log "WARNING: Acceptance criteria not fully satisfied."
  log "  V1 count (should be 0): ${V1_COUNT}"
  log "  V2 count (should be 1): ${V2_COUNT}"
  log "  Description check: ${TICKET_DESC}"
fi
