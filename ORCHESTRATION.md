# Task Manager Orchestration

This document describes how the task-manager now serves as the central orchestrator for AI inference tasks, integrating with cluster-manager workers via Celery.

## 🚀 What's New

The task-manager has been enhanced to:

1. **Dispatch tasks to GPU workers** via Celery message queues
2. **Track real-time task status** from cluster-manager workers  
3. **Monitor worker health** and availability
4. **Route tasks intelligently** based on worker load
5. **Cancel running tasks** via Celery task revocation
6. **Provide worker statistics** and queue information

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   REST Client   │───▶│  Task Manager   │───▶│ Cluster Manager │
│                 │    │  (Orchestrator) │    │   (Workers)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  Redis/Celery   │◀───│   GPU Workers   │
                       │  (Task Queue)   │    │   (Execution)   │
                       └─────────────────┘    └─────────────────┘
```

## 🔧 Setup and Configuration

### 1. Install Dependencies

```bash
cd task-manager
pip install -r requirements.txt
```

New dependencies added:
- `celery>=5.3.4` - Task queue and worker communication
- `redis>=5.0.1` - Message broker and result backend
- `structlog>=23.2.0` - Structured logging

### 2. Configure Celery Settings

The task-manager now includes Celery configuration in `app/core/config.py`:

```python
# Celery Configuration for task orchestration
celery_broker_url: str = "redis://localhost:6379/0"
celery_result_backend: str = "redis://localhost:6379/0"
celery_task_routes: dict = {
    'app.tasks.*': {'queue': 'gpu_queue'}
}
```

### 3. Start Required Services

1. **Start Redis** (message broker):
   ```bash
   redis-server
   ```

2. **Start Cluster Manager Workers**:
   ```bash
   cd cluster-manager
   python -m cluster.worker.app.worker
   ```

3. **Start Task Manager**:
   ```bash
   cd task-manager
   python -m app.main
   ```

## 📋 API Endpoints

### Core Task Operations

- `POST /tasks/` - Create and dispatch new task
- `GET /tasks/{task_id}` - Get task status with real-time updates  
- `GET /tasks/` - List tasks with filtering
- `PATCH /tasks/{task_id}/cancel` - Cancel running task
- `DELETE /tasks/{task_id}` - Delete task
- `GET /tasks/stats/metrics` - Get task execution statistics

### Worker Monitoring (New)

- `GET /tasks/workers/health` - Check worker health and availability
- `GET /tasks/workers/stats` - Get detailed worker statistics and load

## 🧪 Testing the Orchestration

Run the provided test script to validate orchestration functionality:

```bash
cd task-manager
python test_orchestration.py
```

This script tests:
- ✅ Task manager health
- ✅ Worker connectivity  
- ✅ Task creation and dispatch
- ✅ Real-time status tracking
- ✅ Task cancellation
- ✅ Worker statistics
- ✅ Performance metrics

## 🔄 Task Lifecycle

1. **Task Creation**: Client submits task via REST API
2. **Validation**: Task-manager validates task type and parameters
3. **Worker Discovery**: Find optimal worker based on current load
4. **Dispatch**: Send task to cluster-manager worker via Celery
5. **Tracking**: Monitor task progress via Celery AsyncResult
6. **Completion**: Return results to client and update metrics

## 📊 Worker Load Balancing

The orchestrator includes intelligent worker selection:

```python
async def get_optimal_worker(self, task_type: TaskType) -> Optional[str]:
    """Find worker with lowest current load"""
    # Analyzes active, scheduled, and reserved tasks per worker
    # Routes to worker with minimum total load
```

## 🚫 Task Cancellation

Tasks can be cancelled at any stage:

```python
async def cancel_task(self, task_id: str) -> Optional[Dict[str, Any]]:
    """Cancel via Celery task revocation"""
    self.celery_app.control.revoke(
        celery_task_id, 
        terminate=True,
        signal='SIGKILL'
    )
```

## 📈 Monitoring and Metrics

### Worker Health

```bash
curl http://localhost:8002/tasks/workers/health
```

```json
{
  "status": "healthy",
  "total_workers": 2,
  "online_workers": 2,
  "queue_info": {
    "gpu_queue": {"length": 0}
  }
}
```

### Task Statistics

```bash
curl http://localhost:8002/tasks/stats/metrics
```

```json
{
  "total_tasks": 15,
  "pending_tasks": 2,
  "running_tasks": 1,
  "completed_tasks": 10,
  "failed_tasks": 2,
  "success_rate": 83.3,
  "average_execution_time": 12.5
}
```

## 🔧 Supported Task Types

The orchestrator supports all cluster-manager task types:

- `llm` → `app.tasks.run_llm_inference`
- `stable_diffusion` → `app.tasks.run_sd_inference` 
- `tts` → `app.tasks.run_tts_inference`
- `image_to_text` → `app.tasks.run_image_to_text_inference`

## 🛠️ Troubleshooting

### No Workers Available

```
⚠️ No workers available - cluster-manager may not be running
```

**Solution**: Start cluster-manager workers:
```bash
cd cluster-manager
python -m cluster.worker.app.worker
```

### Redis Connection Failed

```
❌ Failed to connect to Celery: [Errno 61] Connection refused
```

**Solution**: Start Redis server:
```bash
redis-server
```

### Task Stuck in Pending

**Check worker health**:
```bash
curl http://localhost:8002/tasks/workers/health
```

**Check queue lengths**:
```bash
curl http://localhost:8002/tasks/workers/stats
```

## 🎯 Next Steps

1. **Database Integration**: Replace in-memory storage with PostgreSQL/MongoDB
2. **Authentication**: Add API key/JWT authentication for production
3. **Rate Limiting**: Implement per-user task limits
4. **Batch Processing**: Support for batch task submissions
5. **Advanced Scheduling**: Priority queues and scheduling policies
6. **WebSocket Support**: Real-time task updates via WebSockets
7. **Multi-tenant Support**: Isolate tasks by organization/user

## 🔍 Development Notes

### Key Files Modified

- `app/services/task_service.py` - Core orchestration logic
- `app/core/config.py` - Celery configuration  
- `app/routes/tasks.py` - Worker monitoring endpoints
- `requirements.txt` - Added Celery and Redis dependencies

### Integration Points

- **Celery Client**: `TaskService.celery_app` for worker communication
- **Redis Client**: `TaskService.redis_client` for metadata storage
- **Task Mapping**: Maps TaskType enums to Celery task names
- **Status Sync**: Real-time status updates from AsyncResult

The task-manager now serves as a true orchestrator, bridging REST API clients with distributed GPU workers efficiently and reliably.
