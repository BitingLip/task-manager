# Task Manager Architecture

## Overview

The Task Manager is a FastAPI-based microservice that handles task scheduling, queuing, and lifecycle management within the BitingLip AI inference platform.

## Core Components

### 1. Task API Layer (`main.py`)
- RESTful endpoints for task management
- Request validation using Pydantic models
- FastAPI framework with automatic OpenAPI documentation

### 2. Task Storage
- **Current**: In-memory dictionary storage
- **Planned**: Database integration (PostgreSQL or MongoDB)

### 3. Task Models
- Shared data models from `common/models/`
- TaskType enum (text_generation, image_generation, etc.)
- TaskStatus enum (pending, running, completed, failed)

## Task Lifecycle

```
1. Task Creation (POST /tasks)
   ↓
2. Task Queuing (status: PENDING)
   ↓
3. Task Assignment to Worker (status: RUNNING)
   ↓
4. Task Execution
   ↓
5. Task Completion (status: COMPLETED/FAILED)
```

## Integration Points

### With Gateway Manager
- Receives task requests from API gateway
- Returns task status and results

### With Cluster Manager  
- Coordinates with worker assignment
- Receives status updates from workers

### With Model Manager
- Validates model availability
- Coordinates model loading requirements

## Future Architecture

### Database Layer
- Task persistence
- Task history and auditing
- Performance metrics storage

### Queue Management
- Redis-based task queuing
- Priority queue implementation
- Dead letter queue for failed tasks

### Monitoring
- Task execution metrics
- Performance monitoring
- Health checks and alerting
