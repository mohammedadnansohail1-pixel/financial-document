"""
Example usage of the Financial Report Intelligence System
Demonstrates core functionality: document processing, querying, and analysis
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_processing.financial_data_processor import FinancialDataProcessor
from src.retrieval.tmm_hybrid_rag import TMMHybridRAG, TemporalContext
from src.knowledge_graph.financial_kg import FinancialKnowledgeGraph
from src.generation.citation_aware_generator import CitationAwareGenerator
from src.temporal.temporal_analyzer import TemporalFinancialAnalyzer
from src.compliance.compliance_engine import ComplianceEngine

import pandas as pd
import numpy as np


def example_1_process_document():
    """
    Example 1: Process a financial document (10-K filing)
    """
    print("=" * 70)
    print("EXAMPLE 1: Processing Financial Document")
    print("=" * 70)

    processor = FinancialDataProcessor()

    # Sample 10-K filing data
    sample_filing = {
        'document_id': 'AAPL-10K-2023',
        'document_type': '10-K',
        'company': 'Apple Inc.',
        'cik': '0000320193',
        'filing_date': datetime(2023, 11, 3),
        'content': """
        ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS

        Revenue for fiscal 2023 was $383.3 billion, a decrease of 3% compared to fiscal 2022.
        Net income for fiscal 2023 was $97.0 billion, representing a net margin of 25.3%.

        iPhone revenue increased 2% year-over-year to $200.6 billion.
        Services revenue grew 9% to $85.2 billion, driven by growth across all categories.

        ITEM 1A. RISK FACTORS

        The Company faces significant market risk related to foreign currency fluctuations.
        Supply chain disruptions could materially impact our ability to meet customer demand.
        Regulatory changes in data privacy could affect our Services business.
        """
    }

    # Process the filing
    processed = processor.process_10k_filing(sample_filing)

    print(f"\n✓ Document processed successfully!")
    print(f"  - Document ID: {processed.document_id}")
    print(f"  - Company: {processed.company}")
    print(f"  - Filing Date: {processed.filing_date}")
    print(f"  - Total Chunks: {len(processed.chunks)}")
    print(f"  - Total Entities: {len(processed.entities)}")
    print(f"  - Temporal References: {len(processed.temporal_references)}")

    print(f"\n✓ Sample chunks:")
    for i, chunk in enumerate(processed.chunks[:3], 1):
        print(f"\n  Chunk {i} ({chunk.get('section_type')}):")
        print(f"  {chunk.get('text', '')[:150]}...")

    print(f"\n✓ Sample entities:")
    for i, entity in enumerate(processed.entities[:5], 1):
        print(f"  {i}. {entity.get('type')}: {entity.get('text')}")

    return processed


def example_2_build_knowledge_graph(processed_doc):
    """
    Example 2: Build financial knowledge graph
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Building Knowledge Graph")
    print("=" * 70)

    kg = FinancialKnowledgeGraph()

    # Build graph from processed document
    filing_data = {
        'document_id': processed_doc.document_id,
        'company': processed_doc.company,
        'cik': processed_doc.cik,
        'filing_date': processed_doc.filing_date,
        'chunks': processed_doc.chunks
    }

    result = kg.construct_from_filing(filing_data)

    print(f"\n✓ Knowledge graph constructed successfully!")
    print(f"  - Nodes created: {len(result['nodes'])}")
    print(f"  - Edges created: {len(result['edges'])}")

    # Get statistics
    stats = kg.get_statistics()
    print(f"\n✓ Graph statistics:")
    print(f"  - Total nodes: {stats['total_nodes']}")
    print(f"  - Total edges: {stats['total_edges']}")
    print(f"  - Node types: {stats['node_types']}")
    print(f"  - Edge types: {stats['edge_types']}")

    # Query by entity
    company_id = f"company_{processed_doc.cik}"
    if company_id in kg.nodes:
        subgraph = kg.query_by_entity(company_id, max_depth=2)
        print(f"\n✓ Queried subgraph for {processed_doc.company}:")
        print(f"  - Related nodes: {len(subgraph['nodes'])}")
        print(f"  - Relationships: {len(subgraph['edges'])}")

    return kg


