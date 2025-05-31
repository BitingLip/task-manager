"""
Utility functions for task management
"""

import uuid
from datetime import datetime
from typing import Any, Dict


def generate_task_id() -> str:
    """Generate a unique task ID"""
    return str(uuid.uuid4())


def format_timestamp(dt: datetime | None = None) -> str:
    """Format datetime as ISO string"""
    if dt is None:
        dt = datetime.utcnow()
    return dt.isoformat() + "Z"


def create_error_response(message: str, error_code: str = "INTERNAL_ERROR") -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "error": {
            "code": error_code,
            "message": message,
            "timestamp": format_timestamp()
        }
    }


def create_success_response(data: Any = None, message: str = "Success") -> Dict[str, Any]:
    """Create standardized success response"""
    response = {
        "success": True,
        "message": message,
        "timestamp": format_timestamp()
    }
    if data is not None:
        response["data"] = data
    return response
