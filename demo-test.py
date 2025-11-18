#!/usr/bin/env python3
"""
Financial Report Intelligence System - Demo Test Script
Comprehensive testing and demonstration of all system capabilities
"""

import asyncio
import json
import time
from typing import Dict, Any, List
import aiohttp
from datetime import datetime, timedelta
import sys

# Configuration
API_URL = "http://localhost:8000"
EDGE_US_URL = "http://localhost:8001"
MODEL_SERVING_URL = "http://localhost:8002"

# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BOLD = '\033[1m'
    NC = '\033[0m'


class DemoTest:
    """Demo test suite for Financial RAG System"""

    def __init__(self):
        self.results = []
        self.start_time = None
        self.session = None

    def print_header(self, text: str):
        """Print section header"""
        print(f"\n{Colors.BLUE}{'=' * 60}{Colors.NC}")
        print(f"{Colors.BLUE}{text}{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 60}{Colors.NC}\n")

    def print_success(self, text: str):
        """Print success message"""
        print(f"{Colors.GREEN}✓ {text}{Colors.NC}")

    def print_error(self, text: str):
        """Print error message"""
        print(f"{Colors.RED}✗ {text}{Colors.NC}")

    def print_warning(self, text: str):
        """Print warning message"""
        print(f"{Colors.YELLOW}⚠ {text}{Colors.NC}")

    def print_info(self, text: str):
        """Print info message"""
        print(f"{text}")

    async def test_health_check(self):
        """Test 1: Health Checks"""
        self.print_header("Test 1: Health Checks")

        try:
            # Central API
            async with self.session.get(f"{API_URL}/health") as resp:
                if resp.status == 200:
                    self.print_success("Central API: Healthy")
                    self.results.append(("Health Check - Central API", True))
                else:
                    self.print_error(f"Central API: Unhealthy (status {resp.status})")
                    self.results.append(("Health Check - Central API", False))
        except Exception as e:
            self.print_error(f"Central API: Connection failed - {e}")
            self.results.append(("Health Check - Central API", False))

        # Edge Node (optional)
        try:
            async with self.session.get(f"{EDGE_US_URL}/health", timeout=aiohttp.ClientTimeout(total=2)) as resp:
                if resp.status == 200:
                    self.print_success("Edge US: Healthy")
                    self.results.append(("Health Check - Edge US", True))
        except:
            self.print_warning("Edge US: Not available (optional)")

        # Model Serving (optional)
        try:
            async with self.session.get(f"{MODEL_SERVING_URL}/health", timeout=aiohttp.ClientTimeout(total=2)) as resp:
                if resp.status == 200:
                    self.print_success("Model Serving: Healthy")
                    self.results.append(("Health Check - Model Serving", True))
        except:
            self.print_warning("Model Serving: Not available (optional)")

    async def test_query_financial_data(self):
        """Test 2: Query Financial Data with Citations"""
        self.print_header("Test 2: Query Financial Data with Citations")

        query_data = {
            "query": "What were Apple's Q4 2023 earnings?",
            "start_date": "2023-10-01",
            "end_date": "2023-12-31",
            "k": 20,
            "include_citations": True
        }

        try:
            start_time = time.time()
            async with self.session.post(
                f"{API_URL}/api/v1/query",
                json=query_data
            ) as resp:
                elapsed = (time.time() - start_time) * 1000

                if resp.status == 200:
                    data = await resp.json()
                    self.print_success(f"Query successful (latency: {elapsed:.0f}ms)")

                    print("\nResponse Preview:")
                    print(f"  Answer: {data.get('answer', 'N/A')[:200]}...")
                    print(f"  Citations: {len(data.get('citations', []))}")
                    print(f"  Confidence: {data.get('confidence', 0):.2f}")
                    print(f"  Hallucination Score: {data.get('hallucination_score', 0):.3f}")

                    self.results.append(("Query Financial Data", True))

                    # Check performance
                    if elapsed < 500:
                        self.print_success(f"Performance: Excellent (<500ms)")
                    elif elapsed < 1000:
                        self.print_info(f"Performance: Good (<1s)")
                    else:
                        self.print_warning(f"Performance: Slow (>{elapsed:.0f}ms)")
                else:
                    self.print_error(f"Query failed with status {resp.status}")
                    self.results.append(("Query Financial Data", False))
        except Exception as e:
            self.print_error(f"Query failed: {e}")
            self.results.append(("Query Financial Data", False))

    async def test_document_upload(self):
        """Test 3: Document Upload"""
        self.print_header("Test 3: Document Upload")

        document_data = {
            "company": "DEMO",
            "document_type": "10-K",
            "filing_date": datetime.now().strftime("%Y-%m-%d"),
            "content": "This is a demo financial document. Revenue: $100M, Net Income: $20M, Operating Margin: 20%.",
            "metadata": {
                "fiscal_year": 2023,
                "fiscal_quarter": 4,
                "test_document": True
            }
        }

        try:
            async with self.session.post(
                f"{API_URL}/api/v1/upload",
                json=document_data
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.print_success("Document uploaded successfully")
                    print(f"  Document ID: {data.get('document_id', 'N/A')}")
                    self.results.append(("Document Upload", True))
                else:
                    self.print_error(f"Upload failed with status {resp.status}")
                    self.results.append(("Document Upload", False))
        except Exception as e:
            self.print_error(f"Upload failed: {e}")
            self.results.append(("Document Upload", False))

    async def test_compliance_check(self):
        """Test 4: Compliance Validation"""
        self.print_header("Test 4: Compliance Validation")

        compliance_data = {
            "company": "DEMO",
            "report_type": "10-K",
            "fiscal_year": 2023,
            "jurisdiction": "US"
        }

        try:
            async with self.session.post(
                f"{API_URL}/api/v1/compliance",
                json=compliance_data
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.print_success("Compliance check successful")

                    print(f"\nCompliance Status:")
                    print(f"  Is Compliant: {data.get('is_compliant', False)}")
                    print(f"  Violations: {len(data.get('violations', []))}")
                    print(f"  Warnings: {len(data.get('warnings', []))}")

                    if data.get('risk_score'):
                        print(f"\nRisk Scores:")
                        for risk_type, score in data['risk_score'].items():
                            print(f"  {risk_type}: {score:.2f}")

                    self.results.append(("Compliance Check", True))
                else:
                    self.print_error(f"Compliance check failed with status {resp.status}")
                    self.results.append(("Compliance Check", False))
        except Exception as e:
            self.print_error(f"Compliance check failed: {e}")
            self.results.append(("Compliance Check", False))

    async def test_temporal_analysis(self):
        """Test 5: Temporal Analysis"""
        self.print_header("Test 5: Temporal Analysis")

        temporal_data = {
            "company": "DEMO",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "metrics": ["revenue", "net_income", "operating_margin"]
        }

        try:
            async with self.session.post(
                f"{API_URL}/api/v1/temporal/analyze",
                json=temporal_data
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.print_success("Temporal analysis successful")

                    print("\nTemporal Analysis Results:")
                    if data.get('trends'):
                        print("  Trends detected:")
                        for period, trends in data['trends'].items():
                            print(f"    {period}: {len(trends)} metrics")

                    if data.get('events'):
                        print(f"  Anomalies detected: {len(data['events'])}")

                    if data.get('forecasts'):
                        print(f"  Forecasts generated: {len(data['forecasts'])} metrics")

                    self.results.append(("Temporal Analysis", True))
                else:
                    self.print_error(f"Temporal analysis failed with status {resp.status}")
                    self.results.append(("Temporal Analysis", False))
        except Exception as e:
            self.print_error(f"Temporal analysis failed: {e}")
            self.results.append(("Temporal Analysis", False))

    async def test_risk_assessment(self):
        """Test 6: Risk Assessment"""
        self.print_header("Test 6: Risk Assessment")

        risk_data = {
            "company": "DEMO",
            "include_monte_carlo": True,
            "confidence_levels": [0.95, 0.99]
        }

        try:
            async with self.session.post(
                f"{API_URL}/api/v1/risk/assess",
                json=risk_data
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.print_success("Risk assessment successful")

                    print("\nRisk Assessment Results:")
                    if data.get('risk_scores'):
                        print("  Risk Scores:")
                        for category, score in data['risk_scores'].items():
                            print(f"    {category}: {score:.2f}")

                    if data.get('var_95'):
                        print(f"  VaR (95%): {data['var_95']:.2f}")
                    if data.get('var_99'):
                        print(f"  VaR (99%): {data['var_99']:.2f}")

                    self.results.append(("Risk Assessment", True))
                else:
                    self.print_error(f"Risk assessment failed with status {resp.status}")
                    self.results.append(("Risk Assessment", False))
        except Exception as e:
            self.print_error(f"Risk assessment failed: {e}")
            self.results.append(("Risk Assessment", False))

    async def test_system_stats(self):
        """Test 7: System Statistics"""
        self.print_header("Test 7: System Statistics")

        try:
            async with self.session.get(f"{API_URL}/api/v1/stats") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.print_success("System stats retrieved")

                    print("\nSystem Statistics:")
                    for key, value in data.items():
                        if isinstance(value, (int, float)):
                            print(f"  {key}: {value}")
                        elif isinstance(value, dict) and len(value) < 5:
                            print(f"  {key}: {json.dumps(value, indent=4)}")

                    self.results.append(("System Stats", True))
                else:
                    self.print_error(f"Stats retrieval failed with status {resp.status}")
                    self.results.append(("System Stats", False))
        except Exception as e:
            self.print_error(f"Stats retrieval failed: {e}")
            self.results.append(("System Stats", False))

    async def test_model_serving(self):
        """Test 8: Model Serving - Embeddings"""
        self.print_header("Test 8: Model Serving - Embeddings")

        try:
            # Check if model serving is available
            async with self.session.get(
                f"{MODEL_SERVING_URL}/health",
                timeout=aiohttp.ClientTimeout(total=2)
            ) as resp:
                if resp.status != 200:
                    self.print_warning("Model serving not available (optional)")
                    return

            # Test embedding generation
            embedding_data = {
                "texts": [
                    "Apple reported strong Q4 earnings",
                    "Revenue grew 15% year-over-year",
                    "Net income increased significantly"
                ],
                "model_id": "financial-embeddings",
                "batch_size": 32
            }

            start_time = time.time()
            async with self.session.post(
                f"{MODEL_SERVING_URL}/embed",
                json=embedding_data
            ) as resp:
                elapsed = (time.time() - start_time) * 1000

                if resp.status == 200:
                    data = await resp.json()
                    self.print_success(f"Embedding generation successful (latency: {elapsed:.0f}ms)")

                    print(f"\nEmbedding Results:")
                    print(f"  Texts processed: {data.get('count', 0)}")
                    print(f"  Embedding dimension: {len(data.get('embeddings', [[]])[0])}")
                    print(f"  Throughput: {(data.get('count', 0) / elapsed * 1000):.0f} texts/sec")

                    self.results.append(("Model Serving", True))
                else:
                    self.print_error(f"Embedding generation failed with status {resp.status}")
                    self.results.append(("Model Serving", False))
        except Exception as e:
            self.print_warning(f"Model serving not available: {e}")

    async def test_performance(self):
        """Test 9: Performance Test"""
        self.print_header("Test 9: Performance Test (10 concurrent queries)")

        num_queries = 10
        latencies = []
        success_count = 0

        # Create query tasks
        tasks = []
        for i in range(num_queries):
            task = self.single_query_perf(i)
            tasks.append(task)

        # Run queries concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        for i, result in enumerate(results):
            if isinstance(result, tuple) and result[0]:
                success_count += 1
                latencies.append(result[1])
                self.print_info(f"  Query {i+1}: {result[1]:.0f}ms ✓")
            else:
                self.print_error(f"  Query {i+1}: Failed")

        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

            print(f"\n{Colors.BOLD}Performance Summary:{Colors.NC}")
            print(f"  Success Rate: {success_count}/{num_queries} ({success_count*10}%)")
            print(f"  Average Latency: {avg_latency:.0f}ms")
            print(f"  P95 Latency: {p95_latency:.0f}ms")
            print(f"  Min/Max: {min(latencies):.0f}ms / {max(latencies):.0f}ms")

            if avg_latency < 500:
                self.print_success("Performance target met (<500ms average)")
            else:
                self.print_warning(f"Performance target not met ({avg_latency:.0f}ms > 500ms)")

            self.results.append(("Performance Test", success_count == num_queries))

    async def single_query_perf(self, query_num: int):
        """Single query for performance testing"""
        try:
            start_time = time.time()
            async with self.session.post(
                f"{API_URL}/api/v1/query",
                json={"query": f"Test query {query_num}", "k": 5}
            ) as resp:
                elapsed = (time.time() - start_time) * 1000
                if resp.status == 200:
                    return (True, elapsed)
                return (False, elapsed)
        except:
            return (False, 0)

    def print_summary(self):
        """Print test summary"""
        self.print_header("Demo Test Summary")

        passed = sum(1 for _, success in self.results if success)
        total = len(self.results)

        print(f"Tests Passed: {passed}/{total} ({passed/total*100:.0f}%)\n")

        print("Test Results:")
        for test_name, success in self.results:
            status = f"{Colors.GREEN}✓ PASSED{Colors.NC}" if success else f"{Colors.RED}✗ FAILED{Colors.NC}"
            print(f"  {test_name}: {status}")

        elapsed = time.time() - self.start_time
        print(f"\nTotal execution time: {elapsed:.2f}s")

        print("\n" + "=" * 60)
        if passed == total:
            self.print_success("All tests passed! System is operational.")
        elif passed > total * 0.7:
            self.print_warning(f"Most tests passed ({passed}/{total}). Check failed tests.")
        else:
            self.print_error(f"Multiple tests failed ({total-passed}/{total}). Review system setup.")

        print("\nNext Steps:")
        print(f"  1. API Documentation: {API_URL}/docs")
        print("  2. Grafana Dashboard: http://localhost:3000")
        print("  3. Prometheus Metrics: http://localhost:9090")
        print("  4. Run load tests: k6 run deploy/scaling/load-test.js")
        print("\nFor production deployment, see DEPLOYMENT_CHECKLIST.md\n")

    async def run_all_tests(self):
        """Run all demo tests"""
        print(f"\n{Colors.BOLD}{'=' * 60}{Colors.NC}")
        print(f"{Colors.BOLD}Financial Report Intelligence System - Demo Test{Colors.NC}")
        print(f"{Colors.BOLD}{'=' * 60}{Colors.NC}")

        self.start_time = time.time()

        # Create session
        async with aiohttp.ClientSession() as session:
            self.session = session

            # Run tests
            await self.test_health_check()
            await self.test_query_financial_data()
            await self.test_document_upload()
            await self.test_compliance_check()
            await self.test_temporal_analysis()
            await self.test_risk_assessment()
            await self.test_system_stats()
            await self.test_model_serving()
            await self.test_performance()

        # Print summary
        self.print_summary()


async def main():
    """Main entry point"""
    try:
        demo = DemoTest()
        await demo.run_all_tests()
        return 0 if all(success for _, success in demo.results) else 1
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        return 130
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {e}{Colors.NC}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