def example_3_rag_retrieval(processed_doc):
    """
    Example 3: RAG retrieval with temporal context
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: RAG Retrieval with Temporal Context")
    print("=" * 70)

    rag = TMMHybridRAG()

    # Add documents to RAG system
    documents = [
        {
            'document_id': processed_doc.document_id,
            'chunk_id': f"chunk_{i}",
            'text': chunk.get('text', ''),
            'metadata': chunk.get('source_metadata', {}),
            'temporal_context': {
                'date': processed_doc.filing_date
            }
        }
        for i, chunk in enumerate(processed_doc.chunks)
    ]

    rag.add_documents(documents)

    # Query with temporal context
    query = "What was Apple's revenue and how did it change?"

    temporal_context = TemporalContext(
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        period_type='annual'
    )

    results = rag.retrieve(
        query=query,
        temporal_context=temporal_context,
        k=5
    )

    print(f"\n✓ Query: {query}")
    print(f"✓ Retrieved {len(results)} relevant chunks:\n")

    for i, result in enumerate(results, 1):
        print(f"  {i}. [Score: {result.score:.3f}] {result.content[:120]}...")

    return results


def example_4_citation_generation(query, retrieved_docs):
    """
    Example 4: Generate answer with citations
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Citation-Aware Generation")
    print("=" * 70)

    generator = CitationAwareGenerator()

    # Convert retrieval results to dict format
    doc_dicts = [
        {
            'document_id': doc.document_id,
            'chunk_id': doc.chunk_id,
            'content': doc.content,
            'document_type': doc.metadata.get('document_type', '10-K'),
            'filing_date': datetime(2023, 11, 3),
            'credibility': 0.95,
            'source_type': doc.source_type
        }
        for doc in retrieved_docs
    ]

    # Generate response
    response = generator.generate_with_citations(
        query=query,
        retrieved_docs=doc_dicts,
        context={}
    )

    print(f"\n✓ Query: {query}\n")
    print(f"✓ Generated Answer:")
    print(f"  {response.text}\n")
    print(f"✓ Quality Metrics:")
    print(f"  - Confidence: {response.confidence:.2%}")
    print(f"  - Hallucination Score: {response.hallucination_score:.2%}")
    print(f"  - Source Count: {len(response.source_documents)}")
    print(f"\n✓ Citations ({len(response.citations)}):")

    for i, citation in enumerate(response.citations, 1):
        print(f"  [{i}] Source: {citation.source_type} | {citation.source_document}")
        print(f"      Excerpt: {citation.excerpt[:100]}...")
        print(f"      Confidence: {citation.confidence:.2%}")

    return response


