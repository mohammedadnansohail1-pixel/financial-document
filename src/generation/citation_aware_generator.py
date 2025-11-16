"""
Citation-Aware Generator with Reference Validation
Implements CRAG (Corrective RAG) and hallucination detection
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """Container for citation information"""
    citation_id: str
    source_document: str
    source_type: str
    excerpt: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    confidence: float = 1.0
    timestamp: Optional[datetime] = None


@dataclass
class GeneratedResponse:
    """Container for generated response with citations"""
    text: str
    citations: List[Citation]
    confidence: float
    hallucination_score: float
    source_documents: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class CitationValidator:
    """
    Validate citations and source credibility
    """

    def __init__(self):
        self.trusted_sources = {
            'SEC_EDGAR': 1.0,
            '10-K': 0.95,
            '10-Q': 0.95,
            '8-K': 0.90,
            'earnings_call': 0.85,
            'news': 0.70,
            'analyst_report': 0.75
        }

    def check_source_credibility(self, document: Dict[str, Any]) -> float:
        """
        Check credibility of source document
        """
        source_type = document.get('source_type', '').upper()
        doc_type = document.get('document_type', '').upper()

        # Check against trusted sources
        credibility = self.trusted_sources.get(source_type, 0.5)
        doc_credibility = self.trusted_sources.get(doc_type, 0.5)

        # Use higher of the two
        return max(credibility, doc_credibility)

    def verify_temporal_consistency(self, document: Dict[str, Any]) -> bool:
        """
        Verify temporal consistency of document
        """
        # Check if document has valid timestamp
        timestamp = document.get('timestamp') or document.get('filing_date')
        if not timestamp:
            logger.warning(f"Document missing timestamp: {document.get('document_id')}")
            return False

        # Check if timestamp is in the past
        if isinstance(timestamp, datetime):
            if timestamp > datetime.now():
                logger.warning(f"Document has future timestamp: {timestamp}")
                return False

        return True

    def find_contradictions(
        self,
        document: Dict[str, Any],
        other_documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Find contradictions between documents
        """
        contradictions = []

        # Extract numerical claims from document
        doc_claims = self._extract_numerical_claims(document.get('content', ''))

        for other_doc in other_documents:
            if other_doc.get('document_id') == document.get('document_id'):
                continue

            other_claims = self._extract_numerical_claims(other_doc.get('content', ''))

            # Check for contradicting claims
            for claim_key, claim_value in doc_claims.items():
                if claim_key in other_claims:
                    other_value = other_claims[claim_key]
                    # Check if values differ significantly
                    if self._values_contradict(claim_value, other_value):
                        contradictions.append({
                            'claim': claim_key,
                            'value1': claim_value,
                            'value2': other_value,
                            'source1': document.get('document_id'),
                            'source2': other_doc.get('document_id')
                        })

        return contradictions

    def _extract_numerical_claims(self, text: str) -> Dict[str, float]:
        """
        Extract numerical claims from text
        """
        claims = {}

        # Look for revenue mentions
        revenue_pattern = r'revenue.*?\$\s*([\d,.]+)\s*(million|billion)'
        for match in re.finditer(revenue_pattern, text, re.IGNORECASE):
            amount = float(match.group(1).replace(',', ''))
            unit = match.group(2).lower()
            if unit == 'billion':
                amount *= 1000
            claims['revenue'] = amount

        # Look for earnings/profit
        earnings_pattern = r'(?:earnings|profit|income).*?\$\s*([\d,.]+)\s*(million|billion)'
        for match in re.finditer(earnings_pattern, text, re.IGNORECASE):
            amount = float(match.group(1).replace(',', ''))
            unit = match.group(2).lower()
            if unit == 'billion':
                amount *= 1000
            claims['earnings'] = amount

        return claims

    def _values_contradict(self, value1: float, value2: float, threshold: float = 0.1) -> bool:
        """
        Check if two values contradict each other
        """
        if value1 == 0 or value2 == 0:
            return False

        # Calculate relative difference
        diff = abs(value1 - value2) / max(value1, value2)
        return diff > threshold


class HallucinationDetector:
    """
    Detect hallucinations in generated text
    """

    def __init__(self):
        self.confidence_threshold = 0.8

    def detect(
        self,
        generated_text: str,
        source_documents: List[Dict[str, Any]]
    ) -> float:
        """
        Detect hallucination in generated text
        Returns hallucination score (0 = no hallucination, 1 = full hallucination)
        """
        # Extract claims from generated text
        generated_claims = self._extract_claims(generated_text)

        if not generated_claims:
            return 0.0

        # Check each claim against source documents
        verified_claims = 0
        for claim in generated_claims:
            if self._verify_claim_in_sources(claim, source_documents):
                verified_claims += 1

        # Calculate hallucination score
        hallucination_score = 1 - (verified_claims / len(generated_claims))

        return hallucination_score

    def _extract_claims(self, text: str) -> List[str]:
        """
        Extract factual claims from text
        """
        # Simple implementation: split into sentences
        sentences = re.split(r'[.!?]+', text)
        claims = [s.strip() for s in sentences if s.strip()]

        return claims

    def _verify_claim_in_sources(
        self,
        claim: str,
        source_documents: List[Dict[str, Any]]
    ) -> bool:
        """
        Verify if claim is supported by source documents
        """
        claim_lower = claim.lower()

        for doc in source_documents:
            content = doc.get('content', '').lower()

            # Simple keyword matching
            # In production, use semantic similarity
            claim_words = set(claim_lower.split())
            content_words = set(content.split())

            # Check overlap
            overlap = len(claim_words & content_words) / len(claim_words)

            if overlap > 0.5:
                return True

        return False


