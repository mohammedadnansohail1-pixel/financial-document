"""
Multi-Modal Financial Data Processor
Handles SEC filings, earnings calls, market data, and news feeds
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ProcessedDocument:
    """Container for processed financial document"""
    document_id: str
    document_type: str
    company: str
    cik: Optional[str]
    filing_date: datetime
    chunks: List[Dict[str, Any]]
    entities: List[Dict[str, Any]]
    temporal_references: List[Dict[str, Any]]
    metadata: Dict[str, Any]


@dataclass
class FinancialTable:
    """Container for financial table data"""
    table_id: str
    title: str
    structured_data: pd.DataFrame
    time_periods: List[str]
    summary: str
    metrics: Dict[str, Any]
    source_metadata: Dict[str, Any]


class TextProcessor:
    """Process textual content from financial documents"""

    def __init__(self, max_chunk_size: int = 512):
        self.max_chunk_size = max_chunk_size

    def chunk_by_semantic_boundaries(
        self,
        text: str,
        preserve_context: bool = True,
        max_tokens: int = 512
    ) -> List[str]:
        """
        Chunk text by semantic boundaries (paragraphs, sections)
        """
        # Split by paragraphs
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            # Rough token estimation (words * 1.3)
            estimated_tokens = len(para.split()) * 1.3
            current_tokens = len(current_chunk.split()) * 1.3

            if current_tokens + estimated_tokens <= max_tokens:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def extract_sentences(self, text: str) -> List[str]:
        """Extract sentences from text"""
        # Simple sentence splitting
        sentence_pattern = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_pattern, text)
        return [s.strip() for s in sentences if s.strip()]


class TableExtractor:
    """Extract and process financial tables"""

    def extract(self, table_html: str) -> pd.DataFrame:
        """
        Extract table from HTML/structured format
        """
        try:
            # For now, simple HTML table parsing
            # In production, use camelot or tabula for PDFs
            df = pd.read_html(table_html)[0]
            return df
        except Exception as e:
            logger.error(f"Table extraction error: {e}")
            return pd.DataFrame()

    def normalize_table(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize table structure and values
        """
        # Remove empty rows/columns
        df = df.dropna(how='all', axis=0)
        df = df.dropna(how='all', axis=1)

        # Clean column names
        df.columns = [str(col).strip() for col in df.columns]

        return df


