-- Migration: 012_auto_renewal.sql
-- Add auto-renewal columns to premium_subscriptions
-- Bot pays $99/mo from user's Smart Account via session key

-- Auto-renewal opt-in flag (default OFF — user must explicitly enable)
ALTER TABLE premium_subscriptions
ADD COLUMN IF NOT EXISTS auto_renewal_enabled BOOLEAN DEFAULT FALSE;

-- TX hash of last successful auto-renewal
ALTER TABLE premium_subscriptions
ADD COLUMN IF NOT EXISTS last_renewal_tx TEXT;

-- Timestamp of last failed renewal attempt (for retry backoff)
ALTER TABLE premium_subscriptions
ADD COLUMN IF NOT EXISTS renewal_failed_at TIMESTAMPTZ;

-- Index for cron job: find subscriptions due for renewal
CREATE INDEX IF NOT EXISTS idx_premium_auto_renewal
ON premium_subscriptions(auto_renewal_enabled, expires_at)
WHERE auto_renewal_enabled = TRUE AND status = 'active';

-- Comments
COMMENT ON COLUMN premium_subscriptions.auto_renewal_enabled IS 'User opt-in for auto-payment from agent Smart Account';
COMMENT ON COLUMN premium_subscriptions.last_renewal_tx IS 'TX hash of last successful auto-renewal payment';
COMMENT ON COLUMN premium_subscriptions.renewal_failed_at IS 'Last failed renewal attempt timestamp for retry backoff';
