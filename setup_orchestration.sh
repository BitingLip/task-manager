#!/bin/bash
# Quick setup script for task-manager orchestration testing

echo "🚀 Setting up Task Manager Orchestration Environment"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "app/main.py" ]; then
    echo "❌ Please run this script from the task-manager directory"
    exit 1
fi

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🔧 Starting Redis server (if not already running)..."
# Check if Redis is running
if ! pgrep -x "redis-server" > /dev/null; then
    echo "Starting Redis..."
    redis-server --daemonize yes
else
    echo "Redis is already running"
fi

echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Start cluster-manager workers:"
echo "   cd ../cluster-manager"
echo "   python -m cluster.worker.app.worker"
echo ""
echo "2. Start task-manager:"
echo "   python -m app.main"
echo ""
echo "3. Run orchestration tests:"
echo "   python test_orchestration.py"
echo ""
echo "🌐 API will be available at: http://localhost:8002"
echo "📖 API docs will be at: http://localhost:8002/docs"
