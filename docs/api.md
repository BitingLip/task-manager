# Task Manager API Reference

## Overview

The Task Manager API provides RESTful endpoints for managing AI inference tasks within the BitingLip platform. Built with FastAPI, it offers automatic OpenAPI documentation and request validation.

## Base URL
```
http://localhost:8002
```

## Authentication
Currently no authentication required. Future versions will implement API key authentication.

---

## Endpoints

### Task Management

#### Create Task
**POST** `/tasks`

Creates a new AI inference task and queues it for execution.

**Request Body:**
```json
{
  "task_type": "text_generation",
  "model_name": "microsoft/DialoGPT-medium",
  "input_data": {
    "prompt": "Hello, how are you today?"
  },
  "parameters": {
    "max_length": 100,
    "temperature": 0.8,
    "do_sample": true
  }
}
```

**Parameters:**
- `task_type` (string, required): Type of AI task
  - `text_generation` - LLM text generation
  - `image_generation` - Stable Diffusion image creation
  - `text_to_speech` - TTS audio generation
  - `image_to_text` - Image captioning/OCR
- `model_name` (string, required): Model identifier to use
- `input_data` (object, required): Task-specific input data
- `parameters` (object, optional): Model inference parameters

**Response:**
```json
{
  "task_id": "task_123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "task_type": "text_generation",
  "model_name": "microsoft/DialoGPT-medium",
  "created_at": "2025-05-30T12:00:00Z",
  "estimated_completion": "2025-05-30T12:02:00Z"
}
```

**Status Codes:**
- `201` - Task created successfully
- `400` - Invalid request parameters
- `422` - Validation error
- `503` - Service unavailable

---

#### Get Task Status
**GET** `/tasks/{task_id}`

Retrieves the current status and details of a specific task.

**Path Parameters:**
- `task_id` (string, required): Unique task identifier

**Response:**
```json
{
  "task_id": "task_123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "task_type": "text_generation", 
  "model_name": "microsoft/DialoGPT-medium",
  "created_at": "2025-05-30T12:00:00Z",
  "started_at": "2025-05-30T12:00:15Z",
  "completed_at": "2025-05-30T12:01:30Z",
  "worker_id": "worker_gpu_0",
  "result": {
    "generated_text": "Hello! I'm doing great, thank you for asking. How can I help you today?",
    "tokens_generated": 18,
    "inference_time": 1.2
  }
}
```

**Task Status Values:**
- `pending` - Task queued, waiting for worker
- `running` - Task assigned to worker, in progress
- `completed` - Task finished successfully
- `failed` - Task failed with error
- `cancelled` - Task was cancelled

**Status Codes:**
- `200` - Task found and returned
- `404` - Task not found

---

#### List Tasks
**GET** `/tasks`

Retrieves a list of tasks with optional filtering and pagination.

**Query Parameters:**
- `status` (string, optional): Filter by task status
- `task_type` (string, optional): Filter by task type
- `model_name` (string, optional): Filter by model name
- `limit` (integer, optional): Maximum number of tasks to return (default: 50)
- `offset` (integer, optional): Number of tasks to skip (default: 0)
- `sort_by` (string, optional): Sort field (created_at, status, task_type)
- `sort_order` (string, optional): Sort direction (asc, desc)

**Response:**
```json
{
  "tasks": [
    {
      "task_id": "task_123e4567-e89b-12d3-a456-426614174000",
      "status": "completed",
      "task_type": "text_generation",
      "model_name": "microsoft/DialoGPT-medium",
      "created_at": "2025-05-30T12:00:00Z",
      "completed_at": "2025-05-30T12:01:30Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

**Status Codes:**
- `200` - Tasks retrieved successfully

---

#### Cancel Task
**DELETE** `/tasks/{task_id}`

Cancels a pending or running task.

**Path Parameters:**
- `task_id` (string, required): Unique task identifier

**Response:**
```json
{
  "task_id": "task_123e4567-e89b-12d3-a456-426614174000",
  "status": "cancelled",
  "cancelled_at": "2025-05-30T12:00:45Z"
}
```

**Status Codes:**
- `200` - Task cancelled successfully
- `404` - Task not found
- `409` - Task cannot be cancelled (already completed/failed)

---

### System Endpoints

#### Health Check
**GET** `/health`

Returns the health status of the Task Manager service.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-05-30T12:00:00Z",
  "version": "1.0.0",
  "uptime": 3600,
  "active_tasks": 5,
  "pending_tasks": 12,
  "completed_tasks": 157,
  "failed_tasks": 3
}
```

**Status Codes:**
- `200` - Service is healthy
- `503` - Service is unhealthy

---

#### Metrics
**GET** `/metrics`

Returns Prometheus-compatible metrics for monitoring.

**Response:**
```
# HELP task_manager_tasks_total Total number of tasks processed
# TYPE task_manager_tasks_total counter
task_manager_tasks_total{status="completed"} 157
task_manager_tasks_total{status="failed"} 3
task_manager_tasks_total{status="pending"} 12
task_manager_tasks_total{status="running"} 5

# HELP task_manager_processing_time_seconds Task processing time
# TYPE task_manager_processing_time_seconds histogram
task_manager_processing_time_seconds_bucket{le="1.0"} 45
task_manager_processing_time_seconds_bucket{le="5.0"} 120
task_manager_processing_time_seconds_bucket{le="10.0"} 157
```

---

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid task parameters",
    "details": {
      "field": "model_name",
      "reason": "Model not found"
    }
  },
  "timestamp": "2025-05-30T12:00:00Z",
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000"
}
```

### Error Codes
- `VALIDATION_ERROR` - Request validation failed
- `MODEL_NOT_FOUND` - Specified model not available
- `WORKER_UNAVAILABLE` - No workers available for task
- `TASK_NOT_FOUND` - Requested task does not exist
- `SERVICE_UNAVAILABLE` - Service temporarily unavailable
- `INTERNAL_ERROR` - Unexpected internal error

---

## Rate Limiting

- **Default**: 100 requests per minute per IP
- **Burst**: Up to 20 requests in 10 seconds
- **Headers**:
  - `X-RateLimit-Remaining`: Requests remaining in current window
  - `X-RateLimit-Reset`: Unix timestamp when limit resets

---

## WebSocket API (Future)

Planned WebSocket endpoints for real-time task updates:

```javascript
// Connect to task updates
const ws = new WebSocket('ws://localhost:8002/ws/tasks');

// Subscribe to specific task
ws.send(JSON.stringify({
  "action": "subscribe",
  "task_id": "task_123e4567-e89b-12d3-a456-426614174000"
}));

// Receive real-time updates
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Task update:', update.status);
};
```

---

## SDK Examples

### Python SDK
```python
import asyncio
from task_manager_client import TaskManagerClient

async def main():
    client = TaskManagerClient("http://localhost:8002")
    
    # Create task
    task = await client.create_task(
        task_type="text_generation",
        model_name="microsoft/DialoGPT-medium",
        input_data={"prompt": "Hello world!"}
    )
    
    # Poll for completion
    while task.status in ["pending", "running"]:
        await asyncio.sleep(1)
        task = await client.get_task(task.task_id)
    
    print(f"Result: {task.result}")

asyncio.run(main())
```

### cURL Examples
```bash
# Create task
curl -X POST http://localhost:8002/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "text_generation",
    "model_name": "microsoft/DialoGPT-medium",
    "input_data": {"prompt": "Hello world!"}
  }'

# Get task status
curl http://localhost:8002/tasks/task_123e4567-e89b-12d3-a456-426614174000

# List tasks
curl "http://localhost:8002/tasks?status=completed&limit=10"
```
