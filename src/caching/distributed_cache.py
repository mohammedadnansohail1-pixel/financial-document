"""
Distributed Caching Layer
Multi-level distributed caching with Redis Cluster support
"""

import logging
import asyncio
import redis
from redis.cluster import RedisCluster
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib
import pickle
import time
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache levels"""
    L1_MEMORY = "l1_memory"  # In-memory cache (fastest)
    L2_REDIS = "l2_redis"    # Redis cache (fast, distributed)
    L3_DISK = "l3_disk"      # Disk cache (persistent)


class CacheStrategy(Enum):
    """Cache strategies"""
    LRU = "lru"              # Least Recently Used
    LFU = "lfu"              # Least Frequently Used
    FIFO = "fifo"            # First In First Out
    TTL = "ttl"              # Time To Live


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    level: CacheLevel
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    size_bytes: int = 0
    tags: List[str] = field(default_factory=list)


@dataclass
class CacheStats:
    """Cache statistics"""
    total_hits: int = 0
    total_misses: int = 0
    l1_hits: int = 0
    l2_hits: int = 0
    l3_hits: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.total_hits + self.total_misses
        return (self.total_hits / total * 100) if total > 0 else 0.0


class L1MemoryCache:
    """
    Level 1: In-memory cache (fastest)
    """

    def __init__(
        self,
        max_size_mb: int = 500,
        max_entries: int = 10000,
        strategy: CacheStrategy = CacheStrategy.LRU
    ):
        self.max_size_mb = max_size_mb
        self.max_entries = max_entries
        self.strategy = strategy

        self.cache: Dict[str, CacheEntry] = {}
        self.stats = CacheStats()

    def get(self, key: str) -> Optional[Any]:
        """Get from L1 cache"""
        if key in self.cache:
            entry = self.cache[key]

            # Check TTL
            if entry.ttl_seconds:
                age = (datetime.now() - entry.created_at).total_seconds()
                if age > entry.ttl_seconds:
                    self._evict(key)
                    return None

            # Update access info
            entry.accessed_at = datetime.now()
            entry.access_count += 1

            self.stats.total_hits += 1
            self.stats.l1_hits += 1

            logger.debug(f"L1 cache hit: {key}")
            return entry.value

        logger.debug(f"L1 cache miss: {key}")
        self.stats.total_misses += 1
        return None

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        tags: Optional[List[str]] = None
    ):
        """Set in L1 cache"""
        # Estimate size
        size_bytes = len(pickle.dumps(value))

        # Check if eviction needed
        while (self.stats.size_bytes + size_bytes > self.max_size_mb * 1024 * 1024 or
               len(self.cache) >= self.max_entries):
            self._evict_one()

        # Create entry
        entry = CacheEntry(
            key=key,
            value=value,
            level=CacheLevel.L1_MEMORY,
            created_at=datetime.now(),
            accessed_at=datetime.now(),
            ttl_seconds=ttl_seconds,
            size_bytes=size_bytes,
            tags=tags or []
        )

        self.cache[key] = entry
        self.stats.size_bytes += size_bytes
        self.stats.entry_count = len(self.cache)

        logger.debug(f"L1 cache set: {key} ({size_bytes} bytes)")

    def _evict_one(self):
        """Evict one entry based on strategy"""
        if not self.cache:
            return

        if self.strategy == CacheStrategy.LRU:
            # Evict least recently accessed
            key_to_evict = min(
                self.cache.items(),
                key=lambda x: x[1].accessed_at
            )[0]
        elif self.strategy == CacheStrategy.LFU:
            # Evict least frequently used
            key_to_evict = min(
                self.cache.items(),
                key=lambda x: x[1].access_count
            )[0]
        else:  # FIFO
            # Evict oldest
            key_to_evict = min(
                self.cache.items(),
                key=lambda x: x[1].created_at
            )[0]

        self._evict(key_to_evict)

    def _evict(self, key: str):
        """Evict specific key"""
        if key in self.cache:
            entry = self.cache[key]
            self.stats.size_bytes -= entry.size_bytes
            del self.cache[key]
            self.stats.evictions += 1
            self.stats.entry_count = len(self.cache)

            logger.debug(f"L1 cache evicted: {key}")

    def invalidate(self, key: str):
        """Invalidate specific key"""
        self._evict(key)

    def invalidate_by_tags(self, tags: List[str]):
        """Invalidate entries by tags"""
        keys_to_evict = [
            key for key, entry in self.cache.items()
            if any(tag in entry.tags for tag in tags)
        ]

        for key in keys_to_evict:
            self._evict(key)

    def clear(self):
        """Clear all entries"""
        self.cache.clear()
        self.stats = CacheStats()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'level': 'L1',
            'hit_rate': self.stats.hit_rate,
            'total_hits': self.stats.l1_hits,
            'total_misses': self.stats.total_misses,
            'evictions': self.stats.evictions,
            'size_mb': self.stats.size_bytes / (1024 * 1024),
            'max_size_mb': self.max_size_mb,
            'entry_count': len(self.cache),
            'max_entries': self.max_entries
        }


class L2RedisCache:
    """
    Level 2: Redis cache (fast, distributed)
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        redis_cluster: bool = False,
        prefix: str = "finrag",
        default_ttl: int = 3600
    ):
        self.redis_url = redis_url
        self.redis_cluster = redis_cluster
        self.prefix = prefix
        self.default_ttl = default_ttl

        self.client: Optional[Union[redis.Redis, RedisCluster]] = None
        self.stats = CacheStats()

    def connect(self):
        """Connect to Redis"""
        try:
            if self.redis_cluster:
                # Redis Cluster
                self.client = RedisCluster.from_url(
                    self.redis_url,
                    decode_responses=False
                )
            else:
                # Single Redis instance
                self.client = redis.from_url(
                    self.redis_url,
                    decode_responses=False
                )

            # Test connection
            self.client.ping()

            logger.info(f"Connected to Redis ({'cluster' if self.redis_cluster else 'single'})")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _make_key(self, key: str) -> str:
        """Make prefixed key"""
        return f"{self.prefix}:{key}"

    def get(self, key: str) -> Optional[Any]:
        """Get from L2 cache"""
        if not self.client:
            return None

        try:
            prefixed_key = self._make_key(key)
            value = self.client.get(prefixed_key)

            if value:
                self.stats.total_hits += 1
                self.stats.l2_hits += 1

                # Deserialize
                result = pickle.loads(value)

                logger.debug(f"L2 cache hit: {key}")
                return result

            self.stats.total_misses += 1
            logger.debug(f"L2 cache miss: {key}")
            return None

        except Exception as e:
            logger.error(f"L2 cache get error: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        tags: Optional[List[str]] = None
    ):
        """Set in L2 cache"""
        if not self.client:
            return

        try:
            prefixed_key = self._make_key(key)
            ttl = ttl_seconds or self.default_ttl

            # Serialize
            serialized = pickle.dumps(value)

            # Set with TTL
            self.client.setex(prefixed_key, ttl, serialized)

            # Store tags if provided
            if tags:
                for tag in tags:
                    tag_key = self._make_key(f"tag:{tag}")
                    self.client.sadd(tag_key, key)
                    self.client.expire(tag_key, ttl)

            logger.debug(f"L2 cache set: {key} (TTL={ttl}s)")

        except Exception as e:
            logger.error(f"L2 cache set error: {e}")

    def invalidate(self, key: str):
        """Invalidate specific key"""
        if not self.client:
            return

        try:
            prefixed_key = self._make_key(key)
            self.client.delete(prefixed_key)

            logger.debug(f"L2 cache invalidated: {key}")

        except Exception as e:
            logger.error(f"L2 cache invalidate error: {e}")

    def invalidate_by_tags(self, tags: List[str]):
        """Invalidate entries by tags"""
        if not self.client:
            return

        try:
            for tag in tags:
                tag_key = self._make_key(f"tag:{tag}")
                keys = self.client.smembers(tag_key)

                if keys:
                    # Delete all keys with this tag
                    prefixed_keys = [self._make_key(k.decode()) for k in keys]
                    self.client.delete(*prefixed_keys)

                    # Delete tag set
                    self.client.delete(tag_key)

                    logger.debug(f"L2 cache invalidated by tag: {tag} ({len(keys)} keys)")

        except Exception as e:
            logger.error(f"L2 cache invalidate by tags error: {e}")

    def clear(self):
        """Clear all cache entries with prefix"""
        if not self.client:
            return

        try:
            # Scan for keys with prefix
            cursor = 0
            while True:
                cursor, keys = self.client.scan(
                    cursor,
                    match=f"{self.prefix}:*",
                    count=100
                )

                if keys:
                    self.client.delete(*keys)

                if cursor == 0:
                    break

            logger.info("L2 cache cleared")

        except Exception as e:
            logger.error(f"L2 cache clear error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            'level': 'L2',
            'hit_rate': self.stats.hit_rate,
            'total_hits': self.stats.l2_hits,
            'total_misses': self.stats.total_misses
        }

        if self.client:
            try:
                info = self.client.info('stats')
                stats.update({
                    'redis_hits': info.get('keyspace_hits', 0),
                    'redis_misses': info.get('keyspace_misses', 0),
                    'evicted_keys': info.get('evicted_keys', 0)
                })

                memory_info = self.client.info('memory')
                stats['memory_mb'] = memory_info.get('used_memory', 0) / (1024 * 1024)

            except:
                pass

        return stats


