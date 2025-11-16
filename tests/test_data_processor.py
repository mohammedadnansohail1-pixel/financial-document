"""
Unit tests for financial data processor
"""

import pytest
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_processing.financial_data_processor import (
    FinancialDataProcessor,
    TextProcessor,
    TemporalExtractor,
    FinancialEntityExtractor
)


class TestTextProcessor:
    """Test text processing functionality"""

    def setup_method(self):
        """Setup for each test"""
        self.processor = TextProcessor()

    def test_chunking(self):
        """Test text chunking"""
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."

        chunks = self.processor.chunk_by_semantic_boundaries(
            text,
            max_tokens=50
        )

        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert all(len(chunk.split()) <= 50 * 1.3 for chunk in chunks)  # Rough token estimate

    def test_sentence_extraction(self):
        """Test sentence extraction"""
        text = "First sentence. Second sentence! Third sentence?"

        sentences = self.processor.extract_sentences(text)

        assert len(sentences) == 3
        assert "First sentence" in sentences[0]


class TestTemporalExtractor:
    """Test temporal extraction"""

    def setup_method(self):
        """Setup for each test"""
        self.extractor = TemporalExtractor()

    def test_date_extraction(self):
        """Test extracting dates"""
        text = "The company reported results on 12/31/2023 and for Q1 2024."

        refs = self.extractor.extract_temporal_context(text)

        assert len(refs) > 0
        assert any('2023' in ref['text'] for ref in refs)
        assert any('Q1' in ref['text'] for ref in refs)

    def test_temporal_classification(self):
        """Test classifying temporal references"""
        fiscal_ref = "Q4 2023"
        date_ref = "2023-12-31"

        fiscal_type = self.extractor._classify_temporal_ref(fiscal_ref)
        date_type = self.extractor._classify_temporal_ref(date_ref)

        assert fiscal_type == 'fiscal_period'
        assert date_type == 'specific_date'


class TestFinancialEntityExtractor:
    """Test financial entity extraction"""

    def setup_method(self):
        """Setup for each test"""
        self.extractor = FinancialEntityExtractor()

    def test_monetary_extraction(self):
        """Test extracting monetary amounts"""
        text = "Revenue was $119.6 million and profit was $2.3 billion."

        entities = self.extractor.extract_financial_entities(text)

        monetary = [e for e in entities if e['type'] == 'monetary_amount']

        assert len(monetary) >= 2
        assert any('119.6' in e['text'] for e in monetary)
        assert any('2.3' in e['text'] for e in monetary)

    def test_percentage_extraction(self):
        """Test extracting percentages"""
        text = "Growth was 15.5% and margin improved to 25.3%."

        entities = self.extractor.extract_financial_entities(text)

        percentages = [e for e in entities if e['type'] == 'percentage']

        assert len(percentages) >= 2
        assert any(e['value'] == 15.5 for e in percentages)
        assert any(e['value'] == 25.3 for e in percentages)

    def test_monetary_parsing(self):
        """Test parsing monetary values"""
        assert self.extractor._parse_monetary_value("$100 million") == pytest.approx(100e6)
        assert self.extractor._parse_monetary_value("$2.5 billion") == pytest.approx(2.5e9)
        assert self.extractor._parse_monetary_value("$50 thousand") == pytest.approx(50e3)


class TestFinancialDataProcessor:
    """Test main data processor"""

    def setup_method(self):
        """Setup for each test"""
        self.processor = FinancialDataProcessor()

    def test_10k_processing(self):
        """Test processing 10-K filing"""
        filing = {
            'document_id': 'TEST-10K-2023',
            'document_type': '10-K',
            'company': 'Test Corp',
            'cik': '0001234567',
            'filing_date': datetime(2023, 12, 31),
            'content': """
            ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS

            Revenue for fiscal 2023 was $500 million, an increase of 10% year-over-year.
            Net income was $100 million, representing a 20% margin.

            ITEM 1A. RISK FACTORS

            The company faces market risk from economic conditions.
            Supply chain disruptions could impact operations.
            """
        }

        processed = self.processor.process_10k_filing(filing)

        assert processed.document_id == 'TEST-10K-2023'
        assert processed.company == 'Test Corp'
        assert len(processed.chunks) > 0
        assert len(processed.entities) > 0

    def test_earnings_call_processing(self):
        """Test processing earnings call"""
        transcript = {
            'document_id': 'TEST-EC-Q1-2024',
            'document_type': 'earnings_call',
            'company': 'Test Corp',
            'date': datetime(2024, 1, 31),
            'quarter': 'Q1 2024',
            'content': """
            We delivered strong results in Q1 2024 with revenue of $150 million,
            up 15% year-over-year. Our guidance for Q2 is $160 million.
            """
        }

        processed = self.processor.process_earnings_call(transcript)

        assert processed.document_type == 'earnings_call'
        assert processed.company == 'Test Corp'
        assert len(processed.chunks) > 0


@pytest.fixture
def sample_filing():
    """Sample filing for testing"""
    return {
        'document_id': 'AAPL-10K-2023',
        'document_type': '10-K',
        'company': 'Apple Inc.',
        'cik': '0000320193',
        'filing_date': datetime(2023, 11, 3),
        'content': """
        ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS

        Total net sales decreased 3% or $11.0 billion to $383.3 billion in 2023.
        Net income decreased to $97.0 billion in 2023.

        ITEM 1A. RISK FACTORS

        We face market risk related to foreign currency fluctuations.
        """
    }


def test_full_processing_pipeline(sample_filing):
    """Test complete processing pipeline"""
    processor = FinancialDataProcessor()

    processed = processor.process_10k_filing(sample_filing)

    # Check basic structure
    assert processed.document_id == 'AAPL-10K-2023'
    assert processed.company == 'Apple Inc.'
    assert processed.document_type == '10-K'

    # Check chunks were created
    assert len(processed.chunks) > 0

    # Check entities were extracted
    assert len(processed.entities) > 0

    # Verify financial entities
    monetary_entities = [e for e in processed.entities if e.get('type') == 'monetary_amount']
    assert len(monetary_entities) > 0

    # Verify sections were identified
    section_types = set(chunk.get('section_type') for chunk in processed.chunks)
    assert 'mda' in section_types or 'risk_factors' in section_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