class TemporalExtractor:
    """Extract temporal references from financial text"""

    def __init__(self):
        self.date_patterns = [
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',  # MM/DD/YYYY
            r'\b\d{4}-\d{2}-\d{2}\b',  # YYYY-MM-DD
            r'\b(?:Q[1-4]|FY)\s*\d{4}\b',  # Q1 2024, FY 2024
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b'
        ]

    def extract_temporal_context(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract temporal references from text
        """
        temporal_refs = []

        for pattern in self.date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                temporal_refs.append({
                    'text': match.group(),
                    'start_pos': match.start(),
                    'end_pos': match.end(),
                    'type': self._classify_temporal_ref(match.group())
                })

        return temporal_refs

    def _classify_temporal_ref(self, ref: str) -> str:
        """Classify type of temporal reference"""
        if 'Q' in ref or 'FY' in ref:
            return 'fiscal_period'
        elif re.match(r'\d{4}-\d{2}-\d{2}', ref):
            return 'specific_date'
        elif re.match(r'\d{1,2}/\d{1,2}/\d{2,4}', ref):
            return 'specific_date'
        else:
            return 'month_year'


class FinancialEntityExtractor:
    """Extract financial entities from text"""

    def __init__(self):
        self.metric_patterns = {
            'revenue': r'\$\s*[\d,.]+\s*(?:million|billion|M|B)',
            'percentage': r'\d+\.?\d*%',
            'eps': r'EPS\s+of\s+\$[\d.]+',
            'margin': r'(?:gross|operating|net)\s+margin',
        }

    def extract_financial_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract financial entities (metrics, amounts, etc.)
        """
        entities = []

        # Extract monetary amounts
        money_pattern = r'\$\s*[\d,.]+\s*(?:million|billion|thousand|M|B|K)?'
        for match in re.finditer(money_pattern, text):
            entities.append({
                'type': 'monetary_amount',
                'text': match.group(),
                'start_pos': match.start(),
                'end_pos': match.end(),
                'value': self._parse_monetary_value(match.group())
            })

        # Extract percentages
        pct_pattern = r'\d+\.?\d*%'
        for match in re.finditer(pct_pattern, text):
            entities.append({
                'type': 'percentage',
                'text': match.group(),
                'start_pos': match.start(),
                'end_pos': match.end(),
                'value': float(match.group().rstrip('%'))
            })

        # Extract company mentions (simplified)
        # In production, use spaCy or similar NER

        return entities

    def _parse_monetary_value(self, text: str) -> float:
        """Parse monetary value to float"""
        # Remove $ and spaces
        text = text.replace('$', '').replace(' ', '').upper()

        # Extract number
        num_match = re.search(r'[\d,.]+', text)
        if not num_match:
            return 0.0

        num = float(num_match.group().replace(',', ''))

        # Apply multiplier
        if 'B' in text or 'BILLION' in text:
            num *= 1e9
        elif 'M' in text or 'MILLION' in text:
            num *= 1e6
        elif 'K' in text or 'THOUSAND' in text:
            num *= 1e3

        return num


class FinancialDataProcessor:
    """
    Main processor for multi-modal financial data
    """

    def __init__(self):
        self.text_processor = TextProcessor()
        self.table_extractor = TableExtractor()
        self.temporal_extractor = TemporalExtractor()
        self.entity_extractor = FinancialEntityExtractor()

    def process_10k_filing(self, filing: Dict[str, Any]) -> ProcessedDocument:
        """
        Process SEC 10-K filing with element-based chunking
        """
        logger.info(f"Processing 10-K filing for {filing.get('company')}")

        # Extract different elements
        elements = self._extract_document_elements(filing)

        all_chunks = []
        all_entities = []
        all_temporal_refs = []

        # Process Management Discussion & Analysis
        for section in elements.get('mda', []):
            chunks = self.text_processor.chunk_by_semantic_boundaries(
                section,
                preserve_context=True,
                max_tokens=512
            )

            for chunk in chunks:
                # Extract temporal references
                temporal_refs = self.temporal_extractor.extract_temporal_context(chunk)
                all_temporal_refs.extend(temporal_refs)

                # Extract financial entities
                entities = self.entity_extractor.extract_financial_entities(chunk)
                all_entities.extend(entities)

                all_chunks.append({
                    'text': chunk,
                    'chunk_type': 'narrative',
                    'section_type': 'mda',
                    'entities': entities,
                    'temporal_context': temporal_refs,
                    'source_metadata': {
                        'filing_date': filing.get('filing_date'),
                        'company': filing.get('company'),
                        'cik': filing.get('cik'),
                        'document_id': filing.get('document_id')
                    }
                })

        # Process risk factors
        for section in elements.get('risk_factors', []):
            chunks = self.text_processor.chunk_by_semantic_boundaries(
                section,
                max_tokens=512
            )

            for chunk in chunks:
                all_chunks.append({
                    'text': chunk,
                    'chunk_type': 'narrative',
                    'section_type': 'risk_factors',
                    'entities': self.entity_extractor.extract_financial_entities(chunk),
                    'temporal_context': self.temporal_extractor.extract_temporal_context(chunk),
                    'source_metadata': {
                        'filing_date': filing.get('filing_date'),
                        'company': filing.get('company'),
                        'cik': filing.get('cik'),
                        'document_id': filing.get('document_id')
                    }
                })

        # Process financial tables
        for table in elements.get('tables', []):
            table_data = self._process_financial_table(table, filing)
            all_chunks.append({
                'text': table_data['summary'],
                'chunk_type': 'table',
                'section_type': 'financials',
                'structured_data': table_data['structured_data'],
                'metrics': table_data['metrics'],
                'source_metadata': {
                    'filing_date': filing.get('filing_date'),
                    'company': filing.get('company'),
                    'cik': filing.get('cik'),
                    'document_id': filing.get('document_id')
                }
            })

        return ProcessedDocument(
            document_id=filing.get('document_id', ''),
            document_type='10-K',
            company=filing.get('company', ''),
            cik=filing.get('cik'),
            filing_date=filing.get('filing_date', datetime.now()),
            chunks=all_chunks,
            entities=all_entities,
            temporal_references=all_temporal_refs,
            metadata={
                'total_chunks': len(all_chunks),
                'total_entities': len(all_entities),
                'sections_processed': list(elements.keys())
            }
        )

    def _extract_document_elements(self, filing: Dict[str, Any]) -> Dict[str, List]:
        """
        Extract different elements from filing
        """
        # This is a simplified version
        # In production, parse XBRL/HTML structure properly
        content = filing.get('content', '')

        elements = {
            'mda': [],
            'risk_factors': [],
            'tables': [],
            'business_description': []
        }

        # Simple section extraction based on headers
        # In production, use proper XBRL parsing
        mda_pattern = r'(?:ITEM 7|Management.*?Discussion.*?Analysis)(.*?)(?:ITEM 8|Financial Statements)'
        risk_pattern = r'(?:ITEM 1A|Risk Factors)(.*?)(?:ITEM 1B|ITEM 2)'

        mda_match = re.search(mda_pattern, content, re.IGNORECASE | re.DOTALL)
        if mda_match:
            elements['mda'].append(mda_match.group(1))

        risk_match = re.search(risk_pattern, content, re.IGNORECASE | re.DOTALL)
        if risk_match:
            elements['risk_factors'].append(risk_match.group(1))

        return elements

    def _process_financial_table(
        self,
        table: Any,
        filing: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract and structure financial table data
        """
        # Extract table to DataFrame
        if isinstance(table, str):
            df = self.table_extractor.extract(table)
        else:
            df = pd.DataFrame(table)

        # Normalize
        normalized = self.table_extractor.normalize_table(df)

        # Extract time periods from columns
        time_periods = self._extract_time_periods(normalized)

        # Generate textual summary
        summary = self._generate_table_summary(normalized)

        # Extract key metrics
        metrics = self._extract_key_metrics(normalized)

        return {
            'structured_data': normalized.to_dict(),
            'time_periods': time_periods,
            'summary': summary,
            'metrics': metrics
        }

    def _extract_time_periods(self, df: pd.DataFrame) -> List[str]:
        """Extract time periods from table columns"""
        time_periods = []

        for col in df.columns:
            col_str = str(col)
            # Look for year patterns
            if re.search(r'\d{4}', col_str):
                time_periods.append(col_str)
            # Look for quarter patterns
            elif re.search(r'Q[1-4]', col_str, re.IGNORECASE):
                time_periods.append(col_str)

        return time_periods

    def _generate_table_summary(self, df: pd.DataFrame) -> str:
        """Generate textual summary of table"""
        summary_parts = []

        # Get table dimensions
        summary_parts.append(f"Financial table with {len(df)} rows and {len(df.columns)} columns.")

        # Get column headers
        if len(df.columns) > 0:
            summary_parts.append(f"Columns: {', '.join([str(c) for c in df.columns[:5]])}")

        # Get key metrics from first column if available
        if len(df) > 0 and len(df.columns) > 0:
            first_col = df.iloc[:, 0]
            summary_parts.append(f"Key items: {', '.join([str(v) for v in first_col.head()])}")

        return " ".join(summary_parts)

    def _extract_key_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract key financial metrics from table"""
        metrics = {}

        # Look for common financial metrics
        metric_keywords = [
            'revenue', 'net income', 'earnings', 'assets', 'liabilities',
            'cash flow', 'operating income', 'gross profit'
        ]

        for idx, row in df.iterrows():
            for col in df.columns:
                cell_value = str(row[col]).lower()
                for keyword in metric_keywords:
                    if keyword in cell_value:
                        metrics[keyword] = row.to_dict()
                        break

        return metrics

    def process_earnings_call(self, transcript: Dict[str, Any]) -> ProcessedDocument:
        """
        Process earnings call transcript
        """
        logger.info(f"Processing earnings call for {transcript.get('company')}")

        content = transcript.get('content', '')
        chunks = self.text_processor.chunk_by_semantic_boundaries(
            content,
            max_tokens=512
        )

        processed_chunks = []
        all_entities = []
        all_temporal_refs = []

        for chunk in chunks:
            entities = self.entity_extractor.extract_financial_entities(chunk)
            temporal_refs = self.temporal_extractor.extract_temporal_context(chunk)

            all_entities.extend(entities)
            all_temporal_refs.extend(temporal_refs)

            processed_chunks.append({
                'text': chunk,
                'chunk_type': 'narrative',
                'section_type': 'earnings_call',
                'entities': entities,
                'temporal_context': temporal_refs,
                'source_metadata': {
                    'call_date': transcript.get('date'),
                    'company': transcript.get('company'),
                    'quarter': transcript.get('quarter'),
                    'document_id': transcript.get('document_id')
                }
            })

        return ProcessedDocument(
            document_id=transcript.get('document_id', ''),
            document_type='earnings_call',
            company=transcript.get('company', ''),
            cik=None,
            filing_date=transcript.get('date', datetime.now()),
            chunks=processed_chunks,
            entities=all_entities,
            temporal_references=all_temporal_refs,
            metadata={
                'total_chunks': len(processed_chunks),
                'quarter': transcript.get('quarter')
            }
        )
