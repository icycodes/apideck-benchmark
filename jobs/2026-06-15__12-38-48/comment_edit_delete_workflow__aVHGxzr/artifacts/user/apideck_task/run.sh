#!/usr/bin/env bash
set -euo pipefail

# ── Environment ──────────────────────────────────────────────────────
APP_ID="${APIDECK_APP_ID:?}"
API_KEY="${APIDECK_API_KEY:?}"
CONSUMER_ID="${APIDECK_CONSUMER_ID:?}"
COLLECTION_ID="${APIDECK_ISSUE_TRACKING_COLLECTION_ID:?}"
RUN_ID="${ZEALT_RUN_ID:?}"

BASE_URL="https://unify.apideck.com/issue-tracking/collections/${COLLECTION_ID}"

AUTH_HEADERS=(
  -H "Authorization: Bearer ${API_KEY}"
  -H "x-apideck-app-id: ${APP_ID}"
  -H "x-apideck-consumer-id: ${CONSUMER_ID}"
  -H "x-apideck-service-id: github"
  -H "Content-Type: application/json"
)

LOG_FILE="/home/user/apideck_task/output.log"
: > "$LOG_FILE"   # truncate

log() { echo "$@" | tee -a "$LOG_FILE"; }

# ── 1. Create ticket ─────────────────────────────────────────────────
log "=== Creating ticket ==="

TICKET_SUBJECT="[COMMENT-EDIT-DELETE] ${RUN_ID}"

CREATE_RESP=$(curl -sS -w '\n%{http_code}' "${AUTH_HEADERS[@]}" \
  -d "{\"subject\":\"${TICKET_SUBJECT}\",\"description\":\"Integration test for comment edit & delete workflow.\"}" \
  "${BASE_URL}/tickets")

HTTP_CODE=$(echo "$CREATE_RESP" | tail -1)
BODY=$(echo "$CREATE_RESP" | sed '$d')

if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "201" ]; then
  log "ERROR: Create ticket failed with HTTP $HTTP_CODE"
  log "$BODY"
  exit 1
fi

TICKET_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")
log "Ticket ID: ${TICKET_ID}"

# ── 2. Add four comments ─────────────────────────────────────────────
log "=== Adding comments ==="

COMMENT_A="A-${RUN_ID}"
COMMENT_B="B-${RUN_ID}"
COMMENT_C="C-${RUN_ID}"
COMMENT_D="D-${RUN_ID}"

add_comment() {
  local body_text="$1"
  local label="$2"
  local resp
  resp=$(curl -sS -w '\n%{http_code}' "${AUTH_HEADERS[@]}" \
    -d "{\"body\":\"${body_text}\"}" \
    "${BASE_URL}/tickets/${TICKET_ID}/comments")
  local code=$(echo "$resp" | tail -1)
  local b=$(echo "$resp" | sed '$d')
  if [ "$code" != "200" ] && [ "$code" != "201" ]; then
    log "ERROR: Add comment ${label} failed with HTTP $code"
    log "$b"
    exit 1
  fi
  local cid=$(echo "$b" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")
  log "  Added comment ${label}: id=${cid}" >&2
  echo "$cid"
}

CID_A=$(add_comment "$COMMENT_A" "A")
CID_B=$(add_comment "$COMMENT_B" "B")
CID_C=$(add_comment "$COMMENT_C" "C")
CID_D=$(add_comment "$COMMENT_D" "D")

# ── 3. Edit comment B → B-EDITED-<RUN_ID> ────────────────────────────
log "=== Editing comment B ==="

EDIT_BODY="B-EDITED-${RUN_ID}"
EDIT_RESP=$(curl -sS -w '\n%{http_code}' "${AUTH_HEADERS[@]}" \
  -X PATCH \
  -d "{\"body\":\"${EDIT_BODY}\"}" \
  "${BASE_URL}/tickets/${TICKET_ID}/comments/${CID_B}")

EDIT_CODE=$(echo "$EDIT_RESP" | tail -1)
EDIT_B=$(echo "$EDIT_RESP" | sed '$d')
if [ "$EDIT_CODE" != "200" ] && [ "$EDIT_CODE" != "201" ]; then
  log "ERROR: Edit comment B failed with HTTP $EDIT_CODE"
  log "$EDIT_B"
  exit 1
fi
log "  Edited comment B to: ${EDIT_BODY}"

# ── 4. Delete comment C ──────────────────────────────────────────────
log "=== Deleting comment C ==="

DEL_RESP=$(curl -sS -w '\n%{http_code}' "${AUTH_HEADERS[@]}" \
  -X DELETE \
  "${BASE_URL}/tickets/${TICKET_ID}/comments/${CID_C}")

DEL_CODE=$(echo "$DEL_RESP" | tail -1)
DEL_B=$(echo "$DEL_RESP" | sed '$d')
if [ "$DEL_CODE" != "200" ] && [ "$DEL_CODE" != "201" ] && [ "$DEL_CODE" != "204" ]; then
  log "ERROR: Delete comment C failed with HTTP $DEL_CODE"
  log "$DEL_B"
  exit 1
fi
log "  Deleted comment C (id=${CID_C})"

# ── 5. Verify final state ────────────────────────────────────────────
log "=== Verifying final state ==="

# Paginate through all comments
NEXT_CURSOR=""
ALL_BODIES=""
PAGE=0

while true; do
  PAGE=$((PAGE + 1))
  URL="${BASE_URL}/tickets/${TICKET_ID}/comments?limit=100"
  if [ -n "$NEXT_CURSOR" ]; then
    URL="${URL}&cursor=${NEXT_CURSOR}"
  fi

  LIST_RESP=$(curl -sS -w '\n%{http_code}' "${AUTH_HEADERS[@]}" -X GET "$URL")
  LIST_CODE=$(echo "$LIST_RESP" | tail -1)
  LIST_B=$(echo "$LIST_RESP" | sed '$d')

  if [ "$LIST_CODE" != "200" ]; then
    log "ERROR: List comments failed with HTTP $LIST_CODE"
    log "$LIST_B"
    exit 1
  fi

  # Extract bodies from this page
  PAGE_BODIES=$(echo "$LIST_B" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data.get('data', []):
    print(c.get('body', ''))
")
  ALL_BODIES="${ALL_BODIES}${PAGE_BODIES}"$'\n'

  # Check for next cursor
  NEXT_CURSOR=$(echo "$LIST_B" | python3 -c "
import sys, json
data = json.load(sys.stdin)
meta = data.get('meta', {})
cursors = meta.get('cursors', {})
nxt = cursors.get('next')
if nxt is None:
    print('')
else:
    print(nxt)
")

  if [ -z "$NEXT_CURSOR" ]; then
    break
  fi
  log "  Fetched page ${PAGE}, following cursor..."
done

log "  Total pages fetched: ${PAGE}"

# Normalize: sort and deduplicate
SORTED_BODIES=$(echo "$ALL_BODIES" | grep -v '^$' | sort | tr '\n' ',' | sed 's/,$//')
EXPECTED="A-${RUN_ID},B-EDITED-${RUN_ID},D-${RUN_ID}"

log "  Found bodies:    ${SORTED_BODIES}"
log "  Expected bodies: ${EXPECTED}"

if [ "$SORTED_BODIES" = "$EXPECTED" ]; then
  log "=== VERIFICATION PASSED ==="
else
  log "=== VERIFICATION FAILED ==="
  log "ALL_BODIES raw:"
  echo "$ALL_BODIES"
  exit 1
fi

log "=== Workflow complete ==="
