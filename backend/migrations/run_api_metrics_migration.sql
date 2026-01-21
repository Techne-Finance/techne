-- ===========================================
-- SIMPLIFIED API METRICS - Daily/Weekly Aggregates
-- Run this in Supabase SQL Editor
-- ===========================================

-- ===========================================
-- DAILY METRICS (resets/archives each day)
-- ===========================================
CREATE TABLE IF NOT EXISTS api_metrics_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    service TEXT NOT NULL,  -- 'moralis', 'goplus', 'defillama', 'geckoterminal', 'thegraph', 'supabase', 'alchemy'
    
    -- Call counts
    total_calls INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    
    -- Response times (ms)
    avg_response_ms DECIMAL(10,2) DEFAULT 0,
    min_response_ms DECIMAL(10,2) DEFAULT 0,
    max_response_ms DECIMAL(10,2) DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    
    UNIQUE(date, service)
);

CREATE INDEX IF NOT EXISTS idx_metrics_daily_date ON api_metrics_daily(date DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_daily_service ON api_metrics_daily(service);

-- ===========================================
-- WEEKLY AGGREGATES (for trending/history)
-- ===========================================
CREATE TABLE IF NOT EXISTS api_metrics_weekly (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    week_start DATE NOT NULL,  -- Monday of the week
    service TEXT NOT NULL,
    
    -- Aggregated counts
    total_calls INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    
    -- Averaged response times
    avg_response_ms DECIMAL(10,2) DEFAULT 0,
    
    -- Success rate
    success_rate DECIMAL(5,2) DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT now(),
    
    UNIQUE(week_start, service)
);

CREATE INDEX IF NOT EXISTS idx_metrics_weekly_week ON api_metrics_weekly(week_start DESC);

-- ===========================================
-- RLS POLICIES
-- ===========================================
ALTER TABLE api_metrics_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_metrics_weekly ENABLE ROW LEVEL SECURITY;

-- Full access for backend (anon key with permissive RLS)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'api_metrics_daily' AND policyname = 'api_metrics_daily_all') THEN
        CREATE POLICY "api_metrics_daily_all" ON api_metrics_daily FOR ALL USING (true) WITH CHECK (true);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'api_metrics_weekly' AND policyname = 'api_metrics_weekly_all') THEN
        CREATE POLICY "api_metrics_weekly_all" ON api_metrics_weekly FOR ALL USING (true) WITH CHECK (true);
    END IF;
END $$;

-- ===========================================
-- FUNCTION: Aggregate daily to weekly (run at week end)
-- ===========================================
CREATE OR REPLACE FUNCTION aggregate_weekly_metrics()
RETURNS void AS $$
DECLARE
    week_monday DATE := date_trunc('week', CURRENT_DATE)::DATE;
BEGIN
    INSERT INTO api_metrics_weekly (week_start, service, total_calls, success_count, error_count, avg_response_ms, success_rate)
    SELECT 
        week_monday,
        service,
        SUM(total_calls),
        SUM(success_count),
        SUM(error_count),
        AVG(avg_response_ms),
        CASE WHEN SUM(total_calls) > 0 
            THEN ROUND((SUM(success_count)::DECIMAL / SUM(total_calls)) * 100, 2) 
            ELSE 0 
        END
    FROM api_metrics_daily
    WHERE date >= week_monday AND date < week_monday + INTERVAL '7 days'
    GROUP BY service
    ON CONFLICT (week_start, service) 
    DO UPDATE SET 
        total_calls = EXCLUDED.total_calls,
        success_count = EXCLUDED.success_count,
        error_count = EXCLUDED.error_count,
        avg_response_ms = EXCLUDED.avg_response_ms,
        success_rate = EXCLUDED.success_rate;
END;
$$ LANGUAGE plpgsql;

-- ===========================================
-- VERIFICATION QUERY
-- ===========================================
-- SELECT table_name FROM information_schema.tables 
-- WHERE table_schema = 'public' AND table_name LIKE 'api_metrics%';
