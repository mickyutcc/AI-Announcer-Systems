#!/usr/bin/env bash
set -euo pipefail

# Default to localhost:7860, but allow override
BASE="${1:-http://localhost:7860}"
ADMIN_API_BASE="$BASE"

echo "Running smoke tests against: $BASE"

# Check dependencies
if ! command -v jq &> /dev/null; then
    echo "❌ Error: jq is not installed. Please install jq first."
    exit 1
fi

# 1) Health
echo "== Checking /healthz =="
if curl -fsS "$BASE/healthz" > /dev/null; then
    echo "✅ /healthz OK"
else
    echo "❌ /healthz failed"
    exit 1
fi

# 2) Create subscription (simulate file upload via multipart)
echo "== Create subscription =="
# Create a dummy image file
echo "fake image content" > /tmp/smoke.png

curl -sS -X POST "$BASE/api/subscriptions" \
  -F "user_id=99999" \
  -F "plan=standard" \
  -F "payment_ref=SMOKETEST" \
  -F "file=@/tmp/smoke.png;filename=smoke.png;type=image/png" \
  -o /tmp/smoke_create.json

echo "Response:"
jq . /tmp/smoke_create.json || cat /tmp/smoke_create.json

SID=$(jq -r '.subscription_id // empty' /tmp/smoke_create.json)
if [ -z "$SID" ] || [ "$SID" = "null" ]; then
  echo "❌ Create subscription failed"
  # Don't exit yet, check output
  exit 1
fi
echo "✅ Created subscription id=$SID"

# 3) Admin approve (simulate admin call)
echo "== Admin approve =="
curl -sS -X POST "$ADMIN_API_BASE/api/admin/subscriptions/$SID/approve" \
  -H "Content-Type: application/json" \
  -d '{"admin_id":999,"period_days":30}' -o /tmp/smoke_approve.json

echo "Response:"
jq . /tmp/smoke_approve.json || cat /tmp/smoke_approve.json

STATUS=$(jq -r '.ok // empty' /tmp/smoke_approve.json)
if [ "$STATUS" = "true" ]; then
    echo "✅ Subscription approved successfully"
else
    echo "❌ Approval failed"
    exit 1
fi

# Cleanup
rm /tmp/smoke.png /tmp/smoke_create.json /tmp/smoke_approve.json
echo "🎉 Smoke test passed!"
