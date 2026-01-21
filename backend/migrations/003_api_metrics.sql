-- API Metrics Persistence Schema
-- Stores periodic snapshots of API usage metrics

-- ===========================================
-- API METRICS SNAPSHOTS (every 5 minutes)
-- ===========================================
CREATE TABLE IF NOT EXISTS api_metrics_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT now(),
    
    -- Service identification
    service TEXT NOT NULL,  -- 'supabase', 'defillama', 'geckoterminal', 'moralis', 'thegraph', 'alchemy'
    
    -- Call counts
    total_calls INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    timeout_count INTEGER DEFAULT 0,
    rate_limit_count INTEGER DEFAULT 0,
    
    -- Rates
    success_rate DECIMAL(5,2) DEFAULT 0,  -- 0-100%
    
    -- Response times (milliseconds)
    avg_response_ms DECIMAL(10,2) DEFAULT 0,
    min_response_ms DECIMAL(10,2) DEFAULT 0,
    max_response_ms DECIMAL(10,2) DEFAULT 0,
    
    -- Error details
    last_error TEXT,
    last_error_time TIMESTAMPTZ
);

-- Index for time-series queries
CREATE INDEX IF NOT EXISTS idx_metrics_snapshots_service_time 
ON api_metrics_snapshots(service, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_metrics_snapshots_time 
ON api_metrics_snapshots(created_at DESC);

-- ===========================================
-- API ERROR LOG (real-time)
-- ===========================================
CREATE TABLE IF NOT EXISTS api_error_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT now(),
    
    service TEXT NOT NULL,
    endpoint TEXT,
    status TEXT,  -- 'error', 'timeout', 'rate_limited'
    status_code INTEGER,
    error_message TEXT,
    response_time_ms DECIMAL(10,2)
);

-- Index for recent errors
CREATE INDEX IF NOT EXISTS idx_error_log_time 
ON api_error_log(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_error_log_service 
ON api_error_log(service, created_at DESC);

-- ===========================================
-- DAILY SUMMARY (for dashboard)
-- ===========================================
CREATE TABLE IF NOT EXISTS api_metrics_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    service TEXT NOT NULL,
    
    total_calls INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    avg_response_ms DECIMAL(10,2) DEFAULT 0,
    success_rate DECIMAL(5,2) DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    
    UNIQUE(date, service)
);

CREATE INDEX IF NOT EXISTS idx_metrics_daily_date 
ON api_metrics_daily(date DESC);

-- ===========================================
-- RLS POLICIES (Read-only for anon)
-- ===========================================
ALTER TABLE api_metrics_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_error_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_metrics_daily ENABLE ROW LEVEL SECURITY;

-- Backend can read/write all
CREATE POLICY "Backend full access to metrics_snapshots" ON api_metrics_snapshots
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Backend full access to error_log" ON api_error_log
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Backend full access to metrics_daily" ON api_metrics_daily
    FOR ALL USING (true) WITH CHECK (true);
