"""
Supabase Table Creation Script
Run this script to create all required tables.

Usage: python create_supabase_tables.py
"""

import httpx
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# SQL to create all tables
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS positions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_address TEXT NOT NULL,
    protocol TEXT NOT NULL,
    entry_value DECIMAL,
    current_value DECIMAL,
    entry_time TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    UNIQUE(user_address, protocol)
);

CREATE TABLE IF NOT EXISTS transactions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_address TEXT NOT NULL,
    action_type TEXT NOT NULL,
    tx_hash TEXT,
    details JSONB DEFAULT '{}',
    status TEXT DEFAULT 'completed',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pool_snapshots (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    pool_name TEXT NOT NULL,
    protocol TEXT NOT NULL,
    apy DECIMAL,
    tvl DECIMAL,
    snapshot_time TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS leverage_positions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_address TEXT NOT NULL,
    protocol TEXT NOT NULL,
    initial_deposit DECIMAL,
    current_collateral DECIMAL,
    current_debt DECIMAL,
    leverage DECIMAL,
    health_factor DECIMAL,
    loop_count INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_address, protocol)
);

CREATE TABLE IF NOT EXISTS agent_configs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_address TEXT NOT NULL UNIQUE,
    config JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS harvests (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_address TEXT NOT NULL,
    executor_address TEXT NOT NULL,
    protocol TEXT NOT NULL,
    harvested_amount DECIMAL,
    executor_reward DECIMAL,
    tx_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_positions_user ON positions(user_address);
CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_address);
CREATE INDEX IF NOT EXISTS idx_leverage_user ON leverage_positions(user_address);
"""


def test_connection():
    """Test Supabase connection by inserting a test record"""
    print(f"Testing Supabase connection...")
    print(f"URL: {SUPABASE_URL}")
    print(f"Key: {SUPABASE_KEY[:20]}...")
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    # Test the REST API
    response = httpx.get(
        f"{SUPABASE_URL}/rest/v1/",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500] if response.text else 'Empty'}")
    
    return response.status_code == 200


def main():
    print("=" * 50)
    print("Supabase Table Creation")
    print("=" * 50)
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Missing SUPABASE_URL or SUPABASE_KEY in .env")
        return
    
    # Test connection first
    if test_connection():
        print("\n✅ Connection successful!")
        print("\n📋 To create tables, copy the SQL below and run it in Supabase SQL Editor:")
        print("=" * 50)
        print(SCHEMA_SQL)
        print("=" * 50)
        print("\n🔗 Or go to: https://supabase.com/dashboard/project/qbslpllbulbocuypsjy/sql/new")
    else:
        print("\n❌ Connection failed. Check your API key.")


if __name__ == "__main__":
    main()
