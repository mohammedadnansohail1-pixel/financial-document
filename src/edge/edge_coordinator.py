"""
Edge Node Coordinator
Manages edge deployment nodes and sync with central cluster
"""

import logging
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EdgeNodeStatus(Enum):
    """Edge node status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    SYNCING = "syncing"


class SyncStrategy(Enum):
    """Data synchronization strategy"""
    FULL_SYNC = "full_sync"
    INCREMENTAL = "incremental"
    SELECTIVE = "selective"
    ON_DEMAND = "on_demand"


@dataclass
class EdgeNode:
    """Edge node configuration"""
    node_id: str
    region: str
    endpoint: str
    capabilities: List[str]
    status: EdgeNodeStatus = EdgeNodeStatus.HEALTHY
    last_sync: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    local_cache_size: int = 0
    sync_strategy: SyncStrategy = SyncStrategy.INCREMENTAL


@dataclass
class SyncTask:
    """Synchronization task"""
    task_id: str
    node_id: str
    data_type: str
    priority: int
    created_at: datetime
    status: str = "pending"
    progress: float = 0.0
    error: Optional[str] = None


class EdgeCache:
    """
    Local cache management for edge nodes
    """

    def __init__(self, max_size_mb: int = 1000):
        self.max_size_mb = max_size_mb
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, datetime] = {}
        self.current_size_mb = 0

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get from cache"""
        if key in self.cache:
            self.access_times[key] = datetime.now()
            logger.debug(f"Cache hit: {key}")
            return self.cache[key]

        logger.debug(f"Cache miss: {key}")
        return None

    def put(self, key: str, value: Dict[str, Any], size_mb: float):
        """Put into cache with LRU eviction"""
        # Evict if necessary
        while self.current_size_mb + size_mb > self.max_size_mb and self.cache:
            self._evict_lru()

        self.cache[key] = value
        self.access_times[key] = datetime.now()
        self.current_size_mb += size_mb

        logger.debug(f"Cached: {key} ({size_mb:.2f}MB)")

    def _evict_lru(self):
        """Evict least recently used item"""
        if not self.access_times:
            return

        lru_key = min(self.access_times.items(), key=lambda x: x[1])[0]

        # Estimate size (simplified)
        estimated_size = len(json.dumps(self.cache[lru_key])) / (1024 * 1024)

        del self.cache[lru_key]
        del self.access_times[lru_key]
        self.current_size_mb -= estimated_size

        logger.debug(f"Evicted: {lru_key}")

    def clear(self):
        """Clear cache"""
        self.cache.clear()
        self.access_times.clear()
        self.current_size_mb = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'size_mb': self.current_size_mb,
            'max_size_mb': self.max_size_mb,
            'item_count': len(self.cache),
            'utilization': (self.current_size_mb / self.max_size_mb) * 100
        }


