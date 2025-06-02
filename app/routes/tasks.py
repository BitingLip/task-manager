"""
Task management routes
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Body
from app.services.task_service import TaskService
from common.models import TaskRequest, TaskResponse, TaskStatus, TaskType, TaskStatistics
from pydantic import BaseModel

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskDependencyRequest(BaseModel):
    """Request model for adding task dependencies"""
    dependency_task_id: str
    dependency_type: str = "completion"


class TaskMetricRequest(BaseModel):
    """Request model for adding task metrics"""
    metric_name: str
    metric_value: float
    metric_unit: str = ""
    metadata: Optional[Dict[str, Any]] = None


class TaskCancelRequest(BaseModel):
    """Request model for cancelling tasks"""
    reason: str = "User cancelled"
    cancelled_by: str = "api"


class TaskRetryRequest(BaseModel):
    """Request model for retrying tasks"""
    max_retries: int = 3
    reason: str = "Manual retry"


def get_task_service(request: Request) -> TaskService:
    """Get task service from app state"""
    return request.app.state.task_service


@router.post("/", response_model=TaskResponse)
async def create_task(
    task_request: TaskRequest,
    task_service: TaskService = Depends(get_task_service)
) -> TaskResponse:
    """Create a new task"""
    try:
        return await task_service.create_task(task_request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
) -> TaskResponse:
    """Get task details by ID"""
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    task_type: Optional[TaskType] = Query(None, description="Filter by task type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of tasks to return"),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
    task_service: TaskService = Depends(get_task_service)
) -> List[TaskResponse]:
    """List tasks with optional filtering and pagination"""
    try:
        return await task_service.list_tasks(
            status=status,
            task_type=task_type,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


# Phase 2: Enhanced Task Operations

@router.patch("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    request: TaskCancelRequest = Body(default=TaskCancelRequest()),
    task_service: TaskService = Depends(get_task_service)
):
    """Cancel a pending or running task with tracking"""
    success = await task_service.cancel_task(
        task_id=task_id, 
        reason=request.reason, 
        cancelled_by=request.cancelled_by
    )
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")
    return {"message": "Task cancelled successfully", "task_id": task_id, "reason": request.reason}


@router.post("/{task_id}/retry")
async def retry_task(
    task_id: str,
    request: TaskRetryRequest = Body(default=TaskRetryRequest()),
    task_service: TaskService = Depends(get_task_service)
):
    """Retry a failed task"""
    success = await task_service.retry_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or cannot be retried")
    return {"message": "Task retry initiated", "task_id": task_id}


# Phase 2: Task Dependencies

@router.post("/{task_id}/dependencies")
async def add_task_dependency(
    task_id: str,
    dependency: TaskDependencyRequest,
    task_service: TaskService = Depends(get_task_service)
):
    """Add a dependency relationship between tasks"""
    try:
        success = await task_service.add_task_dependency(
            task_id=task_id,
            dependency_task_id=dependency.dependency_task_id,
            dependency_type=dependency.dependency_type
        )
        if not success:
            raise HTTPException(status_code=400, detail="Failed to add dependency")
        return {"message": "Dependency added successfully", "task_id": task_id, 
                "dependency_task_id": dependency.dependency_task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add dependency: {str(e)}")


@router.get("/{task_id}/dependencies")
async def get_task_dependencies(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
):
    """Get all dependencies for a task"""
    try:
        dependencies = await task_service.get_task_dependencies(task_id)
        return {"task_id": task_id, "dependencies": dependencies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dependencies: {str(e)}")


@router.get("/ready/list")
async def get_ready_tasks(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of tasks to return"),
    task_service: TaskService = Depends(get_task_service)
):
    """Get tasks that are ready to execute (all dependencies satisfied)"""
    try:
        tasks = await task_service.get_ready_tasks(limit)
        return {"ready_tasks": tasks, "count": len(tasks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ready tasks: {str(e)}")


# Phase 2: Task Metrics and Analytics

@router.post("/{task_id}/metrics")
async def add_task_metric(
    task_id: str,
    metric: TaskMetricRequest,
    task_service: TaskService = Depends(get_task_service)
):
    """Add a performance metric for a task"""
    try:
        success = await task_service.add_task_metric(
            task_id=task_id,
            metric_name=metric.metric_name,
            metric_value=metric.metric_value,
            metric_unit=metric.metric_unit,
            metadata=metric.metadata
        )
        if not success:
            raise HTTPException(status_code=400, detail="Failed to add metric")
        return {"message": "Metric added successfully", "task_id": task_id, 
                "metric_name": metric.metric_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add metric: {str(e)}")


@router.get("/analytics/summary")
async def get_task_analytics(
    hours_back: int = Query(24, ge=1, le=168, description="Hours to look back for analytics"),
    task_service: TaskService = Depends(get_task_service)
):
    """Get comprehensive task analytics and insights"""
    try:
        analytics = await task_service.get_task_analytics(hours_back)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


@router.get("/metrics/performance")
async def get_performance_metrics(
    metric_name: Optional[str] = Query(None, description="Filter by specific metric name"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of metrics to return"),
    task_service: TaskService = Depends(get_task_service)
):
    """Get performance metrics across all tasks"""
    try:
        metrics = await task_service.get_performance_metrics(metric_name, limit)
        return {"metrics": metrics, "count": len(metrics)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")


# Phase 2: Worker Management

@router.post("/{task_id}/assign/{worker_id}")
async def assign_task_to_worker(
    task_id: str,
    worker_id: str,
    task_service: TaskService = Depends(get_task_service)
):
    """Assign a task to a specific worker"""
    try:
        success = await task_service.assign_task_to_worker(task_id, worker_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to assign task to worker")
        return {"message": "Task assigned successfully", "task_id": task_id, "worker_id": worker_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign task: {str(e)}")


@router.get("/workers/{worker_id}/performance")
async def get_worker_performance(
    worker_id: str,
    hours_back: int = Query(24, ge=1, le=168, description="Hours to look back for performance data"),
    task_service: TaskService = Depends(get_task_service)
):
    """Get performance metrics for a specific worker"""
    try:
        performance = await task_service.get_worker_performance(worker_id, hours_back)
        return {"worker_id": worker_id, "performance": performance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get worker performance: {str(e)}")


# Phase 2: Task Execution Logs

@router.get("/{task_id}/logs")
async def get_task_execution_logs(
    task_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of log entries to return"),
    task_service: TaskService = Depends(get_task_service)
):
    """Get execution logs for a task"""
    try:
        logs = await task_service.get_task_execution_logs(task_id, limit)
        return {"task_id": task_id, "logs": logs, "count": len(logs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task logs: {str(e)}")


@router.get("/{task_id}/history")
async def get_task_status_history(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
):
    """Get status change history for a task"""
    try:
        history = await task_service.get_task_status_history(task_id)
        return {"task_id": task_id, "status_history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task history: {str(e)}")


# Original Phase 1 endpoints (maintained for compatibility)

@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
):
    """Delete a task"""
    success = await task_service.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully", "task_id": task_id}


@router.get("/stats/metrics", response_model=TaskStatistics)
async def get_task_metrics(
    task_service: TaskService = Depends(get_task_service)
) -> TaskStatistics:
    """Get task execution statistics and metrics"""
    try:
        return await task_service.get_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/workers/stats")
async def get_worker_stats(
    task_service: TaskService = Depends(get_task_service)
):
    """Get statistics about available Celery workers"""
    try:
        stats = await task_service.get_worker_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get worker stats: {str(e)}")


@router.get("/workers/health")
async def check_worker_health(
    task_service: TaskService = Depends(get_task_service)
):
    """Check the health of Celery workers and queues"""
    try:
        stats = await task_service.get_worker_stats()
          # Simple health check based on worker availability
        health_status = "healthy" if stats.get("online_workers", 0) > 0 else "unhealthy"
        
        return {
            "status": health_status,
            "total_workers": stats.get("total_workers", 0),
            "online_workers": stats.get("online_workers", 0),
            "queue_info": stats.get("queue_info", {}),
            "timestamp": None  # Can be enhanced later with proper async Redis time call
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check worker health: {str(e)}")


@router.patch("/{task_id}/status")
async def update_task_status(
    task_id: str,
    status: TaskStatus,
    worker_id: Optional[str] = None,
    task_service: TaskService = Depends(get_task_service)
):
    """Update task status (internal endpoint for workers)"""
    task = await task_service.update_task_status(
        task_id=task_id,
        status=status,
        worker_id=worker_id
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task status updated", "task_id": task_id, "status": status}
