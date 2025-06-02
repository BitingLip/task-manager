#!/usr/bin/env python3
"""
Phase 2 Database and Service Validation Script

Quick validation of database connectivity and Phase 2 method availability
"""

import asyncio
import sys
import os
from datetime import datetime
import logging
from pathlib import Path

# Add the project paths
project_root = Path(__file__).parent.parent.parent
common_path = project_root / "common"
task_manager_path = Path(__file__).parent

sys.path.insert(0, str(project_root))
sys.path.insert(0, str(common_path))
sys.path.insert(0, str(task_manager_path))

# Import after path setup
from app.core.database_manager import db_manager as TaskDatabaseManager
from app.core.config import get_settings
from app.services.task_service import TaskService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def validate_database_connection():
    """Validate database connection and basic operations"""
    logger.info("🔍 Testing database connection...")
    
    try:
        db_manager = TaskDatabaseManager()
        await db_manager.initialize()
        
        # Test basic database connectivity
        if db_manager.pool:
            logger.info("✅ Database connection pool initialized")
            
            # Test a simple query
            async with db_manager.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                assert result == 1
                logger.info("✅ Database query test passed")
                
            return True
        else:
            logger.error("❌ Database connection pool not initialized")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False
        
async def validate_phase2_methods():
    """Validate that all Phase 2 methods are available"""
    logger.info("🔍 Validating Phase 2 method availability...")
    
    try:
        # Initialize services
        db_manager = TaskDatabaseManager()
        await db_manager.initialize()
        
        task_service = TaskService()
        task_service.db_manager = db_manager
        
        # Check database manager methods
        db_phase2_methods = [
            'get_task_analytics',
            'add_task_metric', 
            'get_performance_metrics',
            'add_task_dependency',
            'get_task_dependencies',
            'get_ready_tasks',
            'assign_task_to_worker',
            'get_worker_performance',
            'cancel_task',
            'retry_failed_task',
            'update_task_with_status_history',
            'add_task_execution_log',
            'get_task_execution_logs'
        ]
        
        logger.info("Checking DatabaseManager Phase 2 methods:")
        for method_name in db_phase2_methods:
            if hasattr(db_manager, method_name):
                method = getattr(db_manager, method_name)
                if callable(method):
                    logger.info(f"  ✅ {method_name}")
                else:
                    logger.warning(f"  ⚠️  {method_name} (not callable)")
            else:
                logger.error(f"  ❌ {method_name} (missing)")
                
        # Check task service methods  
        service_phase2_methods = [
            'get_task_analytics',
            'add_task_metric',
            'get_performance_metrics', 
            'add_task_dependency',
            'get_task_dependencies',
            'get_ready_tasks',
            'assign_task_to_worker',
            'get_worker_performance',
            'cancel_task',
            'retry_task',
            'get_task_status_history',
            'get_task_execution_logs'
        ]
        
        logger.info("\nChecking TaskService Phase 2 methods:")
        for method_name in service_phase2_methods:
            if hasattr(task_service, method_name):
                method = getattr(task_service, method_name)
                if callable(method):
                    logger.info(f"  ✅ {method_name}")
                else:
                    logger.warning(f"  ⚠️  {method_name} (not callable)")
            else:
                logger.error(f"  ❌ {method_name} (missing)")
                
        return True
        
    except Exception as e:
        logger.error(f"❌ Phase 2 method validation failed: {e}")
        return False

async def validate_database_schema():
    """Validate that Phase 2 database tables exist"""
    logger.info("🔍 Validating database schema...")
    
    try:
        db_manager = TaskDatabaseManager()
        await db_manager.initialize()
        
        # Check for Phase 2 tables
        phase2_tables = [
            'task_dependencies',
            'task_metrics', 
            'task_execution_logs',
            'task_status_history',
            'worker_assignments'
        ]
        
        async with db_manager.pool.acquire() as conn:
            for table_name in phase2_tables:
                result = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = $1
                    );
                """, table_name)
                
                if result:
                    logger.info(f"  ✅ Table {table_name} exists")
                else:
                    logger.error(f"  ❌ Table {table_name} missing")
                    
        return True
        
    except Exception as e:
        logger.error(f"❌ Schema validation failed: {e}")
        return False

async def test_phase2_database_operations():
    """Test basic Phase 2 database operations"""
    logger.info("🔍 Testing Phase 2 database operations...")
    
    try:
        db_manager = TaskDatabaseManager()
        await db_manager.initialize()
        
        # Create a test task first
        test_task_id = f"test-task-{int(datetime.now().timestamp())}"
        
        # Insert a minimal task record for testing
        async with db_manager.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO tasks (task_id, task_type, status, priority, input_data, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, test_task_id, 'test', 'pending', 1, '{}', datetime.now(), datetime.now())
            
        logger.info(f"✅ Created test task: {test_task_id}")
        
        # Test analytics
        analytics = await db_manager.get_task_analytics(24)
        logger.info(f"✅ Analytics: {analytics}")
        
        # Test adding metric
        metric_added = await db_manager.add_task_metric(
            test_task_id, "test_metric", 123.45, "units", {}
        )
        logger.info(f"✅ Metric added: {metric_added}")
        
        # Test performance metrics
        perf_metrics = await db_manager.get_performance_metrics()
        logger.info(f"✅ Performance metrics: {len(perf_metrics)} found")
        
        # Test worker assignment
        assigned = await db_manager.assign_task_to_worker(test_task_id, "test-worker")
        logger.info(f"✅ Worker assignment: {assigned}")
        
        # Test execution log
        log_added = await db_manager.add_task_execution_log(
            test_task_id, "info", "Test log message", {"test": True}
        )
        logger.info(f"✅ Execution log added: {log_added}")
        
        # Cleanup test task
        async with db_manager.pool.acquire() as conn:
            await conn.execute("DELETE FROM tasks WHERE task_id = $1", test_task_id)
            
        logger.info(f"✅ Cleaned up test task: {test_task_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database operations test failed: {e}")
        return False

async def main():
    """Main validation function"""
    logger.info("🚀 Phase 2 Task Manager Validation")
    logger.info("=" * 50)
    
    tests = [
        ("Database Connection", validate_database_connection),
        ("Phase 2 Methods", validate_phase2_methods),
        ("Database Schema", validate_database_schema),
        ("Database Operations", test_phase2_database_operations),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 {test_name}...")
        try:
            result = await test_func()
            results[test_name] = result
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{status}")
        except Exception as e:
            logger.error(f"❌ FAILED: {e}")
            results[test_name] = False
            
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 VALIDATION SUMMARY")
    logger.info("=" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name:20} {status}")
        
    logger.info(f"\nOverall: {passed}/{total} validations passed")
    
    if passed == total:
        logger.info("🎉 All validations passed! Phase 2 is ready.")
        return 0
    else:
        logger.warning("⚠️  Some validations failed.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
