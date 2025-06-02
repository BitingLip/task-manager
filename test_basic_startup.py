#!/usr/bin/env python3
"""
Basic Task Manager Startup Test
Tests if the Task Manager can start and basic functionality works.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "common"))
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_settings
from app.core.database_manager import db_manager, initialize_database
from app.services.task_service import TaskService

async def test_startup():
    """Test basic startup functionality"""
    print("🚀 Testing Task Manager Phase 2 startup...")
    
    try:
        # Load settings
        settings = get_settings()
        print(f"✅ Configuration loaded - Port: {settings.port}")
        
        # Initialize database
        print("🔍 Testing database initialization...")
        await initialize_database(settings)
        print("✅ Database manager initialized")
        
        # Test database connection
        print("🔍 Testing database connection...")
        async with db_manager.pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            if result == 1:
                print("✅ Database connection successful")
            else:
                print("❌ Database connection test failed")
                return False
        
        # Initialize task service
        print("🔍 Testing task service initialization...")
        task_service = TaskService(settings, db_manager)
        await task_service.initialize()
        print("✅ Task service initialized")
        
        # Test Phase 2 methods exist
        print("🔍 Checking Phase 2 database methods...")
        phase2_methods = [
            'get_task_analytics',
            'add_task_metric',
            'get_performance_metrics',
            'add_task_dependency',
            'get_task_dependencies',
            'get_ready_tasks',
            'assign_task_to_worker',
            'get_worker_performance'
        ]
        
        missing_methods = []
        for method in phase2_methods:
            if not hasattr(db_manager, method):
                missing_methods.append(method)
        
        if missing_methods:
            print(f"❌ Missing database methods: {missing_methods}")
            return False
        else:
            print("✅ All Phase 2 database methods available")
        
        # Test service methods
        print("🔍 Checking Phase 2 service methods...")
        service_methods = ['get_analytics_data', 'add_task_metric', 'cancel_task']
        
        missing_service_methods = []
        for method in service_methods:
            if not hasattr(task_service, method):
                missing_service_methods.append(method)
        
        if missing_service_methods:
            print(f"❌ Missing service methods: {missing_service_methods}")
            return False
        else:
            print("✅ All Phase 2 service methods available")
        
        print("\n🎉 Task Manager Phase 2 validation successful!")
        print(f"📊 Database methods: {len(phase2_methods)} available")
        print(f"🔧 Service methods: {len(service_methods)} available")
        
        # Cleanup
        await task_service.cleanup()
        
        return True
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_startup())
    if success:
        print("\n✅ Ready for Phase 2 testing!")
        sys.exit(0)
    else:
        print("\n❌ Phase 2 validation failed!")
        sys.exit(1)
