import http from 'k6/http';
import { sleep, check } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const responseTime = new Trend('response_time');

// Konfigurasi test
export const options = {
  stages: [
    { duration: '30s', target: 10 }, // Ramp-up ke 10 VU selama 30 detik
    { duration: '1m', target: 10 },  // Tetap 10 VU selama 1 menit
    { duration: '30s', target: 0 },  // Ramp-down ke 0 VU selama 30 detik
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% request harus selesai dalam 500ms
    errors: ['rate<0.1'],             // Error rate harus kurang dari 10%
  },
  ext: {
    influxdb: {
      url: 'http://localhost:8086',
      database: 'k6',
      username: '',
      password: '',
      tags: {
        test: 'load-balancer-test'
      }
    }
  }
};

// Fungsi utama test
export default function () {
  // Test endpoint round-robin
  const roundRobinRes = http.get('http://localhost:8080/round-robin/');
  check(roundRobinRes, {
    'round-robin status is 200': (r) => r.status === 200,
  });
  errorRate.add(roundRobinRes.status !== 200);
  responseTime.add(roundRobinRes.timings.duration);
  sleep(1);

  // Test endpoint least-conn
  const leastConnRes = http.get('http://localhost:8080/least-conn/');
  check(leastConnRes, {
    'least-conn status is 200': (r) => r.status === 200,
  });
  errorRate.add(leastConnRes.status !== 200);
  responseTime.add(leastConnRes.timings.duration);
  sleep(1);

  // Test endpoint weighted-least-conn
  const weightedLeastConnRes = http.get('http://localhost:8080/weighted-least-conn/');
  check(weightedLeastConnRes, {
    'weighted-least-conn status is 200': (r) => r.status === 200,
  });
  errorRate.add(weightedLeastConnRes.status !== 200);
  responseTime.add(weightedLeastConnRes.timings.duration);
  sleep(1);

  // Test endpoint ip-hash
  const ipHashRes = http.get('http://localhost:8080/ip-hash/');
  check(ipHashRes, {
    'ip-hash status is 200': (r) => r.status === 200,
  });
  errorRate.add(ipHashRes.status !== 200);
  responseTime.add(ipHashRes.timings.duration);
  sleep(1);
} 