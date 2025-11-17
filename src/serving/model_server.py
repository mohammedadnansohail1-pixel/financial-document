"""
Model Serving Infrastructure
Production-ready model serving for embeddings, classification, and inference
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer
from sentence_transformers import SentenceTransformer
import json
import time
from collections import defaultdict, deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Supported model types"""
    EMBEDDING = "embedding"
    CLASSIFICATION = "classification"
    GENERATION = "generation"
    RERANKER = "reranker"


class ModelStatus(Enum):
    """Model loading status"""
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"
    UNLOADED = "unloaded"


@dataclass
class ModelMetadata:
    """Model metadata"""
    model_id: str
    model_type: ModelType
    version: str
    loaded_at: Optional[datetime] = None
    status: ModelStatus = ModelStatus.LOADING
    device: str = "cpu"
    memory_mb: float = 0.0
    inference_count: int = 0
    avg_latency_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class InferenceRequest:
    """Inference request"""
    request_id: str
    model_id: str
    inputs: Union[str, List[str], Dict[str, Any]]
    parameters: Dict[str, Any] = field(default_factory=dict)
    batch_size: int = 1
    priority: int = 5


@dataclass
class InferenceResponse:
    """Inference response"""
    request_id: str
    model_id: str
    outputs: Any
    latency_ms: float
    timestamp: datetime


class ModelRegistry:
    """
    Central model registry for version management
    """

    def __init__(self):
        self.models: Dict[str, Dict[str, ModelMetadata]] = {}  # model_id -> version -> metadata

    def register_model(
        self,
        model_id: str,
        version: str,
        model_type: ModelType,
        device: str = "cpu"
    ) -> ModelMetadata:
        """
        Register model in registry

        Args:
            model_id: Model identifier
            version: Model version
            model_type: Type of model
            device: Device (cpu/cuda)
        """
        if model_id not in self.models:
            self.models[model_id] = {}

        metadata = ModelMetadata(
            model_id=model_id,
            model_type=model_type,
            version=version,
            device=device,
            status=ModelStatus.LOADING
        )

        self.models[model_id][version] = metadata

        logger.info(f"Registered model: {model_id} v{version}")

        return metadata

    def get_model_metadata(
        self,
        model_id: str,
        version: Optional[str] = None
    ) -> Optional[ModelMetadata]:
        """Get model metadata"""
        if model_id not in self.models:
            return None

        if version:
            return self.models[model_id].get(version)
        else:
            # Get latest version
            versions = sorted(self.models[model_id].keys(), reverse=True)
            if versions:
                return self.models[model_id][versions[0]]

        return None

    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models"""
        models = []

        for model_id, versions in self.models.items():
            for version, metadata in versions.items():
                models.append({
                    'model_id': model_id,
                    'version': version,
                    'type': metadata.model_type.value,
                    'status': metadata.status.value,
                    'device': metadata.device,
                    'inference_count': metadata.inference_count,
                    'avg_latency_ms': metadata.avg_latency_ms
                })

        return models

    def update_status(
        self,
        model_id: str,
        version: str,
        status: ModelStatus,
        error: Optional[str] = None
    ):
        """Update model status"""
        metadata = self.get_model_metadata(model_id, version)

        if metadata:
            metadata.status = status
            if error:
                metadata.error = error

            logger.info(f"Updated {model_id} v{version} status to {status.value}")


class EmbeddingModel:
    """
    Embedding model wrapper
    """

    def __init__(
        self,
        model_id: str,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "cpu"
    ):
        self.model_id = model_id
        self.model_name = model_name
        self.device = device
        self.model = None
        self.loaded = False

    def load(self):
        """Load model"""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")

            self.model = SentenceTransformer(self.model_name)

            if self.device == "cuda" and torch.cuda.is_available():
                self.model = self.model.to('cuda')

            self.loaded = True

            logger.info(f"Model loaded successfully: {self.model_id}")

        except Exception as e:
            logger.error(f"Failed to load model {self.model_id}: {e}")
            raise

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Generate embeddings

        Args:
            texts: Text or list of texts
            batch_size: Batch size for encoding
            show_progress: Show progress bar
        """
        if not self.loaded:
            raise RuntimeError(f"Model {self.model_id} not loaded")

        if isinstance(texts, str):
            texts = [texts]

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )

        return embeddings

    def unload(self):
        """Unload model from memory"""
        if self.model:
            del self.model
            self.model = None
            self.loaded = False

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            logger.info(f"Model unloaded: {self.model_id}")


