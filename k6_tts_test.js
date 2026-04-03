import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend } from 'k6/metrics';

const latencyTrend = new Trend('tts_latency_ms');

export const options = {
  vus: __ENV.K6_VUS ? parseInt(__ENV.K6_VUS, 10) : 10,
  duration: __ENV.K6_DURATION ? __ENV.K6_DURATION : '30s',
  thresholds: {
    http_req_duration: ['p(95)<5000']
  }
};

const endpoint = __ENV.TTS_ENDPOINT;
const apiKey = __ENV.TTS_API_KEY;
const voiceID = __ENV.TTS_VOICE_ID || '21m00Tcm4TlvDq8ikWAM';
const modelID = __ENV.TTS_MODEL_ID || 'eleven_multilingual_v2';
const safetyNotice = __ENV.TTS_SAFETY_NOTICE || 'Load testing against ElevenLabs incurs real cost. Prefer mock/stub first, start low rate if real.';

const examples = [
  'สวัสดีครับ นี่คือการทดสอบความเร็วของระบบ',
  'กรุณาชำระเงินจำนวน 1,234 บาท ภายใน 31 ธันวาคม',
  'สภาพอากาศวันนี้มีฝนตกเล็กน้อย อุณหภูมิ 28 องศา',
  'MuseGen ช่วยให้สร้างเพลงได้ง่ายขึ้นด้วยเทคโนโลยี AI'
];

export default function () {
  if (__ITER === 0) {
    console.log(safetyNotice);
  }
  const text = examples[Math.floor(Math.random() * examples.length)];
  const payload = JSON.stringify({
    text: text,
    model_id: modelID,
    voice_settings: { stability: 0.4, similarity_boost: 0.1 }
  });
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'xi-api-key': apiKey,
      'Accept': 'audio/mpeg'
    },
    timeout: '120s'
  };
  const res = http.post(endpoint + '/' + voiceID, payload, params);
  check(res, {
    'status is 200': (r) => r.status === 200,
    'non-empty body': (r) => r.body && r.body.length > 100
  });
  latencyTrend.add(res.timings.duration);
  sleep(1);
}
