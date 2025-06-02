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
        else:
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
            else:
                return {
                    'host': os.getenv('POSTGRES_HOST', 'localhost'),
                    'port': os.getenv('POSTGRES_PORT', '5432'),
                    'database': os.getenv('POSTGRES_DB', 'task_manager_db')
                }
        except:
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
        query = """        SELECT 
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


# Global database manager instance
db_manager = TaskDatabaseManager()


async def get_db() -> TaskDatabaseManager:
    """Dependency to get database manager"""
    return db_manager


async def initialize_database(settings=None):
    """Initialize database on startup"""
    global db_manager
    if settings:
        db_manager = TaskDatabaseManager(settings)
    await db_manager.initialize()


async def close_database():
    """Close database on shutdown"""
    await db_manager.close()
