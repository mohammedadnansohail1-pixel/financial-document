"""
TMMHybridRAG: Temporal Multi-Modal Hybrid Retrieval-Augmented Generation
Integrates dense retrieval, graph-based retrieval, and temporal filtering
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Container for retrieval results"""
    document_id: str
    chunk_id: str
    content: str
    score: float
    source_type: str
    metadata: Dict[str, Any]
    temporal_context: Optional[Dict[str, Any]] = None


@dataclass
class TemporalContext:
    """Temporal context for queries"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    reference_date: Optional[datetime] = None
    period_type: Optional[str] = None  # 'daily', 'weekly', 'monthly', 'quarterly', 'annual'


class DenseRetriever:
    """
    Dense retrieval using embeddings
    """

    def __init__(self, model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.embeddings_cache = {}
        logger.info(f"Initialized DenseRetriever with model: {model_name}")

    def encode(self, text: str) -> np.ndarray:
        """
        Encode text to embedding vector
        In production, use actual embedding model
        """
        # Placeholder: return random embedding
        # In production, use sentence-transformers or similar
        if text in self.embeddings_cache:
            return self.embeddings_cache[text]

        # Simulate embedding (384 dimensions for all-MiniLM-L6-v2)
        embedding = np.random.randn(384).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)  # Normalize

        self.embeddings_cache[text] = embedding
        return embedding

    def search(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        k: int = 20
    ) -> List[RetrievalResult]:
        """
        Dense vector search
        """
        query_embedding = self.encode(query)

        results = []
        for doc in documents:
            # Get document embedding
            doc_text = doc.get('text', '')
            doc_embedding = self.encode(doc_text)

            # Calculate cosine similarity
            similarity = np.dot(query_embedding, doc_embedding)

            results.append(RetrievalResult(
                document_id=doc.get('document_id', ''),
                chunk_id=doc.get('chunk_id', ''),
                content=doc_text,
                score=float(similarity),
                source_type='dense',
                metadata=doc.get('metadata', {}),
                temporal_context=doc.get('temporal_context')
            ))

        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:k]


class GraphRetriever:
    """
    Graph-based retrieval using knowledge graph traversal
    """

    def __init__(self, graph_db_uri: str = "bolt://localhost:7687"):
        self.graph_db_uri = graph_db_uri
        self.graph = {}  # Placeholder for graph structure
        logger.info(f"Initialized GraphRetriever with URI: {graph_db_uri}")

    def query(self, cypher_query: str) -> List[Dict[str, Any]]:
        """
        Execute graph query
        In production, connect to Neo4j or similar
        """
        # Placeholder implementation
        logger.info(f"Executing graph query")
        return []

    def retrieve_by_entities(
        self,
        entities: List[str],
        temporal_context: Optional[TemporalContext] = None,
        max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents by entity traversal
        """
        results = []

        # Placeholder: In production, traverse actual graph
        for entity in entities:
            logger.debug(f"Traversing from entity: {entity}")

        return results


class TemporalFilter:
    """
    Filter and rank results based on temporal relevance
    """

    def __init__(self):
        self.temporal_decay_factor = 0.95

    def filter(
        self,
        results: List[RetrievalResult],
        temporal_context: TemporalContext
    ) -> List[RetrievalResult]:
        """
        Filter results based on temporal constraints
        """
        if not temporal_context.start_date and not temporal_context.end_date:
            return results

        filtered = []

        for result in results:
            doc_temporal = result.temporal_context
            if not doc_temporal:
                # Keep documents without temporal info but lower their score
                result.score *= 0.5
                filtered.append(result)
                continue

            doc_date = doc_temporal.get('date')
            if not doc_date:
                continue

            # Check if within date range
            if temporal_context.start_date and doc_date < temporal_context.start_date:
                continue
            if temporal_context.end_date and doc_date > temporal_context.end_date:
                continue

            # Apply temporal decay if reference date provided
            if temporal_context.reference_date:
                days_diff = abs((doc_date - temporal_context.reference_date).days)
                decay = self.temporal_decay_factor ** (days_diff / 30)
                result.score *= decay

            filtered.append(result)

        return filtered

    def apply_recency_boost(
        self,
        results: List[RetrievalResult],
        reference_date: datetime,
        boost_factor: float = 1.2
    ) -> List[RetrievalResult]:
        """
        Boost scores of more recent documents
        """
        for result in results:
            doc_temporal = result.temporal_context
            if not doc_temporal or not doc_temporal.get('date'):
                continue

            doc_date = doc_temporal['date']
            days_diff = (reference_date - doc_date).days

            if days_diff < 30:
                result.score *= boost_factor
            elif days_diff < 90:
                result.score *= (boost_factor * 0.75)

        return results


