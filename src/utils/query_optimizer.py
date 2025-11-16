"""
Query Optimizer with Caching
Optimizes query performance through intelligent caching and query planning
"""

import logging
import hashlib
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import time
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Query type classification"""
    POINT_LOOKUP = "point_lookup"
    TEMPORAL_ANALYSIS = "temporal_analysis"
    COMPARATIVE = "comparative"
    AGGREGATION = "aggregation"
    GENERAL_RAG = "general_rag"


@dataclass
class CacheEntry:
    """Cache entry"""
    key: str
    value: Any
    created_at: datetime
    accessed_at: datetime
    access_count: int
    ttl: int  # Time to live in seconds
    size_bytes: int


@dataclass
class QueryPlan:
    """Query execution plan"""
    query_id: str
    query_type: QueryType
    use_cache: bool
    use_graph: bool
    use_temporal: bool
    parallel_retrieval: bool
    max_workers: int
    estimated_cost: float


class RedisCache:
    """
    Redis-based caching system (placeholder implementation)
    In production, use actual Redis client
    """

    def __init__(self, host: str = "localhost", port: int = 6379, ttl: int = 3600):
        self.host = host
        self.port = port
        self.default_ttl = ttl

        # In-memory cache for demonstration
        # In production, use redis.Redis()
        self.cache: Dict[str, CacheEntry] = {}
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0
        }

        logger.info(f"RedisCache initialized (ttl={ttl}s)")

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        """
        if key in self.cache:
            entry = self.cache[key]

            # Check if expired
            if self._is_expired(entry):
                await self.delete(key)
                self.stats['misses'] += 1
                return None

            # Update access stats
            entry.accessed_at = datetime.now()
            entry.access_count += 1
            self.stats['hits'] += 1

            logger.debug(f"Cache HIT: {key}")
            return entry.value

        self.stats['misses'] += 1
        logger.debug(f"Cache MISS: {key}")
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ):
        """
        Set value in cache
        """
        if ttl is None:
            ttl = self.default_ttl

        # Calculate size (rough estimate)
        size_bytes = len(json.dumps(str(value)))

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            accessed_at=datetime.now(),
            access_count=0,
            ttl=ttl,
            size_bytes=size_bytes
        )

        self.cache[key] = entry
        self.stats['sets'] += 1

        logger.debug(f"Cache SET: {key} (ttl={ttl}s, size={size_bytes}B)")

        # Evict old entries if cache is too large
        await self._evict_if_needed()

    async def delete(self, key: str):
        """
        Delete key from cache
        """
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"Cache DELETE: {key}")

    async def clear(self):
        """
        Clear all cache
        """
        self.cache.clear()
        logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        """
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0

        return {
            'total_requests': total_requests,
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': hit_rate,
            'sets': self.stats['sets'],
            'evictions': self.stats['evictions'],
            'cache_size': len(self.cache),
            'total_size_bytes': sum(entry.size_bytes for entry in self.cache.values())
        }

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if entry is expired"""
        age = (datetime.now() - entry.created_at).total_seconds()
        return age > entry.ttl

    async def _evict_if_needed(self, max_size: int = 10000):
        """
        Evict old entries if cache is too large
        """
        if len(self.cache) <= max_size:
            return

        # Evict least recently used
        sorted_entries = sorted(
            self.cache.items(),
            key=lambda x: x[1].accessed_at
        )

        num_to_evict = len(self.cache) - max_size
        for key, _ in sorted_entries[:num_to_evict]:
            await self.delete(key)
            self.stats['evictions'] += 1


class QueryClassifier:
    """
    Classify query types for optimization
    """

    def __init__(self):
        self.patterns = {
            QueryType.POINT_LOOKUP: [
                'what is', 'who is', 'when did', 'where is',
                'define', 'explain'
            ],
            QueryType.TEMPORAL_ANALYSIS: [
                'trend', 'over time', 'historical', 'forecast',
                'growth', 'change', 'quarterly', 'annual'
            ],
            QueryType.COMPARATIVE: [
                'compare', 'versus', 'vs', 'difference between',
                'better', 'worse', 'higher', 'lower'
            ],
            QueryType.AGGREGATION: [
                'total', 'sum', 'average', 'mean', 'median',
                'maximum', 'minimum', 'count'
            ]
        }

    def classify(self, query: str) -> QueryType:
        """
        Classify query type
        """
        query_lower = query.lower()

        # Check patterns
        for query_type, patterns in self.patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                return query_type

        # Default to general RAG
        return QueryType.GENERAL_RAG


