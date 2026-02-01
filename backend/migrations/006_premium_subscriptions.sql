-- Migration: 006_premium_subscriptions.sql
-- Techne Premium + Artisan Agent subscription management

-- Premium subscriptions
CREATE TABLE IF NOT EXISTS premium_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_address TEXT NOT NULL,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'cancelled', 'expired', 'pending')),
    autonomy_mode TEXT DEFAULT 'advisor' CHECK (autonomy_mode IN ('observer', 'advisor', 'copilot', 'full_auto')),
    activation_code TEXT UNIQUE,
    code_used_at TIMESTAMPTZ,
    telegram_chat_id BIGINT,
    telegram_username TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    x402_payment_id TEXT,
    monthly_price_usd DECIMAL(10,2) DEFAULT 50.00,
    UNIQUE(user_address)
);

-- Artisan agent conversation history
CREATE TABLE IF NOT EXISTS artisan_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID REFERENCES premium_subscriptions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    tool_calls JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Artisan agent action log (audit trail)
CREATE TABLE IF NOT EXISTS artisan_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID REFERENCES premium_subscriptions(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL CHECK (action_type IN ('analyze', 'suggest', 'trade', 'exit', 'emergency_exit', 'report', 'other')),
    details JSONB NOT NULL DEFAULT '{}',
    confirmation_required BOOLEAN DEFAULT FALSE,
    confirmed BOOLEAN DEFAULT FALSE,
    confirmed_at TIMESTAMPTZ,
    executed BOOLEAN DEFAULT FALSE,
    executed_at TIMESTAMPTZ,
    tx_hash TEXT,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_premium_user_address ON premium_subscriptions(user_address);
CREATE INDEX IF NOT EXISTS idx_premium_activation_code ON premium_subscriptions(activation_code);
CREATE INDEX IF NOT EXISTS idx_premium_telegram ON premium_subscriptions(telegram_chat_id);
CREATE INDEX IF NOT EXISTS idx_conversations_subscription ON artisan_conversations(subscription_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON artisan_conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_actions_subscription ON artisan_actions(subscription_id);
CREATE INDEX IF NOT EXISTS idx_actions_created ON artisan_actions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_actions_pending ON artisan_actions(subscription_id) WHERE confirmation_required = TRUE AND confirmed = FALSE;

-- Comments for documentation
COMMENT ON TABLE premium_subscriptions IS 'Techne Premium ($50/mo) subscriptions with Artisan Agent access';
COMMENT ON COLUMN premium_subscriptions.autonomy_mode IS 'observer=view only, advisor=suggest+confirm, copilot=auto<$1k, full_auto=all auto';
COMMENT ON TABLE artisan_conversations IS 'Kimi K2.5 conversation history for context persistence';
COMMENT ON TABLE artisan_actions IS 'Audit trail of all agent actions for transparency and debugging';
