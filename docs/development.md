# Task Manager Development Guide

## Overview

This guide provides comprehensive information for developing and contributing to the Task Manager service, including setup, testing, coding standards, and development workflows.

## Development Environment Setup

### Prerequisites
- Python 3.10 or higher
- Git
- Docker and Docker Compose (for testing)
- Virtual environment tool (venv, conda, etc.)

### Initial Setup
```powershell
# Clone repository and navigate to task-manager
cd c:\Users\admin\Desktop\BitingLip\biting-lip\task-manager

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### Development Dependencies
```txt
# Testing
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
httpx>=0.24.0

# Code Quality
black>=23.0.0
isort>=5.12.0
flake8>=6.0.0
mypy>=1.0.0

# Development Tools
uvicorn[standard]>=0.22.0
python-dotenv>=1.0.0
pre-commit>=3.0.0
```

---

## Project Structure

```
task-manager/
├── src/                          # Source code
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   ├── api/                      # API layer
│   │   ├── __init__.py
│   │   ├── tasks.py             # Task endpoints
│   │   └── health.py            # Health/metrics endpoints
│   ├── core/                     # Core business logic
│   │   ├── __init__.py
│   │   ├── config.py            # Configuration management
│   │   ├── task_manager.py      # Task management logic
│   │   └── storage.py           # Data storage abstraction
│   ├── models/                   # Data models
│   │   ├── __init__.py
│   │   ├── requests.py          # Request/response models
│   │   └── entities.py          # Domain entities
│   └── utils/                    # Utilities
│       ├── __init__.py
│       ├── logging.py           # Logging configuration
│       └── helpers.py           # Helper functions
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py              # Pytest configuration
│   ├── unit/                    # Unit tests
│   │   ├── test_task_manager.py
│   │   └── test_storage.py
│   ├── integration/             # Integration tests
│   │   ├── test_api.py
│   │   └── test_end_to_end.py
│   └── fixtures/                # Test fixtures
│       └── sample_data.py
├── docs/                         # Documentation
├── scripts/                      # Development scripts
│   ├── start_dev.py             # Development server
│   └── run_tests.py             # Test runner
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development dependencies
├── pyproject.toml               # Tool configuration
├── Dockerfile                   # Container definition
└── docker-compose.yml          # Local development stack
```

---

## Development Workflow

### 1. Feature Development
```powershell
# Create feature branch
git checkout -b feature/new-task-type

# Make changes and test
python -m pytest tests/

# Run code quality checks
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/

# Commit and push
git add .
git commit -m "feat: add support for new task type"
git push origin feature/new-task-type
```

### 2. Running Development Server
```powershell
# Start with auto-reload
uvicorn src.main:app --reload --port 8002

# Or use development script
python scripts/start_dev.py

# With environment variables
$env:TASK_MANAGER_DEBUG="true"
$env:TASK_MANAGER_LOG_LEVEL="debug"
uvicorn src.main:app --reload --port 8002
```

### 3. Testing
```powershell
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src --cov-report=html

# Run specific test categories
python -m pytest tests/unit/           # Unit tests only
python -m pytest tests/integration/   # Integration tests only

# Run with verbose output
python -m pytest -v

# Run specific test
python -m pytest tests/unit/test_task_manager.py::test_create_task
```

---

## Testing Strategy

### Test Categories

#### 1. Unit Tests
Test individual components in isolation:
```python
# tests/unit/test_task_manager.py
import pytest
from src.core.task_manager import TaskManager
from src.models.entities import Task, TaskType, TaskStatus

@pytest.fixture
def task_manager():
    return TaskManager()

def test_create_task(task_manager):
    task = task_manager.create_task(
        task_type=TaskType.TEXT_GENERATION,
        model_name="test-model",
        input_data={"prompt": "test"}
    )
    
    assert task.status == TaskStatus.PENDING
    assert task.task_type == TaskType.TEXT_GENERATION
    assert task.model_name == "test-model"

def test_get_task_not_found(task_manager):
    with pytest.raises(TaskNotFoundError):
        task_manager.get_task("nonexistent-id")
```

#### 2. Integration Tests
Test API endpoints and service interactions:
```python
# tests/integration/test_api.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_create_task_endpoint(client):
    response = client.post("/tasks", json={
        "task_type": "text_generation",
        "model_name": "test-model",
        "input_data": {"prompt": "test"}
    })
    
    assert response.status_code == 201
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "pending"