class MultiLevelCache:
    """
    Multi-level cache coordinator
    L1 (Memory) -> L2 (Redis) -> Source
    """

    def __init__(
        self,
        l1_max_size_mb: int = 500,
        l2_redis_url: str = "redis://localhost:6379",
        l2_redis_cluster: bool = False,
        default_ttl: int = 3600
    ):
        # Initialize cache levels
        self.l1 = L1MemoryCache(max_size_mb=l1_max_size_mb)
        self.l2 = L2RedisCache(
            redis_url=l2_redis_url,
            redis_cluster=l2_redis_cluster,
            default_ttl=default_ttl
        )

        # Connect L2
        self.l2.connect()

        logger.info("Multi-level cache initialized")

    async def get(
        self,
        key: str,
        fetch_func: Optional[Callable] = None
    ) -> Optional[Any]:
        """
        Get from cache with multi-level fallback

        Args:
            key: Cache key
            fetch_func: Function to fetch if not in cache
        """
        # Try L1
        value = self.l1.get(key)
        if value is not None:
            return value

        # Try L2
        value = self.l2.get(key)
        if value is not None:
            # Populate L1
            self.l1.set(key, value)
            return value

        # Fetch from source if provided
        if fetch_func:
            logger.debug(f"Cache miss, fetching: {key}")

            if asyncio.iscoroutinefunction(fetch_func):
                value = await fetch_func()
            else:
                value = fetch_func()

            if value is not None:
                # Populate all levels
                await self.set(key, value)

            return value

        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        tags: Optional[List[str]] = None
    ):
        """Set in all cache levels"""
        # Set in L1
        self.l1.set(key, value, ttl_seconds=ttl_seconds, tags=tags)

        # Set in L2
        self.l2.set(key, value, ttl_seconds=ttl_seconds, tags=tags)

    async def invalidate(self, key: str):
        """Invalidate key in all levels"""
        self.l1.invalidate(key)
        self.l2.invalidate(key)

    async def invalidate_by_tags(self, tags: List[str]):
        """Invalidate by tags in all levels"""
        self.l1.invalidate_by_tags(tags)
        self.l2.invalidate_by_tags(tags)

    async def clear(self):
        """Clear all levels"""
        self.l1.clear()
        self.l2.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics"""
        l1_stats = self.l1.get_stats()
        l2_stats = self.l2.get_stats()

        total_hits = l1_stats['total_hits'] + l2_stats['total_hits']
        total_misses = max(l1_stats['total_misses'], l2_stats['total_misses'])

        return {
            'overall_hit_rate': (total_hits / (total_hits + total_misses) * 100) if (total_hits + total_misses) > 0 else 0.0,
            'l1': l1_stats,
            'l2': l2_stats
        }


class CacheWarmer:
    """
    Cache warming and preloading
    """

    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self.warming_tasks: Dict[str, asyncio.Task] = {}

    async def warm_keys(
        self,
        keys: List[str],
        fetch_func: Callable,
        batch_size: int = 10
    ):
        """
        Warm cache with keys

        Args:
            keys: Keys to warm
            fetch_func: Function to fetch values
            batch_size: Batch size for parallel fetching
        """
        logger.info(f"Warming cache with {len(keys)} keys")

        # Process in batches
        for i in range(0, len(keys), batch_size):
            batch = keys[i:i + batch_size]

            tasks = [
                self._warm_single_key(key, fetch_func)
                for key in batch
            ]

            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"Cache warming completed for {len(keys)} keys")

    async def _warm_single_key(self, key: str, fetch_func: Callable):
        """Warm single key"""
        try:
            # Check if already cached
            value = await self.cache.get(key)

            if value is None:
                # Fetch and cache
                if asyncio.iscoroutinefunction(fetch_func):
                    value = await fetch_func(key)
                else:
                    value = fetch_func(key)

                if value is not None:
                    await self.cache.set(key, value)

                logger.debug(f"Warmed key: {key}")

        except Exception as e:
            logger.error(f"Failed to warm key {key}: {e}")

    async def continuous_warming(
        self,
        keys: List[str],
        fetch_func: Callable,
        interval_seconds: int = 300
    ):
        """
        Continuously warm cache at intervals

        Args:
            keys: Keys to warm
            fetch_func: Function to fetch values
            interval_seconds: Warming interval
        """
        while True:
            await self.warm_keys(keys, fetch_func)
            await asyncio.sleep(interval_seconds)


# Example usage
async def main():
    """Example distributed cache usage"""
    # Initialize multi-level cache
    cache = MultiLevelCache(
        l1_max_size_mb=500,
        l2_redis_url="redis://localhost:6379",
        default_ttl=3600
    )

    # Example fetch function
    async def fetch_data(key):
        # Simulate data fetch
        await asyncio.sleep(0.1)
        return f"Data for {key}"

    # Set value
    await cache.set("test_key", {"value": 123}, ttl_seconds=300, tags=["test"])

    # Get value (L1 hit)
    value1 = await cache.get("test_key")
    print(f"Value 1: {value1}")

    # Get value (with fetch fallback)
    value2 = await cache.get("missing_key", lambda: fetch_data("missing_key"))
    print(f"Value 2: {value2}")

    # Invalidate by tag
    await cache.invalidate_by_tags(["test"])

    # Get stats
    stats = cache.get_stats()
    print(f"Cache stats: {json.dumps(stats, indent=2)}")

    # Cache warming
    warmer = CacheWarmer(cache)
    await warmer.warm_keys(
        keys=["key1", "key2", "key3"],
        fetch_func=fetch_data,
        batch_size=2
    )


if __name__ == "__main__":
    asyncio.run(main())
