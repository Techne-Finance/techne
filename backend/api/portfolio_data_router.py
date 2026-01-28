"""
Portfolio Data Router - Unified endpoint for all portfolio data
Combines: Supabase positions, on-chain LP, parking status, audit trail
"""

from fastapi import APIRouter, Query
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/portfolio-data", tags=["Portfolio Data"])


@router.get("/{user_address}")
async def get_portfolio_data(
    user_address: str,
    include_audit: bool = Query(True, description="Include audit trail logs")
):
    """
    Unified portfolio data endpoint.
    
    Combines data from:
    1. Supabase user_positions (persistent positions)
    2. On-chain LP positions (real-time)
    3. Parking status (Aave V3)
    4. Audit trail (reasoning logs)
    
    Returns:
        {
            "positions": [...],     # All active positions
            "parked": {...},        # Parking status if any
            "audit_logs": [...],    # Recent audit entries
            "totals": {...}         # Aggregated values
        }
    """
    result = {
        "success": True,
        "user_address": user_address,
        "positions": [],
        "parked": None,
        "audit_logs": [],
        "totals": {
            "deposited_usd": 0,
            "current_usd": 0,
            "pnl_usd": 0,
            "pnl_percent": 0
        }
    }
    
    # 1. Get positions from Supabase
    try:
        from infrastructure.supabase_client import supabase
        if supabase and supabase.is_available:
            supabase_positions = await supabase.get_user_positions(user_address)
            for pos in supabase_positions:
                result["positions"].append({
                    "id": pos.get("id"),
                    "protocol": pos.get("protocol"),
                    "asset": pos.get("asset", "USDC"),
                    "pool_type": pos.get("pool_type", "single"),
                    "entry_value": pos.get("entry_value", 0),
                    "current_value": pos.get("current_value", 0),
                    "apy": pos.get("apy", 0),
                    "pool_address": pos.get("pool_address"),
                    "source": "supabase",
                    "status": pos.get("status", "active")
                })
    except Exception as e:
        print(f"[PortfolioData] Supabase fetch failed: {e}")
    
    # 2. Get on-chain LP positions
    try:
        from api.agent_router import get_agent_lp_positions
        
        # Get agent address for this user
        from api.agent_config_router import DEPLOYED_AGENTS
        agents = DEPLOYED_AGENTS.get(user_address.lower(), [])
        
        for agent in agents:
            agent_addr = agent.get("agent_address")
            if agent_addr:
                lp_result = await get_agent_lp_positions(agent_addr)
                if lp_result.get("success"):
                    for lp in lp_result.get("positions", []):
                        # Avoid duplicates (check by pool_address)
                        existing = [p for p in result["positions"] 
                                   if p.get("pool_address") == lp.get("lp_address")]
                        if not existing:
                            result["positions"].append({
                                "id": f"lp_{lp.get('lp_address', '')[:10]}",
                                "protocol": lp.get("protocol", "Aerodrome"),
                                "asset": "LP",
                                "pool_type": "lp",
                                "pool_name": lp.get("pool_name"),
                                "entry_value": lp.get("value_usd", 0),
                                "current_value": lp.get("value_usd", 0),
                                "apy": lp.get("apy", 0),
                                "pool_address": lp.get("lp_address"),
                                "lp_tokens": lp.get("lp_tokens"),
                                "source": "onchain",
                                "status": "active"
                            })
    except Exception as e:
        print(f"[PortfolioData] LP positions fetch failed: {e}")
    
    # 3. Check parking status
    try:
        from services.parking_strategy import get_parking_strategy
        parking = get_parking_strategy()
        parked_info = parking.get_parked_info(user_address)
        if parked_info and parked_info.get("amount", 0) > 0:
            result["parked"] = {
                "protocol": parked_info.get("protocol", "aave_v3"),
                "amount_usd": parked_info.get("amount", 0),
                "apy": parking.get_parking_apy(),
                "message": "Safety Mode: Capital secured in Aave V3"
            }
    except Exception as e:
        print(f"[PortfolioData] Parking status check failed: {e}")
    
    # 4. Get audit trail (reasoning logs)
    if include_audit:
        try:
            from infrastructure.supabase_client import supabase
            if supabase and supabase.is_available:
                audit_logs = await supabase.get_transactions(user_address, limit=20)
                
                # Map action types to user-friendly messages
                ACTION_MESSAGES = {
                    "PROFITABILITY_GATE": "🔒 Rotation aborted. Costs exceed projected profit",
                    "SCAM_DETECTED": "🛡️ AI Scam Filter triggered. Pool blacklisted",
                    "STALE_DATA": "⏳ Pyth Oracle alert. Waiting for update",
                    "APY_DROP": "📉 APY dropped below threshold",
                    "ROTATION_STARTED": "🔄 Position rotation initiated",
                    "DEPOSIT": "💰 Funds deposited",
                    "WITHDRAW": "💸 Funds withdrawn",
                    "LP_ENTRY": "🏊 Entered LP position",
                    "LP_EXIT": "🚪 Exited LP position",
                    "PARKED": "🅿️ Capital parked in safety protocol"
                }
                
                for log in audit_logs:
                    action_type = log.get("action_type", "")
                    result["audit_logs"].append({
                        "id": log.get("id"),
                        "action": action_type,
                        "message": ACTION_MESSAGES.get(action_type, log.get("action_type")),
                        "details": log.get("details", {}),
                        "timestamp": log.get("created_at"),
                        "status": log.get("status", "completed")
                    })
        except Exception as e:
            print(f"[PortfolioData] Audit trail fetch failed: {e}")
    
    # 5. Calculate totals
    total_deposited = sum(p.get("entry_value", 0) for p in result["positions"])
    total_current = sum(p.get("current_value", 0) for p in result["positions"])
    
    # Add parked capital to totals
    if result["parked"]:
        total_current += result["parked"].get("amount_usd", 0)
        total_deposited += result["parked"].get("amount_usd", 0)
    
    pnl = total_current - total_deposited
    pnl_percent = (pnl / total_deposited * 100) if total_deposited > 0 else 0
    
    result["totals"] = {
        "deposited_usd": round(total_deposited, 2),
        "current_usd": round(total_current, 2),
        "pnl_usd": round(pnl, 2),
        "pnl_percent": round(pnl_percent, 2),
        "position_count": len(result["positions"])
    }
    
    return result


@router.get("/{user_address}/subscribe-info")
async def get_subscribe_info(user_address: str):
    """
    Get Supabase Realtime subscription config.
    
    Returns channel and filter info for frontend to subscribe.
    """
    return {
        "channel": "portfolio_updates",
        "tables": [
            {
                "table": "user_positions",
                "filter": f"user_address=eq.{user_address}",
                "events": ["INSERT", "UPDATE", "DELETE"]
            },
            {
                "table": "audit_trail", 
                "filter": f"user_address=eq.{user_address}",
                "events": ["INSERT"]
            }
        ],
        "supabase_url": os.getenv("SUPABASE_URL", ""),
        "supabase_anon_key": os.getenv("SUPABASE_ANON_KEY", "")
    }
