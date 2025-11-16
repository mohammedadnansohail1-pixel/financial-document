
# Deployment Guide

This guide covers deploying the Financial Report Intelligence System to production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Deployment Options](#deployment-options)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **CPU**: 8+ cores recommended
- **RAM**: 32GB+ recommended
- **Storage**: 500GB+ SSD
- **Network**: 1Gbps+ bandwidth
- **OS**: Ubuntu 20.04+ LTS, RHEL 8+, or compatible

### Software Requirements

- Docker 24.0+
- Docker Compose 2.20+
- Kubernetes 1.27+ (for K8s deployment)
- Helm 3.12+ (for K8s deployment)

## Deployment Options

### Option 1: Docker Compose (Recommended for Small-Medium Scale)

Best for: Single-server deployments, development, testing

**Pros:**
- Simple setup
- All services in one place
- Easy to manage

**Cons:**
- Limited scalability
- Single point of failure

### Option 2: Kubernetes (Recommended for Production)

Best for: Large-scale production, high availability

**Pros:**
- Auto-scaling
- High availability
- Rolling updates
- Service mesh support

**Cons:**
- Complex setup
- Higher resource requirements

### Option 3: Cloud-Managed Services

Best for: Cloud-native deployments

**Providers:**
- AWS (ECS, EKS)
- Google Cloud (GKE)
- Azure (AKS)

## Docker Deployment

### 1. Prepare Environment

```bash
# Clone repository
git clone https://github.com/your-org/financial-report-intelligence.git
cd financial-report-intelligence

# Copy environment file
cp .env.example .env

# Edit configuration
nano .env
```

### 2. Configure Environment Variables

Required variables in `.env`:

```bash
# LLM API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Database Passwords
POSTGRES_PASSWORD=strong_password_here
REDIS_PASSWORD=strong_password_here
NEO4J_PASSWORD=strong_password_here

# JWT Secret
JWT_SECRET_KEY=generate_strong_secret_key

# Data Source APIs
NEWSAPI_KEY=...
ALPHA_VANTAGE_KEY=...
```

### 3. Deploy Services

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### 4. Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs

# Grafana dashboard
open http://localhost:3000
# Login: admin / finrag_grafana_pass
```

### 5. Scale Services

```bash
# Scale API service
docker-compose up -d --scale api=3

# Scale document processor
docker-compose up -d --scale document-processor=2
```

## Kubernetes Deployment

### 1. Prepare Cluster

```bash
# Create namespace
kubectl create namespace finrag

# Set context
kubectl config set-context --current --namespace=finrag
```

### 2. Create Secrets

```bash
# Create secret from env file
kubectl create secret generic finrag-secrets \
  --from-env-file=.env

# Verify
kubectl get secrets
```

### 3. Deploy with Helm

```bash
# Add Helm repository
helm repo add finrag https://charts.finrag.example.com
helm repo update

# Install
helm install finrag finrag/finrag \
  --namespace finrag \
  --values values.prod.yaml \
  --wait

# Check status
helm status finrag -n finrag
```

### 4. Configure Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: finrag-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
    - hosts:
        - api.finrag.example.com
      secretName: finrag-tls
  rules:
    - host: api.finrag.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: finrag-api
                port:
                  number: 8000
```

```bash
kubectl apply -f ingress.yaml
```

### 5. Configure Auto-Scaling

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: finrag-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: finrag-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

```bash
kubectl apply -f hpa.yaml
```

## Cloud Deployment

### AWS EKS Deployment

```bash
# Create EKS cluster
eksctl create cluster \
  --name finrag-production \
  --region us-east-1 \
  --node-type m5.2xlarge \
  --nodes 3 \
  --nodes-min 3 \
  --nodes-max 10 \
  --managed

# Configure kubectl
aws eks update-kubeconfig --name finrag-production --region us-east-1

# Deploy
helm install finrag finrag/finrag \
  --namespace finrag \
  --values values.aws.yaml
```

### Google Cloud GKE Deployment

```bash
# Create GKE cluster
gcloud container clusters create finrag-production \
  --region us-central1 \
  --machine-type n1-standard-8 \
  --num-nodes 3 \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 10

# Get credentials
gcloud container clusters get-credentials finrag-production --region us-central1

# Deploy
helm install finrag finrag/finrag \
  --namespace finrag \
  --values values.gcp.yaml
```

### Azure AKS Deployment

```bash
# Create resource group
az group create --name finrag-rg --location eastus

# Create AKS cluster
az aks create \
  --resource-group finrag-rg \
  --name finrag-production \
  --node-count 3 \
  --node-vm-size Standard_D8s_v3 \
  --enable-cluster-autoscaler \
  --min-count 3 \
  --max-count 10

# Get credentials
az aks get-credentials --resource-group finrag-rg --name finrag-production

# Deploy
helm install finrag finrag/finrag \
  --namespace finrag \
  --values values.azure.yaml
```

## Configuration

### Production Configuration Checklist

- [ ] Strong passwords for all databases
- [ ] API rate limiting enabled
- [ ] TLS/SSL certificates configured
- [ ] Firewall rules configured
- [ ] Backup strategy implemented
- [ ] Monitoring alerts configured
- [ ] Log aggregation setup
- [ ] Secrets management (Vault, AWS Secrets Manager)
- [ ] Resource limits defined
- [ ] Auto-scaling configured

### Security Hardening

```yaml
# security-policy.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: finrag-restricted
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'persistentVolumeClaim'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

## Monitoring

### Prometheus Queries

```promql
# Query latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Cache hit rate
rate(cache_hits_total[5m]) / rate(cache_requests_total[5m])

# Active connections
sum(active_connections)
```

### Grafana Dashboards

Import dashboard IDs:
- System Overview: 12345
- API Metrics: 12346
- Database Metrics: 12347

### Alerts Setup

```bash
# Configure Alertmanager
kubectl create configmap alertmanager-config \
  --from-file=config/alertmanager.yml \
  --namespace monitoring

# Restart Alertmanager
kubectl rollout restart deployment alertmanager -n monitoring
```

## Backup & Recovery

### Database Backups

```bash
# PostgreSQL backup
docker exec finrag-postgres pg_dump -U finrag finrag_db > backup.sql

# Neo4j backup
docker exec finrag-neo4j neo4j-admin backup \
  --database=neo4j \
  --to=/backups/neo4j-backup

# Weaviate backup
curl -X POST http://localhost:8080/v1/backups/filesystem
```

### Automated Backup Script

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/$DATE"

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker exec finrag-postgres pg_dump -U finrag finrag_db > $BACKUP_DIR/postgres.sql

# Backup Neo4j
docker exec finrag-neo4j neo4j-admin backup --database=neo4j --to=$BACKUP_DIR/neo4j

# Upload to S3
aws s3 sync $BACKUP_DIR s3://finrag-backups/$DATE/

# Cleanup old backups (keep last 7 days)
find /backups -type d -mtime +7 -exec rm -rf {} \;
```

### Schedule Backups

```bash
# Add to crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * /path/to/backup.sh
```

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check logs
docker-compose logs service-name

# Check resource usage
docker stats

# Verify configuration
docker-compose config
```

#### Database Connection Errors

```bash
# Check database status
docker-compose ps postgres

# Test connection
docker exec -it finrag-postgres psql -U finrag -d finrag_db

# Reset database
docker-compose down
docker volume rm finrag_postgres_data
docker-compose up -d postgres
```

#### High Memory Usage

```bash
# Check memory usage
docker stats

# Adjust memory limits in docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 8G

# Restart services
docker-compose restart api
```

#### Slow Queries

```bash
# Enable query logging
export QUERY_LOG_LEVEL=DEBUG

# Check slow queries in logs
docker-compose logs api | grep "took.*ms"

# Optimize database indexes
docker exec -it finrag-postgres psql -U finrag -d finrag_db
CREATE INDEX idx_documents_date ON documents(filing_date);
```

## Performance Tuning

### API Optimization

```yaml
# config.yaml
api:
  workers: 8  # Increase for higher throughput
  worker_class: uvicorn.workers.UvicornWorker
  timeout: 60
  keepalive: 5

performance:
  caching:
    enabled: true
    ttl: 3600
    max_size: "10GB"

  connection_pooling:
    min_size: 10
    max_size: 100
```

### Database Optimization

```sql
-- PostgreSQL optimizations
ALTER SYSTEM SET shared_buffers = '8GB';
ALTER SYSTEM SET effective_cache_size = '24GB';
ALTER SYSTEM SET maintenance_work_mem = '2GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Restart PostgreSQL
SELECT pg_reload_conf();
```

## Maintenance

### Rolling Updates

```bash
# Kubernetes rolling update
kubectl set image deployment/finrag-api \
  api=finrag/api:v1.1.0

# Monitor rollout
kubectl rollout status deployment/finrag-api

# Rollback if needed
kubectl rollout undo deployment/finrag-api
```

### Database Migrations

```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Create new migration
docker-compose exec api alembic revision --autogenerate -m "description"
```

## Support

- Documentation: https://docs.finrag.example.com
- Issues: https://github.com/your-org/finrag/issues
- Email: support@finrag.example.com
- Slack: https://finrag.slack.com

---

**Last Updated**: 2024-01-16
