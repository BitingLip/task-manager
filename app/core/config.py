"""
Task Manager Configuration

MIGRATION NOTICE: This file has been migrated to use centralized configuration.
The new configuration adapter provides backward compatibility while enabling
centralized configuration management across the BitingLip platform.
"""

# Import from centralized configuration system
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../config'))

from central_config import get_config
from service_discovery import ServiceDiscovery

class TaskManagerSettings:
    """Task Manager specific configuration adapter"""
    
    def __init__(self):
        self.config = get_config('task_manager')
        self.service_discovery = ServiceDiscovery()
    
    @property
    def host(self):
        return self.config.task_manager_host
    
    @property 
    def port(self):
        return self.config.task_manager_port
    
    @property
    def debug(self):
        return self.config.debug
    
    @property
    def cors_origins(self):
        return self.config.cors_origins
    
    @property
    def log_format(self):
        return getattr(self.config, 'log_format', 'standard')
    
    @property
    def log_level(self):
        return getattr(self.config, 'log_level', 'INFO')
    
    @property
    def celery_broker_url(self):
        return getattr(self.config, 'celery_broker_url', 'redis://localhost:6379/0')
    
    @property
    def celery_result_backend(self):
        return getattr(self.config, 'celery_result_backend', 'redis://localhost:6379/0')
    
    @property
    def redis_url(self):
        return getattr(self.config, 'redis_url', 'redis://localhost:6379/0')
    
    @property
    def cluster_manager_url(self):
        return f"http://{self.config.cluster_manager_host}:{self.config.cluster_manager_port}"
    
    @property
    def model_manager_url(self):
        return f"http://{self.config.model_manager_host}:{self.config.model_manager_port}"

def get_settings():
    """Get task manager settings instance"""
    return TaskManagerSettings()

def reload_settings():
    """Reload configuration from file"""
    from central_config import reload_config
    reload_config()
    return get_settings()

# Create default instance
settings = get_settings()

# Backward compatibility alias
Settings = TaskManagerSettings

# Re-export everything for backward compatibility
__all__ = [
    'TaskManagerSettings',
    'Settings',
    'settings',
    'get_settings',
    'reload_settings'
]
