#!/usr/bin/env python3
"""
Test Task Manager Database Integration
"""

import asyncio
import sys
import os
from datetime import datetime

# Add project paths
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'common'))

from app.core.database_manager import TaskDatabaseManager

# Import models
from common.models import TaskType, TaskStatus

async def test_database_integration():
    """Test Task Manager database integration"""
    
    print("🧪 Testing Task Manager Database Integration")
    print("=" * 50)
    
    # Initialize database manager
    db_manager = TaskDatabaseManager()
    
    try:
        await db_manager.initialize()
        print("✅ Database manager initialized")
          # Test 1: Create a task
        print("\n📝 Test 1: Create Task")
        task_data = {
            "id": "test-task-001",
            "type": TaskType.LLM.value,
            "status": TaskStatus.PENDING.value,
            "priority": 5,
            "model_id": "llama-2-7b",
            "input_data": {
                "prompt": "Hello, world!",
                "max_tokens": 100
            },
            "created_at": datetime.now(),
            "timeout_seconds": 300,
            "max_retries": 3,
            "metadata": {"test": True}
        }
        
        task_id = await db_manager.create_task(task_data)
        print(f"✅ Task created with ID: {task_id}")
        
        # Test 2: Retrieve task
        print("\n📖 Test 2: Retrieve Task")
        retrieved_task = await db_manager.get_task(task_id)
        if retrieved_task:
            print(f"✅ Task retrieved: {retrieved_task['id']} - {retrieved_task['status']}")
            print(f"   Type: {retrieved_task['type']}")
            print(f"   Model: {retrieved_task['model_id']}")
        else:
            print("❌ Failed to retrieve task")
            
        # Test 3: Update task status
        print("\n🔄 Test 3: Update Task Status")
        success = await db_manager.update_task_status(
            task_id, 
            TaskStatus.STARTED.value,
            started_at=datetime.now(),
            worker_id="worker-001"
        )
        if success:
            print("✅ Task status updated to STARTED")
            
            # Verify update
            updated_task = await db_manager.get_task(task_id)
            if updated_task and updated_task['status'] == TaskStatus.STARTED.value:
                print(f"✅ Status verified: {updated_task['status']}")
                print(f"   Worker: {updated_task['worker_id']}")
            else:
                print("❌ Status update verification failed")
        else:
            print("❌ Failed to update task status")
            
        # Test 4: Get pending tasks
        print("\n📋 Test 4: Get Pending Tasks")
        
        # Create another pending task
        task_data_2 = task_data.copy()
        task_data_2["id"] = "test-task-002"
        task_data_2["priority"] = 8
        await db_manager.create_task(task_data_2)
        
        pending_tasks = await db_manager.get_pending_tasks(limit=10)
        print(f"✅ Found {len(pending_tasks)} pending tasks")
        for task in pending_tasks:
            print(f"   - {task['id']}: priority {task['priority']}")
            
        # Test 5: Add task metrics
        print("\n📊 Test 5: Add Task Metrics")
        metric_success = await db_manager.add_task_metric(
            task_id,
            "execution_time",
            1.5,
            "seconds",
            {"gpu_used": "RTX 4090"}
        )
        if metric_success:
            print("✅ Task metric added")
        else:
            print("❌ Failed to add task metric")
            
        # Test 6: Get task statistics
        print("\n📈 Test 6: Get Task Statistics")
        stats = await db_manager.get_task_statistics()
        print("✅ Task Statistics:")
        print(f"   Total tasks: {stats['total_tasks']}")
        print("   By status:")
        for status, info in stats['by_status'].items():
            print(f"     {status}: {info['count']} tasks")
            
        # Cleanup test tasks
        print("\n🧹 Cleanup")
        await db_manager.execute_command("DELETE FROM tasks WHERE id LIKE 'test-task-%'")
        print("✅ Test tasks cleaned up")
        
        print("\n🎉 All database integration tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await db_manager.close()
        print("✅ Database connection closed")

if __name__ == "__main__":
    asyncio.run(test_database_integration())
