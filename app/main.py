"""
Task Manager - FastAPI Application Entry Point

This file is focused only on:
- Application setup and configuration
- Dependency injection setup
- Router registration
- Middleware configuration

All business logic is in services/ and routes/
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
import os

# Add common module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'common'))

from .core.config import get_settings
from .core.logging_config import setup_logging
from .routes import tasks, health
from .services.task_service import TaskService


def get_task_service(request: Request) -> TaskService:
    """Dependency to get task service from app state"""
    return request.app.state.task_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    settings = get_settings()
    
    # Setup logging
    setup_logging(settings)
    
    # Initialize services
    task_service = TaskService(settings)
    await task_service.initialize()
    
    # Store services in app state for dependency injection
    app.state.task_service = task_service
    
    yield
    
    # Cleanup on shutdown
    await task_service.cleanup()


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()
    
    app = FastAPI(
        title="BitingLip Task Manager",
        description="Manages task scheduling, queuing, and lifecycle for the BitingLip AI inference platform",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],    )
    
    # Register routers
    app.include_router(tasks.router, tags=["tasks"])
    app.include_router(health.router, tags=["health"])
    
    return app


# Create app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8084)
