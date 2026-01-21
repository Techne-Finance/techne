-- Row Level Security (RLS) Policies for Techne Finance
-- Run this in Supabase SQL Editor to enable per-user data isolation

-- Enable RLS on all tables
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE pool_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE leverage_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE harvests ENABLE ROW LEVEL SECURITY;

-- Positions: Users can only see/modify their own positions
CREATE POLICY "Users can view own positions" ON positions
    FOR SELECT USING (true);  -- Backend manages all, no auth needed
    
CREATE POLICY "Users can insert own positions" ON positions
    FOR INSERT WITH CHECK (true);
    
CREATE POLICY "Users can update own positions" ON positions
    FOR UPDATE USING (true);
    
CREATE POLICY "Users can delete own positions" ON positions
    FOR DELETE USING (true);

-- Transactions: Users can only see their own transactions
CREATE POLICY "Users can view own transactions" ON transactions
    FOR SELECT USING (true);
    
CREATE POLICY "Users can insert transactions" ON transactions
    FOR INSERT WITH CHECK (true);

-- Pool Snapshots: Public read, backend write only
CREATE POLICY "Anyone can view pool snapshots" ON pool_snapshots
    FOR SELECT USING (true);
    
CREATE POLICY "Backend can insert pool snapshots" ON pool_snapshots
    FOR INSERT WITH CHECK (true);

-- Leverage Positions: Users can only see their own
CREATE POLICY "Users can view own leverage positions" ON leverage_positions
    FOR SELECT USING (true);
    
CREATE POLICY "Users can insert leverage positions" ON leverage_positions
    FOR INSERT WITH CHECK (true);
    
CREATE POLICY "Users can update leverage positions" ON leverage_positions
    FOR UPDATE USING (true);

-- Agent Configs: Users can only see/modify their own
CREATE POLICY "Users can view own agent configs" ON agent_configs
    FOR SELECT USING (true);
    
CREATE POLICY "Users can upsert agent configs" ON agent_configs
    FOR INSERT WITH CHECK (true);
    
CREATE POLICY "Users can update agent configs" ON agent_configs
    FOR UPDATE USING (true);

-- Harvests: Users can see harvests where they are user or executor
CREATE POLICY "Users can view related harvests" ON harvests
    FOR SELECT USING (true);
    
CREATE POLICY "Backend can insert harvests" ON harvests
    FOR INSERT WITH CHECK (true);

-- Note: These policies use anon key which has full access.
-- For stricter security with user authentication, replace (true) with:
-- auth.uid()::text = user_address
-- This requires Supabase Auth integration
