-- ============================================================================
-- ENUMS
-- ============================================================================

-- Job status enum
CREATE TYPE job_status AS ENUM (
    'pending',
    'running',
    'completed',
    'failed',
    'cancelled'
);

-- Log level enum
CREATE TYPE log_level AS ENUM (
    'info',
    'warning',
    'error',
    'debug'
);

-- ============================================================================
-- TABLES
-- ============================================================================

-- Jobs table
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status job_status NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 0,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    error_message TEXT,
    result JSONB,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    scheduled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT jobs_priority_check CHECK (priority >= 0),
    CONSTRAINT jobs_retry_count_check CHECK (retry_count >= 0),
    CONSTRAINT jobs_max_retries_check CHECK (max_retries >= 0)
);

-- Job logs table
CREATE TABLE job_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    level log_level NOT NULL DEFAULT 'info',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Index for efficient job polling (most important!)
CREATE INDEX idx_jobs_status_priority_scheduled 
ON jobs(status, priority DESC, scheduled_at ASC)
WHERE status = 'pending';

-- Index for job status queries
CREATE INDEX idx_jobs_status ON jobs(status);

-- Index for time-based queries
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);

-- Index for job type filtering
CREATE INDEX idx_jobs_type ON jobs(type);

-- Index for logs by job_id
CREATE INDEX idx_job_logs_job_id ON job_logs(job_id, created_at DESC);

-- Index for failed jobs
CREATE INDEX idx_jobs_failed ON jobs(status, created_at DESC)
WHERE status = 'failed';

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for jobs table
CREATE TRIGGER update_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to get pending jobs with lock (prevents race conditions)
CREATE OR REPLACE FUNCTION get_pending_jobs_with_lock(
    batch_size INTEGER DEFAULT 1,
    lock_timeout INTEGER DEFAULT 5000
)
RETURNS SETOF jobs AS $$
BEGIN
    -- Set lock timeout for this transaction
    EXECUTE format('SET LOCAL lock_timeout = %s', lock_timeout);
    
    RETURN QUERY
    SELECT *
    FROM jobs
    WHERE status = 'pending'
      AND scheduled_at <= NOW()
    ORDER BY priority DESC, scheduled_at ASC
    LIMIT batch_size
    FOR UPDATE SKIP LOCKED;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old completed/failed jobs
CREATE OR REPLACE FUNCTION cleanup_old_jobs(
    retention_days INTEGER DEFAULT 30
)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM jobs
    WHERE status IN ('completed', 'failed', 'cancelled')
      AND completed_at < NOW() - (retention_days || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VIEWS (Optional - for monitoring/dashboard)
-- ============================================================================

-- Job statistics view
CREATE OR REPLACE VIEW job_stats AS
SELECT
    status,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds
FROM jobs
WHERE started_at IS NOT NULL
GROUP BY status;

-- Recent failed jobs view
CREATE OR REPLACE VIEW recent_failed_jobs AS
SELECT
    id,
    type,
    error_message,
    retry_count,
    max_retries,
    created_at,
    updated_at
FROM jobs
WHERE status = 'failed'
ORDER BY updated_at DESC
LIMIT 100;

-- ============================================================================
-- SAMPLE DATA
-- ============================================================================

-- Insert some sample jobs
INSERT INTO jobs (type, payload, priority) VALUES
    ('email', '{"to": "user@example.com", "subject": "Welcome", "body": "Hello!"}', 10),
    ('image_resize', '{"url": "https://example.com/image.jpg", "width": 800}', 5),
    ('report_generation', '{"report_type": "monthly", "user_id": 123}', 1);