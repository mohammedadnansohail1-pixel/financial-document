"""
Model Serving API
FastAPI server for model inference endpoints
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
import logging
import numpy as np
from datetime import datetime
import asyncio

from src.serving.model_server import ModelServer, ModelType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Model Serving API",
    description="Production model serving for financial intelligence",
    version="1.0.0"
)

# Global model server instance
model_server: Optional[ModelServer] = None


# Request/Response models
class EmbeddingRequest(BaseModel):
    """Embedding request"""
    texts: Union[str, List[str]]
    model_id: str = "financial-embeddings"
    batch_size: int = Field(32, ge=1, le=128)
    version: Optional[str] = None


class EmbeddingResponse(BaseModel):
    """Embedding response"""
    embeddings: List[List[float]]
    model_id: str
    count: int
    latency_ms: float
    timestamp: str


class ClassificationRequest(BaseModel):
    """Classification request"""
    texts: Union[str, List[str]]
    model_id: str = "sentiment-classifier"
    batch_size: int = Field(8, ge=1, le=64)
    version: Optional[str] = None


class ClassificationResponse(BaseModel):
    """Classification response"""
    predictions: List[Dict[str, Any]]
    model_id: str
    count: int
    latency_ms: float
    timestamp: str


class ModelRegistrationRequest(BaseModel):
    """Model registration request"""
    model_id: str
    model_name: str
    model_type: str
    version: str = "1.0.0"
    num_labels: Optional[int] = None


class ModelStatsResponse(BaseModel):
    """Model statistics response"""
    model_id: str
    version: str
    type: str
    status: str
    device: str
    loaded_at: Optional[str]
    memory_mb: float
    inference_count: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float


class ServerStatsResponse(BaseModel):
    """Server statistics response"""
    models: List[Dict[str, Any]]
    cache: Dict[str, Any]
    queue: Dict[str, Any]
    device: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    models_loaded: int
    cache_utilization: float
    timestamp: str


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize model server on startup"""
    global model_server

    logger.info("Starting model serving API")

    # Initialize model server
    model_server = ModelServer(
        max_cached_models=5,
        max_memory_mb=8000,
        device="cpu"  # Change to "cuda" if GPU available
    )

    # Register default models
    try:
        # Embedding model
        model_server.register_embedding_model(
            model_id="financial-embeddings",
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            version="1.0.0"
        )

        logger.info("Default models registered successfully")

    except Exception as e:
        logger.error(f"Failed to register default models: {e}")

    logger.info("Model serving API started successfully")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global model_server

    if model_server:
        model_server.cache.clear()
        logger.info("Model server shutdown complete")


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    if not model_server:
        raise HTTPException(status_code=503, detail="Model server not initialized")

    stats = model_server.get_server_stats()

    return HealthResponse(
        status="healthy",
        models_loaded=len(stats['models']),
        cache_utilization=stats['cache']['utilization'],
        timestamp=datetime.now().isoformat()
    )


