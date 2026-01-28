"""
Migration Script: JSON to Supabase
Migrates existing agents from deployed_agents.json and agent_wallets/ to Supabase
"""

import os
import json
import asyncio
from datetime import datetime

# Add parent to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.agent_service import agent_service, AgentConfig


async def migrate_deployed_agents():
    """Migrate agents from deployed_agents.json"""
    
    json_file = os.path.join(os.path.dirname(__file__), "..", "data", "deployed_agents.json")
    
    if not os.path.exists(json_file):
        print("❌ deployed_agents.json not found")
        return 0
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    migrated = 0
    
    for user_address, agents_list in data.items():
        for agent_data in agents_list:
            print(f"\n📦 Migrating agent: {agent_data.get('name', 'Unknown')} for {user_address[:10]}...")
            
            config = AgentConfig(
                chain=agent_data.get("chain", "base"),
                preset=agent_data.get("preset", "balanced"),
                pool_type=agent_data.get("pool_type", "single"),
                risk_level=agent_data.get("risk_level", "moderate"),
                min_apy=agent_data.get("min_apy", 5),
                max_apy=agent_data.get("max_apy", 1000),
                max_drawdown=agent_data.get("max_drawdown", 20),
                protocols=agent_data.get("protocols", ["aerodrome", "aave"]),
                preferred_assets=agent_data.get("preferred_assets", ["USDC"]),
                is_pro_mode=agent_data.get("is_pro_mode", False)
            )
            
            result = await agent_service.create_agent(
                user_address=user_address,
                agent_address=agent_data["agent_address"],
                encrypted_private_key=agent_data.get("encrypted_private_key", ""),
                config=config,
                agent_name=agent_data.get("name", "Agent")
            )
            
            if result["success"]:
                print(f"   ✅ Migrated: {agent_data['agent_address'][:10]}...")
                
                # Update additional fields
                await agent_service.update_agent(agent_data["agent_address"], {
                    "is_active": agent_data.get("is_active", True),
                    "total_deposited": agent_data.get("total_deposited", 0),
                    "total_value": agent_data.get("total_value", 0),
                    "deployed_at": agent_data.get("deployed_at", datetime.now().isoformat())
                })
                
                migrated += 1
            else:
                print(f"   ❌ Failed: {result.get('error')}")
    
    return migrated


async def migrate_agent_wallets():
    """Migrate additional wallet data from agent_wallets/ folder"""
    
    wallets_dir = os.path.join(os.path.dirname(__file__), "..", "data", "agent_wallets")
    
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
        
        print(f"\n🔄 Processing wallet: {user_address[:10]}...")
        
        # Migrate transactions
        transactions = wallet_data.get("transactions", [])
        for tx in transactions:
            result = await agent_service.record_transaction(
                user_address=user_address,
                agent_address=agent_address,
                tx_type=tx.get("type", "unknown"),
                token=tx.get("token", "USDC"),
                amount=tx.get("amount", 0),
                tx_hash=tx.get("tx_hash"),
                status="completed",
                destination=tx.get("destination"),
                pool_id=tx.get("pool_id"),
                metadata={"migrated_from": "json", "original_timestamp": tx.get("timestamp")}
            )
            if result["success"]:
                migrated_tx += 1
        
        # Migrate balances
        balances = wallet_data.get("balances", {})
        for token, balance in balances.items():
            if balance > 0:
                await agent_service.update_balance(agent_address, token, balance)
        
        print(f"   📊 Migrated {len(transactions)} transactions, {len(balances)} balances")
    
    return migrated_tx


async def main():
    print("=" * 60)
    print("🚀 Techne Finance - JSON to Supabase Migration")
    print("=" * 60)
    
    if not agent_service.supabase:
        print("\n❌ Supabase not configured! Set SUPABASE_URL and SUPABASE_KEY in .env")
        return
    
    # Step 1: Migrate agents
    print("\n📦 Step 1: Migrating deployed agents...")
    agents_migrated = await migrate_deployed_agents()
    print(f"\n✅ Migrated {agents_migrated} agents to Supabase")
    
    # Step 2: Migrate wallet data
    print("\n🔄 Step 2: Migrating wallet transactions...")
    tx_migrated = await migrate_agent_wallets()
    print(f"\n✅ Migrated {tx_migrated} transactions to Supabase")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Migration Complete!")
    print(f"   - Agents: {agents_migrated}")
    print(f"   - Transactions: {tx_migrated}")
    print("=" * 60)
    print("\n💡 You can now safely archive the JSON files.")
    print("   The system will use Supabase as the source of truth.")


if __name__ == "__main__":
    asyncio.run(main())
