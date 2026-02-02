-- Migration: 008_premium_agent_wallet.sql
-- Add agent wallet columns to premium_subscriptions

-- Add agent address column
ALTER TABLE premium_subscriptions
ADD COLUMN IF NOT EXISTS agent_address TEXT;

-- Add session key address column  
ALTER TABLE premium_subscriptions
ADD COLUMN IF NOT EXISTS session_key_address TEXT;

-- Index for agent address lookups
CREATE INDEX IF NOT EXISTS idx_premium_agent ON premium_subscriptions(agent_address);

-- Comments
COMMENT ON COLUMN premium_subscriptions.agent_address IS 'Smart account address created for this subscription';
COMMENT ON COLUMN premium_subscriptions.session_key_address IS 'Session key address for backend trade execution';
