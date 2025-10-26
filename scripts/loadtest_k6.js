import http from 'k6/http';
import { sleep, check } from 'k6';

export const options = {
  vus: 10,
  duration: '30s',
};

export default function () {
  const url = 'http://localhost:8081/ask';
  const payload = JSON.stringify({ question: 'What model does this demo use?' });
  const params = { headers: { 'Content-Type': 'application/json' } };
  const res = http.post(url, payload, params);
  check(res, { 'status 200': (r) => r.status === 200 });
  sleep(0.5);
}
