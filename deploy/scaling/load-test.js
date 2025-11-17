/**
 * Load Testing Script for Financial RAG System
 * Using k6 load testing tool
 *
 * Run with: k6 run load-test.js
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Counter, Trend, Rate } from 'k6/metrics';

// Custom metrics
const queryLatency = new Trend('query_latency');
const queryErrors = new Rate('query_errors');
const querySuccess = new Counter('query_success');

// Test configuration
export let options = {
  // Scaling stages
  stages: [
    { duration: '1m', target: 10 },   // Warm-up: 10 VUs for 1 minute
    { duration: '2m', target: 50 },   // Ramp-up: 50 VUs
    { duration: '5m', target: 100 },  // Sustained load: 100 VUs
    { duration: '2m', target: 200 },  // Spike: 200 VUs
    { duration: '3m', target: 200 },  // Sustained spike
    { duration: '2m', target: 50 },   // Ramp-down
    { duration: '1m', target: 0 },    // Cool-down
  ],

  // Thresholds (SLOs)
  thresholds: {
    // 95% of requests should complete within 500ms
    'http_req_duration': ['p(95)<500'],

    // 99% of requests should complete within 1s
    'http_req_duration{scenario:query}': ['p(99)<1000'],

    // Error rate should be less than 1%
    'http_req_failed': ['rate<0.01'],

    // Query errors should be less than 1%
    'query_errors': ['rate<0.01'],

    // Request rate should be > 50 req/s
    'http_reqs': ['rate>50'],
  },

  // Tags for grouping results
  tags: {
    environment: 'load-test',
    service: 'financial-rag'
  }
};

// Configuration
const BASE_URL = __ENV.API_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'test-key';

// Sample queries for testing
const queries = [
  'What were Apple\'s Q4 2023 earnings?',
  'Analyze Microsoft\'s revenue growth trends',
  'What risks does Tesla face in 2024?',
  'Compare Amazon and Google cloud revenue',
  'What is NVIDIA\'s market position in AI chips?',
  'Analyze Meta\'s advertising revenue',
  'What are the key metrics for Alphabet?',
  'Summarize Intel\'s manufacturing challenges',
  'What is AMD\'s competitive advantage?',
  'Analyze Netflix subscriber growth',
  'What are the trends in semiconductor industry?',
  'Compare profit margins of tech companies',
  'What factors affect Apple stock price?',
  'Analyze quarterly revenue trends for FAANG stocks',
  'What are the regulatory risks for Meta?'
];

// Helper function to get random query
function getRandomQuery() {
  return queries[Math.floor(Math.random() * queries.length)];
}

// Helper function to get random date range
function getRandomDateRange() {
  const endDate = new Date();
  const startDate = new Date();
  startDate.setMonth(startDate.getMonth() - Math.floor(Math.random() * 12) - 1);

  return {
    start_date: startDate.toISOString().split('T')[0],
    end_date: endDate.toISOString().split('T')[0]
  };
}

// Test setup
export function setup() {
  // Health check before starting load test
  const healthRes = http.get(`${BASE_URL}/health`);

  check(healthRes, {
    'health check passed': (r) => r.status === 200,
  });

  if (healthRes.status !== 200) {
    throw new Error('Health check failed - aborting test');
  }

  console.log('Load test starting...');
  return { startTime: Date.now() };
}

// Main test scenario
export default function (data) {
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${API_KEY}`
  };

  group('Financial RAG Query Test', () => {
    // Test 1: Standard query
    group('Standard Query', () => {
      const query = getRandomQuery();
      const dateRange = getRandomDateRange();

      const payload = JSON.stringify({
        query: query,
        start_date: dateRange.start_date,
        end_date: dateRange.end_date,
        k: 20,
        include_citations: true
      });

      const startTime = Date.now();
      const response = http.post(
        `${BASE_URL}/api/v1/query`,
        payload,
        { headers: headers, tags: { scenario: 'query' } }
      );
      const duration = Date.now() - startTime;

      // Record custom metrics
      queryLatency.add(duration);

      const success = check(response, {
        'status is 200': (r) => r.status === 200,
        'has answer': (r) => {
          try {
            const body = JSON.parse(r.body);
            return body.answer && body.answer.length > 0;
          } catch (e) {
            return false;
          }
        },
        'has citations': (r) => {
          try {
            const body = JSON.parse(r.body);
            return body.citations && body.citations.length > 0;
          } catch (e) {
            return false;
          }
        },
        'response time < 1s': (r) => r.timings.duration < 1000,
        'response time < 500ms': (r) => r.timings.duration < 500,
      });

      if (success) {
        querySuccess.add(1);
      } else {
        queryErrors.add(1);
      }
    });

    // Test 2: Document upload (less frequent)
    if (Math.random() < 0.1) {  // 10% of requests
      group('Document Upload', () => {
        const document = {
          company: 'AAPL',
          document_type: '10-K',
          content: 'Sample financial document content...',
          filing_date: new Date().toISOString().split('T')[0]
        };

        const response = http.post(
          `${BASE_URL}/api/v1/upload`,
          JSON.stringify(document),
          { headers: headers, tags: { scenario: 'upload' } }
        );

        check(response, {
          'upload status is 200': (r) => r.status === 200,
        });
      });
    }

    // Test 3: Compliance check (less frequent)
    if (Math.random() < 0.05) {  // 5% of requests
      group('Compliance Check', () => {
        const report = {
          company: 'MSFT',
          report_type: '10-Q',
          fiscal_year: 2023,
          fiscal_quarter: 4
        };

        const response = http.post(
          `${BASE_URL}/api/v1/compliance`,
          JSON.stringify(report),
          { headers: headers, tags: { scenario: 'compliance' } }
        );

        check(response, {
          'compliance status is 200': (r) => r.status === 200,
        });
      });
    }

    // Test 4: Stats endpoint (health monitoring)
    if (Math.random() < 0.02) {  // 2% of requests
      group('Stats Check', () => {
        const response = http.get(
          `${BASE_URL}/api/v1/stats`,
          { headers: headers, tags: { scenario: 'stats' } }
        );

        check(response, {
          'stats status is 200': (r) => r.status === 200,
        });
      });
    }
  });

  // Think time (simulate user behavior)
  sleep(Math.random() * 2 + 1);  // 1-3 seconds
}

// Test teardown
export function teardown(data) {
  const duration = (Date.now() - data.startTime) / 1000;
  console.log(`Load test completed in ${duration}s`);
}

// Handle errors
export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: '  ', enableColors: true }),
    'summary.json': JSON.stringify(data, null, 2),
  };
}

function textSummary(data, options) {
  const { indent = '', enableColors = false } = options;

  let summary = '\n';
  summary += `${indent}✓ Test Duration: ${(data.state.testRunDurationMs / 1000).toFixed(2)}s\n`;
  summary += `${indent}✓ Total Requests: ${data.metrics.http_reqs.values.count}\n`;
  summary += `${indent}✓ Request Rate: ${data.metrics.http_reqs.values.rate.toFixed(2)} req/s\n`;
  summary += `${indent}✓ Success Rate: ${(100 - data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%\n`;
  summary += `${indent}✓ Avg Response Time: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms\n`;
  summary += `${indent}✓ P95 Response Time: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms\n`;
  summary += `${indent}✓ P99 Response Time: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms\n`;

  return summary;
}
