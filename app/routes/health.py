"""
Health check routes for task manager
"""

from fastapi import APIRouter, Depends, Request
from app.services.task_service import TaskService

router = APIRouter(prefix="/health", tags=["health"])


def get_task_service(request: Request) -> TaskService:
    """Get task service from app state"""
    return request.app.state.task_service


@router.get("/")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "service": "task-manager"}


@router.get("/ready")
async def readiness_check(task_service: TaskService = Depends(get_task_service)):
    """Readiness check - ensures service dependencies are available"""
    try:
        # Check if task service is properly initialized
        metrics = await task_service.get_metrics()
        return {
            "status": "ready", 
            "service": "task-manager",
            "tasks": {
                "total": metrics.total_tasks,
                "pending": metrics.pending_tasks,
                "running": metrics.running_tasks
            }
        }
    except Exception as e:
        return {"status": "not ready", "error": str(e)}


@router.get("/metrics")
async def get_health_metrics(task_service: TaskService = Depends(get_task_service)):
    """Get detailed health and performance metrics"""
    try:
        metrics = await task_service.get_metrics()
        return {
            "status": "healthy",
            "service": "task-manager", 
            "metrics": metrics.dict()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