class FinancialLLM:
    """
    Wrapper for financial-tuned language model
    In production, integrate with BloombergGPT, FinBERT, or similar
    """

    def __init__(self, model_name: str = "bloomberg-gpt"):
        self.model_name = model_name
        logger.info(f"Initialized FinancialLLM with model: {model_name}")

    def generate(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.3,
        citation_mode: bool = False
    ) -> str:
        """
        Generate text using financial LLM
        """
        # Placeholder implementation
        # In production, call actual LLM API (OpenAI, Anthropic, etc.)

        logger.info(f"Generating response (max_tokens={max_tokens}, temp={temperature})")

        # Simulate response
        response = f"""Based on the provided financial documents, the analysis shows:

1. Revenue performance has been strong in recent quarters
2. Operating margins have improved year-over-year
3. Management guidance indicates continued growth trajectory

These insights are derived from SEC filings and quarterly earnings reports."""

        return response


class CitationAwareGenerator:
    """
    Main citation-aware generator with reference validation
    Implements CRAG (Corrective RAG) approach
    """

    def __init__(
        self,
        llm_model: str = "bloomberg-gpt",
        enable_hallucination_detection: bool = True
    ):
        self.llm = FinancialLLM(model=llm_model)
        self.citation_validator = CitationValidator()
        self.hallucination_detector = HallucinationDetector()
        self.enable_hallucination_detection = enable_hallucination_detection

        logger.info("Initialized CitationAwareGenerator")

    def generate_with_citations(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> GeneratedResponse:
        """
        Generate response with validated citations
        """
        logger.info(f"Generating response for query: {query[:100]}")

        # Stage 1: Reference validation
        validated_refs = self._validate_references(retrieved_docs)
        logger.info(f"Validated {len(validated_refs)}/{len(retrieved_docs)} references")

        if not validated_refs:
            logger.warning("No validated references available")
            return GeneratedResponse(
                text="Insufficient reliable sources to answer the query.",
                citations=[],
                confidence=0.0,
                hallucination_score=0.0,
                source_documents=[],
                metadata={'error': 'No validated references'}
            )

        # Stage 2: Build augmented prompt
        prompt = self._build_financial_prompt(
            query,
            validated_refs,
            context or {}
        )

        # Stage 3: Generate with citation markers
        response_text = self.llm.generate(
            prompt,
            max_tokens=1024,
            temperature=0.3,
            citation_mode=True
        )

        # Stage 4: Insert citations
        cited_response = self._insert_citations(
            response_text,
            validated_refs
        )

        # Stage 5: Hallucination check
        hallucination_score = 0.0
        if self.enable_hallucination_detection:
            hallucination_score = self._check_hallucination(
                cited_response,
                validated_refs
            )
            logger.info(f"Hallucination score: {hallucination_score:.3f}")

        # Stage 6: Apply corrective RAG if needed
        if hallucination_score > 0.2:
            logger.warning("High hallucination detected, applying corrective RAG")
            cited_response = self._apply_corrective_rag(
                query,
                cited_response,
                validated_refs
            )

        # Extract citations from response
        citations = self._extract_citations(cited_response, validated_refs)

        # Calculate confidence
        confidence = self._calculate_confidence(
            validated_refs,
            hallucination_score
        )

        return GeneratedResponse(
            text=cited_response,
            citations=citations,
            confidence=confidence,
            hallucination_score=hallucination_score,
            source_documents=validated_refs,
            metadata={
                'num_sources': len(validated_refs),
                'query': query
            }
        )

    def _validate_references(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validate and grade document relevance
        """
        validated = []

        for doc in documents:
            # Check source credibility
            credibility = self.citation_validator.check_source_credibility(doc)

            # Verify temporal consistency
            temporal_valid = self.citation_validator.verify_temporal_consistency(doc)

            # Check for contradictions
            contradictions = self.citation_validator.find_contradictions(doc, documents)

            # Accept if credibility is high and no major issues
            if credibility > 0.7 and temporal_valid and len(contradictions) == 0:
                doc['credibility'] = credibility
                doc['source_classification'] = self._classify_source(doc)
                validated.append(doc)
            elif credibility > 0.5 and temporal_valid:
                # Include with warning
                doc['credibility'] = credibility
                doc['warning'] = 'Lower credibility or minor contradictions detected'
                validated.append(doc)

        return validated

    def _classify_source(self, document: Dict[str, Any]) -> str:
        """
        Classify source type
        """
        doc_type = document.get('document_type', '').upper()

        if doc_type in ['10-K', '10-Q', '8-K']:
            return 'SEC_FILING'
        elif doc_type == 'EARNINGS_CALL':
            return 'EARNINGS_CALL'
        elif 'news' in doc_type.lower():
            return 'NEWS'
        else:
            return 'OTHER'

    def _build_financial_prompt(
        self,
        query: str,
        validated_refs: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> str:
        """
        Build augmented prompt for financial LLM
        """
        prompt_parts = []

        # Add system instruction
        prompt_parts.append("""You are a financial analysis expert. Answer the question based ONLY on the provided documents.
Include specific citations to support your claims. Be precise with numbers and dates.""")

        # Add context if provided
        if context:
            temporal_context = context.get('temporal_context', '')
            if temporal_context:
                prompt_parts.append(f"\nTemporal Context: {temporal_context}")

        # Add source documents
        prompt_parts.append("\n\n=== SOURCE DOCUMENTS ===\n")

        for idx, doc in enumerate(validated_refs[:10], 1):  # Limit to top 10
            content = doc.get('content', '')[:500]  # Truncate for context limit
            doc_type = doc.get('document_type', 'Unknown')
            doc_date = doc.get('filing_date', 'Unknown date')

            prompt_parts.append(f"\n[Document {idx}] Type: {doc_type}, Date: {doc_date}")
            prompt_parts.append(f"Content: {content}\n")

        # Add query
        prompt_parts.append(f"\n\n=== QUESTION ===\n{query}")

        prompt_parts.append("\n\n=== ANSWER ===\n")

        return "\n".join(prompt_parts)

    def _insert_citations(
        self,
        response: str,
        validated_refs: List[Dict[str, Any]]
    ) -> str:
        """
        Insert citation markers into response
        """
        # For simplicity, add citations at end of key statements
        # In production, use more sophisticated citation placement

        cited_response = response

        # Add citation markers [1], [2], etc.
        sentences = re.split(r'([.!?])', cited_response)

        for i, sentence in enumerate(sentences):
            if sentence.strip() and len(sentence) > 20:
                # Add citation to substantial sentences
                if i < len(validated_refs):
                    sentences[i] = sentence + f" [{i+1}]"

        cited_response = "".join(sentences)

        return cited_response

    def _check_hallucination(
        self,
        response: str,
        validated_refs: List[Dict[str, Any]]
    ) -> float:
        """
        Check for hallucinations in response
        """
        return self.hallucination_detector.detect(response, validated_refs)

    def _apply_corrective_rag(
        self,
        query: str,
        response: str,
        references: List[Dict[str, Any]]
    ) -> str:
        """
        Apply CRAG correction when hallucination detected
        """
        logger.info("Applying corrective RAG")

        # Re-generate with stronger grounding instruction
        corrective_prompt = f"""IMPORTANT: Base your answer STRICTLY on the provided documents. Do not infer or extrapolate.

Question: {query}

Sources:
{self._format_sources(references[:5])}

Previous answer (contained inaccuracies):
{response}

Please provide a corrected answer that is fully grounded in the source documents:"""

        corrected = self.llm.generate(
            corrective_prompt,
            max_tokens=1024,
            temperature=0.1  # Lower temperature for more conservative generation
        )

        return corrected

    def _format_sources(self, references: List[Dict[str, Any]]) -> str:
        """Format sources for prompt"""
        formatted = []

        for idx, ref in enumerate(references, 1):
            content = ref.get('content', '')[:300]
            formatted.append(f"[{idx}] {content}")

        return "\n\n".join(formatted)

    def _extract_citations(
        self,
        response: str,
        validated_refs: List[Dict[str, Any]]
    ) -> List[Citation]:
        """
        Extract citation objects from response
        """
        citations = []

        # Find citation markers [1], [2], etc.
        citation_pattern = r'\[(\d+)\]'
        matches = re.finditer(citation_pattern, response)

        for match in matches:
            citation_num = int(match.group(1)) - 1

            if citation_num < len(validated_refs):
                ref = validated_refs[citation_num]

                citation = Citation(
                    citation_id=self._generate_citation_id(ref),
                    source_document=ref.get('document_id', ''),
                    source_type=ref.get('document_type', ''),
                    excerpt=ref.get('content', '')[:200],
                    confidence=ref.get('credibility', 1.0),
                    timestamp=ref.get('filing_date')
                )

                citations.append(citation)

        return citations

    def _generate_citation_id(self, reference: Dict[str, Any]) -> str:
        """Generate unique citation ID"""
        content = f"{reference.get('document_id', '')}_{reference.get('chunk_id', '')}"
        return hashlib.md5(content.encode()).hexdigest()[:8]

    def _calculate_confidence(
        self,
        validated_refs: List[Dict[str, Any]],
        hallucination_score: float
    ) -> float:
        """
        Calculate overall confidence in generated response
        """
        # Average credibility of sources
        avg_credibility = sum(ref.get('credibility', 0.5) for ref in validated_refs) / max(len(validated_refs), 1)

        # Penalize for hallucinations
        confidence = avg_credibility * (1 - hallucination_score)

        # Boost if multiple high-quality sources
        if len(validated_refs) >= 3:
            confidence *= 1.1

        return min(confidence, 1.0)
