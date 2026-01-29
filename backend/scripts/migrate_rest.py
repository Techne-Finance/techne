"""
Migration Script: JSON to Supabase (REST API version)
Migrates existing agents from deployed_agents.json to Supabase using direct REST calls
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}


def insert_user_agent(agent_data: dict, user_address: str) -> bool:
    """Insert agent into user_agents table"""
    
    payload = {
        "user_address": user_address.lower(),
        "agent_address": agent_data["agent_address"],
        "agent_name": agent_data.get("name", "Agent"),
        "encrypted_private_key": agent_data.get("encrypted_private_key", ""),
        "chain": agent_data.get("chain", "base"),
        "preset": agent_data.get("preset", "balanced"),
        "pool_type": agent_data.get("pool_type", "single"),
        "risk_level": agent_data.get("risk_level", "moderate"),
        "min_apy": agent_data.get("min_apy", 5),
        "max_apy": agent_data.get("max_apy", 1000),
        "max_drawdown": agent_data.get("max_drawdown", 20),
        "is_active": agent_data.get("is_active", True),
        "status": "active" if agent_data.get("is_active", True) else "paused",
        "protocols": agent_data.get("protocols", ["aerodrome", "aave"]),
        "preferred_assets": agent_data.get("preferred_assets", ["USDC"]),
        "is_pro_mode": agent_data.get("is_pro_mode", False),
        "total_deposited": agent_data.get("total_deposited", 0),
        "total_value": agent_data.get("total_value", 0),
        "deployed_at": agent_data.get("deployed_at", datetime.now().isoformat())
    }
    
    try:
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/user_agents",
            headers=HEADERS,
            json=payload,
            timeout=10
        )
        
        if resp.status_code in [200, 201]:
            return True
        elif resp.status_code == 409:
            print(f"      ⚠️ Agent already exists (duplicate)")
            return False
        else:
            print(f"      ❌ HTTP {resp.status_code}: {resp.text[:100]}")
            return False
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return False


def migrate_deployed_agents():
    """Migrate agents from deployed_agents.json"""
    
    script_dir = os.path.dirname(__file__)
    json_file = os.path.join(script_dir, "..", "data", "deployed_agents.json")
    
    if not os.path.exists(json_file):
        print("❌ deployed_agents.json not found")
        return 0
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    migrated = 0
    
    for user_address, agents_list in data.items():
        print(f"\n👤 User: {user_address[:15]}...")
        
        for agent_data in agents_list:
            agent_name = agent_data.get('name', 'Unknown')
            agent_addr = agent_data.get('agent_address', '')[:15]
            print(f"   📦 {agent_name} ({agent_addr}...)")
            
            if insert_user_agent(agent_data, user_address):
                print(f"      ✅ Migrated!")
                migrated += 1
    
    return migrated


def migrate_wallet_transactions():
    """Migrate transactions from agent_wallets/*.json"""
    
    script_dir = os.path.dirname(__file__)
    wallets_dir = os.path.join(script_dir, "..", "data", "agent_wallets")
    
    if not os.path.exists(wallets_dir):
        print("❌ agent_wallets/ directory not found")
        return 0
    
    migrated_tx = 0
    
    for filename in os.listdir(wallets_dir):
        if not filename.endswith('.json'):
            continue
        
        filepath = os.path.join(wallets_dir, filename)
        
        with open(filepath, 'r') as f:
            wallet_data = json.load(f)
        
        user_address = wallet_data.get("user_id", "").lower()
        agent_address = wallet_data.get("agent_address", "")
        
        if not agent_address:
            continue
        
        transactions = wallet_data.get("transactions", [])
        if not transactions:
            continue
            
        print(f"\n🔄 Wallet: {user_address[:15]}... ({len(transactions)} tx)")
        
        for tx in transactions:
            payload = {
                "user_address": user_address,
                "agent_address": agent_address,
                "tx_type": tx.get("type", "unknown"),
                "token": tx.get("token", "USDC"),
                "amount": tx.get("amount", 0),
                "tx_hash": tx.get("tx_hash"),
                "status": "completed",
                "metadata": {"migrated_from": "json", "original_timestamp": tx.get("timestamp")}
            }
            
            try:
                resp = requests.post(
                    f"{SUPABASE_URL}/rest/v1/agent_transactions",
                    headers=HEADERS,
                    json=payload,
                    timeout=10
                )
                if resp.status_code in [200, 201]:
                    migrated_tx += 1
            except:
                pass
        
        # Migrate balances
        balances = wallet_data.get("balances", {})
        for token, balance in balances.items():
            if balance > 0:
                payload = {
                    "agent_address": agent_address,
                    "token": token,
                    "balance": balance,
                    "balance_usd": 0
                }
                try:
                    requests.post(
                        f"{SUPABASE_URL}/rest/v1/agent_balances",
                        headers={**HEADERS, "Prefer": "resolution=merge-duplicates"},
                        json=payload,
                        timeout=5
                    )
                except:
                    pass
    
    return migrated_tx


def main():
    print("=" * 60)
    print("🚀 Techne Finance - JSON to Supabase Migration (REST)")
    print("=" * 60)
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("\n❌ Missing SUPABASE_URL or SUPABASE_KEY in .env!")
        return
    
    print(f"\n🔗 Supabase: {SUPABASE_URL[:40]}...")
    
    # Step 1: Migrate agents
    print("\n📦 Step 1: Migrating deployed agents...")
    agents_migrated = migrate_deployed_agents()
    print(f"\n✅ Migrated {agents_migrated} agents")
    
    # Step 2: Migrate transactions
    print("\n🔄 Step 2: Migrating wallet transactions...")
    tx_migrated = migrate_wallet_transactions()
    print(f"\n✅ Migrated {tx_migrated} transactions")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Migration Complete!")
    print(f"   - Agents: {agents_migrated}")
    print(f"   - Transactions: {tx_migrated}")
    print("=" * 60)


if __name__ == "__main__":
    main()
