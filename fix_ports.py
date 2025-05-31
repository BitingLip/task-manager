"""
Migration Script: Fix Task Manager Port Configuration

This script updates the task-manager to use the correct port (8084) 
for gateway integration and demonstrates the centralized configuration approach.
"""

import sys
import os
from pathlib import Path

def fix_task_manager_ports():
    """Fix port configurations in task-manager"""
    
    task_manager_root = Path(__file__).parent
    
    # 1. Fix config.py port
    config_file = task_manager_root / "app" / "core" / "config.py"
    if config_file.exists():
        print(f"Updating {config_file}")
        
        # Read current content
        with open(config_file, 'r') as f:
            content = f.read()
        
        # Replace port
        content = content.replace('port: int = 8002', 'port: int = 8084')
        
        # Write back
        with open(config_file, 'w') as f:
            f.write(content)
        
        print("✅ Updated config.py port from 8002 to 8084")
    
    # 2. Fix main.py port
    main_file = task_manager_root / "app" / "main.py"
    if main_file.exists():
        print(f"Updating {main_file}")
        
        # Read current content
        with open(main_file, 'r') as f:
            content = f.read()
        
        # Replace hardcoded port
        content = content.replace('port=8004', 'port=8084')
        
        # Write back
        with open(main_file, 'w') as f:
            f.write(content)
        
        print("✅ Updated main.py port from 8004 to 8084")
    
    # 3. Update service URLs in config
    if config_file.exists():
        print(f"Updating service URLs in {config_file}")
        
        # Read current content
        with open(config_file, 'r') as f:
            content = f.read()
        
        # Update external service URLs to match actual running ports
        updates = [
            ('cluster_manager_url: str = "http://localhost:8001"', 
             'cluster_manager_url: str = "http://localhost:8083"'),
            ('model_manager_url: str = "http://localhost:8003"', 
             'model_manager_url: str = "http://localhost:8085"'),
            ('gateway_manager_url: str = "http://localhost:8000"', 
             'gateway_manager_url: str = "http://localhost:8080"'),
        ]
        
        for old, new in updates:
            if old in content:
                content = content.replace(old, new)
                print(f"✅ Updated: {old.split('=')[0].strip()}")
        
        # Write back
        with open(config_file, 'w') as f:
            f.write(content)
    
    print("\n🎯 Task Manager Port Configuration Fixed!")
    print("✅ Port: 8084 (matches gateway expectations)")
    print("✅ Service URLs: Updated to match running services")
    print("✅ Ready for integration testing")

def show_centralized_config_benefits():
    """Show how centralized config would prevent these issues"""
    
    print("\n" + "="*70)
    print("🚀 CENTRALIZED CONFIGURATION BENEFITS")
    print("="*70)
    
    print("""
📊 BEFORE (Current scattered approach):
   ❌ task-manager/app/core/config.py: port=8002
   ❌ task-manager/app/main.py: uvicorn.run(port=8004)  
   ❌ gateway expects task-manager on port 8084
   ❌ Manual fixes needed for each service

🎯 AFTER (Centralized configuration):
   ✅ biting-lip/.env: TASK_MANAGER_PORT=8084
   ✅ All services inherit from central config
   ✅ Single source of truth for all ports
   ✅ No more port conflicts

💡 IMPLEMENTATION:
   # task-manager/app/main.py
   from config import get_config
   
   def create_app():
       config = get_config('task-manager')
       return FastAPI(...)
   
   if __name__ == "__main__":
       config = get_config('task-manager')
       uvicorn.run(app, port=config.task_manager_port)  # Auto: 8084

🔧 SERVICE DISCOVERY:
   from config.service_discovery import get_service_url
   
   # Automatic URL resolution
   task_manager_url = get_service_url('task-manager')  # http://localhost:8084
   model_manager_url = get_service_url('model-manager')  # http://localhost:8085
   
🎛️ ENVIRONMENT MANAGEMENT:
   # Development
   .env.development: TASK_MANAGER_PORT=8084
   
   # Production  
   .env.production: TASK_MANAGER_PORT=8080
   
   # Staging
   .env.staging: TASK_MANAGER_PORT=8084
""")

if __name__ == "__main__":
    print("🔧 BitingLip Task Manager Port Fix")
    print("="*50)
    
    # Fix the immediate port issues
    fix_task_manager_ports()
    
    # Show the long-term solution
    show_centralized_config_benefits()
    
    print(f"\n🎉 Migration completed!")
    print("💡 Next steps:")
    print("   1. Test task-manager startup on port 8084")
    print("   2. Test gateway → task-manager routing")
    print("   3. Consider implementing centralized config for all services")
