-- Migration: 009_artisan_strategies.sql
-- Strategy configuration for Artisan Bot users

CREATE TABLE IF NOT EXISTS artisan_strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_address TEXT UNIQUE NOT NULL,
    
    -- Risk settings
    risk_level TEXT DEFAULT 'moderate' CHECK (
        risk_level IN ('conservative', 'moderate', 'aggressive')
    ),
    target_apy DECIMAL(5,2) DEFAULT 15.0,
    max_drawdown DECIMAL(5,2) DEFAULT 20.0,
    
    -- Asset preferences
    stablecoin_only BOOLEAN DEFAULT FALSE,
    preferred_protocols TEXT[] DEFAULT ARRAY['Aerodrome', 'Aave'],
    
    -- Automation settings
    auto_compound BOOLEAN DEFAULT TRUE,
    rebalance_threshold DECIMAL(5,2) DEFAULT 10.0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_artisan_strategies_user ON artisan_strategies(user_address);

-- Comments
COMMENT ON TABLE artisan_strategies IS 'User strategy configuration for Artisan Bot autonomous trading';
COMMENT ON COLUMN artisan_strategies.risk_level IS 'conservative=stables+low IL, moderate=balanced, aggressive=high APY focus';
COMMENT ON COLUMN artisan_strategies.rebalance_threshold IS 'Percentage deviation that triggers auto-rebalance';
