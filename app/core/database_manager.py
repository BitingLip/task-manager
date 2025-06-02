"""
Database connection and management for Task Manager
"""

import asyncpg
import asyncio
import json
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import structlog
from datetime import datetime
import os
import sys

# Add project root to path to access common module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from common.models import TaskResponse, TaskStatus, TaskType

# Import settings (will implement after creating the file)
# from app.core.config import settings

logger = structlog.get_logger(__name__)


class TaskDatabaseManager:
    """Database connection manager for PostgreSQL - Task Manager"""
    
    def __init__(self, settings=None):
        self.settings = settings
        self.pool: Optional[asyncpg.Pool] = None
        self._connection_url = self._build_connection_url()
        
    def _build_connection_url(self) -> str:
        """Build PostgreSQL connection URL from config"""
        if self.settings:
            # Use settings if provided
            return f"postgresql://{self.settings.db_user}:{self.settings.db_password}@{self.settings.db_host}:{self.settings.db_port}/{self.settings.db_name}"
        
        # Fallback to environment variables
        db_user = os.getenv('POSTGRES_USER', 'postgres')
        db_password = os.getenv('POSTGRES_PASSWORD', 'postgres')
        db_host = os.getenv('POSTGRES_HOST', 'localhost')
        db_port = os.getenv('POSTGRES_PORT', '5432')
        db_name = os.getenv('POSTGRES_DB', 'bitinglip_tasks')
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    async def initialize(self):
        """Initialize database connection pool and schema"""
        try:
            self.pool = await asyncpg.create_pool(
                self._connection_url,
                min_size=3,
                max_size=10,
                command_timeout=60,
                server_settings={
                    'application_name': 'task-manager'
                }
            )
            
            db_info = self._parse_connection_url()
            logger.info("Task Manager database connection pool initialized", 
                       host=db_info['host'], 
                       port=db_info['port'], 
                       database=db_info['database'])
            
            # Test connection
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
                
            # Initialize schema if needed
            await self._initialize_schema()
                
        except Exception as e:
            logger.error("Failed to initialize Task Manager database connection", error=str(e))
            raise
    
    def _parse_connection_url(self) -> Dict[str, str]:
        """Parse connection URL for logging"""
        try:
            # Extract host, port, database from URL for logging
            if self.settings:
                return {
                    'host': self.settings.db_host,
                    'port': str(self.settings.db_port),
                    'database': self.settings.db_name
                }
            
            return {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': os.getenv('POSTGRES_PORT', '5432'),
                'database': os.getenv('POSTGRES_DB', 'bitinglip_tasks')
            }
        except Exception:
            return {'host': 'unknown', 'port': 'unknown', 'database': 'unknown'}
    
    async def _initialize_schema(self):
        """Initialize database schema from SQL file"""
        try:
            schema_path = os.path.join(
                os.path.dirname(__file__), 
                '..', '..', 'database', 'task_manager_schema.sql'
            )
            
            if os.path.exists(schema_path):
                with open(schema_path, 'r') as f:
                    schema_sql = f.read()
                
                if not self.pool:
                    logger.error("Database pool is not initialized, cannot initialize schema")
                    return

                async with self.pool.acquire() as conn:
                    await conn.execute(schema_sql)
                    
                logger.info("Task Manager database schema initialized")
            else:
                logger.warning("Schema file not found", path=schema_path)
                
        except Exception as e:
            logger.error("Failed to initialize database schema", error=str(e))
            # Don't raise - let the service start even if schema init fails
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Task Manager database connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
            
        async with self.pool.acquire() as connection:
            yield connection
    
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute query and return results"""
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def execute_command(self, command: str, *args) -> str:
        """Execute command and return status"""
        async with self.get_connection() as conn:
            return await conn.execute(command, *args)
    
    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch single row"""
        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None
        
    async def execute_returning(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute INSERT/UPDATE/DELETE with RETURNING clause"""
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    # Task-specific database methods
    async def create_task(self, task_data: Dict[str, Any]) -> str:
        """Create a new task in database"""
        query = """
        INSERT INTO tasks (
            id, type, status, priority, model_id, worker_id, 
            input_data, created_at, metadata
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9
        ) RETURNING id
        """        
        result = await self.execute_returning(
            query,
            task_data['id'],
            task_data['type'],
            task_data.get('status', 'pending'),
            task_data.get('priority', 0),
            task_data.get('model_id'),
            task_data.get('worker_id'),
            json.dumps(task_data['input_data']),
            task_data.get('created_at', datetime.now()),
            json.dumps(task_data.get('metadata', {}))
        )
        
        return result[0]['id'] if result else ""
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID"""
        query = "SELECT * FROM tasks WHERE id = $1"
        return await self.fetch_one(query, task_id)
    
    async def update_task_status(self, task_id: str, status: str, **kwargs) -> bool:
        """Update task status and optional fields"""
        # Build dynamic update query
        updates = ["status = $2"]
        values = [task_id, status]
        param_count = 2
        for field, value in kwargs.items():
            if field in ['started_at', 'completed_at', 'output_data', 'error_message', 'worker_id']:
                param_count += 1
                updates.append(f"{field} = ${param_count}")
                values.append(value)
        
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = $1"
        result = await self.execute_command(query, *values)
        return "UPDATE 1" in result
    
    async def get_tasks_by_status(self, status: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get tasks by status"""
        query = "SELECT * FROM tasks WHERE status = $1 ORDER BY created_at DESC LIMIT $2"
        return await self.execute_query(query, status, limit)
    
    async def get_pending_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get pending tasks ordered by priority and creation time"""
        query = """
        SELECT * FROM tasks 
        WHERE status = 'pending' 
        ORDER BY priority DESC, created_at ASC 
        LIMIT $1
        """
        return await self.execute_query(query, limit)
    
    async def list_tasks(self, 
                        status: Optional[str] = None,
                        task_type: Optional[str] = None,
                        limit: int = 100,
                        offset: int = 0) -> List[TaskResponse]:
        """List tasks with optional filtering and pagination"""
        
        # Build dynamic query with filters
        conditions = []
        params = []
        param_count = 0
        
        if status:
            param_count += 1
            conditions.append(f"status = ${param_count}")
            params.append(status)
        
        if task_type:
            param_count += 1
            conditions.append(f"type = ${param_count}")
            params.append(task_type)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        param_count += 1
        limit_param = f"${param_count}"
        params.append(limit)
        
        param_count += 1
        offset_param = f"${param_count}"
        params.append(offset)
        
        query = f"""
        SELECT id, type, status, priority, model_id, worker_id, 
               input_data, output_data, error_message, 
               created_at, started_at, completed_at, metadata
        FROM tasks 
        {where_clause}
        ORDER BY created_at DESC 
        LIMIT {limit_param} OFFSET {offset_param}
        """
        
        try:
            rows = await self.execute_query(query, *params)
            tasks = []
            
            for row in rows:
                task_response = TaskResponse(
                    task_id=row['id'],
                    status=TaskStatus(row['status']),
                    task_type=TaskType(row['type']),
                    model_name=row['model_id'] or 'unknown',
                    created_at=row['created_at'],
                    started_at=row.get('started_at'),
                    completed_at=row.get('completed_at'),
                    worker_id=row.get('worker_id'),
                    result=row.get('output_data'),
                    error=row.get('error_message')
                )
                tasks.append(task_response)
            
            return tasks
        
        except Exception as e:
            logger.error("Failed to list tasks", error=str(e))
            return []
    
    async def add_task_metric(self, task_id: str, metric_name: str, metric_value: float,
                             metric_unit: str = "", metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Add task performance metric"""
        query = """
        INSERT INTO task_metrics (task_id, metric_name, metric_value, metric_unit, metadata)
        VALUES ($1, $2, $3, $4, $5)
        """
        try:
            await self.execute_command(
                query, task_id, metric_name, metric_value, 
                metric_unit, json.dumps(metadata or {})
            )
            return True
        except Exception as e:
            logger.error("Failed to add task metric", task_id=task_id, error=str(e))
            return False
    
    async def get_task_statistics(self) -> Dict[str, Any]:
        """Get overall task statistics"""
        query = """
        SELECT 
            status,
            COUNT(*) as count
        FROM tasks
        GROUP BY status
        """
        results = await self.execute_query(query)
        
        return {
            'total_tasks': sum(r['count'] for r in results),
            'by_status': {r['status']: r for r in results}
        }

    # Phase 2A: Advanced Task Analytics & Metrics Methods
    
    async def get_task_analytics(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get comprehensive task analytics for the specified time period"""
        query = """
        SELECT 
            COUNT(*) as total_tasks,
            COUNT(*) FILTER (WHERE status = 'completed') as completed_tasks,
            COUNT(*) FILTER (WHERE status = 'failed') as failed_tasks,
            COUNT(*) FILTER (WHERE status = 'pending') as pending_tasks,
            COUNT(*) FILTER (WHERE status = 'started') as running_tasks,
            AVG(actual_duration) FILTER (WHERE actual_duration IS NOT NULL) as avg_duration_seconds,
            MAX(actual_duration) FILTER (WHERE actual_duration IS NOT NULL) as max_duration_seconds,
            MIN(actual_duration) FILTER (WHERE actual_duration IS NOT NULL) as min_duration_seconds,
            AVG(retry_count) as avg_retries,
            COUNT(DISTINCT worker_id) FILTER (WHERE worker_id IS NOT NULL) as active_workers
        FROM tasks 
        WHERE created_at >= NOW() - INTERVAL '%s hours'
        """
        
        result = await self.fetch_one(query, hours_back)
        
        # Get hourly breakdown
        hourly_query = """
        SELECT * FROM task_statistics 
        WHERE hour >= NOW() - INTERVAL '%s hours'
        ORDER BY hour DESC
        LIMIT 48
        """
        
        hourly_stats = await self.execute_query(hourly_query, hours_back)
        
        return {
            'summary': dict(result) if result else {},
            'hourly_breakdown': hourly_stats,
            'period_hours': hours_back
        }
    
    async def get_task_metrics_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all metrics for a specific task"""
        query = """
        SELECT metric_name, metric_value, metric_unit, recorded_at, metadata
        FROM task_metrics 
        WHERE task_id = $1 
        ORDER BY recorded_at DESC
        """
        return await self.execute_query(query, task_id)
    
    async def get_performance_metrics(self, metric_name: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get performance metrics, optionally filtered by metric name"""
        if metric_name:
            query = """
            SELECT t.id, t.type, t.status, tm.metric_name, tm.metric_value, 
                   tm.metric_unit, tm.recorded_at, t.worker_id
            FROM task_metrics tm
            JOIN tasks t ON tm.task_id = t.id
            WHERE tm.metric_name = $1
            ORDER BY tm.recorded_at DESC
            LIMIT $2
            """
            return await self.execute_query(query, metric_name, limit)
        else:
            query = """
            SELECT t.id, t.type, t.status, tm.metric_name, tm.metric_value, 
                   tm.metric_unit, tm.recorded_at, t.worker_id
            FROM task_metrics tm
            JOIN tasks t ON tm.task_id = t.id
            ORDER BY tm.recorded_at DESC
            LIMIT $1
            """
            return await self.execute_query(query, limit)
    
    async def add_task_execution_log(self, task_id: str, log_level: str, message: str, 
                                   worker_id: Optional[str] = None, step_name: Optional[str] = None,
                                   metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Add task execution log entry"""
        query = """
        INSERT INTO task_execution_logs (task_id, log_level, message, worker_id, step_name, metadata)
        VALUES ($1, $2, $3, $4, $5, $6)
        """
        try:
            await self.execute_command(
                query, task_id, log_level, message, worker_id, step_name,
                json.dumps(metadata or {})
            )
            return True
        except Exception as e:
            logger.error("Failed to add task execution log", task_id=task_id, error=str(e))
            return False
    
    async def get_task_execution_logs(self, task_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution logs for a task"""
        query = """
        SELECT log_level, message, timestamp, worker_id, step_name, metadata
        FROM task_execution_logs 
        WHERE task_id = $1 
        ORDER BY timestamp DESC 
        LIMIT $2
        """
        return await self.execute_query(query, task_id, limit)
    
    # Phase 2B: Task Dependencies & Advanced Queuing
    
    async def add_task_dependency(self, task_id: str, dependency_task_id: str, 
                                dependency_type: str = "requires_completion") -> bool:
        """Add a task dependency relationship"""
        query = """
        INSERT INTO task_dependencies (task_id, dependency_task_id, dependency_type)
        VALUES ($1, $2, $3)
        ON CONFLICT (task_id, dependency_task_id) DO NOTHING
        """
        try:
            await self.execute_command(query, task_id, dependency_task_id, dependency_type)
            return True
        except Exception as e:
            logger.error("Failed to add task dependency", task_id=task_id, 
                        dependency_task_id=dependency_task_id, error=str(e))
            return False
    
    async def get_task_dependencies(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all dependencies for a task"""
        query = """
        SELECT td.dependency_task_id, td.dependency_type, td.created_at,
               t.status as dependency_status, t.type as dependency_type_name
        FROM task_dependencies td
        JOIN tasks t ON td.dependency_task_id = t.id
        WHERE td.task_id = $1
        ORDER BY td.created_at
        """
        return await self.execute_query(query, task_id)
    
    async def get_ready_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get tasks that are ready to run (all dependencies satisfied)"""
        query = """
        SELECT t.* FROM tasks t
        WHERE t.status = 'pending'
        AND NOT EXISTS (
            SELECT 1 FROM task_dependencies td
            JOIN tasks dep_task ON td.dependency_task_id = dep_task.id
            WHERE td.task_id = t.id
            AND dep_task.status NOT IN ('completed', 'skipped')
        )
        ORDER BY t.priority DESC, t.created_at ASC
        LIMIT $1
        """
        return await self.execute_query(query, limit)
    
    async def assign_task_to_worker(self, task_id: str, worker_id: str, 
                                  estimated_completion: Optional[datetime] = None,
                                  assignment_score: float = 0.0) -> bool:
        """Assign a task to a worker"""
        query = """
        INSERT INTO worker_assignments (worker_id, task_id, estimated_completion, assignment_score)
        VALUES ($1, $2, $3, $4)
        """
        try:
            await self.execute_command(query, worker_id, task_id, estimated_completion, assignment_score)
            # Also update the task's worker_id
            await self.execute_command("UPDATE tasks SET worker_id = $1 WHERE id = $2", worker_id, task_id)
            return True
        except Exception as e:
            logger.error("Failed to assign task to worker", task_id=task_id, 
                        worker_id=worker_id, error=str(e))
            return False
    
    async def get_worker_assignments(self, worker_id: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get worker assignments, optionally filtered by worker"""
        base_query = """
        SELECT wa.*, t.type, t.status, t.priority, t.created_at as task_created_at
        FROM worker_assignments wa
        JOIN tasks t ON wa.task_id = t.id
        """
        
        conditions = []
        params = []
        
        param_count = 0
        if worker_id:
            param_count = 1
            conditions.append(f"wa.worker_id = ${param_count}")
            params.append(worker_id)
            
        if active_only:
            conditions.append("t.status IN ('pending', 'started', 'running')")
        
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
            
        base_query += " ORDER BY wa.assigned_at DESC"
        
        return await self.execute_query(base_query, *params)
    
    async def get_worker_performance(self, worker_id: str, hours_back: int = 24) -> Dict[str, Any]:
        """Get performance metrics for a specific worker"""
        query = """
        SELECT 
            COUNT(*) as total_tasks,
            COUNT(*) FILTER (WHERE status = 'completed') as completed_tasks,
            COUNT(*) FILTER (WHERE status = 'failed') as failed_tasks,
            AVG(actual_duration) FILTER (WHERE actual_duration IS NOT NULL) as avg_duration_seconds,
            AVG(retry_count) as avg_retries,
            MIN(started_at) as first_task,
            MAX(completed_at) as last_completed
        FROM tasks 
        WHERE worker_id = $1 
        AND created_at >= NOW() - INTERVAL '%s hours'
        """
        
        result = await self.fetch_one(query, worker_id, hours_back)
        return dict(result) if result else {}
    
    # Phase 2C: Enhanced Task Operations
    
    async def update_task_with_status_history(self, task_id: str, new_status: str, 
                                            changed_by: str = "system", reason: Optional[str] = None,
                                            **kwargs) -> bool:
        """Update task status with audit trail"""
        # Get current status first
        current_task = await self.get_task(task_id)
        if not current_task:
            return False
            
        old_status = current_task.get('status')
        
        # Update the task
        success = await self.update_task_status(task_id, new_status, **kwargs)
        
        if success:
            # Add status history record
            history_query = """
            INSERT INTO task_status_history (task_id, old_status, new_status, changed_by, reason)
            VALUES ($1, $2, $3, $4, $5)
            """
            try:
                await self.execute_command(history_query, task_id, old_status, new_status, changed_by, reason)
            except Exception as e:
                logger.warning("Failed to record status history", task_id=task_id, error=str(e))
        
        return success
    
    async def get_task_status_history(self, task_id: str) -> List[Dict[str, Any]]:
        """Get status change history for a task"""
        query = """
        SELECT old_status, new_status, changed_at, changed_by, reason, metadata
        FROM task_status_history 
        WHERE task_id = $1 
        ORDER BY changed_at DESC
        """
        return await self.execute_query(query, task_id)
    
    async def cancel_task(self, task_id: str, reason: str = "User cancelled", 
                         cancelled_by: str = "system") -> bool:
        """Cancel a task with proper status tracking"""
        from datetime import timezone
        return await self.update_task_with_status_history(
            task_id, "cancelled", changed_by=cancelled_by, reason=reason,
            completed_at=datetime.now(timezone.utc)
        )
    
    async def retry_failed_task(self, task_id: str, max_retries: Optional[int] = None) -> bool:
        """Retry a failed task"""
        current_task = await self.get_task(task_id)
        if not current_task:
            return False
            
        current_retries = current_task.get('retry_count', 0)
        task_max_retries = max_retries or current_task.get('max_retries', 3)
        
        if current_retries >= task_max_retries:
            logger.warning("Task exceeded max retries", task_id=task_id, 
                          retries=current_retries, max_retries=task_max_retries)
            return False
        
        # Reset task to pending and increment retry count
        return await self.update_task_with_status_history(
            task_id, "pending", 
            changed_by="retry_system", 
            reason=f"Retry attempt {current_retries + 1}",
            retry_count=current_retries + 1,
            started_at=None,
            completed_at=None,
            error_message=None
        )    
  # Global database manager instance
db_manager = TaskDatabaseManager()


async def get_db() -> TaskDatabaseManager:
    """Dependency to get database manager"""
    return db_manager


async def initialize_database(settings=None):
    """Initialize database on startup"""
    global db_manager
    if settings:
        # Update the existing instance with settings instead of creating a new one
        db_manager.settings = settings
        db_manager._connection_url = db_manager._build_connection_url()
    await db_manager.initialize()


async def close_database():
    """Close database on shutdown"""
    await db_manager.close()
