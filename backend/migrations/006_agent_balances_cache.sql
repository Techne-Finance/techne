-- Migration: Create agent_balances table for cached portfolio data
-- This saves RPC calls by storing balances in Supabase

-- Drop existing table if schema changed
DROP TABLE IF EXISTS agent_balances CASCADE;

CREATE TABLE agent_balances (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    agent_address TEXT NOT NULL,
    user_address TEXT NOT NULL,
    
    -- Cached holdings (JSON array)
    holdings JSONB DEFAULT '[]'::jsonb,
    
    -- Cached positions (JSON array)  
    positions JSONB DEFAULT '[]'::jsonb,
    
    -- Total portfolio value
    total_value_usd NUMERIC(20, 2) DEFAULT 0,
    
    -- Timestamps
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint on agent
    CONSTRAINT agent_balances_agent_unique UNIQUE (agent_address)
);

-- Index for fast user lookups
CREATE INDEX IF NOT EXISTS idx_agent_balances_user ON agent_balances(user_address);

-- Index for finding stale data
CREATE INDEX IF NOT EXISTS idx_agent_balances_fetched ON agent_balances(fetched_at);

-- RLS policies
ALTER TABLE agent_balances ENABLE ROW LEVEL SECURITY;

-- Allow all operations for now (backend service role)
CREATE POLICY "Allow all for service role" ON agent_balances
    FOR ALL USING (true) WITH CHECK (true);

COMMENT ON TABLE agent_balances IS 'Cached portfolio balances to reduce RPC calls. Refreshed by background job every 10 min.';
