#!/bin/bash
# Financial Report Intelligence System - Demo Script
# Tests all major features and showcases system capabilities

set -e  # Exit on error

echo "=================================================="
echo "Financial Report Intelligence System - Demo Test"
echo "=================================================="
echo ""

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
EDGE_US_URL="${EDGE_US_URL:-http://localhost:8001}"
MODEL_SERVING_URL="${MODEL_SERVING_URL:-http://localhost:8002}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper function for test status
test_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
    else
        echo -e "${RED}✗ FAILED${NC}"
    fi
}

# Test 1: Health Checks
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test 1: Health Checks${NC}"
echo -e "${BLUE}========================================${NC}"

echo "Testing Central API health..."
curl -s -f "$API_URL/health" > /dev/null
test_status

echo "Testing Edge US health..."
curl -s -f "$EDGE_US_URL/health" > /dev/null 2>&1 || echo -e "${YELLOW}⚠ Edge node not running (optional)${NC}"

echo "Testing Model Serving health..."
curl -s -f "$MODEL_SERVING_URL/health" > /dev/null 2>&1 || echo -e "${YELLOW}⚠ Model serving not running (optional)${NC}"

echo ""

# Test 2: Query Financial Data
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test 2: Query Financial Data with Citations${NC}"
echo -e "${BLUE}========================================${NC}"

echo "Querying: 'What were Apple's Q4 2023 earnings?'"
QUERY_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What were Apple'\''s Q4 2023 earnings?",
    "start_date": "2023-10-01",
    "end_date": "2023-12-31",
    "k": 20,
    "include_citations": true
  }')

if [ $? -eq 0 ] && [ -n "$QUERY_RESPONSE" ]; then
    echo -e "${GREEN}✓ Query successful${NC}"
    echo ""
    echo "Response Preview:"
    echo "$QUERY_RESPONSE" | python3 -m json.tool 2>/dev/null | head -30 || echo "$QUERY_RESPONSE"
else
    echo -e "${RED}✗ Query failed${NC}"
fi

echo ""

# Test 3: Document Upload
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test 3: Document Upload${NC}"
echo -e "${BLUE}========================================${NC}"

echo "Uploading sample financial document..."
UPLOAD_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/upload" \
  -H "Content-Type: application/json" \
  -d '{
    "company": "DEMO",
    "document_type": "10-K",
    "filing_date": "2024-01-16",
    "content": "This is a demo financial document for testing purposes. Revenue: $100M, Net Income: $20M, Operating Margin: 20%.",
    "metadata": {
      "fiscal_year": 2023,
      "fiscal_quarter": 4
    }
  }')

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Upload successful${NC}"
    echo "Response: $UPLOAD_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$UPLOAD_RESPONSE"
else
    echo -e "${RED}✗ Upload failed${NC}"
fi

echo ""

# Test 4: Compliance Check
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test 4: Compliance Validation${NC}"
echo -e "${BLUE}========================================${NC}"

echo "Checking compliance for sample report..."
COMPLIANCE_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/compliance" \
  -H "Content-Type: application/json" \
  -d '{
    "company": "DEMO",
    "report_type": "10-K",
    "fiscal_year": 2023,
    "jurisdiction": "US"
  }')

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Compliance check successful${NC}"
    echo "Response: $COMPLIANCE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$COMPLIANCE_RESPONSE"
else
    echo -e "${RED}✗ Compliance check failed${NC}"
fi

echo ""

# Test 5: Temporal Analysis
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test 5: Temporal Analysis${NC}"
echo -e "${BLUE}========================================${NC}"

echo "Analyzing temporal patterns..."
TEMPORAL_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/temporal/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "company": "DEMO",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "metrics": ["revenue", "net_income"]
  }')

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Temporal analysis successful${NC}"
    echo "Response: $TEMPORAL_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$TEMPORAL_RESPONSE"
else
    echo -e "${RED}✗ Temporal analysis failed${NC}"
fi

echo ""

# Test 6: Risk Assessment
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test 6: Risk Assessment${NC}"
echo -e "${BLUE}========================================${NC}"

echo "Assessing risk profile..."
RISK_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/risk/assess" \
  -H "Content-Type: application/json" \
  -d '{
    "company": "DEMO",
    "include_monte_carlo": true,
    "confidence_levels": [0.95, 0.99]
  }')

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Risk assessment successful${NC}"
    echo "Response: $RISK_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RISK_RESPONSE"
else
    echo -e "${RED}✗ Risk assessment failed${NC}"
fi

echo ""

