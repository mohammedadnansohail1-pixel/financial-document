"""
FastAPI Server for Financial Report Intelligence System
Provides REST API endpoints for analysis, retrieval, and compliance checking
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Query, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Import core components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_processing.financial_data_processor import FinancialDataProcessor
from retrieval.tmm_hybrid_rag import TMMHybridRAG, TemporalContext
from knowledge_graph.financial_kg import FinancialKnowledgeGraph
from generation.citation_aware_generator import CitationAwareGenerator
from temporal.temporal_analyzer import TemporalFinancialAnalyzer
from compliance.compliance_engine import ComplianceEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Financial Report Intelligence API",
    description="Production-level Financial Analysis with RefRAG",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core components
data_processor = FinancialDataProcessor()
rag_system = TMMHybridRAG()
knowledge_graph = FinancialKnowledgeGraph()
generator = CitationAwareGenerator()
temporal_analyzer = TemporalFinancialAnalyzer()
compliance_engine = ComplianceEngine()


# Request/Response Models
class QueryRequest(BaseModel):
    query: str = Field(..., description="User question or query")
    temporal_context: Optional[Dict[str, Any]] = Field(None, description="Temporal context")
    k: int = Field(20, description="Number of results to retrieve")
    use_citation: bool = Field(True, description="Include citations in response")


class AnalysisResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]]
    confidence: float
    hallucination_score: float
    source_count: int
    metadata: Dict[str, Any]


class DocumentUploadRequest(BaseModel):
    document_id: str
    document_type: str
    company: str
    cik: Optional[str] = None
    filing_date: str
    content: str


class ComplianceCheckRequest(BaseModel):
    document_id: str
    document_type: str
    company: str
    content: str
    jurisdiction: str = "US"


class TemporalAnalysisRequest(BaseModel):
    company: str
    start_date: str
    end_date: str
    metrics: List[str]


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Financial Report Intelligence API",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "data_processor": "operational",
            "rag_system": "operational",
            "knowledge_graph": "operational",
            "generator": "operational"
        }
    }


@app.post("/api/v1/query", response_model=AnalysisResponse)
async def query_financial_data(request: QueryRequest):
    """
    Query financial data with RAG
    """
    try:
        logger.info(f"Processing query: {request.query}")

        # Build temporal context
        temporal_context = None
        if request.temporal_context:
            temporal_context = TemporalContext(
                start_date=datetime.fromisoformat(request.temporal_context.get('start_date')) if request.temporal_context.get('start_date') else None,
                end_date=datetime.fromisoformat(request.temporal_context.get('end_date')) if request.temporal_context.get('end_date') else None,
                reference_date=datetime.fromisoformat(request.temporal_context.get('reference_date')) if request.temporal_context.get('reference_date') else None,
                period_type=request.temporal_context.get('period_type')
            )

        # Retrieve relevant documents
        retrieved_docs = rag_system.retrieve(
            query=request.query,
            temporal_context=temporal_context,
            k=request.k
        )

        logger.info(f"Retrieved {len(retrieved_docs)} documents")

        # Convert RetrievalResult to dict format expected by generator
        doc_dicts = [
            {
                'document_id': doc.document_id,
                'chunk_id': doc.chunk_id,
                'content': doc.content,
                'document_type': doc.metadata.get('document_type', ''),
                'filing_date': doc.temporal_context.get('date') if doc.temporal_context else None,
                'credibility': 0.9,  # Would come from actual scoring
                'source_type': doc.source_type
            }
            for doc in retrieved_docs
        ]

        # Generate response with citations
        if request.use_citation:
            response = generator.generate_with_citations(
                query=request.query,
                retrieved_docs=doc_dicts,
                context={'temporal_context': temporal_context}
            )

            return AnalysisResponse(
                answer=response.text,
                citations=[
                    {
                        'citation_id': c.citation_id,
                        'source_document': c.source_document,
                        'source_type': c.source_type,
                        'excerpt': c.excerpt,
                        'confidence': c.confidence
                    }
                    for c in response.citations
                ],
                confidence=response.confidence,
                hallucination_score=response.hallucination_score,
                source_count=len(response.source_documents),
                metadata=response.metadata
            )
        else:
            # Simple retrieval without generation
            return AnalysisResponse(
                answer="Retrieved documents (generation disabled)",
                citations=[],
                confidence=1.0,
                hallucination_score=0.0,
                source_count=len(retrieved_docs),
                metadata={'retrieved_docs': len(retrieved_docs)}
            )

    except Exception as e:
        logger.error(f"Query processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/documents/upload")
async def upload_document(request: DocumentUploadRequest):
    """
    Upload and process a financial document
    """
    try:
        logger.info(f"Uploading document: {request.document_id}")

        # Process document
        filing_data = {
            'document_id': request.document_id,
            'document_type': request.document_type,
            'company': request.company,
            'cik': request.cik,
            'filing_date': datetime.fromisoformat(request.filing_date),
            'content': request.content
        }

        # Process based on document type
        if request.document_type in ['10-K', '10-Q', '8-K']:
            processed = data_processor.process_10k_filing(filing_data)
        elif request.document_type == 'earnings_call':
            processed = data_processor.process_earnings_call(filing_data)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported document type: {request.document_type}")

        # Add to RAG system
        chunks_for_rag = [
            {
                'document_id': processed.document_id,
                'chunk_id': f"chunk_{i}",
                'text': chunk.get('text', ''),
                'metadata': chunk.get('source_metadata', {}),
                'temporal_context': {
                    'date': processed.filing_date
                }
            }
            for i, chunk in enumerate(processed.chunks)
        ]

        rag_system.add_documents(chunks_for_rag)

        # Build knowledge graph
        kg_result = knowledge_graph.construct_from_filing({
            'document_id': processed.document_id,
            'company': processed.company,
            'cik': processed.cik,
            'filing_date': processed.filing_date,
            'chunks': processed.chunks
        })

        return {
            'status': 'success',
            'document_id': request.document_id,
            'chunks_processed': len(processed.chunks),
            'entities_extracted': len(processed.entities),
            'kg_nodes_created': len(kg_result.get('nodes', [])),
            'kg_edges_created': len(kg_result.get('edges', []))
        }

    except Exception as e:
        logger.error(f"Document upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/compliance/check")
async def check_compliance(request: ComplianceCheckRequest):
    """
    Check compliance of financial report
    """
    try:
        logger.info(f"Checking compliance for document: {request.document_id}")

        report_data = {
            'document_id': request.document_id,
            'document_type': request.document_type,
            'company': request.company,
            'content': request.content
        }

        compliance_report = compliance_engine.validate_financial_report(
            report_data,
            jurisdiction=request.jurisdiction
        )

        # Generate summary
        summary = compliance_engine.generate_compliance_summary(compliance_report)

        return {
            'report_id': compliance_report.report_id,
            'document_id': compliance_report.document_id,
            'compliant': compliance_report.compliant,
            'violations': [
                {
                    'violation_id': v.violation_id,
                    'regulation': v.regulation,
                    'severity': v.severity,
                    'description': v.description,
                    'recommendation': v.recommendation
                }
                for v in compliance_report.violations
            ],
            'warnings': compliance_report.warnings,
            'risk_scores': compliance_report.risk_scores,
            'summary': summary,
            'timestamp': compliance_report.timestamp.isoformat()
        }

    except Exception as e:
        logger.error(f"Compliance check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/temporal/analyze")
async def temporal_analysis(request: TemporalAnalysisRequest):
    """
    Perform temporal analysis on financial data
    """
    try:
        logger.info(f"Performing temporal analysis for {request.company}")

        # Mock time series data
        # In production, fetch from database
        import pandas as pd
        import numpy as np

        dates = pd.date_range(
            start=request.start_date,
            end=request.end_date,
            freq='D'
        )

        data = pd.DataFrame(index=dates)
        for metric in request.metrics:
            data[metric] = np.random.randn(len(dates)).cumsum() + 100

        # Perform analysis
        analysis = temporal_analyzer.analyze_temporal_patterns(
            company=request.company,
            data=data,
            time_range=(
                datetime.fromisoformat(request.start_date),
                datetime.fromisoformat(request.end_date)
            )
        )

        # Format response
        return {
            'company': request.company,
            'time_range': {
                'start': request.start_date,
                'end': request.end_date
            },
            'trends': {
                period: {
                    metric: {
                        'direction': trend.direction,
                        'magnitude': trend.magnitude,
                        'confidence': trend.confidence
                    }
                    for metric, trend in trends.items()
                }
                for period, trends in analysis['trends'].items()
            },
            'events': [
                {
                    'event_id': event.event_id,
                    'event_type': event.event_type,
                    'timestamp': event.timestamp.isoformat(),
                    'severity': event.severity,
                    'description': event.description
                }
                for event in analysis['events']
            ],
            'forecasts': {
                metric: {
                    'predictions': [
                        {'date': date.isoformat(), 'value': value}
                        for date, value in forecast.predictions[:7]  # First week
                    ],
                    'horizon_days': forecast.horizon_days,
                    'model': forecast.model_name
                }
                for metric, forecast in analysis['forecasts'].items()
            }
        }

    except Exception as e:
        logger.error(f"Temporal analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/knowledge-graph/stats")
async def get_kg_stats():
    """
    Get knowledge graph statistics
    """
    try:
        stats = knowledge_graph.get_statistics()

        return {
            'total_nodes': stats['total_nodes'],
            'total_edges': stats['total_edges'],
            'node_types': stats['node_types'],
            'edge_types': stats['edge_types']
        }

    except Exception as e:
        logger.error(f"KG stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/knowledge-graph/entity/{entity_id}")
async def query_entity(
    entity_id: str,
    max_depth: int = Query(2, description="Maximum traversal depth")
):
    """
    Query knowledge graph by entity
    """
    try:
        result = knowledge_graph.query_by_entity(
            entity_id=entity_id,
            max_depth=max_depth
        )

        return {
            'entity_id': entity_id,
            'nodes': [
                {
                    'node_id': node.node_id,
                    'node_type': node.node_type,
                    'properties': node.properties
                }
                for node in result['nodes']
            ],
            'edges': [
                {
                    'edge_id': edge.edge_id,
                    'source': edge.source_id,
                    'target': edge.target_id,
                    'relationship': edge.relationship,
                    'confidence': edge.confidence
                }
                for edge in result['edges']
            ]
        }

    except Exception as e:
        logger.error(f"Entity query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/system/stats")
async def get_system_stats():
    """
    Get system statistics
    """
    return {
        'documents_indexed': len(rag_system.document_store),
        'knowledge_graph': knowledge_graph.get_statistics(),
        'timestamp': datetime.now().isoformat()
    }


# Run server
if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