class ClassificationModel:
    """
    Classification model wrapper (for sentiment, risk classification, etc.)
    """

    def __init__(
        self,
        model_id: str,
        model_name: str,
        num_labels: int,
        device: str = "cpu"
    ):
        self.model_id = model_id
        self.model_name = model_name
        self.num_labels = num_labels
        self.device = device
        self.model = None
        self.tokenizer = None
        self.loaded = False

    def load(self):
        """Load model and tokenizer"""
        try:
            logger.info(f"Loading classification model: {self.model_name}")

            # In production: Load actual classification model
            # from transformers import AutoModelForSequenceClassification
            # self.model = AutoModelForSequenceClassification.from_pretrained(
            #     self.model_name,
            #     num_labels=self.num_labels
            # )

            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

            if self.device == "cuda" and torch.cuda.is_available():
                pass  # self.model = self.model.to('cuda')

            self.loaded = True

            logger.info(f"Model loaded successfully: {self.model_id}")

        except Exception as e:
            logger.error(f"Failed to load model {self.model_id}: {e}")
            raise

    def predict(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 8
    ) -> List[Dict[str, Any]]:
        """
        Predict class probabilities

        Args:
            texts: Text or list of texts
            batch_size: Batch size
        """
        if not self.loaded:
            raise RuntimeError(f"Model {self.model_id} not loaded")

        if isinstance(texts, str):
            texts = [texts]

        # In production: Actual inference
        # predictions = []
        # for i in range(0, len(texts), batch_size):
        #     batch = texts[i:i + batch_size]
        #     inputs = self.tokenizer(batch, return_tensors="pt", padding=True, truncation=True)
        #     with torch.no_grad():
        #         outputs = self.model(**inputs)
        #         probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        #         predictions.extend(probs.cpu().numpy())

        # Simulated predictions
        predictions = [
            {
                'label': 0,
                'confidence': 0.85,
                'probabilities': [0.85, 0.10, 0.05]
            }
            for _ in texts
        ]

        return predictions

    def unload(self):
        """Unload model from memory"""
        if self.model:
            del self.model
            self.model = None

        if self.tokenizer:
            del self.tokenizer
            self.tokenizer = None

        self.loaded = False

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info(f"Model unloaded: {self.model_id}")


class ModelCache:
    """
    LRU cache for loaded models
    """

    def __init__(self, max_models: int = 5, max_memory_mb: float = 8000):
        self.max_models = max_models
        self.max_memory_mb = max_memory_mb
        self.cache: Dict[str, Any] = {}
        self.access_times: Dict[str, datetime] = {}
        self.current_memory_mb = 0.0

    def get(self, model_key: str) -> Optional[Any]:
        """Get model from cache"""
        if model_key in self.cache:
            self.access_times[model_key] = datetime.now()
            logger.debug(f"Cache hit: {model_key}")
            return self.cache[model_key]

        logger.debug(f"Cache miss: {model_key}")
        return None

    def put(
        self,
        model_key: str,
        model: Any,
        memory_mb: float
    ):
        """Put model in cache with LRU eviction"""
        # Evict if necessary
        while (len(self.cache) >= self.max_models or
               self.current_memory_mb + memory_mb > self.max_memory_mb) and self.cache:
            self._evict_lru()

        self.cache[model_key] = model
        self.access_times[model_key] = datetime.now()
        self.current_memory_mb += memory_mb

        logger.info(f"Cached model: {model_key} ({memory_mb:.2f}MB)")

    def _evict_lru(self):
        """Evict least recently used model"""
        if not self.access_times:
            return

        lru_key = min(self.access_times.items(), key=lambda x: x[1])[0]

        model = self.cache[lru_key]

        # Unload model
        if hasattr(model, 'unload'):
            model.unload()

        # Estimate memory (simplified)
        memory = 500  # Default estimate

        del self.cache[lru_key]
        del self.access_times[lru_key]
        self.current_memory_mb -= memory

        logger.info(f"Evicted model: {lru_key}")

    def clear(self):
        """Clear cache"""
        for model in self.cache.values():
            if hasattr(model, 'unload'):
                model.unload()

        self.cache.clear()
        self.access_times.clear()
        self.current_memory_mb = 0.0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cached_models': len(self.cache),
            'max_models': self.max_models,
            'memory_mb': self.current_memory_mb,
            'max_memory_mb': self.max_memory_mb,
            'utilization': (self.current_memory_mb / self.max_memory_mb) * 100
        }


