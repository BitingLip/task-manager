# Task Manager Deployment Guide

## Overview

This guide covers deployment strategies for the Task Manager service in both development and production environments, including containerization, orchestration, monitoring, and security considerations.

---

## Development Deployment

### Local Development Setup

#### Prerequisites
- Python 3.10+
- Docker and Docker Compose
- Git

#### Quick Start
```powershell
# Clone and setup
git clone <repository-url>
cd task-manager

# Setup virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Start dependencies
docker-compose up -d redis postgres

# Run migrations (future)
# python scripts/migrate.py

# Start development server
uvicorn src.main:app --reload --port 8002
```

#### Development Docker Compose
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  task-manager:
    build: 
      context: .
      dockerfile: Dockerfile.dev
    ports:
      - "8002:8002"
    environment:
      - TASK_MANAGER_DEBUG=true
      - TASK_MANAGER_LOG_LEVEL=debug
      - TASK_MANAGER_DATABASE_URL=postgresql://taskuser:taskpass@postgres:5432/taskmanager
      - TASK_MANAGER_REDIS_URL=redis://redis:6379/0
    volumes:
      - ./src:/app/src
      - ./tests:/app/tests
    depends_on:
      - postgres
      - redis
    command: uvicorn src.main:app --host 0.0.0.0 --port 8002 --reload

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: taskmanager
      POSTGRES_USER: taskuser
      POSTGRES_PASSWORD: taskpass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  redis-commander:
    image: rediscommander/redis-commander:latest
    environment:
      - REDIS_HOSTS=local:redis:6379
    ports:
      - "8081:8081"

volumes:
  postgres_data:
  redis_data:
```

#### Development Commands
```powershell
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f task-manager

# Run tests
docker-compose -f docker-compose.dev.yml exec task-manager python -m pytest

# Access database
docker-compose -f docker-compose.dev.yml exec postgres psql -U taskuser -d taskmanager
```

---

## Production Deployment

### Docker Production Setup

#### Production Dockerfile
```dockerfile
# Dockerfile
FROM python:3.10-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production image
FROM python:3.10-slim

# Create non-root user
RUN groupadd -r taskmanager && useradd -r -g taskmanager taskmanager

# Copy virtual environment
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Change ownership
RUN chown -R taskmanager:taskmanager /app

# Switch to non-root user
USER taskmanager

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Expose port
EXPOSE 8002

# Start application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002"]
```

#### Multi-stage Build Optimization
```dockerfile
# Dockerfile.optimized
FROM python:3.10-slim as base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Builder stage
FROM base as builder
RUN apt-get update && apt-get install -y build-essential
COPY requirements.txt .
RUN pip wheel --no-deps --wheel-dir /wheels -r requirements.txt

# Production stage
FROM base as production
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-index --find-links /wheels -r requirements.txt \
    && rm -rf /wheels

# Add non-root user
RUN groupadd -r taskmanager && useradd -r -g taskmanager taskmanager

WORKDIR /app
COPY --chown=taskmanager:taskmanager src/ ./src/
USER taskmanager

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8002/health')"

EXPOSE 8002
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "4"]
```

### Build and Push Commands
```powershell
# Build production image
docker build -t bitinglip/task-manager:latest .

# Tag for registry
docker tag bitinglip/task-manager:latest registry.example.com/bitinglip/task-manager:v1.0.0

# Push to registry
docker push registry.example.com/bitinglip/task-manager:v1.0.0
```

---

## Kubernetes Deployment

### Namespace and ConfigMap
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: bitinglip
  labels:
    name: bitinglip

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: task-manager-config
  namespace: bitinglip
data:
  TASK_MANAGER_HOST: "0.0.0.0"
  TASK_MANAGER_PORT: "8002"
  TASK_MANAGER_LOG_LEVEL: "info"
  TASK_MANAGER_MAX_CONCURRENT_TASKS: "100"
  CLUSTER_MANAGER_URL: "http://cluster-manager:8001"
  MODEL_MANAGER_URL: "http://model-manager:8003"
  GATEWAY_MANAGER_URL: "http://gateway-manager:8000"
```

### Secrets
```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: task-manager-secrets
  namespace: bitinglip
type: Opaque
data:
  DATABASE_URL: cG9zdGdyZXNxbDovL3VzZXI6cGFzc0Bwb3N0Z3JlczozNTQzMi90YXNrbWFuYWdlcg==
  REDIS_URL: cmVkaXM6Ly9yZWRpczozNjM3OS8w
```

