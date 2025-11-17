"""
Edge Server
Lightweight FastAPI server for edge deployment
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
import os
from datetime import datetime
import asyncio

from src.edge.edge_coordinator import EdgeCoordinator, EdgeNodeManager, SyncStrategy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Financial RAG Edge Server",
    description="Lightweight edge deployment for distributed financial intelligence",
    version="1.0.0"
)

# Configuration from environment
CENTRAL_ENDPOINT = os.getenv('CENTRAL_ENDPOINT', 'http://central-api:8000')
NODE_ID = os.getenv('NODE_ID', 'edge-node-1')
REGION = os.getenv('REGION', 'us-east')
CACHE_SIZE_MB = int(os.getenv('CACHE_SIZE_MB', '500'))

# Global coordinator instance
coordinator: Optional[EdgeCoordinator] = None


# Request/Response models
class QueryRequest(BaseModel):
    """Query request"""
    query: str
    region: Optional[str] = None
    use_cache: bool = True


class QueryResponse(BaseModel):
    """Query response"""
    status: str
    source: str
    result: Dict[str, Any]
    latency_ms: float
    timestamp: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    node_id: str
    region: str
    uptime_seconds: float
    cache_stats: Dict[str, Any]


class SyncRequest(BaseModel):
    """Sync request"""
    force_full: bool = False


class HeartbeatRequest(BaseModel):
    """Heartbeat request"""
    metrics: Optional[Dict[str, Any]] = None


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize edge coordinator on startup"""
    global coordinator

    logger.info(f"Starting edge server: {NODE_ID} in {REGION}")

    coordinator = EdgeCoordinator(
        central_endpoint=CENTRAL_ENDPOINT,
        local_cache_size_mb=CACHE_SIZE_MB
    )

    # Register this node with central coordinator
    coordinator.node_manager.register_node(
        node_id=NODE_ID,
        region=REGION,
        endpoint=f"http://{NODE_ID}:8001",
        capabilities=['query', 'retrieval', 'cache'],
        sync_strategy=SyncStrategy.INCREMENTAL
    )

    # Start coordinator
    await coordinator.start()

    logger.info("Edge coordinator started successfully")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global coordinator

    if coordinator:
        await coordinator.stop()
        logger.info("Edge coordinator stopped")


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    """
    if not coordinator:
        raise HTTPException(status_code=503, detail="Coordinator not initialized")

    stats = coordinator.get_coordinator_stats()

    return HealthResponse(
        status="healthy",
        node_id=NODE_ID,
        region=REGION,
        uptime_seconds=0.0,  # In production: track actual uptime
        cache_stats=stats['cache']
    )


# Query endpoint
@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Process query at edge

    Args:
        request: Query request with query text and optional region
    """
    if not coordinator:
        raise HTTPException(status_code=503, detail="Coordinator not initialized")

    try:
        result = await coordinator.process_query_at_edge(
            query=request.query,
            region=request.region or REGION
        )

        return QueryResponse(
            status=result['status'],
            source=result['source'],
            result=result['result'],
            latency_ms=result['latency_ms'],
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Sync endpoint
@app.post("/sync")
async def sync_node(request: SyncRequest):
    """
    Trigger node synchronization

    Args:
        request: Sync request with optional force_full flag
    """
    if not coordinator:
        raise HTTPException(status_code=503, detail="Coordinator not initialized")

    try:
        result = await coordinator.node_manager.sync_node(
            node_id=NODE_ID,
            force_full_sync=request.force_full
        )

        return {
            'status': 'success',
            'sync_result': result,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Heartbeat endpoint
@app.post("/heartbeat")
async def heartbeat(request: HeartbeatRequest):
    """
    Send heartbeat to coordinator

    Args:
        request: Heartbeat with optional metrics
    """
    if not coordinator:
        raise HTTPException(status_code=503, detail="Coordinator not initialized")

    try:
        await coordinator.node_manager.heartbeat(
            node_id=NODE_ID,
            metrics=request.metrics
        )

        return {
            'status': 'success',
            'node_id': NODE_ID,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Heartbeat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Stats endpoint
@app.get("/stats")
async def get_stats():
    """
    Get edge node statistics
    """
    if not coordinator:
        raise HTTPException(status_code=503, detail="Coordinator not initialized")

    try:
        stats = coordinator.get_coordinator_stats()

        return {
            'node_id': NODE_ID,
            'region': REGION,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Cache management endpoint
@app.post("/cache/clear")
async def clear_cache():
    """Clear local cache"""
    if not coordinator:
        raise HTTPException(status_code=503, detail="Coordinator not initialized")

    try:
        coordinator.local_cache.clear()

        return {
            'status': 'success',
            'message': 'Cache cleared',
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with server info"""
    return {
        'service': 'Financial RAG Edge Server',
        'version': '1.0.0',
        'node_id': NODE_ID,
        'region': REGION,
        'endpoints': [
            '/health',
            '/query',
            '/sync',
            '/heartbeat',
            '/stats',
            '/cache/clear'
        ]
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )
