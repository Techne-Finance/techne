-- ==================================================
-- MIGRATION: Scalable Agent System
-- Enables thousands of users with multiple agents
-- ==================================================

-- ==========================================
-- 1. USER AGENTS (główna tabela agentów)
-- ==========================================
CREATE TABLE IF NOT EXISTS user_agents (
    id BIGSERIAL PRIMARY KEY,
    user_address TEXT NOT NULL,
    agent_address TEXT NOT NULL UNIQUE,
    agent_name TEXT DEFAULT 'Agent',
    encrypted_private_key TEXT NOT NULL,
    
    -- Config
    chain TEXT DEFAULT 'base',
    preset TEXT DEFAULT 'balanced',
    pool_type TEXT DEFAULT 'single',
    risk_level TEXT DEFAULT 'moderate',
    min_apy NUMERIC DEFAULT 5,
    max_apy NUMERIC DEFAULT 1000,
    max_drawdown NUMERIC DEFAULT 20,
    
    -- Status  
    is_active BOOLEAN DEFAULT true,
    status TEXT DEFAULT 'active',  -- active, paused, draining, locked
    
    -- Settings JSONB
    settings JSONB DEFAULT '{
        "auto_compound": true,
        "max_gas_gwei": 50,
        "slippage_tolerance": 0.5,
        "emergency_withdraw_enabled": true
    }',
    protocols JSONB DEFAULT '["aerodrome", "aave", "morpho"]',
    preferred_assets JSONB DEFAULT '["USDC", "WETH"]',
    
    -- Pro mode
    is_pro_mode BOOLEAN DEFAULT false,
    pro_config JSONB,
    
    -- Financial tracking
    total_deposited NUMERIC DEFAULT 0,
    total_value NUMERIC DEFAULT 0,
    total_earnings NUMERIC DEFAULT 0,
    
    -- Timestamps
    deployed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_user_agents_user ON user_agents(user_address);
CREATE INDEX IF NOT EXISTS idx_user_agents_agent ON user_agents(agent_address);
CREATE INDEX IF NOT EXISTS idx_user_agents_active ON user_agents(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_user_agents_status ON user_agents(status);
CREATE INDEX IF NOT EXISTS idx_user_agents_chain ON user_agents(chain);

-- RLS
ALTER TABLE user_agents ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "user_agents_read" ON user_agents;
DROP POLICY IF EXISTS "user_agents_write" ON user_agents;
CREATE POLICY "user_agents_read" ON user_agents FOR SELECT USING (true);
CREATE POLICY "user_agents_write" ON user_agents FOR ALL USING (true);


-- ==========================================
-- 2. AGENT TRANSACTIONS (historia)
-- ==========================================
CREATE TABLE IF NOT EXISTS agent_transactions (
    id BIGSERIAL PRIMARY KEY,
    user_address TEXT NOT NULL,
    agent_address TEXT NOT NULL,
    tx_type TEXT NOT NULL,  -- deposit, withdraw, strategy_deposit, strategy_withdraw, claim, rebalance
    token TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    tx_hash TEXT,
    status TEXT DEFAULT 'completed',  -- pending, completed, failed
    destination TEXT,  -- for withdrawals
    pool_id TEXT,  -- for strategy ops
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_tx_user ON agent_transactions(user_address);
CREATE INDEX IF NOT EXISTS idx_agent_tx_agent ON agent_transactions(agent_address);
CREATE INDEX IF NOT EXISTS idx_agent_tx_type ON agent_transactions(tx_type);
CREATE INDEX IF NOT EXISTS idx_agent_tx_time ON agent_transactions(created_at DESC);

ALTER TABLE agent_transactions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "agent_tx_read" ON agent_transactions;
DROP POLICY IF EXISTS "agent_tx_write" ON agent_transactions;
CREATE POLICY "agent_tx_read" ON agent_transactions FOR SELECT USING (true);
CREATE POLICY "agent_tx_write" ON agent_transactions FOR ALL USING (true);


-- ==========================================
-- 3. AGENT BALANCES (cache szybki dostęp)
-- ==========================================
CREATE TABLE IF NOT EXISTS agent_balances (
    id BIGSERIAL PRIMARY KEY,
    agent_address TEXT NOT NULL,
    token TEXT NOT NULL,
    balance NUMERIC NOT NULL DEFAULT 0,
    balance_usd NUMERIC DEFAULT 0,
    last_verified TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(agent_address, token)
);

CREATE INDEX IF NOT EXISTS idx_agent_balances_agent ON agent_balances(agent_address);

ALTER TABLE agent_balances ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "agent_balances_read" ON agent_balances;
DROP POLICY IF EXISTS "agent_balances_write" ON agent_balances;
CREATE POLICY "agent_balances_read" ON agent_balances FOR SELECT USING (true);
CREATE POLICY "agent_balances_write" ON agent_balances FOR ALL USING (true);


-- ==========================================
-- 4. AGENT POSITIONS (aktywne pozycje LP)
-- ==========================================
CREATE TABLE IF NOT EXISTS agent_positions (
    id BIGSERIAL PRIMARY KEY,
    agent_address TEXT NOT NULL,
    user_address TEXT NOT NULL,
    protocol TEXT NOT NULL,  -- aerodrome, aave, morpho
    pool_address TEXT,
    pool_name TEXT,
    
    -- Position data
    token0 TEXT,
    token1 TEXT,
    amount0 NUMERIC DEFAULT 0,
    amount1 NUMERIC DEFAULT 0,
    lp_tokens NUMERIC DEFAULT 0,
    
    -- Value tracking
    entry_value_usd NUMERIC NOT NULL,
    current_value_usd NUMERIC NOT NULL,
    apy NUMERIC DEFAULT 0,
    
    -- Status
    status TEXT DEFAULT 'active',  -- active, closed, pending
    entry_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    exit_time TIMESTAMP WITH TIME ZONE,
    
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_agent_positions_agent ON agent_positions(agent_address);
CREATE INDEX IF NOT EXISTS idx_agent_positions_user ON agent_positions(user_address);
CREATE INDEX IF NOT EXISTS idx_agent_positions_status ON agent_positions(status);
CREATE INDEX IF NOT EXISTS idx_agent_positions_protocol ON agent_positions(protocol);

ALTER TABLE agent_positions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "agent_positions_read" ON agent_positions;
DROP POLICY IF EXISTS "agent_positions_write" ON agent_positions;
CREATE POLICY "agent_positions_read" ON agent_positions FOR SELECT USING (true);
CREATE POLICY "agent_positions_write" ON agent_positions FOR ALL USING (true);


-- ==========================================
-- 5. AUDIT TRAIL (reasoning terminal)
-- ==========================================
CREATE TABLE IF NOT EXISTS audit_trail (
    id BIGSERIAL PRIMARY KEY,
    agent_address TEXT NOT NULL,
    user_address TEXT NOT NULL,
    action TEXT NOT NULL,  -- scan, analyze, deposit, rotate, withdraw, alert
    message TEXT NOT NULL,
    severity TEXT DEFAULT 'info',  -- info, warning, error, success
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_trail(agent_address);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_trail(user_address);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_trail(created_at DESC);

ALTER TABLE audit_trail ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "audit_read" ON audit_trail;
DROP POLICY IF EXISTS "audit_write" ON audit_trail;
CREATE POLICY "audit_read" ON audit_trail FOR SELECT USING (true);
CREATE POLICY "audit_write" ON audit_trail FOR ALL USING (true);
