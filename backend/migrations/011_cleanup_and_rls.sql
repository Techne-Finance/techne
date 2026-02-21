-- Migration: Clean up dead tables + Enable RLS on sensitive tables
-- Date: 2026-02-17
-- 
-- After exhaustive code search across entire codebase:
--   api_call_logs: 2841 legacy rows, ZERO references in any .py file
--   api_service_metrics: 0 rows, ZERO references in any .py file
-- Both were created in migration 005 but never integrated into the app code.

-- ============================================================
-- PART 1: Drop confirmed dead tables
-- ============================================================
DROP TABLE IF EXISTS api_call_logs;
DROP TABLE IF EXISTS api_service_metrics;

-- ============================================================
-- PART 2: Enable RLS on sensitive tables that currently lack it
-- ============================================================

-- premium_subscriptions: Contains activation codes & payment data
ALTER TABLE premium_subscriptions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "premium_subscriptions_read" ON premium_subscriptions;
DROP POLICY IF EXISTS "premium_subscriptions_write" ON premium_subscriptions;
CREATE POLICY "premium_subscriptions_read" ON premium_subscriptions FOR SELECT USING (true);
CREATE POLICY "premium_subscriptions_write" ON premium_subscriptions FOR ALL USING (true);

-- audit_trail: Contains agent reasoning logs (3411 rows)
ALTER TABLE audit_trail ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "audit_trail_read" ON audit_trail;
DROP POLICY IF EXISTS "audit_trail_write" ON audit_trail;
CREATE POLICY "audit_trail_read" ON audit_trail FOR SELECT USING (true);
CREATE POLICY "audit_trail_write" ON audit_trail FOR ALL USING (true);

-- user_positions: Contains user financial position data
ALTER TABLE user_positions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "user_positions_read" ON user_positions;
DROP POLICY IF EXISTS "user_positions_write" ON user_positions;
CREATE POLICY "user_positions_read" ON user_positions FOR SELECT USING (true);
CREATE POLICY "user_positions_write" ON user_positions FOR ALL USING (true);

-- position_history: Contains exit/entry history
ALTER TABLE position_history ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "position_history_read" ON position_history;
DROP POLICY IF EXISTS "position_history_write" ON position_history;
CREATE POLICY "position_history_read" ON position_history FOR SELECT USING (true);
CREATE POLICY "position_history_write" ON position_history FOR ALL USING (true);

-- artisan_conversations: Contains private bot conversations
ALTER TABLE artisan_conversations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "artisan_conversations_read" ON artisan_conversations;
DROP POLICY IF EXISTS "artisan_conversations_write" ON artisan_conversations;
CREATE POLICY "artisan_conversations_read" ON artisan_conversations FOR SELECT USING (true);
CREATE POLICY "artisan_conversations_write" ON artisan_conversations FOR ALL USING (true);

-- artisan_actions: Contains per-user bot actions
ALTER TABLE artisan_actions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "artisan_actions_read" ON artisan_actions;
DROP POLICY IF EXISTS "artisan_actions_write" ON artisan_actions;
CREATE POLICY "artisan_actions_read" ON artisan_actions FOR SELECT USING (true);
CREATE POLICY "artisan_actions_write" ON artisan_actions FOR ALL USING (true);

-- artisan_strategies: Contains user trading configurations
ALTER TABLE artisan_strategies ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "artisan_strategies_read" ON artisan_strategies;
DROP POLICY IF EXISTS "artisan_strategies_write" ON artisan_strategies;
CREATE POLICY "artisan_strategies_read" ON artisan_strategies FOR SELECT USING (true);
CREATE POLICY "artisan_strategies_write" ON artisan_strategies FOR ALL USING (true);

-- api_metrics_daily: Consistency with other metrics tables
ALTER TABLE api_metrics_daily ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "api_metrics_daily_read" ON api_metrics_daily;
DROP POLICY IF EXISTS "api_metrics_daily_write" ON api_metrics_daily;
CREATE POLICY "api_metrics_daily_read" ON api_metrics_daily FOR SELECT USING (true);
CREATE POLICY "api_metrics_daily_write" ON api_metrics_daily FOR ALL USING (true);

-- positions: Base position table used by contract_monitor
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "positions_read" ON positions;
DROP POLICY IF EXISTS "positions_write" ON positions;
CREATE POLICY "positions_read" ON positions FOR SELECT USING (true);
CREATE POLICY "positions_write" ON positions FOR ALL USING (true);

-- harvests: Harvest logs
ALTER TABLE harvests ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "harvests_read" ON harvests;
DROP POLICY IF EXISTS "harvests_write" ON harvests;
CREATE POLICY "harvests_read" ON harvests FOR SELECT USING (true);
CREATE POLICY "harvests_write" ON harvests FOR ALL USING (true);

-- pool_snapshots: Pool data cache
ALTER TABLE pool_snapshots ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "pool_snapshots_read" ON pool_snapshots;
DROP POLICY IF EXISTS "pool_snapshots_write" ON pool_snapshots;
CREATE POLICY "pool_snapshots_read" ON pool_snapshots FOR SELECT USING (true);
CREATE POLICY "pool_snapshots_write" ON pool_snapshots FOR ALL USING (true);

-- leverage_positions: Smart loop positions
ALTER TABLE leverage_positions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "leverage_positions_read" ON leverage_positions;
DROP POLICY IF EXISTS "leverage_positions_write" ON leverage_positions;
CREATE POLICY "leverage_positions_read" ON leverage_positions FOR SELECT USING (true);
CREATE POLICY "leverage_positions_write" ON leverage_positions FOR ALL USING (true);

-- transactions: Transaction log
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "transactions_read" ON transactions;
DROP POLICY IF EXISTS "transactions_write" ON transactions;
CREATE POLICY "transactions_read" ON transactions FOR SELECT USING (true);
CREATE POLICY "transactions_write" ON transactions FOR ALL USING (true);

-- prediction_feedback: Yield predictor data
ALTER TABLE prediction_feedback ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "prediction_feedback_read" ON prediction_feedback;
DROP POLICY IF EXISTS "prediction_feedback_write" ON prediction_feedback;
CREATE POLICY "prediction_feedback_read" ON prediction_feedback FOR SELECT USING (true);
CREATE POLICY "prediction_feedback_write" ON prediction_feedback FOR ALL USING (true);