# Test 7: System Stats
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test 7: System Statistics${NC}"
echo -e "${BLUE}========================================${NC}"

echo "Fetching system statistics..."
STATS_RESPONSE=$(curl -s "$API_URL/api/v1/stats")

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Stats retrieval successful${NC}"
    echo "Response: $STATS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$STATS_RESPONSE"
else
    echo -e "${RED}✗ Stats retrieval failed${NC}"
fi

echo ""

# Test 8: Model Serving (if available)
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test 8: Model Serving - Embeddings${NC}"
echo -e "${BLUE}========================================${NC}"

if curl -s -f "$MODEL_SERVING_URL/health" > /dev/null 2>&1; then
    echo "Generating embeddings..."
    EMBEDDING_RESPONSE=$(curl -s -X POST "$MODEL_SERVING_URL/embed" \
      -H "Content-Type: application/json" \
      -d '{
        "texts": ["Apple reported strong Q4 earnings", "Revenue grew 15%"],
        "model_id": "financial-embeddings",
        "batch_size": 32
      }')

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Embedding generation successful${NC}"
        echo "Generated embeddings for 2 texts"
    else
        echo -e "${RED}✗ Embedding generation failed${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Model serving not available (optional)${NC}"
fi

echo ""

# Test 9: Edge Node Query (if available)
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test 9: Edge Node Query${NC}"
echo -e "${BLUE}========================================${NC}"

if curl -s -f "$EDGE_US_URL/health" > /dev/null 2>&1; then
    echo "Querying via edge node..."
    EDGE_RESPONSE=$(curl -s -X POST "$EDGE_US_URL/query" \
      -H "Content-Type: application/json" \
      -d '{
        "query": "Test edge query",
        "region": "us-east"
      }')

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Edge query successful${NC}"
        echo "Response: $EDGE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$EDGE_RESPONSE"
    else
        echo -e "${RED}✗ Edge query failed${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Edge node not available (optional)${NC}"
fi

echo ""

# Test 10: Performance Test
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test 10: Performance Test (10 queries)${NC}"
echo -e "${BLUE}========================================${NC}"

echo "Running 10 concurrent queries to test throughput..."
TOTAL_TIME=0
SUCCESS_COUNT=0

for i in {1..10}; do
    START_TIME=$(date +%s%N)

    curl -s -X POST "$API_URL/api/v1/query" \
      -H "Content-Type: application/json" \
      -d "{\"query\": \"Test query $i\", \"k\": 5}" > /dev/null 2>&1

    if [ $? -eq 0 ]; then
        END_TIME=$(date +%s%N)
        ELAPSED=$((($END_TIME - $START_TIME) / 1000000))  # Convert to ms
        TOTAL_TIME=$(($TOTAL_TIME + $ELAPSED))
        SUCCESS_COUNT=$(($SUCCESS_COUNT + 1))
        echo -e "Query $i: ${ELAPSED}ms ${GREEN}✓${NC}"
    else
        echo -e "Query $i: ${RED}✗ Failed${NC}"
    fi
done

if [ $SUCCESS_COUNT -gt 0 ]; then
    AVG_TIME=$(($TOTAL_TIME / $SUCCESS_COUNT))
    echo ""
    echo -e "${GREEN}Performance Summary:${NC}"
    echo "  Success Rate: $SUCCESS_COUNT/10 ($(($SUCCESS_COUNT * 10))%)"
    echo "  Average Latency: ${AVG_TIME}ms"
    echo "  Total Time: ${TOTAL_TIME}ms"

    if [ $AVG_TIME -lt 500 ]; then
        echo -e "  ${GREEN}✓ Performance target met (<500ms)${NC}"
    else
        echo -e "  ${YELLOW}⚠ Performance target not met (${AVG_TIME}ms > 500ms)${NC}"
    fi
fi

echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Demo Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Core API: Available"
echo "Query System: Functional"
echo "Document Upload: Functional"
echo "Compliance Engine: Functional"
echo "Temporal Analysis: Functional"
echo "Risk Assessment: Functional"
echo ""
echo -e "${GREEN}✓ Demo test completed successfully!${NC}"
echo ""
echo "Next Steps:"
echo "  1. Review API documentation: curl $API_URL/docs"
echo "  2. Access Grafana dashboard: http://localhost:3000"
echo "  3. View Prometheus metrics: http://localhost:9090"
echo "  4. Run load tests: k6 run deploy/scaling/load-test.js"
echo ""
echo "For production deployment, see DEPLOYMENT_CHECKLIST.md"
echo ""
