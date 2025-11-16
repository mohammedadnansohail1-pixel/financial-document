# Getting Started with Financial Report Intelligence System

This guide will help you get up and running with the Financial Report Intelligence System in minutes.

## 🚀 Quick Start (5 minutes)

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/financial-report-intelligence.git
cd financial-report-intelligence

# Copy environment variables
cp .env.example .env

# Edit .env with your API keys (optional for basic usage)
nano .env
```

### 2. Start with Docker (Recommended)

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
```

Services will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474
- **Grafana**: http://localhost:3000

### 3. Test the System

```bash
# Health check
curl http://localhost:8000/health

# Try a sample query
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are key financial metrics to track?",
    "k": 10,
    "use_citation": true
  }'
```

## 📚 Alternative: Local Development Setup

### Prerequisites

- Python 3.9+
- 16GB RAM recommended
- Virtual environment tool (venv, conda, etc.)

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download NLP models
python -m spacy download en_core_web_sm

# Install the package
pip install -e .
```

### Run Locally

```bash
# Start the API server
uvicorn src.api.server:app --reload --port 8000

# In another terminal, run the example
python examples/example_usage.py
```

## 🎯 First Steps

### Step 1: Upload a Document

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/documents/upload",
    json={
        "document_id": "test-doc-001",
        "document_type": "10-K",
        "company": "Test Corp",
        "filing_date": "2023-12-31",
        "content": "Your financial document content here..."
    }
)

print(response.json())
```

### Step 2: Query the System

```python
response = requests.post(
    "http://localhost:8000/api/v1/query",
    json={
        "query": "What was the revenue?",
        "temporal_context": {
            "start_date": "2023-01-01",
            "end_date": "2023-12-31"
        },
        "k": 20,
        "use_citation": true
    }
)

result = response.json()
print(f"Answer: {result['answer']}")
print(f"Confidence: {result['confidence']}")
print(f"Citations: {len(result['citations'])}")
```

### Step 3: Run Compliance Check

```python
response = requests.post(
    "http://localhost:8000/api/v1/compliance/check",
    json={
        "document_id": "test-doc-001",
        "document_type": "10-K",
        "company": "Test Corp",
        "content": "Your document content...",
        "jurisdiction": "US"
    }
)

compliance = response.json()
print(f"Compliant: {compliance['compliant']}")
print(f"Violations: {len(compliance['violations'])}")
print(f"Risk Scores: {compliance['risk_scores']}")
```

## 📖 Tutorials

### Tutorial 1: Processing SEC Filings

```python
from src.data_processing.financial_data_processor import FinancialDataProcessor
from datetime import datetime

processor = FinancialDataProcessor()

filing = {
    'document_id': 'AAPL-10K-2023',
    'document_type': '10-K',
    'company': 'Apple Inc.',
    'cik': '0000320193',
    'filing_date': datetime(2023, 11, 3),
    'content': open('apple_10k.txt').read()
}

# Process the filing
processed = processor.process_10k_filing(filing)

print(f"Chunks: {len(processed.chunks)}")
print(f"Entities: {len(processed.entities)}")
```

### Tutorial 2: Building Knowledge Graphs

```python
from src.knowledge_graph.financial_kg import FinancialKnowledgeGraph

kg = FinancialKnowledgeGraph()

# Build graph from processed document
result = kg.construct_from_filing(processed.__dict__)

# Query the graph
subgraph = kg.query_by_entity(
    entity_id="company_0000320193",
    max_depth=2
)

# Export to Neo4j
kg.export_to_cypher("output.cypher")
```

### Tutorial 3: Temporal Analysis

```python
from src.temporal.temporal_analyzer import TemporalFinancialAnalyzer
import pandas as pd

analyzer = TemporalFinancialAnalyzer()

# Create sample data
data = pd.DataFrame({
    'revenue': [100, 105, 110, 108, 115],
    'net_income': [20, 21, 23, 22, 25]
}, index=pd.date_range('2023-01-01', periods=5, freq='Q'))

# Analyze
analysis = analyzer.analyze_temporal_patterns(
    company="Test Corp",
    data=data
)

# Access results
for period, trends in analysis['trends'].items():
    print(f"{period}: {trends}")
```

## 🔧 Configuration

### Basic Configuration

Edit `config/config.yaml`:

```yaml
# API Settings
api:
  host: "0.0.0.0"
  port: 8000
  workers: 4

# RAG Configuration
rag:
  retrieval:
    default_k: 20
    use_hybrid: true

# Generation
generation:
  llm:
    provider: "openai"
    model: "gpt-4"
    temperature: 0.3
```

### Environment Variables

Required variables in `.env`:

```bash
# Minimal setup
OPENAI_API_KEY=sk-...

# For full functionality
NEWSAPI_KEY=...
ALPHA_VANTAGE_KEY=...
```

## 🐛 Troubleshooting

### Common Issues

**Issue**: Docker containers won't start
```bash
# Check Docker is running
docker --version

# Check ports are available
netstat -an | grep 8000

# Reset Docker state
docker-compose down -v
docker-compose up -d
```

**Issue**: Module import errors
```bash
# Ensure you're in the right directory
cd financial-report-intelligence

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

**Issue**: API returns 500 errors
```bash
# Check logs
docker-compose logs api

# Restart services
docker-compose restart api
```

## 📚 Next Steps

1. **Read the full documentation**: See [README.md](README.md)

2. **Explore examples**: Check `examples/example_usage.py`

3. **API Reference**: Visit http://localhost:8000/docs

4. **Join the community**: See [CONTRIBUTING.md](CONTRIBUTING.md)

5. **Deploy to production**: See [DEPLOYMENT.md](DEPLOYMENT.md)

## 🎓 Learning Resources

- [Architecture Overview](docs/architecture.md)
- [API Reference](http://localhost:8000/docs)
- [Code Examples](examples/)
- [Best Practices](docs/best-practices.md)
- [FAQ](docs/faq.md)

## 💬 Getting Help

- **Documentation**: https://docs.finrag.example.com
- **GitHub Issues**: https://github.com/your-org/financial-rag/issues
- **Email**: support@finrag.example.com
- **Slack**: https://finrag.slack.com

## ✅ Checklist

Before you start developing:

- [ ] Docker installed and running
- [ ] Environment variables configured
- [ ] Services started successfully
- [ ] Health check passes
- [ ] Example query works
- [ ] API documentation accessible

Happy analyzing! 🚀
