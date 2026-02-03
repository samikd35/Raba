-- Task History Table for Persistent Task Tracking
-- This table stores task execution history and enables task recovery across server restarts

CREATE TABLE IF NOT EXISTS task_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL UNIQUE,
    job_id UUID NOT NULL,
    user_id UUID NOT NULL,
    task_type VARCHAR(50) NOT NULL DEFAULT 'problem_generation',
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'timeout')),
    priority VARCHAR(20) NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'critical')),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    last_heartbeat TIMESTAMPTZ,
    
    -- Progress and messaging
    progress INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    message TEXT,
    error_message TEXT,
    
    -- Retry and timeout configuration
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    timeout_seconds INTEGER NOT NULL DEFAULT 1800,
    
    -- Additional metadata
    metadata JSONB DEFAULT '{}',
    
    -- Audit fields
    created_by UUID REFERENCES auth.users(id),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_task_history_task_id ON task_history(task_id);
CREATE INDEX IF NOT EXISTS idx_task_history_job_id ON task_history(job_id);
CREATE INDEX IF NOT EXISTS idx_task_history_user_id ON task_history(user_id);
CREATE INDEX IF NOT EXISTS idx_task_history_status ON task_history(status);
CREATE INDEX IF NOT EXISTS idx_task_history_created_at ON task_history(created_at);
CREATE INDEX IF NOT EXISTS idx_task_history_user_status ON task_history(user_id, status);
CREATE INDEX IF NOT EXISTS idx_task_history_active_tasks ON task_history(status, created_at) WHERE status IN ('pending', 'running');

-- Composite index for cleanup operations
CREATE INDEX IF NOT EXISTS idx_task_history_cleanup ON task_history(status, completed_at) WHERE status IN ('completed', 'failed', 'cancelled');

-- Updated timestamp trigger
CREATE OR REPLACE FUNCTION update_task_history_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER task_history_updated_at_trigger
    BEFORE UPDATE ON task_history
    FOR EACH ROW
    EXECUTE FUNCTION update_task_history_updated_at();

-- Row Level Security (RLS)
ALTER TABLE task_history ENABLE ROW LEVEL SECURITY;

-- Users can only see their own tasks
CREATE POLICY "Users can view their own task history" ON task_history
    FOR SELECT USING (auth.uid() = user_id);

-- Users can insert their own tasks
CREATE POLICY "Users can insert their own task history" ON task_history
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Users can update their own tasks
CREATE POLICY "Users can update their own task history" ON task_history
    FOR UPDATE USING (auth.uid() = user_id);

-- Service role can do everything
CREATE POLICY "Service role can manage all task history" ON task_history
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Admin users can view all tasks (for monitoring)
CREATE POLICY "Admin users can view all task history" ON task_history
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM auth.users 
            WHERE auth.users.id = auth.uid() 
            AND auth.users.raw_user_meta_data->>'role' = 'admin'
        )
    );

-- Comments for documentation
COMMENT ON TABLE task_history IS 'Persistent storage for background task execution history and monitoring';
COMMENT ON COLUMN task_history.task_id IS 'Unique identifier for the task instance';
COMMENT ON COLUMN task_history.job_id IS 'Associated job ID from job_status table';
COMMENT ON COLUMN task_history.user_id IS 'User who initiated the task';
COMMENT ON COLUMN task_history.task_type IS 'Type of task (e.g., problem_generation, data_processing)';
COMMENT ON COLUMN task_history.status IS 'Current task status';
COMMENT ON COLUMN task_history.priority IS 'Task execution priority';
COMMENT ON COLUMN task_history.progress IS 'Task completion percentage (0-100)';
COMMENT ON COLUMN task_history.retry_count IS 'Number of retry attempts made';
COMMENT ON COLUMN task_history.timeout_seconds IS 'Task timeout in seconds';
COMMENT ON COLUMN task_history.metadata IS 'Additional task-specific data in JSON format';
COMMENT ON COLUMN task_history.last_heartbeat IS 'Last heartbeat timestamp for monitoring task health';
