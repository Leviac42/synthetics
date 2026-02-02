-- Synthetic Monitoring Database Schema
-- Optimized for time-series queries and performance metrics storage

-- Create database (for reference, actual creation happens in container init)
-- CREATE DATABASE synthetics;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Monitors table: stores monitor configurations
CREATE TABLE IF NOT EXISTS monitors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    schedule_cron VARCHAR(100) NOT NULL DEFAULT '*/5 * * * *',
    enabled BOOLEAN NOT NULL DEFAULT true,
    timeout_seconds INTEGER NOT NULL DEFAULT 30,
    tags JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT monitors_name_check CHECK (char_length(name) > 0),
    CONSTRAINT monitors_timeout_check CHECK (timeout_seconds >= 5 AND timeout_seconds <= 300)
);

-- Create indexes for monitors
CREATE INDEX IF NOT EXISTS idx_monitors_enabled ON monitors(enabled) WHERE enabled = true;
CREATE INDEX IF NOT EXISTS idx_monitors_created_at ON monitors(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_monitors_tags ON monitors USING GIN(tags);

-- Execution logs table: stores each monitor execution
CREATE TABLE IF NOT EXISTS execution_logs (
    id BIGSERIAL PRIMARY KEY,
    monitor_id INTEGER NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL DEFAULT 'running',
    error_message TEXT,
    har_data JSONB,
    
    CONSTRAINT execution_logs_status_check CHECK (status IN ('running', 'success', 'error', 'timeout'))
);

-- Create indexes optimized for time-series queries
CREATE INDEX IF NOT EXISTS idx_execution_logs_monitor_id ON execution_logs(monitor_id);
CREATE INDEX IF NOT EXISTS idx_execution_logs_started_at ON execution_logs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_execution_logs_monitor_started ON execution_logs(monitor_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_execution_logs_status ON execution_logs(status);
CREATE INDEX IF NOT EXISTS idx_execution_logs_completed_at ON execution_logs(completed_at DESC) WHERE completed_at IS NOT NULL;

-- Performance metrics table: stores time-series performance data
CREATE TABLE IF NOT EXISTS performance_metrics (
    id BIGSERIAL PRIMARY KEY,
    execution_log_id BIGINT NOT NULL REFERENCES execution_logs(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT performance_metrics_metric_name_check CHECK (char_length(metric_name) > 0)
);

-- Create indexes optimized for time-series queries and aggregations
CREATE INDEX IF NOT EXISTS idx_performance_metrics_execution_log_id ON performance_metrics(execution_log_id);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_recorded_at ON performance_metrics(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_metric_name ON performance_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_metric_recorded ON performance_metrics(metric_name, recorded_at DESC);

-- Composite index for common query patterns (Grafana queries)
CREATE INDEX IF NOT EXISTS idx_performance_metrics_composite 
ON performance_metrics(metric_name, recorded_at DESC, metric_value);

-- Create a view for easy querying of latest metrics per monitor
CREATE OR REPLACE VIEW latest_monitor_metrics AS
SELECT 
    m.id as monitor_id,
    m.name as monitor_name,
    m.url as monitor_url,
    m.enabled as monitor_enabled,
    el.id as execution_log_id,
    el.started_at,
    el.completed_at,
    el.status,
    el.error_message,
    MAX(CASE WHEN pm.metric_name = 'ttfb_ms' THEN pm.metric_value END) as ttfb_ms,
    MAX(CASE WHEN pm.metric_name = 'dom_content_loaded_ms' THEN pm.metric_value END) as dom_content_loaded_ms,
    MAX(CASE WHEN pm.metric_name = 'page_load_time_ms' THEN pm.metric_value END) as page_load_time_ms
FROM monitors m
LEFT JOIN LATERAL (
    SELECT * FROM execution_logs 
    WHERE monitor_id = m.id 
    ORDER BY started_at DESC 
    LIMIT 1
) el ON true
LEFT JOIN performance_metrics pm ON el.id = pm.execution_log_id
GROUP BY m.id, m.name, m.url, m.enabled, el.id, el.started_at, el.completed_at, el.status, el.error_message;

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for monitors table
DROP TRIGGER IF EXISTS update_monitors_updated_at ON monitors;
CREATE TRIGGER update_monitors_updated_at
    BEFORE UPDATE ON monitors
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert sample monitor for testing (optional)
INSERT INTO monitors (name, url, schedule_cron, enabled, timeout_seconds, tags)
VALUES 
    ('Example Monitor', 'https://example.com', '*/5 * * * *', true, 30, '{"environment": "production", "team": "platform"}')
ON CONFLICT DO NOTHING;

-- Create a function for cleaning old data (useful for maintenance)
CREATE OR REPLACE FUNCTION cleanup_old_metrics(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete old execution logs and their associated metrics (cascading)
    DELETE FROM execution_logs
    WHERE started_at < NOW() - (retention_days || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust as needed for your security requirements)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO synthetics;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO synthetics;

-- Add comments for documentation
COMMENT ON TABLE monitors IS 'Stores synthetic monitor configurations';
COMMENT ON TABLE execution_logs IS 'Stores execution history for each monitor run';
COMMENT ON TABLE performance_metrics IS 'Stores time-series performance metrics (TTFB, DOM load, page load, etc.)';
COMMENT ON VIEW latest_monitor_metrics IS 'Convenient view showing the latest metrics for each monitor';
COMMENT ON FUNCTION cleanup_old_metrics IS 'Maintenance function to remove metrics older than specified retention period';

-- Performance tuning recommendations (uncomment and adjust based on your workload)
-- ALTER TABLE execution_logs SET (autovacuum_vacuum_scale_factor = 0.05);
-- ALTER TABLE performance_metrics SET (autovacuum_vacuum_scale_factor = 0.02);

-- Create hypertable for performance_metrics if TimescaleDB is available (optional)
-- This is commented out by default but can be enabled if you install TimescaleDB extension
-- CREATE EXTENSION IF NOT EXISTS timescaledb;
-- SELECT create_hypertable('performance_metrics', 'recorded_at', if_not_exists => TRUE);
