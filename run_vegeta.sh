#!/usr/bin/env bash
# Usage: ./run_vegeta.sh <rate_per_sec> <duration>
# Example: ./run_vegeta.sh 5 30s
RATE=${1:-5}
DUR=${2:-30s}
ENDPOINT=${TTS_ENDPOINT:-"https://api.yoursite/v1/tts/21m00Tcm4TlvDq8ikWAM"}
API_KEY=${TTS_API_KEY:-"REDACTED"}
TEXT='สวัสดีครับ นี่คือการทดสอบโหลด'
echo "Warning: Load testing against ElevenLabs incurs real cost. Prefer mock/stub first; if real, start at 1 rps and short duration."

cat <<EOF > req.json
POST $ENDPOINT
Content-Type: application/json
xi-api-key: $API_KEY
Accept: audio/mpeg

{"text":"$TEXT","model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.4,"similarity_boost":0.1}}
EOF

vegeta attack -targets=req.json -rate=${RATE} -duration=${DUR} | vegeta report
# To get detailed metrics into a file:
# vegeta attack -targets=req.json -rate=${RATE} -duration=${DUR} | tee results.bin | vegeta report -type=json > vegeta_report.json