### Deployment
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: task-manager
  namespace: bitinglip
  labels:
    app: task-manager
    version: v1.0.0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: task-manager
  template:
    metadata:
      labels:
        app: task-manager
        version: v1.0.0
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: task-manager
        image: registry.example.com/bitinglip/task-manager:v1.0.0
        ports:
        - containerPort: 8002
          name: http
        envFrom:
        - configMapRef:
            name: task-manager-config
        - secretRef:
            name: task-manager-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8002
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8002
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: cache
          mountPath: /app/.cache
      volumes:
      - name: tmp
        emptyDir: {}
      - name: cache
        emptyDir: {}
      restartPolicy: Always
```

### Service and Ingress
```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: task-manager
  namespace: bitinglip
  labels:
    app: task-manager
spec:
  selector:
    app: task-manager
  ports:
  - name: http
    port: 8002
    targetPort: 8002
    protocol: TCP
  type: ClusterIP

---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: task-manager-ingress
  namespace: bitinglip
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - api.bitinglip.com
    secretName: task-manager-tls
  rules:
  - host: api.bitinglip.com
    http:
      paths:
      - path: /tasks
        pathType: Prefix
        backend:
          service:
            name: task-manager
            port:
              number: 8002
```

### Horizontal Pod Autoscaler
```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: task-manager-hpa
  namespace: bitinglip
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: task-manager
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
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
```

### Deployment Commands
```powershell
# Apply all configurations
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n bitinglip -l app=task-manager

# View logs
kubectl logs -n bitinglip -l app=task-manager -f

# Scale deployment
kubectl scale deployment task-manager -n bitinglip --replicas=5

# Rolling update
kubectl set image deployment/task-manager task-manager=registry.example.com/bitinglip/task-manager:v1.1.0 -n bitinglip

# Check rollout status
kubectl rollout status deployment/task-manager -n bitinglip
```

---

## Monitoring and Observability

### Prometheus Metrics
```yaml
# k8s/servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: task-manager-metrics
  namespace: bitinglip
  labels:
    app: task-manager
spec:
  selector:
    matchLabels:
      app: task-manager
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
    scrapeTimeout: 10s
