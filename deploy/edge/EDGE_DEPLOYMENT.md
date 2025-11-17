# Edge Deployment Guide

Complete guide for deploying lightweight edge nodes for distributed financial intelligence processing.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Local Testing](#local-testing)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Overview

Edge deployment enables distributed processing of financial queries closer to data sources or users, reducing latency and improving scalability.

### Key Features

- **Lightweight Footprint**: Minimal resource requirements (500MB-2GB RAM)
- **Geographic Distribution**: Deploy nodes in multiple regions
- **Intelligent Caching**: LRU cache with configurable size
- **Auto-Sync**: Automatic synchronization with central cluster
- **Fault Tolerance**: Automatic failover to central cluster
- **Low Latency**: Sub-100ms query response times

### Use Cases

1. **Regional Data Processing**: Process queries close to regional users
2. **Branch Office Deployment**: Deploy at financial institution branches
3. **Mobile Edge Computing**: Process on-device or near-device
4. **Disaster Recovery**: Distributed failover capabilities

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Central Cluster                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │   API    │  │ Database │  │   RAG    │          │
│  └──────────┘  └──────────┘  └──────────┘          │
└─────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Edge Node   │ │  Edge Node   │ │  Edge Node   │
│   US-East    │ │   EU-West    │ │  Asia-Pac    │
│              │ │              │ │              │
│ ┌──────────┐ │ │ ┌──────────┐ │ │ ┌──────────┐ │
│ │  Cache   │ │ │ │  Cache   │ │ │ │  Cache   │ │
│ └──────────┘ │ │ └──────────┘ │ │ └──────────┘ │
└──────────────┘ └──────────────┘ └──────────────┘
```

### Data Flow

1. **Query Received**: Edge node receives query
2. **Cache Check**: Check local cache first
3. **Local Processing**: Process if data available
4. **Fallback**: Forward to central if needed
5. **Cache Update**: Update local cache with result
6. **Periodic Sync**: Sync with central cluster

## Prerequisites

### Software Requirements

- Docker 24.0+
- Docker Compose 2.20+ (for local testing)
- Kubernetes 1.27+ (for production)
- kubectl CLI

### Resource Requirements

**Per Edge Node:**
- CPU: 0.5-1.0 cores
- RAM: 1-2GB
- Storage: 5-10GB
- Network: 10Mbps+

## Local Testing

### 1. Build Edge Image

```bash
# Navigate to project root
cd /path/to/financial-document

# Build edge image
docker build -f deploy/edge/Dockerfile.edge -t finrag/edge:latest .
```

### 2. Start Edge Deployment

```bash
# Navigate to edge deployment directory
cd deploy/edge

# Start all services
docker-compose -f docker-compose.edge.yml up -d

# View logs
docker-compose -f docker-compose.edge.yml logs -f

# Check status
docker-compose -f docker-compose.edge.yml ps
```

### 3. Test Edge Nodes

```bash
# Test US East node
curl http://localhost:8001/health

# Test EU West node
curl http://localhost:8002/health

# Test Asia Pacific node
curl http://localhost:8003/health

# Query edge node
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What were Apple'\''s Q4 earnings?", "region": "us-east"}'

# Check node stats
curl http://localhost:8001/stats
```

### 4. Monitor Edge Nodes

```bash
# Access Grafana
open http://localhost:3001
# Login: admin / edge_admin

# Access Prometheus
open http://localhost:9091
```

### 5. Cleanup

```bash
# Stop all services
docker-compose -f docker-compose.edge.yml down

# Remove volumes
docker-compose -f docker-compose.edge.yml down -v
```

## Kubernetes Deployment

### 1. Prepare Cluster

```bash
# Create namespace
kubectl create namespace finrag-edge

# Set context
kubectl config set-context --current --namespace=finrag-edge
```

### 2. Build and Push Image

```bash
# Build image
docker build -f deploy/edge/Dockerfile.edge -t finrag/edge:v1.0.0 .

# Tag for registry
docker tag finrag/edge:v1.0.0 your-registry.com/finrag/edge:v1.0.0

# Push to registry
docker push your-registry.com/finrag/edge:v1.0.0
```

### 3. Update Configuration

Edit `deploy/edge/edge-config.yaml`:

```yaml
# Update image reference
spec:
  containers:
    - name: edge-server
      image: your-registry.com/finrag/edge:v1.0.0  # Update this

# Update central endpoint
data:
  CENTRAL_ENDPOINT: "http://your-central-api:8000"  # Update this
```

### 4. Deploy to Kubernetes

```bash
# Apply configuration
kubectl apply -f deploy/edge/edge-config.yaml

# Check deployment status
kubectl get deployments -n finrag-edge

# Check pods
kubectl get pods -n finrag-edge

# Check services
kubectl get services -n finrag-edge
```

### 5. Verify Deployment

```bash
# Check pod logs
kubectl logs -f deployment/edge-us-east -n finrag-edge

# Test edge service
kubectl port-forward service/edge-us-east 8001:8001 -n finrag-edge

# In another terminal
curl http://localhost:8001/health
```

### 6. Scale Edge Nodes

```bash
# Manual scaling
kubectl scale deployment edge-us-east --replicas=4 -n finrag-edge

# Check HPA status (auto-scaling)
kubectl get hpa -n finrag-edge

# Describe HPA
kubectl describe hpa edge-us-east-hpa -n finrag-edge
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NODE_ID` | Unique node identifier | `edge-node-1` |
| `REGION` | Geographic region | `us-east` |
| `CENTRAL_ENDPOINT` | Central API endpoint | `http://central-api:8000` |
| `CACHE_SIZE_MB` | Local cache size (MB) | `500` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `SYNC_INTERVAL_SECONDS` | Sync interval | `300` |

### Sync Strategies

1. **Full Sync**: Download all data
   ```python
   sync_strategy=SyncStrategy.FULL_SYNC
   ```

2. **Incremental**: Only new/updated data
   ```python
   sync_strategy=SyncStrategy.INCREMENTAL
   ```

3. **Selective**: Filter by region/criteria
   ```python
   sync_strategy=SyncStrategy.SELECTIVE
   ```

4. **On-Demand**: Sync when requested
   ```python
   sync_strategy=SyncStrategy.ON_DEMAND
   ```

### Resource Limits

Edit deployment configuration:

```yaml
resources:
  requests:
    cpu: "500m"      # Adjust based on load
    memory: "1Gi"    # Adjust based on cache size
  limits:
    cpu: "1000m"
    memory: "2Gi"
```

### Auto-Scaling Configuration

```yaml
spec:
  minReplicas: 2    # Minimum replicas
  maxReplicas: 6    # Maximum replicas
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          averageUtilization: 70  # Scale at 70% CPU
```

## Monitoring

### Health Checks

```bash
# Kubernetes health check
kubectl get pods -n finrag-edge

# Individual node health
curl http://edge-node:8001/health
```

### Metrics

Key metrics to monitor:

1. **Cache Hit Rate**: Should be >80%
2. **Query Latency**: Target <100ms
3. **Sync Status**: Last sync time
4. **Resource Usage**: CPU, memory utilization
5. **Error Rate**: Should be <1%

### Prometheus Queries

```promql
# Cache hit rate
rate(cache_hits_total[5m]) / rate(cache_requests_total[5m])

# Average query latency
histogram_quantile(0.95, rate(query_duration_seconds_bucket[5m]))

# Edge node availability
up{job="edge-nodes"}

# Sync lag
time() - last_sync_timestamp_seconds
```

### Grafana Dashboards

Import dashboard for edge monitoring:

```bash
# Import from dashboard JSON
kubectl create configmap grafana-dashboard-edge \
  --from-file=edge-dashboard.json \
  -n monitoring
```

## Troubleshooting

### Edge Node Not Starting

**Symptoms**: Pod in CrashLoopBackOff

**Solutions**:
```bash
# Check logs
kubectl logs pod-name -n finrag-edge

# Common issues:
# 1. Cannot connect to central
kubectl exec -it pod-name -n finrag-edge -- curl http://central-api:8000/health

# 2. Insufficient resources
kubectl describe pod pod-name -n finrag-edge

# 3. Configuration error
kubectl get configmap edge-config -n finrag-edge -o yaml
```

### High Memory Usage

**Symptoms**: OOMKilled pods

**Solutions**:
```bash
# Check memory usage
kubectl top pods -n finrag-edge

# Reduce cache size
kubectl set env deployment/edge-us-east CACHE_SIZE_MB=250 -n finrag-edge

# Increase memory limit
kubectl set resources deployment/edge-us-east \
  --limits=memory=4Gi -n finrag-edge
```

### Sync Failures

**Symptoms**: Stale data, high latency

**Solutions**:
```bash
# Force manual sync
curl -X POST http://edge-node:8001/sync \
  -H "Content-Type: application/json" \
  -d '{"force_full": true}'

# Check sync status
kubectl logs deployment/edge-us-east -n finrag-edge | grep sync

# Verify central connectivity
kubectl exec -it pod-name -n finrag-edge -- \
  curl -v http://central-api:8000
```

### Network Issues

**Symptoms**: Cannot reach central or other services

**Solutions**:
```bash
# Check network policy
kubectl get networkpolicy -n finrag-edge

# Test DNS resolution
kubectl exec -it pod-name -n finrag-edge -- \
  nslookup central-api.finrag.svc.cluster.local

# Test connectivity
kubectl exec -it pod-name -n finrag-edge -- \
  nc -zv central-api.finrag.svc.cluster.local 8000
```

### Low Cache Hit Rate

**Symptoms**: High latency, frequent central queries

**Solutions**:
```bash
# Increase cache size
kubectl set env deployment/edge-us-east CACHE_SIZE_MB=1000 -n finrag-edge

# Check cache stats
curl http://edge-node:8001/stats | jq '.cache'

# Clear and rebuild cache
curl -X POST http://edge-node:8001/cache/clear
curl -X POST http://edge-node:8001/sync -d '{"force_full": true}'
```

## Advanced Configuration

### Multi-Region Deployment

Deploy edge nodes in multiple cloud regions:

```bash
# AWS regions
kubectl apply -f edge-config.yaml --context aws-us-east-1
kubectl apply -f edge-config.yaml --context aws-eu-west-1
kubectl apply -f edge-config.yaml --context aws-ap-southeast-1

# GCP regions
kubectl apply -f edge-config.yaml --context gke-us-central1
kubectl apply -f edge-config.yaml --context gke-europe-west1
kubectl apply -f edge-config.yaml --context gke-asia-east1
```

### Traffic Routing

Use GeoDNS or service mesh for intelligent routing:

```yaml
# Istio VirtualService example
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: edge-routing
spec:
  hosts:
    - edge.finrag.com
  http:
    - match:
        - headers:
            x-region:
              exact: us-east
      route:
        - destination:
            host: edge-us-east
    - match:
        - headers:
            x-region:
              exact: eu-west
      route:
        - destination:
            host: edge-eu-west
```

### Custom Metrics

Add custom Prometheus metrics:

```python
from prometheus_client import Counter, Histogram

# Query counter by region
query_counter = Counter(
    'edge_queries_total',
    'Total edge queries',
    ['region', 'status']
)

# Latency histogram
query_latency = Histogram(
    'edge_query_duration_seconds',
    'Edge query latency',
    ['region']
)
```

## Best Practices

1. **Cache Strategy**: Use incremental sync for most cases
2. **Resource Allocation**: Start with 1GB RAM, scale as needed
3. **Monitoring**: Set up alerts for cache hit rate <70%
4. **Security**: Use network policies to restrict traffic
5. **Backup**: Always have central fallback available
6. **Testing**: Test failover scenarios regularly
7. **Updates**: Use rolling updates to avoid downtime

## Support

- Documentation: See main DEPLOYMENT.md
- Issues: GitHub Issues
- Logs: Check pod logs for detailed errors

---

**Last Updated**: 2024-01-16
