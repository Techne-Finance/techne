-- ==================================================
-- MIGRATION 010: Fix user_positions unique constraint
-- 
-- Problem: Unique key was (user_address, protocol) which meant
-- an agent with 2 positions on the same protocol (e.g. 2 Aave pools)
-- would have the second overwrite the first.
--
-- Fix: Change to (user_address, protocol, pool_address) so each
-- pool is tracked separately.
-- ==================================================

-- 1. Drop old unique constraint
ALTER TABLE user_positions DROP CONSTRAINT IF EXISTS user_positions_user_address_protocol_key;

-- 2. Ensure pool_address has a default (empty string, not NULL)
-- so the unique constraint works reliably
ALTER TABLE user_positions ALTER COLUMN pool_address SET DEFAULT '';
UPDATE user_positions SET pool_address = '' WHERE pool_address IS NULL;
ALTER TABLE user_positions ALTER COLUMN pool_address SET NOT NULL;

-- 3. Create new unique constraint including pool_address
ALTER TABLE user_positions ADD CONSTRAINT user_positions_user_protocol_pool_key 
    UNIQUE(user_address, protocol, pool_address);

-- 4. Add composite index for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_positions_user_protocol_pool 
    ON user_positions(user_address, protocol, pool_address);
