# Quick setup script for task-manager orchestration testing (Windows PowerShell)

Write-Host "🚀 Setting up Task Manager Orchestration Environment" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

# Check if we're in the right directory
if (!(Test-Path "app\main.py")) {
    Write-Host "❌ Please run this script from the task-manager directory" -ForegroundColor Red
    exit 1
}

Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host "🔧 Checking Redis server..." -ForegroundColor Yellow
# Check if Redis process is running
$redisProcess = Get-Process -Name "redis-server" -ErrorAction SilentlyContinue
if (!$redisProcess) {
    Write-Host "Starting Redis server..." -ForegroundColor Yellow
    # Try to start Redis if it's installed
    try {
        Start-Process "redis-server" -WindowStyle Hidden
        Start-Sleep 2
    }
    catch {
        Write-Host "⚠️  Redis not found. Please install Redis or start it manually" -ForegroundColor Yellow
        Write-Host "   Download from: https://github.com/microsoftarchive/redis/releases" -ForegroundColor Cyan
    }
}
else {
    Write-Host "Redis is already running" -ForegroundColor Green
}

Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "1. Start cluster-manager workers:" -ForegroundColor White
Write-Host "   cd ..\cluster-manager" -ForegroundColor Gray
Write-Host "   python -m cluster.worker.app.worker" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Start task-manager:" -ForegroundColor White
Write-Host "   python -m app.main" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Run orchestration tests:" -ForegroundColor White
Write-Host "   python test_orchestration.py" -ForegroundColor Gray
Write-Host ""
Write-Host "🌐 API will be available at: http://localhost:8002" -ForegroundColor Cyan
Write-Host "📖 API docs will be at: http://localhost:8002/docs" -ForegroundColor Cyan
