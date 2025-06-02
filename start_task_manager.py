#!/usr/bin/env python3
"""
Task Manager Startup Script
"""

import sys
import os
import uvicorn

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

def main():
    """Start the Task Manager service"""
    print("🚀 Starting Task Manager Service...")
    
    # Run with uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8006,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
