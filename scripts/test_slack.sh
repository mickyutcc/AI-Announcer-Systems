#!/bin/bash
set -e

# Load .env.production
if [ -f .env.production ]; then
    export $(grep -v '^#' .env.production | xargs)
else
    echo "❌ .env.production not found!"
    exit 1
fi

if [ -z "$SLACK_WEBHOOK_URL" ]; then
    echo "❌ SLACK_WEBHOOK_URL is not set in .env.production"
    exit 1
fi

echo "🚀 Sending test message to Slack..."
curl -X POST -H 'Content-type: application/json' \
    --data '{"text":"🚨 Test alert from MuseGenx1000 Deployment Script"}' \
    "$SLACK_WEBHOOK_URL"

echo -e "\n✅ Message sent! Check your Slack channel."
