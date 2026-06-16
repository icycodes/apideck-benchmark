#!/usr/bin/env bash
set -euo pipefail

# ── Credentials & IDs from environment ──────────────────────────────────────
API_KEY="${APIDECK_API_KEY}"
APP_ID="${APIDECK_APP_ID}"
CONSUMER_ID="${APIDECK_CONSUMER_ID}"
COLLECTION_ID="${APIDECK_ISSUE_TRACKING_COLLECTION_ID}"
RUN_ID="${ZEALT_RUN_ID}"

BASE_URL="https://unify.apideck.com"
SERVICE_ID="github"
LOG_FILE="/home/user/apideck_task/output.log"

# ── Helper: common curl headers ───────────────────────────────────────────────
apideck_curl() {
  local method="$1"; shift
  local path="$1";   shift
  curl -s -X "$method" \
    "${BASE_URL}${path}" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "x-apideck-app-id: ${APP_ID}" \
    -H "x-apideck-consumer-id: ${CONSUMER_ID}" \
    -H "x-apideck-service-id: ${SERVICE_ID}" \
    -H "Content-Type: application/json" \
    "$@"
}

echo "=== Apideck Comment Edit & Delete Workflow ===" | tee "$LOG_FILE"
echo "Run ID: ${RUN_ID}" | tee -a "$LOG_FILE"
echo "Collection ID: ${COLLECTION_ID}" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# ── Step 1: Create ticket ─────────────────────────────────────────────────────
echo "[1] Creating ticket..." | tee -a "$LOG_FILE"

TICKET_RESP=$(apideck_curl POST "/issue-tracking/collections/${COLLECTION_ID}/tickets" \
  -d "{\"subject\": \"[COMMENT-EDIT-DELETE] ${RUN_ID}\"}")

echo "Ticket response: ${TICKET_RESP}" | tee -a "$LOG_FILE"

TICKET_ID=$(echo "$TICKET_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['id'])")
echo "Ticket ID: ${TICKET_ID}" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# ── Step 2: Add four comments ─────────────────────────────────────────────────
echo "[2] Adding four comments..." | tee -a "$LOG_FILE"

COMMENT_PATH="/issue-tracking/collections/${COLLECTION_ID}/tickets/${TICKET_ID}/comments"

add_comment() {
  local body="$1"
  local resp
  resp=$(apideck_curl POST "$COMMENT_PATH" -d "{\"body\": \"${body}\"}")
  echo "$resp"
}

# Comment A
RESP_A=$(add_comment "A-${RUN_ID}")
echo "Comment A response: ${RESP_A}" | tee -a "$LOG_FILE"
COMMENT_A_ID=$(echo "$RESP_A" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['id'])")
echo "Comment A ID: ${COMMENT_A_ID}" | tee -a "$LOG_FILE"

# Comment B (will be edited)
RESP_B=$(add_comment "B-${RUN_ID}")
echo "Comment B response: ${RESP_B}" | tee -a "$LOG_FILE"
COMMENT_B_ID=$(echo "$RESP_B" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['id'])")
echo "Comment B ID: ${COMMENT_B_ID}" | tee -a "$LOG_FILE"

# Comment C (will be deleted)
RESP_C=$(add_comment "C-${RUN_ID}")
echo "Comment C response: ${RESP_C}" | tee -a "$LOG_FILE"
COMMENT_C_ID=$(echo "$RESP_C" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['id'])")
echo "Comment C ID: ${COMMENT_C_ID}" | tee -a "$LOG_FILE"

# Comment D
RESP_D=$(add_comment "D-${RUN_ID}")
echo "Comment D response: ${RESP_D}" | tee -a "$LOG_FILE"
COMMENT_D_ID=$(echo "$RESP_D" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['id'])")
echo "Comment D ID: ${COMMENT_D_ID}" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# ── Step 3: Edit comment B → "B-EDITED-<RUN_ID>" ─────────────────────────────
echo "[3] Editing comment B (ID: ${COMMENT_B_ID})..." | tee -a "$LOG_FILE"
EDIT_RESP=$(apideck_curl PATCH "${COMMENT_PATH}/${COMMENT_B_ID}" \
  -d "{\"body\": \"B-EDITED-${RUN_ID}\"}")
echo "Edit response: ${EDIT_RESP}" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# ── Step 4: Delete comment C ──────────────────────────────────────────────────
echo "[4] Deleting comment C (ID: ${COMMENT_C_ID})..." | tee -a "$LOG_FILE"
DEL_RESP=$(apideck_curl DELETE "${COMMENT_PATH}/${COMMENT_C_ID}")
echo "Delete response: ${DEL_RESP}" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# ── Step 5: List & verify final comments ─────────────────────────────────────
echo "[5] Verifying final state..." | tee -a "$LOG_FILE"

list_all_comments() {
  local cursor=""
  local all_bodies=""
  local total=0
  while true; do
    local url="${COMMENT_PATH}?limit=100"
    if [ -n "$cursor" ]; then
      url="${url}&cursor=${cursor}"
    fi
    local resp
    resp=$(apideck_curl GET "$url")
    local page_info
    page_info=$(echo "$resp" | python3 -c "
import sys, json
d = json.load(sys.stdin)
items = d.get('data', [])
for c in items:
    print(c['id'] + '|' + c.get('body',''))
print('__NEXT__:' + (d.get('meta',{}).get('cursors',{}).get('next','') or ''))
")
    while IFS= read -r line; do
      if [[ "$line" == __NEXT__:* ]]; then
        cursor="${line#__NEXT__:}"
      else
        total=$((total + 1))
        all_bodies="${all_bodies}  - ID: ${line%%|*} | Body: ${line#*|}\n"
      fi
    done <<< "$page_info"
    if [ -z "$cursor" ]; then
      break
    fi
  done
  echo "Total comments: ${total}"
  printf "%b" "$all_bodies"
}

list_all_comments | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "=== Workflow complete ===" | tee -a "$LOG_FILE"