class FinancialReranker:
    """
    Domain-specific reranking for financial documents
    """

    def __init__(self):
        self.financial_terms = {
            'revenue', 'earnings', 'profit', 'loss', 'cash flow',
            'assets', 'liabilities', 'equity', 'margin', 'guidance'
        }

    def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        temporal_context: Optional[TemporalContext] = None
    ) -> List[RetrievalResult]:
        """
        Rerank results using financial domain knowledge
        """
        query_lower = query.lower()

        for result in results:
            # Boost documents with financial terms matching query
            boost = 1.0
            content_lower = result.content.lower()

            # Check for financial term matches
            for term in self.financial_terms:
                if term in query_lower and term in content_lower:
                    boost *= 1.1

            # Boost SEC filings over other sources
            if result.metadata.get('document_type') in ['10-K', '10-Q', '8-K']:
                boost *= 1.15

            # Boost quarterly earnings
            if result.metadata.get('section_type') == 'earnings_call':
                boost *= 1.1

            result.score *= boost

        # Sort by adjusted score
        results.sort(key=lambda x: x.score, reverse=True)

        return results


class QueryExpander:
    """
    Expand queries with financial context
    """

    def __init__(self):
        self.expansion_rules = {
            'revenue': ['sales', 'income', 'top line'],
            'profit': ['earnings', 'net income', 'bottom line'],
            'margin': ['profitability', 'operating margin', 'gross margin'],
        }

    def expand_query_with_context(
        self,
        query: str,
        temporal_context: Optional[TemporalContext] = None
    ) -> str:
        """
        Expand query with financial synonyms and temporal context
        """
        expanded_terms = [query]

        # Add financial synonyms
        query_lower = query.lower()
        for term, expansions in self.expansion_rules.items():
            if term in query_lower:
                expanded_terms.extend(expansions)

        # Add temporal context to query
        if temporal_context and temporal_context.period_type:
            expanded_terms.append(temporal_context.period_type)

        return " ".join(expanded_terms)


