#!/usr/bin/env python3
"""
Comprehensive Phase 2 Task Manager Testing Script

This script tests all Phase 2 functionality including:
- Advanced task operations (cancel, retry)
- Task dependencies and relationships
- Task metrics and analytics
- Worker management and performance
- Execution logging and audit trails
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
import httpx
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskManagerPhase2Tester:
    def __init__(self, base_url: str = "http://localhost:8006"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = {}
        self.created_tasks = []
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
        
    async def test_health_check(self):
        """Test basic API health"""
        logger.info("🔍 Testing API health check...")
        try:
            response = await self.client.get(f"{self.base_url}/health")
            assert response.status_code == 200
            health_data = response.json()
            logger.info(f"✅ API Health: {health_data}")
            return True
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return False
            
    async def create_test_task(self, task_data: Dict[str, Any]) -> str:
        """Create a test task and return task ID"""
        try:
            response = await self.client.post(f"{self.base_url}/tasks/", json=task_data)
            if response.status_code == 200:
                task = response.json()
                task_id = task['task_id']
                self.created_tasks.append(task_id)
                logger.info(f"✅ Created test task: {task_id}")
                return task_id
            else:
                logger.error(f"❌ Failed to create task: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"❌ Task creation error: {e}")
            return None
            
    async def test_task_creation_and_basic_ops(self):
        """Test basic task creation and operations"""
        logger.info("🔍 Testing basic task operations...")
        
        # Create a simple task
        task_data = {
            "task_type": "llm_inference",
            "input_data": {"prompt": "Test prompt for Phase 2", "model": "test-model"},
            "priority": 1,
            "metadata": {"test_phase": "phase2", "test_category": "basic_ops"}
        }
        
        task_id = await self.create_test_task(task_data)
        if not task_id:
            return False
            
        # Test task retrieval
        try:
            response = await self.client.get(f"{self.base_url}/tasks/{task_id}")
            assert response.status_code == 200
            task = response.json()
            assert task['task_id'] == task_id
            logger.info(f"✅ Task retrieval successful")
            
            # Test task listing
            response = await self.client.get(f"{self.base_url}/tasks/")
            assert response.status_code == 200
            tasks = response.json()
            assert len(tasks) > 0
            logger.info(f"✅ Task listing successful: {len(tasks)} tasks")
            
            return True
        except Exception as e:
            logger.error(f"❌ Basic operations test failed: {e}")
            return False
            
    async def test_task_dependencies(self):
        """Test task dependency management"""
        logger.info("🔍 Testing task dependencies...")
        
        # Create parent task
        parent_task_data = {
            "task_type": "data_processing",
            "input_data": {"data": "parent_data"},
            "priority": 2,
            "metadata": {"role": "parent", "test_phase": "phase2"}
        }
        
        parent_id = await self.create_test_task(parent_task_data)
        if not parent_id:
            return False
            
        # Create child task
        child_task_data = {
            "task_type": "llm_inference", 
            "input_data": {"prompt": "child task", "depends_on": parent_id},
            "priority": 1,
            "metadata": {"role": "child", "test_phase": "phase2"}
        }
        
        child_id = await self.create_test_task(child_task_data)
        if not child_id:
            return False
            
        try:
            # Add dependency relationship
            dependency_data = {
                "dependency_task_id": parent_id,
                "dependency_type": "completion"
            }
            
            response = await self.client.post(
                f"{self.base_url}/tasks/{child_id}/dependencies",
                json=dependency_data
            )
            assert response.status_code == 200
            logger.info(f"✅ Dependency added: {child_id} depends on {parent_id}")
            
            # Get task dependencies
            response = await self.client.get(f"{self.base_url}/tasks/{child_id}/dependencies")
            assert response.status_code == 200
            deps = response.json()
            assert len(deps['dependencies']) > 0
            logger.info(f"✅ Dependencies retrieved: {deps['dependencies']}")
            
            # Get ready tasks (should not include child until parent completes)
            response = await self.client.get(f"{self.base_url}/tasks/ready/list")
            assert response.status_code == 200
            ready_tasks = response.json()
            logger.info(f"✅ Ready tasks: {ready_tasks['count']} tasks ready")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Dependency test failed: {e}")
            return False
            
    async def test_task_metrics_and_analytics(self):
        """Test task metrics and analytics"""
        logger.info("🔍 Testing task metrics and analytics...")
        
        # Create a task for metrics testing
        task_data = {
            "task_type": "model_training",
            "input_data": {"model": "test-model", "dataset": "test-data"},
            "priority": 3,
            "metadata": {"test_phase": "phase2", "test_category": "metrics"}
        }
        
        task_id = await self.create_test_task(task_data)
        if not task_id:
            return False
            
        try:
            # Add various metrics
            metrics = [
                {"metric_name": "processing_time", "metric_value": 125.5, "metric_unit": "seconds"},
                {"metric_name": "memory_usage", "metric_value": 512.0, "metric_unit": "MB"},
                {"metric_name": "accuracy", "metric_value": 0.95, "metric_unit": "percentage"}
            ]
            
            for metric in metrics:
                response = await self.client.post(
                    f"{self.base_url}/tasks/{task_id}/metrics",
                    json=metric
                )
                assert response.status_code == 200
                logger.info(f"✅ Added metric: {metric['metric_name']} = {metric['metric_value']}")
                
            # Get task analytics
            response = await self.client.get(f"{self.base_url}/tasks/analytics/summary?hours_back=24")
            assert response.status_code == 200
            analytics = response.json()
            logger.info(f"✅ Analytics retrieved: {analytics.get('total_tasks', 0)} total tasks")
            
            # Get performance metrics
            response = await self.client.get(f"{self.base_url}/tasks/metrics/performance")
            assert response.status_code == 200
            perf_metrics = response.json()
            logger.info(f"✅ Performance metrics: {perf_metrics['count']} metrics found")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Metrics test failed: {e}")
            return False
            
    async def test_worker_management(self):
        """Test worker assignment and performance tracking"""
        logger.info("🔍 Testing worker management...")
        
        # Create a task for worker testing
        task_data = {
            "task_type": "image_generation",
            "input_data": {"prompt": "test image", "size": "512x512"},
            "priority": 2,
            "metadata": {"test_phase": "phase2", "test_category": "worker"}
        }
        
        task_id = await self.create_test_task(task_data)
        if not task_id:
            return False
            
        try:
            # Assign task to worker
            worker_id = "test-worker-001"
            response = await self.client.post(f"{self.base_url}/tasks/{task_id}/assign/{worker_id}")
            assert response.status_code == 200
            logger.info(f"✅ Task assigned to worker: {worker_id}")
            
            # Get worker performance
            response = await self.client.get(f"{self.base_url}/tasks/workers/{worker_id}/performance")
            assert response.status_code == 200
            performance = response.json()
            logger.info(f"✅ Worker performance retrieved: {performance}")
            
            # Get general worker stats
            response = await self.client.get(f"{self.base_url}/tasks/workers/stats")
            assert response.status_code == 200
            stats = response.json()
            logger.info(f"✅ Worker stats: {stats}")
            
            # Check worker health
            response = await self.client.get(f"{self.base_url}/tasks/workers/health")
            assert response.status_code == 200
            health = response.json()
            logger.info(f"✅ Worker health: {health['status']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Worker management test failed: {e}")
            return False
            
    async def test_enhanced_task_operations(self):
        """Test enhanced task operations (cancel, retry, etc.)"""
        logger.info("🔍 Testing enhanced task operations...")
        
        # Create tasks for operation testing
        task_data_1 = {
            "task_type": "long_running_process",
            "input_data": {"duration": 300, "task": "simulation"},
            "priority": 1,
            "metadata": {"test_phase": "phase2", "test_category": "operations"}
        }
        
        task_data_2 = {
            "task_type": "error_prone_task",
            "input_data": {"simulate_error": True},
            "priority": 1,
            "metadata": {"test_phase": "phase2", "test_category": "operations"}
        }
        
        task_id_1 = await self.create_test_task(task_data_1)
        task_id_2 = await self.create_test_task(task_data_2)
        
        if not task_id_1 or not task_id_2:
            return False
            
        try:
            # Test task cancellation
            cancel_data = {
                "reason": "Test cancellation for Phase 2",
                "cancelled_by": "test_script"
            }
            
            response = await self.client.patch(
                f"{self.base_url}/tasks/{task_id_1}/cancel",
                json=cancel_data
            )
            assert response.status_code == 200
            logger.info(f"✅ Task cancelled: {task_id_1}")
            
            # Test task retry
            retry_data = {
                "max_retries": 3,
                "reason": "Test retry for Phase 2"
            }
            
            response = await self.client.post(
                f"{self.base_url}/tasks/{task_id_2}/retry",
                json=retry_data
            )
            assert response.status_code == 200
            logger.info(f"✅ Task retry initiated: {task_id_2}")
            
            # Get task status history
            response = await self.client.get(f"{self.base_url}/tasks/{task_id_1}/history")
            assert response.status_code == 200
            history = response.json()
            logger.info(f"✅ Status history retrieved: {len(history['status_history'])} entries")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Enhanced operations test failed: {e}")
            return False
            
    async def test_execution_logging(self):
        """Test task execution logging and audit trails"""
        logger.info("🔍 Testing execution logging...")
        
        # Create a task for logging testing
        task_data = {
            "task_type": "audit_test",
            "input_data": {"test": "logging_functionality"},
            "priority": 1,
            "metadata": {"test_phase": "phase2", "test_category": "logging"}
        }
        
        task_id = await self.create_test_task(task_data)
        if not task_id:
            return False
            
        try:
            # Get execution logs
            response = await self.client.get(f"{self.base_url}/tasks/{task_id}/logs")
            assert response.status_code == 200
            logs = response.json()
            logger.info(f"✅ Execution logs retrieved: {logs['count']} log entries")
            
            # Get task status history
            response = await self.client.get(f"{self.base_url}/tasks/{task_id}/history")
            assert response.status_code == 200
            history = response.json()
            logger.info(f"✅ Task history retrieved: {len(history['status_history'])} status changes")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Execution logging test failed: {e}")
            return False
            
    async def cleanup_test_tasks(self):
        """Clean up created test tasks"""
        logger.info("🧹 Cleaning up test tasks...")
        
        cleanup_count = 0
        for task_id in self.created_tasks:
            try:
                response = await self.client.delete(f"{self.base_url}/tasks/{task_id}")
                if response.status_code == 200:
                    cleanup_count += 1
            except Exception as e:
                logger.warning(f"Failed to cleanup task {task_id}: {e}")
                
        logger.info(f"✅ Cleaned up {cleanup_count}/{len(self.created_tasks)} test tasks")
        
    async def run_comprehensive_test(self) -> Dict[str, bool]:
        """Run all Phase 2 tests"""
        logger.info("🚀 Starting Phase 2 Task Manager Comprehensive Test Suite")
        logger.info("=" * 60)
        
        test_suite = [
            ("Health Check", self.test_health_check),
            ("Basic Operations", self.test_task_creation_and_basic_ops),
            ("Task Dependencies", self.test_task_dependencies),
            ("Metrics & Analytics", self.test_task_metrics_and_analytics),
            ("Worker Management", self.test_worker_management),
            ("Enhanced Operations", self.test_enhanced_task_operations),
            ("Execution Logging", self.test_execution_logging),
        ]
        
        results = {}
        
        for test_name, test_func in test_suite:
            logger.info(f"\n🧪 Running test: {test_name}")
            try:
                result = await test_func()
                results[test_name] = result
                status = "✅ PASSED" if result else "❌ FAILED"
                logger.info(f"   {status}")
            except Exception as e:
                logger.error(f"   ❌ FAILED with exception: {e}")
                results[test_name] = False
                
            # Brief pause between tests
            await asyncio.sleep(1)
            
        # Cleanup
        await self.cleanup_test_tasks()
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 60)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name:25} {status}")
            
        logger.info(f"\nOverall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
        
        if passed == total:
            logger.info("🎉 All Phase 2 tests passed! Ready for production.")
        else:
            logger.warning("⚠️  Some tests failed. Review logs for details.")
            
        return results


async def main():
    """Main test execution"""
    async with TaskManagerPhase2Tester() as tester:
        results = await tester.run_comprehensive_test()
        
        # Return exit code based on results
        all_passed = all(results.values())
        return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
