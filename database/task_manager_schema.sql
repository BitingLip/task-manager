-- Task Manager Database Schema
-- PostgreSQL schema for task orchestration and execution history

-- Task execution table
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    model_id TEXT,
    worker_id TEXT,
    input_data JSONB NOT NULL,
    output_data JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    estimated_duration INTEGER, -- seconds
    actual_duration INTEGER, -- seconds
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    timeout_seconds INTEGER DEFAULT 300,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Task metrics and performance tracking
CREATE TABLE IF NOT EXISTS task_metrics (
    id SERIAL PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL,
    metric_value NUMERIC,
    metric_unit TEXT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Task dependencies
CREATE TABLE IF NOT EXISTS task_dependencies (
    id SERIAL PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    dependency_task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    dependency_type TEXT DEFAULT 'requires_completion',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(task_id, dependency_task_id)
);

-- Worker assignments and load balancing
CREATE TABLE IF NOT EXISTS worker_assignments (
    id SERIAL PRIMARY KEY,
    worker_id TEXT NOT NULL,
    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    estimated_completion TIMESTAMP,
    actual_completion TIMESTAMP,
    assignment_score NUMERIC, -- load balancing score
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Task queue management
CREATE TABLE IF NOT EXISTS task_queues (
    id SERIAL PRIMARY KEY,
    queue_name TEXT NOT NULL UNIQUE,
    priority INTEGER DEFAULT 0,
    max_concurrent_tasks INTEGER DEFAULT 10,
    processing_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Task execution logs
CREATE TABLE IF NOT EXISTS task_execution_logs (
    id SERIAL PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    log_level TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    worker_id TEXT,
    step_name TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(type);
CREATE INDEX IF NOT EXISTS idx_tasks_worker ON tasks(worker_id);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_status_priority ON tasks(status, priority DESC);

CREATE INDEX IF NOT EXISTS idx_task_metrics_task_id ON task_metrics(task_id);
CREATE INDEX IF NOT EXISTS idx_task_metrics_name ON task_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_task_metrics_recorded_at ON task_metrics(recorded_at);

CREATE INDEX IF NOT EXISTS idx_worker_assignments_worker ON worker_assignments(worker_id);
CREATE INDEX IF NOT EXISTS idx_worker_assignments_task ON worker_assignments(task_id);
CREATE INDEX IF NOT EXISTS idx_worker_assignments_assigned_at ON worker_assignments(assigned_at);

CREATE INDEX IF NOT EXISTS idx_task_logs_task_id ON task_execution_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_task_logs_timestamp ON task_execution_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_task_logs_level ON task_execution_logs(log_level);

-- JSONB indexes for metadata searches
CREATE INDEX IF NOT EXISTS idx_tasks_metadata ON tasks USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_task_metrics_metadata ON task_metrics USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_task_logs_metadata ON task_execution_logs USING GIN(metadata);

-- Task status audit trail
CREATE TABLE IF NOT EXISTS task_status_history (
    id SERIAL PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    old_status TEXT,
    new_status TEXT NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by TEXT,
    reason TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_task_status_history_task_id ON task_status_history(task_id);
CREATE INDEX IF NOT EXISTS idx_task_status_history_changed_at ON task_status_history(changed_at);

-- Task statistics aggregation view
CREATE OR REPLACE VIEW task_statistics AS
SELECT 
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as total_tasks,
    COUNT(*) FILTER (WHERE status = 'completed') as completed_tasks,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_tasks,
    COUNT(*) FILTER (WHERE status = 'pending') as pending_tasks,
    COUNT(*) FILTER (WHERE status = 'running') as running_tasks,
    AVG(actual_duration) FILTER (WHERE actual_duration IS NOT NULL) as avg_duration,
    MAX(actual_duration) FILTER (WHERE actual_duration IS NOT NULL) as max_duration,
    MIN(actual_duration) FILTER (WHERE actual_duration IS NOT NULL) as min_duration
FROM tasks
GROUP BY DATE_TRUNC('hour', created_at)
ORDER BY hour DESC;
