-- Artisan Bot Supermemory Table
-- Persistent memory for AI agent across sessions

CREATE TABLE IF NOT EXISTS artisan_memory (
    id SERIAL PRIMARY KEY,
    user_address TEXT NOT NULL UNIQUE,
    
    -- User preferences (trading style, risk, chains)
    preferences JSONB DEFAULT '{}',
    
    -- Long-term facts about the user
    facts JSONB DEFAULT '[]',
    
    -- Recent conversation history (last 50 messages)
    conversation_history JSONB DEFAULT '[]',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast lookup by user
CREATE INDEX IF NOT EXISTS idx_artisan_memory_user ON artisan_memory(user_address);

-- Enable RLS
ALTER TABLE artisan_memory ENABLE ROW LEVEL SECURITY;

-- Policy: Service role can do everything
CREATE POLICY "Service role full access" ON artisan_memory
    FOR ALL USING (true);

-- Auto-update timestamp
CREATE OR REPLACE FUNCTION update_artisan_memory_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER artisan_memory_updated
    BEFORE UPDATE ON artisan_memory
    FOR EACH ROW
    EXECUTE FUNCTION update_artisan_memory_timestamp();

-- Comments
COMMENT ON TABLE artisan_memory IS 'Persistent memory for Artisan Bot - stores user preferences, facts, and conversation history';
COMMENT ON COLUMN artisan_memory.preferences IS 'User preferences: risk_tolerance, trading_style, preferred_chains, etc.';
COMMENT ON COLUMN artisan_memory.facts IS 'Long-term facts extracted from conversations';
COMMENT ON COLUMN artisan_memory.conversation_history IS 'Recent conversation history (max 50 messages)';