class EdgeDataSync:
    """
    Data synchronization between edge and central cluster
    """

    def __init__(self, central_endpoint: str):
        self.central_endpoint = central_endpoint
        self.sync_queue: List[SyncTask] = []
        self.sync_history: Dict[str, datetime] = {}

    async def sync_documents(
        self,
        node_id: str,
        strategy: SyncStrategy = SyncStrategy.INCREMENTAL
    ) -> Dict[str, Any]:
        """
        Sync documents with central cluster

        Args:
            node_id: Edge node ID
            strategy: Synchronization strategy
        """
        logger.info(f"Starting document sync for node {node_id} with strategy {strategy.value}")

        try:
            if strategy == SyncStrategy.FULL_SYNC:
                return await self._full_sync(node_id)
            elif strategy == SyncStrategy.INCREMENTAL:
                return await self._incremental_sync(node_id)
            elif strategy == SyncStrategy.SELECTIVE:
                return await self._selective_sync(node_id)
            else:  # ON_DEMAND
                return await self._on_demand_sync(node_id)

        except Exception as e:
            logger.error(f"Sync failed for node {node_id}: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }

    async def _full_sync(self, node_id: str) -> Dict[str, Any]:
        """Full synchronization"""
        # In production: fetch all documents from central
        async with aiohttp.ClientSession() as session:
            # Simulated full sync
            logger.info(f"Full sync for {node_id}")

            # Would fetch all documents
            # async with session.get(f"{self.central_endpoint}/documents") as resp:
            #     documents = await resp.json()

            return {
                'status': 'completed',
                'strategy': 'full_sync',
                'documents_synced': 0,  # In production: actual count
                'timestamp': datetime.now().isoformat()
            }

    async def _incremental_sync(self, node_id: str) -> Dict[str, Any]:
        """Incremental synchronization (only new/updated documents)"""
        last_sync = self.sync_history.get(node_id)

        if not last_sync:
            # First sync - do full sync
            return await self._full_sync(node_id)

        logger.info(f"Incremental sync for {node_id} since {last_sync}")

        async with aiohttp.ClientSession() as session:
            # In production: fetch documents updated since last_sync
            # params = {'since': last_sync.isoformat()}
            # async with session.get(f"{self.central_endpoint}/documents", params=params) as resp:
            #     documents = await resp.json()

            self.sync_history[node_id] = datetime.now()

            return {
                'status': 'completed',
                'strategy': 'incremental',
                'documents_synced': 0,  # In production: actual count
                'last_sync': last_sync.isoformat() if last_sync else None,
                'timestamp': datetime.now().isoformat()
            }

    async def _selective_sync(self, node_id: str) -> Dict[str, Any]:
        """Selective sync (only documents matching criteria)"""
        logger.info(f"Selective sync for {node_id}")

        # In production: sync based on node region/capabilities
        # For example, only sync documents relevant to node's region

        return {
            'status': 'completed',
            'strategy': 'selective',
            'documents_synced': 0,
            'timestamp': datetime.now().isoformat()
        }

    async def _on_demand_sync(self, node_id: str) -> Dict[str, Any]:
        """On-demand sync (triggered by specific requests)"""
        logger.info(f"On-demand sync for {node_id}")

        return {
            'status': 'completed',
            'strategy': 'on_demand',
            'documents_synced': 0,
            'timestamp': datetime.now().isoformat()
        }

    def create_sync_task(
        self,
        node_id: str,
        data_type: str,
        priority: int = 5
    ) -> SyncTask:
        """Create synchronization task"""
        task = SyncTask(
            task_id=hashlib.md5(f"{node_id}_{data_type}_{time.time()}".encode()).hexdigest(),
            node_id=node_id,
            data_type=data_type,
            priority=priority,
            created_at=datetime.now()
        )

        self.sync_queue.append(task)
        self.sync_queue.sort(key=lambda x: x.priority, reverse=True)

        return task

    def get_sync_status(self, task_id: str) -> Optional[SyncTask]:
        """Get sync task status"""
        for task in self.sync_queue:
            if task.task_id == task_id:
                return task
        return None


class EdgeNodeManager:
    """
    Manage multiple edge nodes
    """

    def __init__(self, central_endpoint: str):
        self.central_endpoint = central_endpoint
        self.nodes: Dict[str, EdgeNode] = {}
        self.data_sync = EdgeDataSync(central_endpoint)

    def register_node(
        self,
        node_id: str,
        region: str,
        endpoint: str,
        capabilities: List[str],
        sync_strategy: SyncStrategy = SyncStrategy.INCREMENTAL
    ) -> EdgeNode:
        """
        Register edge node

        Args:
            node_id: Unique node identifier
            region: Geographic region
            endpoint: Node endpoint URL
            capabilities: List of capabilities
            sync_strategy: Data sync strategy
        """
        node = EdgeNode(
            node_id=node_id,
            region=region,
            endpoint=endpoint,
            capabilities=capabilities,
            sync_strategy=sync_strategy,
            last_heartbeat=datetime.now()
        )

        self.nodes[node_id] = node
        logger.info(f"Registered edge node: {node_id} in {region}")

        return node

    def unregister_node(self, node_id: str):
        """Unregister edge node"""
        if node_id in self.nodes:
            del self.nodes[node_id]
            logger.info(f"Unregistered edge node: {node_id}")

    async def heartbeat(self, node_id: str, metrics: Optional[Dict[str, Any]] = None):
        """
        Process heartbeat from edge node

        Args:
            node_id: Node identifier
            metrics: Optional metrics data
        """
        if node_id not in self.nodes:
            logger.warning(f"Heartbeat from unknown node: {node_id}")
            return

        node = self.nodes[node_id]
        node.last_heartbeat = datetime.now()

        if metrics:
            node.metrics.update(metrics)

        # Update status based on heartbeat
        if node.status == EdgeNodeStatus.OFFLINE:
            node.status = EdgeNodeStatus.HEALTHY
            logger.info(f"Node {node_id} is back online")

    async def check_node_health(self):
        """Check health of all edge nodes"""
        now = datetime.now()
        timeout = timedelta(minutes=5)

        for node_id, node in self.nodes.items():
            if not node.last_heartbeat:
                continue

            time_since_heartbeat = now - node.last_heartbeat

            if time_since_heartbeat > timeout:
                if node.status != EdgeNodeStatus.OFFLINE:
                    node.status = EdgeNodeStatus.OFFLINE
                    logger.warning(f"Node {node_id} is offline (no heartbeat for {time_since_heartbeat})")

    async def sync_node(
        self,
        node_id: str,
        force_full_sync: bool = False
    ) -> Dict[str, Any]:
        """
        Synchronize node with central cluster

        Args:
            node_id: Node to sync
            force_full_sync: Force full synchronization
        """
        if node_id not in self.nodes:
            return {
                'status': 'error',
                'error': f'Node {node_id} not found'
            }

        node = self.nodes[node_id]
        node.status = EdgeNodeStatus.SYNCING

        strategy = SyncStrategy.FULL_SYNC if force_full_sync else node.sync_strategy

        try:
            result = await self.data_sync.sync_documents(node_id, strategy)

            node.last_sync = datetime.now()
            node.status = EdgeNodeStatus.HEALTHY

            return result

        except Exception as e:
            node.status = EdgeNodeStatus.DEGRADED
            logger.error(f"Sync failed for node {node_id}: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def sync_all_nodes(self):
        """Synchronize all nodes"""
        tasks = [
            self.sync_node(node_id)
            for node_id in self.nodes.keys()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if isinstance(r, dict) and r.get('status') == 'completed')

        logger.info(f"Synced {success_count}/{len(self.nodes)} nodes successfully")

        return {
            'total_nodes': len(self.nodes),
            'successful': success_count,
            'failed': len(self.nodes) - success_count
        }

    def get_node_status(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get node status"""
        if node_id not in self.nodes:
            return None

        node = self.nodes[node_id]

        return {
            'node_id': node.node_id,
            'region': node.region,
            'status': node.status.value,
            'capabilities': node.capabilities,
            'last_sync': node.last_sync.isoformat() if node.last_sync else None,
            'last_heartbeat': node.last_heartbeat.isoformat() if node.last_heartbeat else None,
            'metrics': node.metrics,
            'cache_size': node.local_cache_size
        }

    def get_all_nodes_status(self) -> List[Dict[str, Any]]:
        """Get status of all nodes"""
        return [
            self.get_node_status(node_id)
            for node_id in self.nodes.keys()
        ]

    def find_nearest_node(self, region: str) -> Optional[EdgeNode]:
        """
        Find nearest healthy edge node for a region

        Args:
            region: Target region
        """
        # Simple strategy: exact match first, then any healthy node
        for node in self.nodes.values():
            if node.region == region and node.status == EdgeNodeStatus.HEALTHY:
                return node

        # Fallback: any healthy node
        for node in self.nodes.values():
            if node.status == EdgeNodeStatus.HEALTHY:
                return node

        return None


class EdgeCoordinator:
    """
    Main edge deployment coordinator
    Orchestrates edge nodes and central cluster communication
    """

    def __init__(
        self,
        central_endpoint: str,
        local_cache_size_mb: int = 1000
    ):
        self.central_endpoint = central_endpoint
        self.node_manager = EdgeNodeManager(central_endpoint)
        self.local_cache = EdgeCache(max_size_mb=local_cache_size_mb)
        self.is_running = False

        logger.info(f"EdgeCoordinator initialized with central endpoint: {central_endpoint}")

    async def start(self):
        """Start edge coordinator"""
        self.is_running = True
        logger.info("Edge coordinator started")

        # Start background tasks
        asyncio.create_task(self._health_check_loop())
        asyncio.create_task(self._sync_loop())

    async def stop(self):
        """Stop edge coordinator"""
        self.is_running = False
        logger.info("Edge coordinator stopped")

    async def _health_check_loop(self):
        """Background health check loop"""
        while self.is_running:
            try:
                await self.node_manager.check_node_health()
            except Exception as e:
                logger.error(f"Health check error: {e}")

            await asyncio.sleep(60)  # Check every minute

    async def _sync_loop(self):
        """Background sync loop"""
        while self.is_running:
            try:
                await self.node_manager.sync_all_nodes()
            except Exception as e:
                logger.error(f"Sync loop error: {e}")

            await asyncio.sleep(300)  # Sync every 5 minutes

    async def process_query_at_edge(
        self,
        query: str,
        region: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process query at edge node

        Args:
            query: Search query
            region: Preferred region
        """
        # Check local cache first
        cache_key = hashlib.md5(query.encode()).hexdigest()
        cached = self.local_cache.get(cache_key)

        if cached:
            return {
                'status': 'success',
                'source': 'edge_cache',
                'result': cached,
                'latency_ms': 0
            }

        # Find appropriate edge node
        node = self.node_manager.find_nearest_node(region) if region else None

        if node:
            # Process at edge node
            start_time = time.time()

            try:
                async with aiohttp.ClientSession() as session:
                    # In production: forward to edge node
                    # async with session.post(f"{node.endpoint}/query", json={'query': query}) as resp:
                    #     result = await resp.json()

                    # Simulated result
                    result = {'answer': 'Edge processed response'}

                    latency = (time.time() - start_time) * 1000

                    # Cache result
                    self.local_cache.put(cache_key, result, 0.1)

                    return {
                        'status': 'success',
                        'source': f'edge_node_{node.node_id}',
                        'result': result,
                        'latency_ms': latency
                    }

            except Exception as e:
                logger.error(f"Edge query failed: {e}")
                # Fallback to central
                return await self._query_central(query)

        else:
            # No healthy edge node, query central
            return await self._query_central(query)

    async def _query_central(self, query: str) -> Dict[str, Any]:
        """Fallback to central cluster"""
        start_time = time.time()

        async with aiohttp.ClientSession() as session:
            # In production: query central endpoint
            # async with session.post(f"{self.central_endpoint}/query", json={'query': query}) as resp:
            #     result = await resp.json()

            # Simulated result
            result = {'answer': 'Central processed response'}

            latency = (time.time() - start_time) * 1000

            return {
                'status': 'success',
                'source': 'central_cluster',
                'result': result,
                'latency_ms': latency
            }

    def get_coordinator_stats(self) -> Dict[str, Any]:
        """Get coordinator statistics"""
        return {
            'nodes': self.node_manager.get_all_nodes_status(),
            'cache': self.local_cache.get_stats(),
            'is_running': self.is_running
        }


# Example usage
async def main():
    """Example edge coordinator usage"""
    coordinator = EdgeCoordinator(
        central_endpoint='http://central-api:8000',
        local_cache_size_mb=1000
    )

    # Register edge nodes
    coordinator.node_manager.register_node(
        node_id='edge-us-east-1',
        region='us-east',
        endpoint='http://edge-us-east-1:8000',
        capabilities=['query', 'retrieval'],
        sync_strategy=SyncStrategy.INCREMENTAL
    )

    coordinator.node_manager.register_node(
        node_id='edge-eu-west-1',
        region='eu-west',
        endpoint='http://edge-eu-west-1:8000',
        capabilities=['query', 'retrieval'],
        sync_strategy=SyncStrategy.SELECTIVE
    )

    # Start coordinator
    await coordinator.start()

    # Process queries at edge
    result = await coordinator.process_query_at_edge(
        query="What were Apple's Q4 2023 earnings?",
        region='us-east'
    )
    print(f"Query result: {json.dumps(result, indent=2)}")

    # Get stats
    stats = coordinator.get_coordinator_stats()
    print(f"Coordinator stats: {json.dumps(stats, indent=2)}")

    # Sync all nodes
    sync_result = await coordinator.node_manager.sync_all_nodes()
    print(f"Sync result: {json.dumps(sync_result, indent=2)}")

    await coordinator.stop()


if __name__ == "__main__":
    asyncio.run(main())
