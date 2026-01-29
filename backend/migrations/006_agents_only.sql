-- ==================================================
-- MIGRATION: Scalable Agent System (CLEAN VERSION)
-- Only creates the 4 missing tables
-- ==================================================

-- 1. USER AGENTS
CREATE TABLE IF NOT EXISTS user_agents (
    id BIGSERIAL PRIMARY KEY,
    user_address TEXT NOT NULL,
    agent_address TEXT NOT NULL UNIQUE,
    agent_name TEXT DEFAULT 'Agent',
    encrypted_private_key TEXT NOT NULL,
    chain TEXT DEFAULT 'base',
    preset TEXT DEFAULT 'balanced',
    pool_type TEXT DEFAULT 'single',
    risk_level TEXT DEFAULT 'moderate',
    min_apy NUMERIC DEFAULT 5,
    max_apy NUMERIC DEFAULT 1000,
    max_drawdown NUMERIC DEFAULT 20,
    is_active BOOLEAN DEFAULT true,
    status TEXT DEFAULT 'active',
    settings JSONB DEFAULT '{}',
    protocols JSONB DEFAULT '[]',
    preferred_assets JSONB DEFAULT '[]',
    is_pro_mode BOOLEAN DEFAULT false,
    pro_config JSONB,
    total_deposited NUMERIC DEFAULT 0,
    total_value NUMERIC DEFAULT 0,
    total_earnings NUMERIC DEFAULT 0,
    deployed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_agents_user ON user_agents(user_address);
CREATE INDEX IF NOT EXISTS idx_user_agents_agent ON user_agents(agent_address);
CREATE INDEX IF NOT EXISTS idx_user_agents_active ON user_agents(is_active) WHERE is_active = true;

ALTER TABLE user_agents ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "user_agents_read" ON user_agents;
DROP POLICY IF EXISTS "user_agents_write" ON user_agents;
CREATE POLICY "user_agents_read" ON user_agents FOR SELECT USING (true);
CREATE POLICY "user_agents_write" ON user_agents FOR ALL USING (true);


-- 2. AGENT TRANSACTIONS
CREATE TABLE IF NOT EXISTS agent_transactions (
    id BIGSERIAL PRIMARY KEY,
    user_address TEXT NOT NULL,
    agent_address TEXT NOT NULL,
    tx_type TEXT NOT NULL,
    token TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    tx_hash TEXT,
    status TEXT DEFAULT 'completed',
    destination TEXT,
    pool_id TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_tx_user ON agent_transactions(user_address);
CREATE INDEX IF NOT EXISTS idx_agent_tx_agent ON agent_transactions(agent_address);
CREATE INDEX IF NOT EXISTS idx_agent_tx_time ON agent_transactions(created_at DESC);

ALTER TABLE agent_transactions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "agent_tx_read" ON agent_transactions;
DROP POLICY IF EXISTS "agent_tx_write" ON agent_transactions;
CREATE POLICY "agent_tx_read" ON agent_transactions FOR SELECT USING (true);
CREATE POLICY "agent_tx_write" ON agent_transactions FOR ALL USING (true);


-- 3. AGENT BALANCES
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


-- 4. AGENT POSITIONS
CREATE TABLE IF NOT EXISTS agent_positions (
    id BIGSERIAL PRIMARY KEY,
    agent_address TEXT NOT NULL,
    user_address TEXT NOT NULL,
    protocol TEXT NOT NULL,
    pool_address TEXT,
    pool_name TEXT,
    token0 TEXT,
    token1 TEXT,
    amount0 NUMERIC DEFAULT 0,
    amount1 NUMERIC DEFAULT 0,
    lp_tokens NUMERIC DEFAULT 0,
    entry_value_usd NUMERIC NOT NULL,
    current_value_usd NUMERIC NOT NULL,
    apy NUMERIC DEFAULT 0,
    status TEXT DEFAULT 'active',
    entry_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    exit_time TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_agent_positions_agent ON agent_positions(agent_address);
CREATE INDEX IF NOT EXISTS idx_agent_positions_user ON agent_positions(user_address);
CREATE INDEX IF NOT EXISTS idx_agent_positions_status ON agent_positions(status);

ALTER TABLE agent_positions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "agent_positions_read" ON agent_positions;
DROP POLICY IF EXISTS "agent_positions_write" ON agent_positions;
CREATE POLICY "agent_positions_read" ON agent_positions FOR SELECT USING (true);
CREATE POLICY "agent_positions_write" ON agent_positions FOR ALL USING (true);
