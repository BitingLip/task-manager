"""
Task Service - Central orchestrator for task management and execution
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
import asyncio
import sys
import os
from celery import Celery
from celery.result import AsyncResult
import redis

# Add project root to path to access common module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from common.models import (
    TaskRequest, TaskResponse, TaskStatus, TaskType, 
    TaskMetrics, TaskStatistics, WorkerAssignment
)
from ..utils import generate_task_id, format_timestamp
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class TaskService:
    """Central orchestrator for task management and execution via Celery workers"""
    
    def __init__(self, settings, db_manager=None):
        self.settings = settings
        self.db_manager = db_manager
        
        # Legacy in-memory storage (for fallback if no database)
        self.tasks_db: Dict[str, Dict[str, Any]] = {}
        self.worker_assignments: Dict[str, WorkerAssignment] = {}
        
        # Initialize Celery client for task orchestration
        self.celery_app = Celery(
            'task_manager_orchestrator',
            broker=settings.celery_broker_url,
            backend=settings.celery_result_backend
        )
        
        # Configure Celery client
        self.celery_app.conf.update(
            task_serializer='json',
            result_serializer='json',
            accept_content=['json'],
            timezone='UTC',
            enable_utc=True,
            task_track_started=True,
            result_expires=3600  # Results expire after 1 hour
        )
        
        # Redis client for additional task metadata
        self.redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        
        # Map task types to Celery task names
        self.task_type_mapping = {
            TaskType.LLM: 'app.tasks.run_llm_inference',
            TaskType.STABLE_DIFFUSION: 'app.tasks.run_sd_inference',
            TaskType.TTS: 'app.tasks.run_tts_inference',
            TaskType.IMAGE_TO_TEXT: 'app.tasks.run_image_to_text_inference'
        }
        
    async def initialize(self) -> None:
        """Initialize the task service"""
        logger.info("Task Service initializing")
        # Test Celery connection
        try:
            inspector = self.celery_app.control.inspect()
            stats = inspector.stats()
            if stats:
                logger.info("Connected to Celery workers", worker_count=len(stats))
            else:
                logger.warning("No Celery workers found")
        except Exception as e:
            logger.error("Failed to connect to Celery", error=str(e))
        
    async def cleanup(self) -> None:
        """Cleanup resources"""
        logger.info("Task Service cleaning up")        # Close Redis connection
        if hasattr(self, 'redis_client'):
            self.redis_client.close()
        
    async def _dispatch_to_worker(self, task_id: str, task_request: TaskRequest) -> AsyncResult:
        """Dispatch task to appropriate Celery worker with intelligent routing"""
        celery_task_name = self.task_type_mapping[task_request.task_type]
        
        # Find optimal worker for this task
        optimal_worker = await self.get_optimal_worker(task_request.task_type)
        
        # Prepare task payload for worker
        task_payload = {
            'task_id': task_id,
            'model_name': task_request.model_name,
            'payload': task_request.input_data,
            'parameters': task_request.parameters or {}
        }
        
        # Prepare routing options
        routing_options = {
            'priority': 10 - (task_request.priority or 5),  # Celery uses reverse priority
            'soft_time_limit': (task_request.timeout or 300) - 30,
            'time_limit': task_request.timeout or 300,
            'queue': 'gpu_queue',  # Default to GPU queue
        }
        
        # Add worker routing if optimal worker found
        if optimal_worker:
            routing_options['routing_key'] = optimal_worker
            logger.info("Routing task to optimal worker", 
                       task_id=task_id, 
                       worker=optimal_worker, 
                       task_type=task_request.task_type)        
        # Send task to worker
        result = self.celery_app.send_task(
            celery_task_name,
            args=[task_payload],
            **routing_options
        )
        
        return result
    
    async def create_task(self, task_request: TaskRequest) -> TaskResponse:
        """Create and dispatch a new task to cluster workers"""
        task_id = generate_task_id()
        
        # Validate task type
        if task_request.task_type not in self.task_type_mapping:
            raise ValueError(f"Unsupported task type: {task_request.task_type}")
        
        task_data = {
            "id": task_id,
            "type": task_request.task_type.value,
            "status": TaskStatus.PENDING.value,
            "priority": task_request.priority or 5,
            "model_id": task_request.model_name,
            "input_data": {
                "input_data": task_request.input_data,
                "parameters": task_request.parameters or {}
            },
            "created_at": datetime.utcnow(),
            "timeout_seconds": task_request.timeout or 300,
            "max_retries": 3,
            "metadata": {
                "original_request": task_request.dict() if hasattr(task_request, 'dict') else {}
            }
        }
        
        # Store task in database or fallback to memory
        if self.db_manager:
            try:
                await self.db_manager.create_task(task_data)
                logger.info("Task stored in database", task_id=task_id)
            except Exception as e:
                logger.error("Failed to store task in database, using memory fallback", 
                           task_id=task_id, error=str(e))
                self.tasks_db[task_id] = task_data
        else:
            self.tasks_db[task_id] = task_data
        
        logger.info("Task created", task_id=task_id, task_type=task_request.task_type)
        
        # Dispatch task to cluster workers via Celery
        try:
            celery_task_result = await self._dispatch_to_worker(task_id, task_request)
            
            # Update task status in database
            if self.db_manager:
                await self.db_manager.update_task_status(
                    task_id, 
                    TaskStatus.STARTED.value,
                    started_at=datetime.utcnow()
                )
            else:
                task_data["status"] = TaskStatus.STARTED.value
                task_data["started_at"] = datetime.utcnow()
            
            logger.info("Task dispatched to worker", task_id=task_id, celery_task_id=celery_task_result.id)
            
        except Exception as e:
            # Update task status to failure
            if self.db_manager:
                await self.db_manager.update_task_status(
                    task_id,
                    TaskStatus.FAILURE.value,
                    error_message=str(e)
                )
            else:
                task_data["status"] = TaskStatus.FAILURE.value
                task_data["error_message"] = str(e)
            
            logger.error("Failed to dispatch task", task_id=task_id, error=str(e))
          # Get current task data for response
        current_task = await self._get_task_data(task_id)
        if not current_task:
            logger.error("Task data not found after creation", task_id=task_id)
            # Return basic response with task_data as fallback
            current_task = task_data
        
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus(current_task["status"]),
            task_type=task_request.task_type,            model_name=task_request.model_name,
            created_at=current_task["created_at"],
            started_at=current_task.get("started_at"),
            error=current_task.get("error_message")
        )
    
    async def get_task(self, task_id: str) -> Optional[TaskResponse]:
        """Get task details with real-time status from Celery"""
        task = await self._get_task_data(task_id)
        if not task:
            return None
        
        # Ensure task is not None and has required fields
        if not isinstance(task, dict):
            logger.error("Invalid task data type", task_id=task_id, task_type=type(task))
            return None
        
        # Update task status from Celery if available (for legacy tasks)
        if task.get("celery_task_id"):
            await self._update_task_status(task_id)
            # Refresh task data after update
            task = await self._get_task_data(task_id)
            if not task:
                return None
        
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus(task["status"]),
            task_type=TaskType(task.get("type", task.get("task_type", "text_generation"))),
            model_name=task.get("model_id", task.get("model_name", "unknown")),
            created_at=task["created_at"],
            started_at=task.get("started_at"),
            completed_at=task.get("completed_at"),
            worker_id=task.get("worker_id"),
            result=task.get("output_data", task.get("result")),
            error=task.get("error_message", task.get("error"))
        )
    
    async def _update_task_status(self, task_id: str) -> None:
        """Update task status from Celery result"""
        task = self.tasks_db.get(task_id)
        if not task or not task.get("celery_task_id"):
            return
            
        try:
            celery_result = AsyncResult(task["celery_task_id"], app=self.celery_app)
            
            # Map Celery states to our TaskStatus
            status_mapping = {
                'PENDING': TaskStatus.PENDING,
                'STARTED': TaskStatus.STARTED,
                'SUCCESS': TaskStatus.SUCCESS,
                'FAILURE': TaskStatus.FAILURE,
                'RETRY': TaskStatus.RETRY,
                'REVOKED': TaskStatus.REVOKED
            }
            
            celery_status = celery_result.state
            new_status = status_mapping.get(celery_status, TaskStatus.PENDING)
            
            # Only update if status changed
            if task["status"] != new_status:
                task["status"] = new_status
                task["updated_at"] = datetime.utcnow()
                
                if new_status == TaskStatus.SUCCESS:
                    task["completed_at"] = datetime.utcnow()
                    task["result"] = celery_result.result
                elif new_status == TaskStatus.FAILURE:
                    task["completed_at"] = datetime.utcnow()
                    task["error"] = str(celery_result.info)
                    
                logger.info("Task status updated", task_id=task_id, status=new_status)
                
        except Exception as e:
            logger.error("Failed to update task status", task_id=task_id, error=str(e))
        
    async def list_tasks(self, 
                        status: Optional[TaskStatus] = None,
                        task_type: Optional[TaskType] = None,
                        limit: int = 100,
                        offset: int = 0) -> List[TaskResponse]:
        """List tasks with optional filtering"""
        tasks = []
        
        for task_data in self.tasks_db.values():
            # Apply filters
            if status and task_data["status"] != status:
                continue
            if task_type and task_data["task_type"] != task_type:
                continue
                
            task_response = TaskResponse(
                task_id=task_data["task_id"],
                status=task_data["status"],
                task_type=task_data["task_type"],
                model_name=task_data["model_name"],
                created_at=task_data["created_at"],
                started_at=task_data.get("started_at"),
                completed_at=task_data.get("completed_at"),
                worker_id=task_data.get("worker_id"),
                result=task_data.get("result"),
                error=task_data.get("error")
            )
            tasks.append(task_response)
        
        # Sort by creation time (newest first)
        tasks.sort(key=lambda t: t.created_at, reverse=True)
          # Apply pagination
        return tasks[offset:offset + limit]
        
    async def update_task_status(self, 
                               task_id: str, 
                               status: TaskStatus,
                               worker_id: Optional[str] = None,
                               result: Optional[Dict[str, Any]] = None,
                               error: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Update task status and related information"""
        if task_id not in self.tasks_db:
            return None
            
        task = self.tasks_db[task_id]
        old_status = task["status"]
        
        task["status"] = status
        task["updated_at"] = datetime.utcnow()
        
        if worker_id:
            task["worker_id"] = worker_id
            
        if status == TaskStatus.STARTED:
            task["started_at"] = datetime.utcnow()
            
        if result:
            task["result"] = result
            
        if error:
            task["error"] = error
            
        if status in [TaskStatus.SUCCESS, TaskStatus.FAILURE]:
            task["completed_at"] = datetime.utcnow()
            
        logger.info(
            "Task status updated", 
            task_id=task_id, 
            old_status=old_status, 
            new_status=status,
            worker_id=worker_id
        )
        
        return task
        
    async def cancel_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Cancel a pending or running task via Celery revoke"""
        if task_id not in self.tasks_db:
            return None
            
        task = self.tasks_db[task_id]
        
        if task["status"] in [TaskStatus.SUCCESS, TaskStatus.FAILURE]:
            return None  # Cannot cancel completed tasks
            
        # Revoke the Celery task if it exists
        if task.get("celery_task_id"):
            try:
                self.celery_app.control.revoke(
                    task["celery_task_id"], 
                    terminate=True,  # Kill running task
                    signal='SIGKILL'
                )
                logger.info("Celery task revoked", task_id=task_id, celery_task_id=task["celery_task_id"])
            except Exception as e:
                logger.error("Failed to revoke Celery task", task_id=task_id, error=str(e))
                
        task["status"] = TaskStatus.REVOKED
        task["updated_at"] = datetime.utcnow()
        task["completed_at"] = datetime.utcnow()
        
        logger.info("Task cancelled", task_id=task_id)
        
        return task
    
    async def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        if task_id not in self.tasks_db:
            return False
            
        del self.tasks_db[task_id]
        logger.info("Task deleted", task_id=task_id)
        return True
    
    async def get_metrics(self) -> TaskStatistics:
        """Get task manager metrics"""
        if not self.tasks_db:
            return TaskStatistics(
                total_tasks=0,
                pending_tasks=0,
                running_tasks=0,
                completed_tasks=0,
                failed_tasks=0,
                success_rate=0.0,
                average_execution_time=0.0
            )
            
        total = len(self.tasks_db)
        pending = len([t for t in self.tasks_db.values() if t["status"] == TaskStatus.PENDING])
        running = len([t for t in self.tasks_db.values() if t["status"] == TaskStatus.STARTED])
        completed = len([t for t in self.tasks_db.values() if t["status"] == TaskStatus.SUCCESS])
        failed = len([t for t in self.tasks_db.values() if t["status"] == TaskStatus.FAILURE])
        
        success_rate = (completed / total * 100) if total > 0 else 0.0
        
        # Calculate average execution time for completed tasks
        completed_tasks = [t for t in self.tasks_db.values() if t["status"] == TaskStatus.SUCCESS and "completed_at" in t]
        avg_execution_time = 0.0
        if completed_tasks:
            execution_times = [
                (t["completed_at"] - t["created_at"]).total_seconds() 
                for t in completed_tasks 
                if "completed_at" in t
            ]
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0.0
        
        return TaskStatistics(
            total_tasks=total,
            pending_tasks=pending,
            running_tasks=running,
            completed_tasks=completed,
            failed_tasks=failed,
            success_rate=success_rate,
            average_execution_time=avg_execution_time        )
        
    async def get_worker_stats(self) -> Dict[str, Any]:
        """Get statistics about available Celery workers"""
        try:
            inspector = self.celery_app.control.inspect()
            
            # Get worker statistics
            stats = inspector.stats()
            active = inspector.active()
            scheduled = inspector.scheduled()
            reserved = inspector.reserved()
            
            worker_info = {}
            
            if stats:
                for worker_name, worker_stats in stats.items():
                    worker_info[worker_name] = {
                        'status': 'online',
                        'stats': worker_stats,
                        'active_tasks': len(active.get(worker_name, [])) if active else 0,
                        'scheduled_tasks': len(scheduled.get(worker_name, [])) if scheduled else 0,
                        'reserved_tasks': len(reserved.get(worker_name, [])) if reserved else 0,
                        'total_load': len(active.get(worker_name, [])) + len(scheduled.get(worker_name, [])) + len(reserved.get(worker_name, [])) if active and scheduled and reserved else 0
                    }
                    
            return {
                'total_workers': len(worker_info),
                'online_workers': len([w for w in worker_info.values() if w['status'] == 'online']),
                'workers': worker_info,
                'queue_info': self._get_queue_info()
            }
            
        except Exception as e:
            logger.error("Failed to get worker stats", error=str(e))
            return {
                'total_workers': 0,
                'online_workers': 0,
                'workers': {},
                'queue_info': {},
                'error': str(e)
            }
    
    def _get_queue_info(self) -> Dict[str, Any]:
        """Get information about task queues"""
        try:
            # Get queue lengths from Redis
            queue_info = {}
            
            # Check common queue names used by cluster-manager
            queue_names = ['gpu_queue', 'celery', 'default']
            
            for queue_name in queue_names:
                queue_length = self.redis_client.llen(queue_name)
                queue_info[queue_name] = {
                    'length': queue_length,
                    'name': queue_name
                }
                
            return queue_info
            
        except Exception as e:
            logger.error("Failed to get queue info", error=str(e))
            return {}
    
    async def get_optimal_worker(self, task_type: TaskType) -> Optional[str]:
        """Find the optimal worker for a given task type based on current load"""
        try:
            worker_stats = await self.get_worker_stats()
            
            if not worker_stats['workers']:
                logger.warning("No workers available")
                return None
                
            # Find worker with lowest load
            optimal_worker = None
            min_load = float('inf')
            
            for worker_name, worker_info in worker_stats['workers'].items():
                if worker_info['status'] == 'online':
                    current_load = worker_info['total_load']
                    if current_load < min_load:
                        min_load = current_load
                        optimal_worker = worker_name
                        
            logger.info(
                "Selected optimal worker", 
                worker=optimal_worker, 
                load=min_load,
                task_type=task_type
            )
            
            return optimal_worker
            
        except Exception as e:
            logger.error("Failed to find optimal worker", error=str(e))
            return None
    
    async def _queue_task(self, task_id: str) -> None:
        """Queue task for execution with worker discovery"""
        task = self.tasks_db.get(task_id)
        if not task:
            return
            
        # Find optimal worker for the task
        optimal_worker = await self.get_optimal_worker(task['task_type'])
        
        if optimal_worker:
            task['preferred_worker'] = optimal_worker
            logger.info("Task assigned to optimal worker", task_id=task_id, worker=optimal_worker)
        else:
            logger.warning("No optimal worker found, using default routing", task_id=task_id)
    
    async def _get_task_data(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task data from database or memory fallback"""
        if self.db_manager:
            try:
                return await self.db_manager.get_task(task_id)
            except Exception as e:
                logger.error("Failed to get task from database, using memory fallback", 
                           task_id=task_id, error=str(e))
                
        # Fallback to memory storage
        return self.tasks_db.get(task_id)
