-- Database function for safely retrieving pending jobs with row-level locking
-- This prevents race conditions when multiple workers poll for jobs simultaneously

-- Function: get_pending_jobs_with_lock
-- Purpose: Retrieve pending jobs ready for processing with FOR UPDATE SKIP LOCKED
-- This ensures multiple workers can safely poll without conflicts

DROP FUNCTION IF EXISTS get_pending_jobs_with_lock(integer, integer);

CREATE OR REPLACE FUNCTION get_pending_jobs_with_lock(
    batch_size INT DEFAULT 10,
    lock_timeout INT DEFAULT 5000
)
RETURNS TABLE (
    id UUID,
    type VARCHAR,
    payload JSONB,
    status job_status,
    priority INT,
    retry_count INT,
    max_retries INT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    scheduled_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    -- Set lock timeout for this transaction (in milliseconds)
    EXECUTE format('SET LOCAL lock_timeout = %L', lock_timeout);
    
    RETURN QUERY
    SELECT 
        j.id,
        j.type,
        j.payload,
        j.status,
        j.priority,
        j.retry_count,
        j.max_retries,
        j.error_message,
        j.created_at,
        j.updated_at,
        j.scheduled_at,
        j.started_at,
        j.completed_at
    FROM jobs j
    WHERE j.status = 'pending'
        AND (j.scheduled_at IS NULL OR j.scheduled_at <= NOW())
    ORDER BY j.priority DESC, j.created_at ASC
    LIMIT batch_size
    FOR UPDATE SKIP LOCKED;
END;
$$ LANGUAGE plpgsql;

--
COMMENT ON FUNCTION get_pending_jobs_with_lock(INT, INT) IS 
'Safely retrieve pending jobs for processing with row-level locking to prevent race conditions';