```

### Grafana Dashboard
```json
{
  "dashboard": {
    "title": "Task Manager Dashboard",
    "panels": [
      {
        "title": "Task Processing Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(task_manager_tasks_total[5m])",
            "legendFormat": "Tasks/sec"
          }
        ]
      },
      {
        "title": "Active Tasks",
        "type": "singlestat",
        "targets": [
          {
            "expr": "task_manager_active_tasks",
            "legendFormat": "Active"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(task_manager_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      }
    ]
  }
}
```

### Log Aggregation
```yaml
# k8s/fluentd-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-task-manager-config
  namespace: bitinglip
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/task-manager-*.log
      pos_file /var/log/fluentd-task-manager.log.pos
      tag task-manager.*
      format json
      time_key time
      time_format %Y-%m-%dT%H:%M:%S.%NZ
    </source>
    
    <filter task-manager.**>
      @type parser
      key_name log
      reserve_data true
      <parse>
        @type json
      </parse>
    </filter>
    
    <match task-manager.**>
      @type elasticsearch
      host elasticsearch.logging.svc.cluster.local
      port 9200
      index_name task-manager
      type_name _doc
    </match>
```

---

## Security Considerations

### Network Security
```yaml
# k8s/networkpolicy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: task-manager-network-policy
  namespace: bitinglip
spec:
  podSelector:
    matchLabels:
      app: task-manager
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: bitinglip
    - podSelector:
        matchLabels:
          app: gateway-manager
    ports:
    - protocol: TCP
      port: 8002
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
```

### Pod Security Policy
```yaml
# k8s/podsecuritypolicy.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: task-manager-psp
  namespace: bitinglip
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
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

### RBAC Configuration
```yaml
# k8s/rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: task-manager
  namespace: bitinglip

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: bitinglip
  name: task-manager-role
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: task-manager-rolebinding
  namespace: bitinglip
subjects:
- kind: ServiceAccount
  name: task-manager
  namespace: bitinglip
roleRef:
  kind: Role
  name: task-manager-role
  apiGroup: rbac.authorization.k8s.io
```

---

## Database Management

### PostgreSQL Production Setup
```yaml
# k8s/postgres.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: bitinglip
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        env:
        - name: POSTGRES_DB
          value: taskmanager
        - name: POSTGRES_USER
          value: taskuser
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "1Gi"
            cpu: "500m"
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: "ssd"
      resources:
        requests:
          storage: 10Gi
```

### Migration Strategy
```python
# scripts/migrate.py
import asyncio
from sqlalchemy import create_engine, text
from src.core.config import settings

async def run_migrations():
    """Run database migrations"""
    engine = create_async_engine(settings.database_url)
    
    migrations = [
        "CREATE TABLE IF NOT EXISTS tasks (...)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)",
    ]
    
    async with engine.begin() as conn:
        for migration in migrations:
            await conn.execute(text(migration))

if __name__ == "__main__":
    asyncio.run(run_migrations())
```

---

## Backup and Recovery

### Database Backup
```powershell
# Automated backup script
$BACKUP_DIR = "C:\backups\taskmanager"
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$BACKUP_FILE = "$BACKUP_DIR\taskmanager_$TIMESTAMP.sql"

# Create backup directory
New-Item -ItemType Directory -Force -Path $BACKUP_DIR

# Backup database
kubectl exec -n bitinglip postgres-0 -- pg_dump -U taskuser taskmanager > $BACKUP_FILE

# Compress backup
Compress-Archive -Path $BACKUP_FILE -DestinationPath "$BACKUP_FILE.zip"
Remove-Item $BACKUP_FILE

# Upload to cloud storage (Azure Blob, AWS S3, etc.)
az storage blob upload --account-name backupstorage --container-name taskmanager --name "taskmanager_$TIMESTAMP.sql.zip" --file "$BACKUP_FILE.zip"
```

### Disaster Recovery
```yaml
# k8s/backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: bitinglip
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            image: postgres:15-alpine
            command:
            - /bin/bash
            - -c
            - |
              pg_dump -h postgres -U taskuser taskmanager | gzip > /backup/taskmanager_$(date +%Y%m%d_%H%M%S).sql.gz
              # Upload to cloud storage
              aws s3 cp /backup/ s3://bitinglip-backups/taskmanager/ --recursive
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: password
            volumeMounts:
            - name: backup-volume
              mountPath: /backup
          volumes:
          - name: backup-volume
            emptyDir: {}
          restartPolicy: OnFailure
```

---

## Performance Tuning

### Application Optimization
```python
# src/core/config.py - Production settings
class ProductionSettings(Settings):
    # Connection pooling
    database_pool_size: int = 20
    database_max_overflow: int = 30
    database_pool_timeout: int = 30
    
    # Redis configuration
    redis_max_connections: int = 100
    redis_socket_keepalive: bool = True
    redis_socket_keepalive_options: dict = {
        "TCP_KEEPIDLE": 1,
        "TCP_KEEPINTVL": 3,
        "TCP_KEEPCNT": 5
    }
    
    # Performance settings
    max_concurrent_tasks: int = 1000
    worker_processes: int = 4
    worker_connections: int = 1000
```

### Resource Optimization
```yaml
# k8s/deployment.yaml - Production resources
resources:
  requests:
    memory: "512Mi"
    cpu: "200m"
  limits:
    memory: "2Gi"
    cpu: "1000m"

# JVM heap sizing for high-memory workloads
env:
- name: UVICORN_WORKERS
  value: "4"
- name: UVICORN_WORKER_CONNECTIONS
  value: "1000"
```

---

## Troubleshooting

### Common Issues

#### Pod Crashes
```powershell
# Check pod status
kubectl get pods -n bitinglip -l app=task-manager

# View pod logs
kubectl logs -n bitinglip -l app=task-manager --previous

# Describe pod for events
kubectl describe pod -n bitinglip <pod-name>

# Check resource usage
kubectl top pods -n bitinglip -l app=task-manager
```

#### Database Connection Issues
```powershell
# Test database connectivity
kubectl exec -n bitinglip deployment/task-manager -- python -c "
import asyncpg
import asyncio

async def test_db():
    conn = await asyncpg.connect('postgresql://taskuser:taskpass@postgres:5432/taskmanager')
    result = await conn.fetchval('SELECT 1')
    print(f'Database connection: {result}')
    await conn.close()

asyncio.run(test_db())
"

# Check database logs
kubectl logs -n bitinglip postgres-0
```

#### Performance Issues
```powershell
# Check metrics
curl http://api.bitinglip.com/metrics

# View detailed logs
kubectl logs -n bitinglip -l app=task-manager --tail=100 -f

# Check resource constraints
kubectl describe nodes
kubectl describe hpa -n bitinglip task-manager-hpa
```

### Emergency Procedures
1. **Service Downtime**: Scale to 0 replicas, investigate, then scale back up
2. **Database Issues**: Failover to read replica, restore from backup
3. **Memory Leaks**: Rolling restart of pods with memory monitoring
4. **High CPU**: Enable HPA scaling, investigate bottlenecks

This deployment guide provides comprehensive coverage of production deployment scenarios, monitoring, security, and troubleshooting for the Task Manager service.
