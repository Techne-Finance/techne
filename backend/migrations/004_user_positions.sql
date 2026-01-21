# ==================================================
# MIGRATION: User Positions Persistence
# Stores all user positions in Supabase for fast loading
# ==================================================

-- Create user_positions table
CREATE TABLE IF NOT EXISTS user_positions (
    id BIGSERIAL PRIMARY KEY,
    user_address TEXT NOT NULL,
    protocol TEXT NOT NULL,
    pool_address TEXT,
    entry_value NUMERIC NOT NULL,        -- Value in USDC (6 decimals stored as raw)
    current_value NUMERIC NOT NULL,      -- Current value in USDC
    entry_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    asset TEXT DEFAULT 'USDC',
    pool_type TEXT DEFAULT 'single',     -- single, lp, clp
    apy NUMERIC DEFAULT 0,
    status TEXT DEFAULT 'active',        -- active, closed, pending
    metadata JSONB DEFAULT '{}',
    
    -- Unique constraint: one position per user per protocol
    UNIQUE(user_address, protocol)
);

-- Create indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_user_positions_user ON user_positions(user_address);
CREATE INDEX IF NOT EXISTS idx_user_positions_status ON user_positions(status);
CREATE INDEX IF NOT EXISTS idx_user_positions_protocol ON user_positions(protocol);

-- Enable Row Level Security
ALTER TABLE user_positions ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Anyone can read (frontend needs this)
CREATE POLICY "user_positions_read" ON user_positions 
    FOR SELECT USING (true);

-- RLS Policy: Backend can insert/update (using API key)
CREATE POLICY "user_positions_write" ON user_positions 
    FOR ALL USING (true);

-- ==================================================
-- Create position_history for tracking changes
-- ==================================================
CREATE TABLE IF NOT EXISTS position_history (
    id BIGSERIAL PRIMARY KEY,
    user_address TEXT NOT NULL,
    protocol TEXT NOT NULL,
    action TEXT NOT NULL,               -- deposit, withdraw, rebalance, earn
    amount NUMERIC NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tx_hash TEXT,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_position_history_user ON position_history(user_address);
CREATE INDEX IF NOT EXISTS idx_position_history_time ON position_history(timestamp DESC);

ALTER TABLE position_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "position_history_read" ON position_history FOR SELECT USING (true);
CREATE POLICY "position_history_write" ON position_history FOR ALL USING (true);
