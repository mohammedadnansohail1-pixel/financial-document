# Horizontal Scaling Guide

Complete guide for implementing horizontal scaling in the Financial Report Intelligence System.

## Table of Contents

- [Overview](#overview)
- [Scaling Strategies](#scaling-strategies)
- [Auto-Scaling Configuration](#auto-scaling-configuration)
- [Load Balancing](#load-balancing)
- [Service Mesh](#service-mesh)
- [Performance Testing](#performance-testing)
- [Monitoring & Alerts](#monitoring--alerts)
- [Best Practices](#best-practices)

## Overview

The system is designed to scale horizontally across multiple dimensions:

1. **API Layer**: Scales based on request rate and latency
2. **Processing Layer**: Scales based on queue depth
3. **Database Layer**: Vertical scaling with read replicas
4. **Cache Layer**: Distributed Redis cluster
5. **Model Serving**: GPU/CPU-based auto-scaling

### Scaling Triggers

| Component | Scale Metric | Target | Min | Max |
|-----------|-------------|--------|-----|-----|
| API | CPU Utilization | 70% | 3 | 20 |
| API | Request Rate | 100 req/s | 3 | 20 |
| Processor | Queue Depth | 100 items | 2 | 15 |
| RAG Engine | Latency P95 | 200ms | 3 | 12 |
| Model Serving | GPU Utilization | 80% | 2 | 6 |

## Scaling Strategies

### 1. Horizontal Pod Autoscaling (HPA)

Automatic pod scaling based on metrics:

```bash
# Apply HPA configuration
kubectl apply -f deploy/scaling/horizontal-scaling.yaml

# Check HPA status
kubectl get hpa -n finrag

# Describe HPA
kubectl describe hpa finrag-api-hpa -n finrag

# Watch scaling events
kubectl get hpa -n finrag --watch
```

### 2. Vertical Pod Autoscaling (VPA)

Automatic resource adjustment:

```bash
# Check VPA recommendations
kubectl describe vpa weaviate-vpa -n finrag

# View current resource usage
kubectl top pods -n finrag
```

### 3. Cluster Autoscaling

Node-level scaling:

```bash
# GKE example
gcloud container clusters update finrag-production \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 50 \
  --zone us-central1-a

# AWS EKS example
eksctl scale nodegroup --cluster=finrag-production \
  --name=ng-1 \
  --nodes=3 \
  --nodes-min=3 \
  --nodes-max=50

# Azure AKS example
az aks update \
  --resource-group finrag-rg \
  --name finrag-production \
  --enable-cluster-autoscaler \
  --min-count 3 \
  --max-count 50
```

### 4. Event-Driven Autoscaling (KEDA)

Scale based on events (Kafka, queue depth):

```bash
# Install KEDA
kubectl apply -f https://github.com/kedacore/keda/releases/download/v2.12.0/keda-2.12.0.yaml

# Apply KEDA ScaledObject
kubectl apply -f deploy/scaling/keda-scaling.yaml

# Check KEDA status
kubectl get scaledobjects -n finrag
```

## Auto-Scaling Configuration

### CPU/Memory-Based Scaling

```yaml
metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70  # Scale at 70% CPU
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80  # Scale at 80% memory
```

### Custom Metrics Scaling

```yaml
metrics:
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"  # Scale at 100 req/s per pod
```

### Scaling Behavior

Control scale-up/down speed:

```yaml
behavior:
  scaleDown:
    stabilizationWindowSeconds: 300  # Wait 5 min before scale down
    policies:
      - type: Percent
        value: 50  # Max 50% reduction
        periodSeconds: 60
  scaleUp:
    stabilizationWindowSeconds: 0  # Scale up immediately
    policies:
      - type: Percent
        value: 100  # Max 100% increase
        periodSeconds: 30
```

## Load Balancing

### Nginx Ingress

```bash
# Install Nginx Ingress Controller
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.replicaCount=3 \
  --set controller.metrics.enabled=true

# Apply ingress rules
kubectl apply -f deploy/scaling/horizontal-scaling.yaml

# Check ingress
kubectl get ingress -n finrag
```

### Load Balancing Algorithms

1. **Round Robin** (default)
   ```yaml
   nginx.ingress.kubernetes.io/load-balance: "round_robin"
   ```

2. **Least Connections**
   ```yaml
   nginx.ingress.kubernetes.io/load-balance: "least_conn"
   ```

3. **IP Hash** (session affinity)
   ```yaml
   sessionAffinity: ClientIP
   ```

## Service Mesh

### Istio Setup

```bash
# Install Istio
istioctl install --set profile=production

# Enable auto-injection
kubectl label namespace finrag istio-injection=enabled

# Apply Istio configs
kubectl apply -f deploy/scaling/horizontal-scaling.yaml

# Verify mesh
istioctl proxy-status
```

### Traffic Management

**Canary Deployment** (10% to new version):

```yaml
http:
  - route:
      - destination:
          host: finrag-api
          subset: v1
        weight: 90
      - destination:
          host: finrag-api
          subset: v2
        weight: 10
```

**Circuit Breaking**:

```yaml
trafficPolicy:
  outlierDetection:
    consecutiveErrors: 5
    interval: 30s
    baseEjectionTime: 30s
```

**Rate Limiting**:

```yaml
token_bucket:
  max_tokens: 100
  tokens_per_fill: 100
  fill_interval: 60s  # 100 requests per minute
```

### Connection Pooling

```yaml
connectionPool:
  tcp:
    maxConnections: 1000
  http:
    http1MaxPendingRequests: 100
    http2MaxRequests: 1000
    maxRequestsPerConnection: 10
```

## Performance Testing

### Load Testing with k6

```bash
# Install k6
brew install k6  # macOS
# or
sudo apt-get install k6  # Ubuntu

# Run load test
k6 run deploy/scaling/load-test.js

# Run with specific VUs and duration
k6 run --vus 100 --duration 5m deploy/scaling/load-test.js
```

### Load Test Script

```javascript
// load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 100 },  // Ramp up to 100 VUs
    { duration: '5m', target: 100 },  // Stay at 100 VUs
    { duration: '2m', target: 200 },  // Ramp up to 200 VUs
    { duration: '5m', target: 200 },  // Stay at 200 VUs
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% under 500ms
    http_req_failed: ['rate<0.01'],     // <1% errors
  },
};

export default function () {
  const res = http.post('https://api.finrag.example.com/api/v1/query',
    JSON.stringify({
      query: 'What were Apple\\'s Q4 earnings?',
      k: 20
    }), {
      headers: { 'Content-Type': 'application/json' },
    }
  );

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });

  sleep(1);
}
```

### Stress Testing

```bash
# Chaos testing with Chaos Mesh
kubectl apply -f deploy/scaling/chaos-test.yaml

# Monitor during chaos
kubectl get pods -n finrag --watch
```

## Monitoring & Alerts

### Key Metrics to Monitor

1. **Request Metrics**
   - Request rate (req/s)
   - Error rate (%)
   - Latency (p50, p95, p99)

2. **Resource Metrics**
   - CPU utilization (%)
   - Memory utilization (%)
   - Network I/O (MB/s)

3. **Scaling Metrics**
   - Pod count
   - Node count
   - Scale events

### Prometheus Queries

```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Pod count
count(kube_pod_info{namespace="finrag", pod=~"finrag-api.*"})

# CPU usage
avg(rate(container_cpu_usage_seconds_total{namespace="finrag"}[5m])) by (pod)
```

### Grafana Dashboards

Import pre-built dashboards:
- HPA Status: Dashboard ID 12345
- Istio Metrics: Dashboard ID 7645
- Node Metrics: Dashboard ID 11074

### Alerts

```yaml
# Prometheus AlertManager rules
groups:
  - name: scaling-alerts
    rules:
      - alert: HighRequestLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        annotations:
          summary: "High request latency (P95 > 1s)"

      - alert: HPAMaxedOut
        expr: kube_horizontalpodautoscaler_status_current_replicas == kube_horizontalpodautoscaler_spec_max_replicas
        for: 10m
        annotations:
          summary: "HPA at maximum replicas"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        annotations:
          summary: "Error rate > 5%"
```

## Best Practices

### 1. Resource Requests and Limits

Always set resource requests and limits:

```yaml
resources:
  requests:
    cpu: "1000m"
    memory: "2Gi"
  limits:
    cpu: "2000m"
    memory: "4Gi"
```

### 2. Pod Disruption Budgets

Ensure high availability during updates:

```yaml
spec:
  minAvailable: 2  # Always keep 2 pods running
```

### 3. Health Checks

Implement proper health checks:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

### 4. Anti-Affinity Rules

Distribute pods across nodes:

```yaml
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchLabels:
              app: finrag-api
          topologyKey: kubernetes.io/hostname
```

### 5. Connection Pooling

Use connection pools for databases and caches:

```python
# PostgreSQL
engine = create_engine(
    'postgresql://...',
    pool_size=20,
    max_overflow=10
)

# Redis
redis_pool = redis.ConnectionPool(
    host='redis',
    port=6379,
    max_connections=50
)
```

### 6. Caching Strategy

Implement multi-level caching:
- L1: In-memory (500MB)
- L2: Redis (10GB)
- L3: Database

### 7. Async Processing

Use async for I/O-bound operations:

```python
async def process_query(query):
    # Parallel retrieval
    results = await asyncio.gather(
        retrieve_from_vector_db(query),
        retrieve_from_graph_db(query),
        retrieve_from_cache(query)
    )
    return combine_results(results)
```

### 8. Rate Limiting

Implement rate limiting at multiple levels:
- Nginx: 100 req/s per IP
- Application: 1000 req/min per API key
- Database: Connection pooling

### 9. Graceful Shutdown

Handle SIGTERM for graceful shutdown:

```python
def graceful_shutdown(signum, frame):
    logger.info("Shutting down gracefully...")
    # Finish processing current requests
    # Close database connections
    # Flush caches
    sys.exit(0)

signal.signal(signal.SIGTERM, graceful_shutdown)
```

### 10. Monitoring

Monitor all layers:
- Application metrics (Prometheus)
- Infrastructure metrics (Node exporter)
- Business metrics (Custom metrics)

## Troubleshooting

### HPA Not Scaling

```bash
# Check HPA status
kubectl describe hpa finrag-api-hpa -n finrag

# Check metrics server
kubectl get apiservice v1beta1.metrics.k8s.io -o yaml

# Manually test scaling
kubectl scale deployment finrag-api --replicas=5 -n finrag
```

### High Latency Under Load

```bash
# Check resource utilization
kubectl top pods -n finrag

# Check connection pooling
kubectl exec -it pod-name -n finrag -- netstat -an | grep ESTABLISHED | wc -l

# Review slow queries
kubectl logs -f deployment/finrag-api -n finrag | grep "took.*ms"
```

### Pods Evicted

```bash
# Check node resources
kubectl describe nodes

# Check pod QoS class
kubectl get pods -n finrag -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.qosClass}{"\n"}{end}'

# Increase node capacity
kubectl scale nodegroup --nodes=10
```

## Summary

Key points for horizontal scaling:

1. **Auto-scaling**: Configure HPA with appropriate metrics
2. **Load Balancing**: Use Nginx/Istio for traffic distribution
3. **Health Checks**: Implement proper liveness/readiness probes
4. **Resource Management**: Set requests/limits for all pods
5. **Monitoring**: Track all scaling events and metrics
6. **Testing**: Regular load testing to validate scaling
7. **Graceful Handling**: Implement proper shutdown and error handling

---

**Last Updated**: 2024-01-16
