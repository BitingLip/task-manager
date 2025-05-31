"""
Task management routes
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.services.task_service import TaskService
from common.models import TaskRequest, TaskResponse, TaskStatus, TaskType, TaskStatistics

router = APIRouter(prefix="/tasks", tags=["tasks"])


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


@router.patch("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
):
    """Cancel a pending or running task"""
    task = await task_service.cancel_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")
    return {"message": "Task cancelled successfully", "task_id": task_id}


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