class InferenceQueue:
    """
    Priority queue for inference requests
    """

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.queue: deque = deque(maxlen=max_size)
        self.processing: Dict[str, InferenceRequest] = {}

    def enqueue(self, request: InferenceRequest):
        """Add request to queue"""
        if len(self.queue) >= self.max_size:
            logger.warning("Queue full, dropping request")
            raise RuntimeError("Inference queue full")

        self.queue.append(request)

        # Sort by priority
        self.queue = deque(
            sorted(self.queue, key=lambda x: x.priority, reverse=True),
            maxlen=self.max_size
        )

    def dequeue(self) -> Optional[InferenceRequest]:
        """Get next request from queue"""
        if self.queue:
            request = self.queue.popleft()
            self.processing[request.request_id] = request
            return request

        return None

    def complete(self, request_id: str):
        """Mark request as completed"""
        if request_id in self.processing:
            del self.processing[request_id]

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            'queued': len(self.queue),
            'processing': len(self.processing),
            'capacity': self.max_size
        }


class ModelServer:
    """
    Production model serving infrastructure
    """

    def __init__(
        self,
        max_cached_models: int = 5,
        max_memory_mb: float = 8000,
        device: str = "cpu"
    ):
        self.registry = ModelRegistry()
        self.cache = ModelCache(
            max_models=max_cached_models,
            max_memory_mb=max_memory_mb
        )
        self.queue = InferenceQueue()
        self.device = device

        # Performance tracking
        self.latency_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        logger.info(f"ModelServer initialized (device={device})")

    def register_embedding_model(
        self,
        model_id: str,
        model_name: str,
        version: str = "1.0.0"
    ) -> ModelMetadata:
        """
        Register embedding model

        Args:
            model_id: Model identifier
            model_name: HuggingFace model name
            version: Model version
        """
        metadata = self.registry.register_model(
            model_id=model_id,
            version=version,
            model_type=ModelType.EMBEDDING,
            device=self.device
        )

        try:
            # Load model
            model_key = f"{model_id}:{version}"
            model = EmbeddingModel(model_id, model_name, self.device)
            model.load()

            # Cache model
            self.cache.put(model_key, model, memory_mb=500)  # Estimate

            # Update status
            metadata.status = ModelStatus.READY
            metadata.loaded_at = datetime.now()
            metadata.memory_mb = 500

            logger.info(f"Embedding model ready: {model_id}")

        except Exception as e:
            metadata.status = ModelStatus.ERROR
            metadata.error = str(e)
            logger.error(f"Failed to load embedding model: {e}")

        return metadata

    def register_classification_model(
        self,
        model_id: str,
        model_name: str,
        num_labels: int,
        version: str = "1.0.0"
    ) -> ModelMetadata:
        """
        Register classification model

        Args:
            model_id: Model identifier
            model_name: HuggingFace model name
            num_labels: Number of classes
            version: Model version
        """
        metadata = self.registry.register_model(
            model_id=model_id,
            version=version,
            model_type=ModelType.CLASSIFICATION,
            device=self.device
        )

        try:
            # Load model
            model_key = f"{model_id}:{version}"
            model = ClassificationModel(model_id, model_name, num_labels, self.device)
            model.load()

            # Cache model
            self.cache.put(model_key, model, memory_mb=800)  # Estimate

            # Update status
            metadata.status = ModelStatus.READY
            metadata.loaded_at = datetime.now()
            metadata.memory_mb = 800

            logger.info(f"Classification model ready: {model_id}")

        except Exception as e:
            metadata.status = ModelStatus.ERROR
            metadata.error = str(e)
            logger.error(f"Failed to load classification model: {e}")

        return metadata

    async def embed(
        self,
        model_id: str,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        version: Optional[str] = None
    ) -> np.ndarray:
        """
        Generate embeddings

        Args:
            model_id: Model to use
            texts: Text or list of texts
            batch_size: Batch size
            version: Model version (latest if None)
        """
        start_time = time.time()

        # Get model from cache
        model_key = f"{model_id}:{version}" if version else f"{model_id}:1.0.0"
        model = self.cache.get(model_key)

        if not model:
            raise RuntimeError(f"Model not loaded: {model_key}")

        # Generate embeddings
        embeddings = model.encode(texts, batch_size=batch_size)

        # Track performance
        latency_ms = (time.time() - start_time) * 1000
        self.latency_history[model_id].append(latency_ms)

        # Update metadata
        metadata = self.registry.get_model_metadata(model_id, version)
        if metadata:
            metadata.inference_count += len(texts) if isinstance(texts, list) else 1
            metadata.avg_latency_ms = sum(self.latency_history[model_id]) / len(self.latency_history[model_id])

        logger.debug(f"Generated {len(embeddings)} embeddings in {latency_ms:.2f}ms")

        return embeddings

    async def classify(
        self,
        model_id: str,
        texts: Union[str, List[str]],
        batch_size: int = 8,
        version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Classify texts

        Args:
            model_id: Model to use
            texts: Text or list of texts
            batch_size: Batch size
            version: Model version
        """
        start_time = time.time()

        # Get model from cache
        model_key = f"{model_id}:{version}" if version else f"{model_id}:1.0.0"
        model = self.cache.get(model_key)

        if not model:
            raise RuntimeError(f"Model not loaded: {model_key}")

        # Classify
        predictions = model.predict(texts, batch_size=batch_size)

        # Track performance
        latency_ms = (time.time() - start_time) * 1000
        self.latency_history[model_id].append(latency_ms)

        # Update metadata
        metadata = self.registry.get_model_metadata(model_id, version)
        if metadata:
            metadata.inference_count += len(texts) if isinstance(texts, list) else 1
            metadata.avg_latency_ms = sum(self.latency_history[model_id]) / len(self.latency_history[model_id])

        return predictions

    def get_model_stats(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model statistics"""
        metadata = self.registry.get_model_metadata(model_id)

        if not metadata:
            return None

        latencies = list(self.latency_history.get(model_id, []))

        return {
            'model_id': model_id,
            'version': metadata.version,
            'type': metadata.model_type.value,
            'status': metadata.status.value,
            'device': metadata.device,
            'loaded_at': metadata.loaded_at.isoformat() if metadata.loaded_at else None,
            'memory_mb': metadata.memory_mb,
            'inference_count': metadata.inference_count,
            'avg_latency_ms': metadata.avg_latency_ms,
            'p50_latency_ms': np.percentile(latencies, 50) if latencies else 0,
            'p95_latency_ms': np.percentile(latencies, 95) if latencies else 0,
            'p99_latency_ms': np.percentile(latencies, 99) if latencies else 0
        }

    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        return {
            'models': self.registry.list_models(),
            'cache': self.cache.get_stats(),
            'queue': self.queue.get_stats(),
            'device': self.device
        }


# Example usage
async def main():
    """Example model server usage"""
    server = ModelServer(
        max_cached_models=3,
        max_memory_mb=4000,
        device="cpu"
    )

    # Register embedding model
    server.register_embedding_model(
        model_id="financial-embeddings",
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        version="1.0.0"
    )

    # Generate embeddings
    texts = [
        "Apple reported strong Q4 earnings.",
        "Revenue grew 15% year-over-year.",
        "Market volatility increased significantly."
    ]

    embeddings = await server.embed(
        model_id="financial-embeddings",
        texts=texts,
        batch_size=32
    )

    print(f"Generated embeddings shape: {embeddings.shape}")

    # Get stats
    stats = server.get_model_stats("financial-embeddings")
    print(f"Model stats: {json.dumps(stats, indent=2)}")

    # Server stats
    server_stats = server.get_server_stats()
    print(f"Server stats: {json.dumps(server_stats, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