def test_get_task_endpoint(client):
    # Create task first
    create_response = client.post("/tasks", json={
        "task_type": "text_generation",
        "model_name": "test-model", 
        "input_data": {"prompt": "test"}
    })
    task_id = create_response.json()["task_id"]
    
    # Get task
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
```

#### 3. End-to-End Tests
Test complete workflows with external dependencies:
```python
# tests/integration/test_end_to_end.py
import pytest
import asyncio
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_complete_task_workflow():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create task
        response = await client.post("/tasks", json={
            "task_type": "text_generation",
            "model_name": "microsoft/DialoGPT-medium",
            "input_data": {"prompt": "Hello world"}
        })
        
        assert response.status_code == 201
        task_data = response.json()
        task_id = task_data["task_id"]
        
        # Poll until completion (with timeout)
        for _ in range(30):  # 30 second timeout
            response = await client.get(f"/tasks/{task_id}")
            task = response.json()
            
            if task["status"] in ["completed", "failed"]:
                break
                
            await asyncio.sleep(1)
        
        assert task["status"] == "completed"
        assert "result" in task
```

### Test Configuration
```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.core.config import get_settings

@pytest.fixture
def test_settings():
    """Override settings for testing"""
    settings = get_settings()
    settings.database_url = "sqlite:///:memory:"
    settings.redis_url = "redis://localhost:6379/1"  # Test DB
    return settings

@pytest.fixture
def client(test_settings):
    """Test client with test configuration"""
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
async def async_client(test_settings):
    """Async test client"""
    app.dependency_overrides[get_settings] = lambda: test_settings
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
```

---

## Coding Standards

### Code Style
We follow PEP 8 with some modifications:
- Line length: 88 characters (Black default)
- String quotes: Double quotes preferred
- Import order: isort configuration

### Configuration Files

#### pyproject.toml
```toml
[tool.black]
line-length = 88
target-version = ['py310']
include = '\.pyi?$'

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short --strict-markers"
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow running tests",
]

[tool.coverage.run]
source = ["src"]
omit = ["tests/*", "scripts/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
]
```

### Type Hints
All functions should have type hints:
```python
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

def create_task(
    task_type: TaskType,
    model_name: str,
    input_data: Dict[str, Any],
    parameters: Optional[Dict[str, Any]] = None
) -> Task:
    """Create a new task with given parameters."""
    pass

async def get_task_status(task_id: str) -> Optional[TaskStatus]:
    """Get the current status of a task."""
    pass
```

### Error Handling
Use custom exceptions with proper inheritance:
```python
# src/core/exceptions.py
class TaskManagerError(Exception):
    """Base exception for task manager errors."""
    pass

class TaskNotFoundError(TaskManagerError):
    """Raised when a task is not found."""
    def __init__(self, task_id: str):
        super().__init__(f"Task not found: {task_id}")
        self.task_id = task_id

class ValidationError(TaskManagerError):
    """Raised when request validation fails."""
    def __init__(self, message: str, field: str):
        super().__init__(message)
        self.field = field
```

### Logging
Use structured logging:
```python
import logging
from src.utils.logging import get_logger

logger = get_logger(__name__)

def process_task(task: Task) -> None:
    logger.info(
        "Processing task",
        extra={
            "task_id": task.task_id,
            "task_type": task.task_type,
            "model_name": task.model_name
        }
    )
    
    try:
        # Process task
        logger.info("Task completed successfully", extra={"task_id": task.task_id})
    except Exception as e:
        logger.error(
            "Task processing failed",
            extra={"task_id": task.task_id, "error": str(e)},
            exc_info=True
        )
        raise
```

---

## Configuration Management

### Environment Variables
```powershell
# Development
$env:TASK_MANAGER_DEBUG="true"
$env:TASK_MANAGER_LOG_LEVEL="debug"
$env:TASK_MANAGER_HOST="0.0.0.0"
$env:TASK_MANAGER_PORT="8002"

# Database
$env:TASK_MANAGER_DATABASE_URL="postgresql://user:pass@localhost:5432/taskmanager"
$env:TASK_MANAGER_REDIS_URL="redis://localhost:6379/0"