class QueryPlanner:
    """
    Create optimized query execution plans
    """

    def __init__(self):
        self.classifier = QueryClassifier()

    def create_plan(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> QueryPlan:
        """
        Create optimized query plan
        """
        query_type = self.classifier.classify(query)
        context = context or {}

        # Default plan
        plan = QueryPlan(
            query_id=self._generate_query_id(query, context),
            query_type=query_type,
            use_cache=True,
            use_graph=True,
            use_temporal=True,
            parallel_retrieval=True,
            max_workers=10,
            estimated_cost=1.0
        )

        # Optimize based on query type
        if query_type == QueryType.POINT_LOOKUP:
            # Simple lookups can skip graph and use cache heavily
            plan.use_graph = False
            plan.parallel_retrieval = False
            plan.estimated_cost = 0.3

        elif query_type == QueryType.TEMPORAL_ANALYSIS:
            # Temporal queries need temporal features
            plan.use_temporal = True
            plan.max_workers = 15
            plan.estimated_cost = 1.5

        elif query_type == QueryType.COMPARATIVE:
            # Comparative queries need parallel retrieval
            plan.parallel_retrieval = True
            plan.max_workers = 20
            plan.estimated_cost = 2.0

        elif query_type == QueryType.AGGREGATION:
            # Aggregation can use caching heavily
            plan.use_cache = True
            plan.estimated_cost = 1.2

        logger.debug(f"Query plan created: {query_type.value} (cost={plan.estimated_cost})")

        return plan

    def _generate_query_id(self, query: str, context: Dict[str, Any]) -> str:
        """Generate unique query ID"""
        content = f"{query}_{json.dumps(context, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()


class QueryOptimizer:
    """
    Main query optimizer with caching and intelligent planning
    """

    def __init__(
        self,
        cache: Optional[RedisCache] = None,
        enable_cache: bool = True
    ):
        self.cache = cache or RedisCache()
        self.enable_cache = enable_cache
        self.planner = QueryPlanner()

        # Query statistics
        self.query_stats = {
            'total': 0,
            'cache_hits': 0,
            'optimized': 0,
            'total_time_saved_ms': 0
        }

        logger.info("QueryOptimizer initialized")

    async def optimize_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> QueryPlan:
        """
        Multi-level query optimization
        """
        self.query_stats['total'] += 1

        # Create execution plan
        plan = self.planner.create_plan(query, context)

        # Check cache first
        if self.enable_cache and plan.use_cache:
            cached_result = await self._check_cache(plan.query_id)
            if cached_result is not None:
                self.query_stats['cache_hits'] += 1
                logger.info(f"Query served from cache: {plan.query_id[:8]}")
                return cached_result

        self.query_stats['optimized'] += 1

        return plan

    async def _check_cache(self, query_id: str) -> Optional[Any]:
        """
        Check cache for result
        """
        cache_key = self._generate_cache_key(query_id)
        return await self.cache.get(cache_key)

    async def cache_result(
        self,
        query_id: str,
        result: Any,
        ttl: Optional[int] = None
    ):
        """
        Cache query result
        """
        if not self.enable_cache:
            return

        cache_key = self._generate_cache_key(query_id)
        await self.cache.set(cache_key, result, ttl)

    def _generate_cache_key(self, query_id: str) -> str:
        """Generate cache key"""
        return f"query:result:{query_id}"

    async def parallel_retrieval(
        self,
        query: str,
        sources: List[Callable],
        max_workers: int = 10
    ) -> List[Any]:
        """
        Parallel retrieval from multiple sources
        """
        import asyncio

        # Create tasks
        tasks = [source(query) for source in sources]

        # Execute in parallel with timeout
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions
            valid_results = [r for r in results if not isinstance(r, Exception)]

            return valid_results

        except Exception as e:
            logger.error(f"Parallel retrieval error: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """
        Get optimizer statistics
        """
        cache_hit_rate = (
            self.query_stats['cache_hits'] / self.query_stats['total']
            if self.query_stats['total'] > 0 else 0
        )

        return {
            'total_queries': self.query_stats['total'],
            'cache_hits': self.query_stats['cache_hits'],
            'cache_hit_rate': cache_hit_rate,
            'optimized_queries': self.query_stats['optimized'],
            'cache_stats': self.cache.get_stats()
        }


def cached(ttl: int = 3600):
    """
    Decorator for caching function results
    """
    def decorator(func: Callable) -> Callable:
        cache: Dict[str, tuple] = {}

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_data = f"{func.__name__}:{args}:{kwargs}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()

            # Check cache
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                age = (datetime.now() - timestamp).total_seconds()

                if age < ttl:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return result

            # Execute function
            start = time.time()
            result = await func(*args, **kwargs)
            elapsed = time.time() - start

            # Cache result
            cache[cache_key] = (result, datetime.now())

            logger.debug(f"Cached {func.__name__} (took {elapsed:.3f}s)")

            return result

        return wrapper
    return decorator


def timed(func: Callable) -> Callable:
    """
    Decorator for timing function execution
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        elapsed = (time.time() - start) * 1000  # Convert to ms

        logger.info(f"{func.__name__} took {elapsed:.2f}ms")

        return result

    return wrapper