class TMMHybridRAG:
    """
    Main Temporal Multi-Modal Hybrid RAG system
    Combines dense retrieval, graph retrieval, and temporal filtering
    """

    def __init__(
        self,
        dense_model: str = 'sentence-transformers/all-MiniLM-L6-v2',
        graph_db_uri: str = "bolt://localhost:7687"
    ):
        self.dense_retriever = DenseRetriever(model=dense_model)
        self.graph_retriever = GraphRetriever(neo4j_uri=graph_db_uri)
        self.temporal_filter = TemporalFilter()
        self.reranker = FinancialReranker()
        self.query_expander = QueryExpander()

        # Document store (in production, use vector DB)
        self.document_store: List[Dict[str, Any]] = []

        logger.info("Initialized TMMHybridRAG system")

    def add_documents(self, documents: List[Dict[str, Any]]):
        """
        Add documents to the retrieval system
        """
        self.document_store.extend(documents)
        logger.info(f"Added {len(documents)} documents. Total: {len(self.document_store)}")

    def retrieve(
        self,
        query: str,
        temporal_context: Optional[TemporalContext] = None,
        k: int = 20,
        use_graph: bool = True,
        use_temporal: bool = True
    ) -> List[RetrievalResult]:
        """
        Multi-stage retrieval with temporal awareness
        """
        logger.info(f"Retrieving for query: {query[:100]}")

        # Stage 1: Query expansion
        expanded_query = self.query_expander.expand_query_with_context(
            query,
            temporal_context
        )
        logger.debug(f"Expanded query: {expanded_query}")

        # Stage 2: Dense retrieval
        dense_results = self.dense_retriever.search(
            expanded_query,
            self.document_store,
            k=k * 2  # Over-retrieve for fusion
        )
        logger.info(f"Dense retrieval returned {len(dense_results)} results")

        # Stage 3: Graph-based retrieval (if enabled)
        graph_results = []
        if use_graph:
            entities = self._extract_query_entities(query)
            if entities:
                graph_docs = self.graph_retriever.retrieve_by_entities(
                    entities,
                    temporal_context
                )
                # Convert to RetrievalResult format
                for doc in graph_docs:
                    graph_results.append(RetrievalResult(
                        document_id=doc.get('document_id', ''),
                        chunk_id=doc.get('chunk_id', ''),
                        content=doc.get('content', ''),
                        score=doc.get('score', 0.5),
                        source_type='graph',
                        metadata=doc.get('metadata', {}),
                        temporal_context=doc.get('temporal_context')
                    ))

        # Stage 4: Temporal filtering
        if use_temporal and temporal_context:
            dense_results = self.temporal_filter.filter(
                dense_results,
                temporal_context
            )
            if graph_results:
                graph_results = self.temporal_filter.filter(
                    graph_results,
                    temporal_context
                )
            logger.info(f"After temporal filtering: {len(dense_results)} dense, {len(graph_results)} graph")

        # Stage 5: Hybrid fusion
        fused_results = self._fuse_results(
            dense_results,
            graph_results,
            weights={'dense': 0.6, 'graph': 0.4}
        )
        logger.info(f"Fused results: {len(fused_results)}")

        # Stage 6: Domain-specific reranking
        reranked = self.reranker.rerank(
            query,
            fused_results,
            temporal_context
        )

        # Return top-k
        return reranked[:k]

    def _extract_query_entities(self, query: str) -> List[str]:
        """
        Extract entities from query
        In production, use spaCy or similar NER
        """
        # Placeholder: simple token extraction
        entities = []

        # Look for company names (capitalized words)
        import re
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        entities.extend(words)

        return entities

    def _fuse_results(
        self,
        dense_results: List[RetrievalResult],
        graph_results: List[RetrievalResult],
        weights: Dict[str, float]
    ) -> List[RetrievalResult]:
        """
        Fuse results from different retrievers using weighted combination
        """
        # Collect all unique documents
        doc_scores: Dict[str, RetrievalResult] = {}

        # Add dense results
        for result in dense_results:
            key = f"{result.document_id}_{result.chunk_id}"
            if key not in doc_scores:
                result.score *= weights['dense']
                doc_scores[key] = result
            else:
                doc_scores[key].score += result.score * weights['dense']

        # Add graph results
        for result in graph_results:
            key = f"{result.document_id}_{result.chunk_id}"
            if key not in doc_scores:
                result.score *= weights['graph']
                doc_scores[key] = result
            else:
                doc_scores[key].score += result.score * weights['graph']

        # Convert back to list and sort
        fused = list(doc_scores.values())
        fused.sort(key=lambda x: x.score, reverse=True)

        return fused

    def retrieve_temporal_range(
        self,
        query: str,
        start_date: datetime,
        end_date: datetime,
        k: int = 20
    ) -> List[RetrievalResult]:
        """
        Retrieve documents within a specific temporal range
        """
        temporal_context = TemporalContext(
            start_date=start_date,
            end_date=end_date
        )

        return self.retrieve(
            query,
            temporal_context=temporal_context,
            k=k
        )

    def retrieve_with_recency_bias(
        self,
        query: str,
        reference_date: datetime,
        k: int = 20
    ) -> List[RetrievalResult]:
        """
        Retrieve with bias towards recent documents
        """
        temporal_context = TemporalContext(
            reference_date=reference_date
        )

        results = self.retrieve(
            query,
            temporal_context=temporal_context,
            k=k * 2
        )

        # Apply recency boost
        results = self.temporal_filter.apply_recency_boost(
            results,
            reference_date
        )

        # Re-sort and return top-k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:k]