# External Services
$env:CLUSTER_MANAGER_URL="http://localhost:8001"
$env:MODEL_MANAGER_URL="http://localhost:8003"
$env:GATEWAY_MANAGER_URL="http://localhost:8000"
```

### Configuration Classes
```python
# src/core/config.py
from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Service Configuration
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8002
    log_level: str = "info"
    
    # Database
    database_url: str = "sqlite:///./tasks.db"
    redis_url: str = "redis://localhost:6379/0"
    
    # External Services
    cluster_manager_url: str = "http://localhost:8001"
    model_manager_url: str = "http://localhost:8003"
    gateway_manager_url: str = "http://localhost:8000"
    
    # Task Configuration
    max_concurrent_tasks: int = 100
    task_timeout_seconds: int = 300
    task_retry_attempts: int = 3
    
    class Config:
        env_prefix = "TASK_MANAGER_"
        env_file = ".env"

settings = Settings()
```

---

## Performance Optimization

### Async/Await Best Practices
```python
import asyncio
from typing import List

async def process_tasks_batch(tasks: List[Task]) -> List[TaskResult]:
    """Process multiple tasks concurrently."""
    semaphore = asyncio.Semaphore(10)  # Limit concurrency
    
    async def process_single_task(task: Task) -> TaskResult:
        async with semaphore:
            return await task_processor.process(task)
    
    results = await asyncio.gather(
        *[process_single_task(task) for task in tasks],
        return_exceptions=True
    )
    
    return [r for r in results if not isinstance(r, Exception)]
```

### Database Optimization
```python
# Use connection pooling
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)

# Batch operations
async def update_task_statuses(updates: List[TaskUpdate]) -> None:
    async with session_factory() as session:
        await session.execute(
            update(Task),
            [{"task_id": u.task_id, "status": u.status} for u in updates]
        )
        await session.commit()
```

### Caching Strategy
```python
from functools import lru_cache
import redis.asyncio as redis

# In-memory caching for frequently accessed data
@lru_cache(maxsize=1000)
def get_model_config(model_name: str) -> ModelConfig:
    return ModelRegistry.get_config(model_name)

# Redis caching for distributed data
async def get_cached_task_result(task_id: str) -> Optional[TaskResult]:
    cache_key = f"task_result:{task_id}"
    cached = await redis_client.get(cache_key)
    if cached:
        return TaskResult.parse_raw(cached)
    return None

async def cache_task_result(task_id: str, result: TaskResult) -> None:
    cache_key = f"task_result:{task_id}"
    await redis_client.setex(
        cache_key, 
        3600,  # 1 hour TTL
        result.json()
    )
```

---

## Debugging

### Development Tools
```powershell
# Start with debugger
python -m debugpy --listen 5678 --wait-for-client -m uvicorn src.main:app --reload

# Debug specific test
python -m debugpy --listen 5678 --wait-for-client -m pytest tests/unit/test_task_manager.py -s
```

### Logging for Debugging
```python
# Enable debug logging
import logging
logging.getLogger("src").setLevel(logging.DEBUG)

# Request/response logging
import httpx

class LoggingClient:
    def __init__(self):
        self.client = httpx.AsyncClient()
    
    async def request(self, method: str, url: str, **kwargs):
        logger.debug(f"Request: {method} {url}", extra=kwargs)
        response = await self.client.request(method, url, **kwargs)
        logger.debug(f"Response: {response.status_code}", extra={"text": response.text})
        return response
```

### Common Issues
1. **Task stuck in pending state**: Check worker connectivity
2. **Memory leaks**: Review async context managers and connection pooling
3. **Slow API responses**: Enable query logging and check database indexes
4. **Authentication errors**: Verify API keys and service connectivity

---

## Contributing

### Pull Request Process
1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Write tests for new functionality
4. Ensure all tests pass: `python -m pytest`
5. Run code quality checks: `black`, `isort`, `flake8`, `mypy`
6. Update documentation if needed
7. Submit pull request with clear description

### Code Review Checklist
- [ ] Tests added for new functionality
- [ ] All tests passing
- [ ] Code follows style guidelines
- [ ] Type hints added
- [ ] Documentation updated
- [ ] Error handling implemented
- [ ] Performance considerations addressed
- [ ] Security implications reviewed

### Release Process
1. Update version in `__init__.py`
2. Update CHANGELOG.md
3. Create release tag: `git tag v1.2.3`
4. Build and test Docker image
5. Deploy to staging environment
6. Run integration tests
7. Deploy to production
