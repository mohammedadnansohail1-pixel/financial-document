"""
Performance Monitor and Evaluation Metrics
Tracks system performance, accuracy, and resource usage
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import numpy as np
from threading import Lock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Metrics for a single query"""
    query_id: str
    timestamp: datetime
    latency_ms: float
    retrieval_time_ms: float
    generation_time_ms: float
    num_retrieved: int
    num_citations: int
    confidence: float
    hallucination_score: float
    cache_hit: bool = False


@dataclass
class PerformanceSnapshot:
    """Snapshot of system performance"""
    timestamp: datetime
    total_queries: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    queries_per_second: float
    cache_hit_rate: float
    avg_confidence: float
    avg_hallucination_score: float
    error_rate: float


class RetrievalMetrics:
    """
    Calculate retrieval quality metrics
    """

    def __init__(self):
        self.metrics_history = []

    def calculate_precision_at_k(
        self,
        retrieved: List[str],
        relevant: List[str],
        k: int = 10
    ) -> float:
        """
        Calculate Precision@K
        """
        if not retrieved or k == 0:
            return 0.0

        retrieved_k = retrieved[:k]
        relevant_set = set(relevant)

        relevant_retrieved = sum(1 for doc in retrieved_k if doc in relevant_set)

        return relevant_retrieved / k

    def calculate_recall_at_k(
        self,
        retrieved: List[str],
        relevant: List[str],
        k: int = 10
    ) -> float:
        """
        Calculate Recall@K
        """
        if not relevant:
            return 0.0

        retrieved_k = retrieved[:k]
        relevant_set = set(relevant)

        relevant_retrieved = sum(1 for doc in retrieved_k if doc in relevant_set)

        return relevant_retrieved / len(relevant)

    def calculate_mrr(
        self,
        retrieved: List[str],
        relevant: List[str]
    ) -> float:
        """
        Calculate Mean Reciprocal Rank
        """
        relevant_set = set(relevant)

        for i, doc in enumerate(retrieved, 1):
            if doc in relevant_set:
                return 1.0 / i

        return 0.0

    def calculate_ndcg(
        self,
        retrieved: List[str],
        relevance_scores: Dict[str, float],
        k: Optional[int] = None
    ) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain
        """
        if k:
            retrieved = retrieved[:k]

        # Calculate DCG
        dcg = 0.0
        for i, doc in enumerate(retrieved, 1):
            rel = relevance_scores.get(doc, 0.0)
            dcg += (2 ** rel - 1) / np.log2(i + 1)

        # Calculate IDCG (ideal DCG)
        sorted_scores = sorted(relevance_scores.values(), reverse=True)
        if k:
            sorted_scores = sorted_scores[:k]

        idcg = 0.0
        for i, rel in enumerate(sorted_scores, 1):
            idcg += (2 ** rel - 1) / np.log2(i + 1)

        if idcg == 0:
            return 0.0

        return dcg / idcg

    def calculate_map(
        self,
        all_retrieved: List[List[str]],
        all_relevant: List[List[str]]
    ) -> float:
        """
        Calculate Mean Average Precision
        """
        if not all_retrieved:
            return 0.0

        aps = []
        for retrieved, relevant in zip(all_retrieved, all_relevant):
            if not relevant:
                continue

            relevant_set = set(relevant)
            num_relevant = 0
            sum_precisions = 0.0

            for i, doc in enumerate(retrieved, 1):
                if doc in relevant_set:
                    num_relevant += 1
                    precision = num_relevant / i
                    sum_precisions += precision

            if num_relevant > 0:
                ap = sum_precisions / len(relevant)
                aps.append(ap)

        return np.mean(aps) if aps else 0.0


class GenerationMetrics:
    """
    Calculate generation quality metrics
    """

    def __init__(self):
        pass

    def calculate_bleu(
        self,
        generated: str,
        reference: str,
        n: int = 4
    ) -> float:
        """
        Calculate BLEU score (simplified)
        """
        # Simplified BLEU implementation
        gen_tokens = generated.lower().split()
        ref_tokens = reference.lower().split()

        if not gen_tokens or not ref_tokens:
            return 0.0

        # Calculate precision for different n-grams
        precisions = []
        for i in range(1, n + 1):
            gen_ngrams = self._get_ngrams(gen_tokens, i)
            ref_ngrams = self._get_ngrams(ref_tokens, i)

            if not gen_ngrams:
                continue

            matches = sum(min(gen_ngrams[ng], ref_ngrams.get(ng, 0)) for ng in gen_ngrams)
            precision = matches / sum(gen_ngrams.values())
            precisions.append(precision)

        if not precisions:
            return 0.0

        # Geometric mean
        bleu = np.exp(np.mean([np.log(p) if p > 0 else -np.inf for p in precisions]))

        # Brevity penalty
        bp = min(1.0, np.exp(1 - len(ref_tokens) / len(gen_tokens)))

        return bp * bleu

    def _get_ngrams(self, tokens: List[str], n: int) -> Dict[Tuple[str, ...], int]:
        """Get n-grams from tokens"""
        ngrams = defaultdict(int)
        for i in range(len(tokens) - n + 1):
            ngram = tuple(tokens[i:i + n])
            ngrams[ngram] += 1
        return ngrams

    def calculate_rouge_l(
        self,
        generated: str,
        reference: str
    ) -> float:
        """
        Calculate ROUGE-L score
        """
        gen_tokens = generated.lower().split()
        ref_tokens = reference.lower().split()

        if not gen_tokens or not ref_tokens:
            return 0.0

        # Calculate LCS length
        lcs_length = self._lcs_length(gen_tokens, ref_tokens)

        # Calculate precision and recall
        precision = lcs_length / len(gen_tokens) if gen_tokens else 0
        recall = lcs_length / len(ref_tokens) if ref_tokens else 0

        # Calculate F1
        if precision + recall == 0:
            return 0.0

        f1 = 2 * precision * recall / (precision + recall)

        return f1

    def _lcs_length(self, seq1: List[str], seq2: List[str]) -> int:
        """Calculate longest common subsequence length"""
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i - 1] == seq2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        return dp[m][n]

    def measure_factual_accuracy(
        self,
        generated: str,
        source_documents: List[Dict[str, Any]]
    ) -> float:
        """
        Measure factual accuracy against source documents
        """
        # Extract claims from generated text
        gen_claims = set(generated.lower().split())

        # Check against source documents
        source_text = " ".join([doc.get('content', '').lower() for doc in source_documents])
        source_words = set(source_text.split())

        if not gen_claims:
            return 0.0

        # Calculate overlap
        overlap = len(gen_claims & source_words)
        accuracy = overlap / len(gen_claims)

        return accuracy


class FinancialMetrics:
    """
    Calculate financial performance metrics
    """

    def __init__(self):
        pass

    def calculate_sharpe_ratio(
        self,
        returns: np.ndarray,
        risk_free_rate: float = 0.02
    ) -> float:
        """
        Calculate Sharpe ratio
        """
        if len(returns) == 0:
            return 0.0

        excess_returns = returns - risk_free_rate / 252  # Daily risk-free rate
        if np.std(excess_returns) == 0:
            return 0.0

        sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)

        return float(sharpe)

    def calculate_alpha(
        self,
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray,
        risk_free_rate: float = 0.02
    ) -> float:
        """
        Calculate alpha (Jensen's alpha)
        """
        if len(portfolio_returns) != len(benchmark_returns):
            return 0.0

        # Calculate beta
        covariance = np.cov(portfolio_returns, benchmark_returns)[0, 1]
        benchmark_variance = np.var(benchmark_returns)

        if benchmark_variance == 0:
            return 0.0

        beta = covariance / benchmark_variance

        # Calculate expected return (CAPM)
        expected_return = risk_free_rate + beta * (np.mean(benchmark_returns) - risk_free_rate)

        # Alpha is actual return minus expected return
        alpha = np.mean(portfolio_returns) - expected_return

        return float(alpha) * 252  # Annualized

    def calculate_hit_rate(
        self,
        predictions: List[str],
        actuals: List[str]
    ) -> float:
        """
        Calculate prediction hit rate
        """
        if not predictions or len(predictions) != len(actuals):
            return 0.0

        hits = sum(1 for pred, actual in zip(predictions, actuals) if pred == actual)

        return hits / len(predictions)

    def calculate_max_drawdown(self, returns: np.ndarray) -> float:
        """
        Calculate maximum drawdown
        """
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max

        return float(np.min(drawdown))


class PerformanceMonitor:
    """
    Main performance monitoring system
    """

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.query_metrics: deque = deque(maxlen=window_size)
        self.error_count = 0
        self.total_queries = 0

        self.retrieval_metrics = RetrievalMetrics()
        self.generation_metrics = GenerationMetrics()
        self.financial_metrics = FinancialMetrics()

        self.lock = Lock()

        # Performance tracking
        self.latency_history: deque = deque(maxlen=window_size)
        self.confidence_history: deque = deque(maxlen=window_size)
        self.hallucination_history: deque = deque(maxlen=window_size)

        logger.info("PerformanceMonitor initialized")

    def record_query(self, metrics: QueryMetrics):
        """
        Record metrics for a query
        """
        with self.lock:
            self.query_metrics.append(metrics)
            self.latency_history.append(metrics.latency_ms)
            self.confidence_history.append(metrics.confidence)
            self.hallucination_history.append(metrics.hallucination_score)
            self.total_queries += 1

    def record_error(self):
        """
        Record an error
        """
        with self.lock:
            self.error_count += 1

    def get_current_snapshot(self) -> PerformanceSnapshot:
        """
        Get current performance snapshot
        """
        with self.lock:
            if not self.latency_history:
                return PerformanceSnapshot(
                    timestamp=datetime.now(),
                    total_queries=0,
                    avg_latency_ms=0,
                    p50_latency_ms=0,
                    p95_latency_ms=0,
                    p99_latency_ms=0,
                    queries_per_second=0,
                    cache_hit_rate=0,
                    avg_confidence=0,
                    avg_hallucination_score=0,
                    error_rate=0
                )

            latencies = list(self.latency_history)
            cache_hits = sum(1 for m in self.query_metrics if m.cache_hit)

            snapshot = PerformanceSnapshot(
                timestamp=datetime.now(),
                total_queries=self.total_queries,
                avg_latency_ms=float(np.mean(latencies)),
                p50_latency_ms=float(np.percentile(latencies, 50)),
                p95_latency_ms=float(np.percentile(latencies, 95)),
                p99_latency_ms=float(np.percentile(latencies, 99)),
                queries_per_second=len(self.query_metrics) / 60 if self.query_metrics else 0,
                cache_hit_rate=cache_hits / len(self.query_metrics) if self.query_metrics else 0,
                avg_confidence=float(np.mean(list(self.confidence_history))) if self.confidence_history else 0,
                avg_hallucination_score=float(np.mean(list(self.hallucination_history))) if self.hallucination_history else 0,
                error_rate=self.error_count / self.total_queries if self.total_queries > 0 else 0
            )

            return snapshot

    def evaluate_system_performance(
        self,
        predictions: List[Dict[str, Any]],
        ground_truth: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Comprehensive system evaluation
        """
        results = {
            'retrieval': {},
            'generation': {},
            'financial': {}
        }

        # Retrieval metrics
        if predictions and ground_truth:
            all_retrieved = [p.get('retrieved_docs', []) for p in predictions]
            all_relevant = [gt.get('relevant_docs', []) for gt in ground_truth]

            results['retrieval'] = {
                'precision@10': np.mean([
                    self.retrieval_metrics.calculate_precision_at_k(ret, rel, 10)
                    for ret, rel in zip(all_retrieved, all_relevant)
                ]),
                'recall@10': np.mean([
                    self.retrieval_metrics.calculate_recall_at_k(ret, rel, 10)
                    for ret, rel in zip(all_retrieved, all_relevant)
                ]),
                'mrr': np.mean([
                    self.retrieval_metrics.calculate_mrr(ret, rel)
                    for ret, rel in zip(all_retrieved, all_relevant)
                ]),
                'map': self.retrieval_metrics.calculate_map(all_retrieved, all_relevant)
            }

        # Generation metrics
        if predictions and ground_truth:
            bleu_scores = []
            rouge_scores = []

            for pred, gt in zip(predictions, ground_truth):
                if 'generated_text' in pred and 'reference_text' in gt:
                    bleu = self.generation_metrics.calculate_bleu(
                        pred['generated_text'],
                        gt['reference_text']
                    )
                    rouge = self.generation_metrics.calculate_rouge_l(
                        pred['generated_text'],
                        gt['reference_text']
                    )
                    bleu_scores.append(bleu)
                    rouge_scores.append(rouge)

            if bleu_scores:
                results['generation']['bleu'] = float(np.mean(bleu_scores))
            if rouge_scores:
                results['generation']['rouge_l'] = float(np.mean(rouge_scores))

        # Current performance snapshot
        snapshot = self.get_current_snapshot()
        results['system'] = {
            'avg_latency_ms': snapshot.avg_latency_ms,
            'p95_latency_ms': snapshot.p95_latency_ms,
            'queries_per_second': snapshot.queries_per_second,
            'cache_hit_rate': snapshot.cache_hit_rate,
            'avg_confidence': snapshot.avg_confidence,
            'avg_hallucination_score': snapshot.avg_hallucination_score,
            'error_rate': snapshot.error_rate
        }

        return results

    def get_metrics_summary(self) -> str:
        """
        Get human-readable metrics summary
        """
        snapshot = self.get_current_snapshot()

        summary = f"""
Performance Metrics Summary
===========================
Total Queries: {snapshot.total_queries}
Timestamp: {snapshot.timestamp.isoformat()}

Latency:
  - Average: {snapshot.avg_latency_ms:.2f}ms
  - P50: {snapshot.p50_latency_ms:.2f}ms
  - P95: {snapshot.p95_latency_ms:.2f}ms
  - P99: {snapshot.p99_latency_ms:.2f}ms

Throughput:
  - Queries/sec: {snapshot.queries_per_second:.2f}
  - Cache hit rate: {snapshot.cache_hit_rate:.2%}

Quality:
  - Avg Confidence: {snapshot.avg_confidence:.2%}
  - Avg Hallucination: {snapshot.avg_hallucination_score:.2%}
  - Error Rate: {snapshot.error_rate:.2%}
"""

        return summary

    def export_metrics(self) -> Dict[str, Any]:
        """
        Export metrics for external monitoring (Prometheus, etc.)
        """
        snapshot = self.get_current_snapshot()

        return {
            'timestamp': snapshot.timestamp.isoformat(),
            'total_queries': snapshot.total_queries,
            'latency': {
                'avg_ms': snapshot.avg_latency_ms,
                'p50_ms': snapshot.p50_latency_ms,
                'p95_ms': snapshot.p95_latency_ms,
                'p99_ms': snapshot.p99_latency_ms
            },
            'throughput': {
                'queries_per_second': snapshot.queries_per_second,
                'cache_hit_rate': snapshot.cache_hit_rate
            },
            'quality': {
                'avg_confidence': snapshot.avg_confidence,
                'avg_hallucination_score': snapshot.avg_hallucination_score,
                'error_rate': snapshot.error_rate
            }
        }


# Global performance monitor instance
_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """
    Get or create global performance monitor
    """
    global _global_monitor

    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()

    return _global_monitor
