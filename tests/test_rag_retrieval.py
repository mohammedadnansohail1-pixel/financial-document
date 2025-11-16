"""
Unit tests for RAG retrieval system
"""

import pytest
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.retrieval.tmm_hybrid_rag import (
    TMMHybridRAG,
    TemporalContext,
    DenseRetriever,
    TemporalFilter,
    RetrievalResult
)


class TestDenseRetriever:
    """Test dense retrieval functionality"""

    def setup_method(self):
        """Setup for each test"""
        self.retriever = DenseRetriever()

    def test_encoding(self):
        """Test text encoding"""
        text = "Apple reported revenue of $119.6 billion"
        embedding = self.retriever.encode(text)

        assert embedding is not None
        assert len(embedding) == 384  # MiniLM dimension
        assert embedding.dtype.name.startswith('float')

    def test_search(self):
        """Test dense search"""
        documents = [
            {
                'document_id': 'doc1',
                'chunk_id': 'chunk1',
                'text': 'Apple revenue grew 10% year over year',
                'metadata': {}
            },
            {
                'document_id': 'doc2',
                'chunk_id': 'chunk2',
                'text': 'Microsoft earnings exceeded expectations',
                'metadata': {}
            }
        ]

        query = "Apple financial performance"
        results = self.retriever.search(query, documents, k=2)

        assert len(results) == 2
        assert all(isinstance(r, RetrievalResult) for r in results)
        assert results[0].score >= results[1].score  # Sorted by score


class TestTemporalFilter:
    """Test temporal filtering"""

    def setup_method(self):
        """Setup for each test"""
        self.filter = TemporalFilter()

    def test_temporal_filtering(self):
        """Test filtering by date range"""
        results = [
            RetrievalResult(
                document_id='doc1',
                chunk_id='chunk1',
                content='Test content 1',
                score=0.9,
                source_type='dense',
                metadata={},
                temporal_context={'date': datetime(2023, 1, 15)}
            ),
            RetrievalResult(
                document_id='doc2',
                chunk_id='chunk2',
                content='Test content 2',
                score=0.8,
                source_type='dense',
                metadata={},
                temporal_context={'date': datetime(2023, 6, 15)}
            ),
            RetrievalResult(
                document_id='doc3',
                chunk_id='chunk3',
                content='Test content 3',
                score=0.7,
                source_type='dense',
                metadata={},
                temporal_context={'date': datetime(2024, 1, 15)}
            )
        ]

        temporal_context = TemporalContext(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31)
        )

        filtered = self.filter.filter(results, temporal_context)

        assert len(filtered) == 2
        assert all(
            temporal_context.start_date <= r.temporal_context['date'] <= temporal_context.end_date
            for r in filtered
        )

    def test_recency_boost(self):
        """Test recency boosting"""
        results = [
            RetrievalResult(
                document_id='doc1',
                chunk_id='chunk1',
                content='Old content',
                score=0.5,
                source_type='dense',
                metadata={},
                temporal_context={'date': datetime(2023, 1, 1)}
            ),
            RetrievalResult(
                document_id='doc2',
                chunk_id='chunk2',
                content='Recent content',
                score=0.5,
                source_type='dense',
                metadata={},
                temporal_context={'date': datetime(2023, 11, 1)}
            )
        ]

        reference_date = datetime(2023, 12, 1)
        boosted = self.filter.apply_recency_boost(results, reference_date)

        # Recent document should have higher score after boost
        assert boosted[1].score > boosted[0].score


class TestTMMHybridRAG:
    """Test hybrid RAG system"""

    def setup_method(self):
        """Setup for each test"""
        self.rag = TMMHybridRAG()

    def test_add_documents(self):
        """Test document addition"""
        documents = [
            {
                'document_id': 'test1',
                'chunk_id': 'chunk1',
                'text': 'Test document 1',
                'metadata': {},
                'temporal_context': {'date': datetime(2023, 1, 1)}
            }
        ]

        initial_count = len(self.rag.document_store)
        self.rag.add_documents(documents)

        assert len(self.rag.document_store) == initial_count + 1

    def test_retrieval(self):
        """Test basic retrieval"""
        documents = [
            {
                'document_id': 'test1',
                'chunk_id': 'chunk1',
                'text': 'Apple revenue increased by 10 percent',
                'metadata': {'document_type': '10-K'},
                'temporal_context': {'date': datetime(2023, 1, 1)}
            },
            {
                'document_id': 'test2',
                'chunk_id': 'chunk2',
                'text': 'Microsoft cloud services grew significantly',
                'metadata': {'document_type': '10-K'},
                'temporal_context': {'date': datetime(2023, 1, 1)}
            }
        ]

        self.rag.add_documents(documents)

        results = self.rag.retrieve(
            query="Apple financial results",
            k=2
        )

        assert len(results) <= 2
        assert all(isinstance(r, RetrievalResult) for r in results)

    def test_temporal_retrieval(self):
        """Test retrieval with temporal context"""
        documents = [
            {
                'document_id': 'old',
                'chunk_id': 'chunk1',
                'text': 'Old financial data',
                'metadata': {},
                'temporal_context': {'date': datetime(2022, 1, 1)}
            },
            {
                'document_id': 'new',
                'chunk_id': 'chunk2',
                'text': 'Recent financial data',
                'metadata': {},
                'temporal_context': {'date': datetime(2023, 12, 1)}
            }
        ]

        self.rag.add_documents(documents)

        temporal_context = TemporalContext(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31)
        )

        results = self.rag.retrieve(
            query="financial data",
            temporal_context=temporal_context,
            k=5
        )

        # Should only return documents in the date range
        for result in results:
            if result.temporal_context:
                date = result.temporal_context.get('date')
                if date:
                    assert temporal_context.start_date <= date <= temporal_context.end_date


# Pytest fixtures
@pytest.fixture
def sample_documents():
    """Sample documents for testing"""
    return [
        {
            'document_id': 'AAPL-10K-2023',
            'chunk_id': 'chunk1',
            'text': 'Apple Inc. reported revenue of $383.3 billion for fiscal year 2023, representing a decrease of 3% compared to fiscal year 2022.',
            'metadata': {
                'document_type': '10-K',
                'company': 'Apple Inc.',
                'cik': '0000320193'
            },
            'temporal_context': {
                'date': datetime(2023, 11, 3)
            }
        },
        {
            'document_id': 'AAPL-10K-2023',
            'chunk_id': 'chunk2',
            'text': 'Net income for fiscal 2023 was $97.0 billion, representing a net margin of 25.3%.',
            'metadata': {
                'document_type': '10-K',
                'company': 'Apple Inc.',
                'cik': '0000320193'
            },
            'temporal_context': {
                'date': datetime(2023, 11, 3)
            }
        }
    ]


@pytest.fixture
def rag_system(sample_documents):
    """RAG system with sample documents"""
    rag = TMMHybridRAG()
    rag.add_documents(sample_documents)
    return rag


def test_end_to_end_retrieval(rag_system):
    """Test end-to-end retrieval"""
    query = "What was Apple's revenue in 2023?"

    results = rag_system.retrieve(query, k=2)

    assert len(results) > 0
    assert any('revenue' in r.content.lower() for r in results)
    assert any('383.3' in r.content or '97.0' in r.content for r in results)


def test_query_expansion():
    """Test query expansion"""
    rag = TMMHybridRAG()

    original_query = "revenue growth"
    expanded = rag.query_expander.expand_query_with_context(original_query)

    assert 'revenue' in expanded.lower()
    # Should include synonyms
    assert any(word in expanded.lower() for word in ['sales', 'income', 'top line'])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