# Embedding endpoint
@app.post("/embed", response_model=EmbeddingResponse)
async def generate_embeddings(request: EmbeddingRequest):
    """
    Generate embeddings for texts

    Args:
        request: Embedding request with texts and model configuration

    Returns:
        Embeddings and metadata
    """
    if not model_server:
        raise HTTPException(status_code=503, detail="Model server not initialized")

    try:
        import time
        start_time = time.time()

        # Generate embeddings
        embeddings = await model_server.embed(
            model_id=request.model_id,
            texts=request.texts,
            batch_size=request.batch_size,
            version=request.version
        )

        latency_ms = (time.time() - start_time) * 1000

        # Convert to list for JSON serialization
        embeddings_list = embeddings.tolist()

        return EmbeddingResponse(
            embeddings=embeddings_list,
            model_id=request.model_id,
            count=len(embeddings_list),
            latency_ms=latency_ms,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Classification endpoint
@app.post("/classify", response_model=ClassificationResponse)
async def classify_texts(request: ClassificationRequest):
    """
    Classify texts

    Args:
        request: Classification request with texts and model configuration

    Returns:
        Classification predictions and metadata
    """
    if not model_server:
        raise HTTPException(status_code=503, detail="Model server not initialized")

    try:
        import time
        start_time = time.time()

        # Classify
        predictions = await model_server.classify(
            model_id=request.model_id,
            texts=request.texts,
            batch_size=request.batch_size,
            version=request.version
        )

        latency_ms = (time.time() - start_time) * 1000

        return ClassificationResponse(
            predictions=predictions,
            model_id=request.model_id,
            count=len(predictions),
            latency_ms=latency_ms,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Classification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Model registration endpoint
@app.post("/models/register")
async def register_model(request: ModelRegistrationRequest):
    """
    Register new model

    Args:
        request: Model registration request
    """
    if not model_server:
        raise HTTPException(status_code=503, detail="Model server not initialized")

    try:
        if request.model_type == "embedding":
            metadata = model_server.register_embedding_model(
                model_id=request.model_id,
                model_name=request.model_name,
                version=request.version
            )
        elif request.model_type == "classification":
            if not request.num_labels:
                raise ValueError("num_labels required for classification model")

            metadata = model_server.register_classification_model(
                model_id=request.model_id,
                model_name=request.model_name,
                num_labels=request.num_labels,
                version=request.version
            )
        else:
            raise ValueError(f"Unsupported model type: {request.model_type}")

        return {
            'status': 'success',
            'model_id': metadata.model_id,
            'version': metadata.version,
            'model_status': metadata.status.value,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Model registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Model statistics endpoint
@app.get("/models/{model_id}/stats", response_model=ModelStatsResponse)
async def get_model_stats(model_id: str):
    """
    Get model statistics

    Args:
        model_id: Model identifier
    """
    if not model_server:
        raise HTTPException(status_code=503, detail="Model server not initialized")

    stats = model_server.get_model_stats(model_id)

    if not stats:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")

    return ModelStatsResponse(**stats)


# Server statistics endpoint
@app.get("/stats", response_model=ServerStatsResponse)
async def get_server_stats():
    """Get server statistics"""
    if not model_server:
        raise HTTPException(status_code=503, detail="Model server not initialized")

    stats = model_server.get_server_stats()

    return ServerStatsResponse(**stats)


# List models endpoint
@app.get("/models")
async def list_models():
    """List all registered models"""
    if not model_server:
        raise HTTPException(status_code=503, detail="Model server not initialized")

    models = model_server.registry.list_models()

    return {
        'models': models,
        'count': len(models),
        'timestamp': datetime.now().isoformat()
    }


# Batch embedding endpoint (for large batches)
@app.post("/embed/batch")
async def batch_embed(
    texts: List[str],
    model_id: str = "financial-embeddings",
    batch_size: int = 32,
    background_tasks: BackgroundTasks = None
):
    """
    Batch embedding endpoint for large-scale processing

    Args:
        texts: List of texts
        model_id: Model to use
        batch_size: Batch size for processing
    """
    if not model_server:
        raise HTTPException(status_code=503, detail="Model server not initialized")

    if len(texts) > 10000:
        # For very large batches, process in background
        if background_tasks:
            task_id = f"batch_{datetime.now().timestamp()}"

            async def process_batch():
                logger.info(f"Processing batch {task_id} with {len(texts)} texts")
                embeddings = await model_server.embed(
                    model_id=model_id,
                    texts=texts,
                    batch_size=batch_size
                )
                logger.info(f"Batch {task_id} completed")

            background_tasks.add_task(process_batch)

            return {
                'status': 'processing',
                'task_id': task_id,
                'count': len(texts),
                'message': 'Batch processing started'
            }

    # For smaller batches, process immediately
    try:
        embeddings = await model_server.embed(
            model_id=model_id,
            texts=texts,
            batch_size=batch_size
        )

        return {
            'status': 'completed',
            'count': len(embeddings),
            'embedding_dim': embeddings.shape[1],
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Batch embedding failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        'service': 'Model Serving API',
        'version': '1.0.0',
        'endpoints': [
            '/health',
            '/embed',
            '/classify',
            '/embed/batch',
            '/models',
            '/models/register',
            '/models/{model_id}/stats',
            '/stats'
        ]
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        log_level="info"
    )