def example_5_temporal_analysis():
    """
    Example 5: Temporal analysis and forecasting
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Temporal Analysis & Forecasting")
    print("=" * 70)

    analyzer = TemporalFinancialAnalyzer()

    # Create sample time series data
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    data = pd.DataFrame(index=dates)

    # Simulate financial metrics with trends
    np.random.seed(42)
    data['revenue'] = (np.linspace(100, 120, len(dates)) +
                       np.random.randn(len(dates)) * 2).cumsum() / 10
    data['net_income'] = (np.linspace(20, 28, len(dates)) +
                          np.random.randn(len(dates)) * 1).cumsum() / 10
    data['operating_margin'] = 25 + np.random.randn(len(dates)) * 0.5

    # Perform analysis
    analysis = analyzer.analyze_temporal_patterns(
        company="Apple Inc.",
        data=data,
        time_range=(datetime(2023, 1, 1), datetime(2023, 12, 31))
    )

    print(f"\n✓ Analyzed data for Apple Inc. (2023)")
    print(f"\n✓ Trend Analysis:")

    for period_name, trends in analysis['trends'].items():
        if trends:
            print(f"\n  {period_name.upper()}:")
            for metric, trend in list(trends.items())[:2]:
                print(f"    - {metric}: {trend.direction.upper()} " +
                      f"({trend.magnitude:+.1f}%) [confidence: {trend.confidence:.2f}]")

    print(f"\n✓ Anomaly Detection:")
    print(f"  - Total events detected: {len(analysis['events'])}")

    for i, event in enumerate(analysis['events'][:3], 1):
        print(f"  {i}. {event.event_type.upper()} on {event.timestamp.date()}")
        print(f"     Severity: {event.severity:.2f} | {event.description}")

    print(f"\n✓ Forecasts (30-day horizon):")
    for metric, forecast in list(analysis['forecasts'].items())[:2]:
        predictions = forecast.predictions[:7]  # Show first week
        print(f"\n  {metric.upper()}:")
        print(f"    Model: {forecast.model_name}")
        print(f"    First week predictions:")
        for date, value in predictions:
            print(f"      {date.date()}: {value:.2f}")

    return analysis


def example_6_compliance_check():
    """
    Example 6: Regulatory compliance checking
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Regulatory Compliance Checking")
    print("=" * 70)

    compliance_engine = ComplianceEngine()

    # Sample report data
    report_data = {
        'document_id': 'AAPL-10K-2023',
        'document_type': '10-K',
        'company': 'Apple Inc.',
        'content': """
        We, the undersigned officers, certify that this Annual Report on Form 10-K
        fully complies with the requirements of Section 13(a) of the Securities Exchange Act.

        Our internal controls over financial reporting are designed to provide reasonable
        assurance regarding the reliability of financial reporting and the preparation of
        financial statements for external purposes.

        The audit committee of the board of directors is composed entirely of independent
        directors and operates under a written charter.

        BUSINESS
        Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets...

        RISK FACTORS
        We face market volatility, supply chain risks, and regulatory compliance challenges...

        FINANCIAL DATA
        Consolidated Statements of Operations for fiscal years 2023, 2022, and 2021...

        MD&A
        Management's discussion of financial condition and results of operations...

        FINANCIAL STATEMENTS
        Consolidated financial statements and supplementary data...

        CONTROLS AND PROCEDURES
        Disclosure controls and procedures and internal control over financial reporting...
        """
    }

    # Perform compliance check
    compliance_report = compliance_engine.validate_financial_report(
        report_data,
        jurisdiction="US"
    )

    print(f"\n✓ Compliance Report Generated")
    print(f"  - Report ID: {compliance_report.report_id}")
    print(f"  - Document: {compliance_report.document_id}")
    print(f"  - Jurisdiction: {compliance_report.jurisdiction}")
    print(f"  - Status: {'✓ COMPLIANT' if compliance_report.compliant else '✗ NON-COMPLIANT'}")

    if compliance_report.violations:
        print(f"\n✗ Violations Found ({len(compliance_report.violations)}):")
        for violation in compliance_report.violations:
            print(f"  - [{violation.severity}] {violation.regulation}")
            print(f"    {violation.description}")
            print(f"    Recommendation: {violation.recommendation}")
    else:
        print(f"\n✓ No violations found")

    if compliance_report.warnings:
        print(f"\n⚠ Warnings ({len(compliance_report.warnings)}):")
        for warning in compliance_report.warnings[:3]:
            print(f"  - {warning.get('message')}")

    print(f"\n✓ Risk Assessment:")
    for risk_type, score in compliance_report.risk_scores.items():
        risk_level = "LOW" if score < 0.3 else "MEDIUM" if score < 0.6 else "HIGH"
        print(f"  - {risk_type}: {score:.2f} [{risk_level}]")

    return compliance_report


def main():
    """
    Run all examples
    """
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  FINANCIAL REPORT INTELLIGENCE SYSTEM - EXAMPLE USAGE".center(68) + "║")
    print("║" + "  Production-level Financial Analysis with RefRAG".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")

    # Example 1: Process document
    processed_doc = example_1_process_document()

    # Example 2: Build knowledge graph
    kg = example_2_build_knowledge_graph(processed_doc)

    # Example 3: RAG retrieval
    query = "What was Apple's revenue and how did it change?"
    retrieved_docs = example_3_rag_retrieval(processed_doc)

    # Example 4: Citation generation
    response = example_4_citation_generation(query, retrieved_docs)

    # Example 5: Temporal analysis
    analysis = example_5_temporal_analysis()

    # Example 6: Compliance check
    compliance_report = example_6_compliance_check()

    print("\n" + "=" * 70)
    print("✓ All examples completed successfully!")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Start the API server: uvicorn src.api.server:app --reload")
    print("  2. Access API docs: http://localhost:8000/docs")
    print("  3. Try the Python SDK for programmatic access")
    print("  4. Deploy with Docker: docker-compose up -d")
    print("\n")


if __name__ == "__main__":
    main()
