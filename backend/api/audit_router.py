"""
Audit Router - Transaction history and audit logs
"""

from fastapi import APIRouter, Query
from datetime import datetime
from typing import List, Optional, Dict, Any
import os

router = APIRouter(prefix="/api/audit", tags=["Audit"])


# In-memory audit log (in production, use database)
_audit_entries = []


# ============================================
# MESSAGE MAPPING (Technical → Friendly)
# ============================================

REASON_MAPPINGS = {
    # [GUARD] - Profitability & Cost Guards
    "PROFITABILITY_GATE": {
        "category": "GUARD",
        "icon": "⛔",
        "template": "Rotation aborted. Costs (${gas_cost:.2f}) > Profit (${profit:.2f})"
    },
    "GAS_TOO_HIGH": {
        "category": "GUARD", 
        "icon": "⛽",
        "template": "Gas spike detected: ${gas_cost:.2f}. Waiting for cheaper conditions."
    },
    "SLIPPAGE_EXCEEDED": {
        "category": "GUARD",
        "icon": "📉",
        "template": "Slippage too high ({slippage:.1f}%). Trade cancelled."
    },
    
    # [SECURITY] - AI Scam Detection
    "SCAM_DETECTED": {
        "category": "SECURITY",
        "icon": "🚨",
        "template": "Security Alert: Contract flagged as scam (score: {risk_score})"
    },
    "HIGH_RISK_CODE": {
        "category": "SECURITY",
        "icon": "⚠️",
        "template": "High-risk code patterns found by AI. Blocking investment."
    },
    "WASH_TRADING": {
        "category": "SECURITY",
        "icon": "🔴",
        "template": "Wash trading detected. Pool blocked for safety."
    },
    "UNVERIFIED_CONTRACT": {
        "category": "SECURITY",
        "icon": "❓",
        "template": "Contract source not verified. Skipping."
    },
    
    # [PARK] - Parking Strategy
    "PARKING_ENGAGED": {
        "category": "PARK",
        "icon": "🅿️",
        "template": "Capital parked in Aave V3. Earning {apy:.1f}% APY while waiting."
    },
    "PARKING_WITHDRAWN": {
        "category": "PARK",
        "icon": "🚗",
        "template": "Capital unparked. Moving ${amount:.2f} to new opportunity."
    },
    "IDLE_CAPITAL": {
        "category": "PARK",
        "icon": "💤",
        "template": "No matching pools. {idle_hours:.0f}h until parking threshold ($5,000)."
    },
    
    # [ORACLE] - Price & Data Feeds
    "ORACLE_STALE": {
        "category": "ORACLE",
        "icon": "⏰",
        "template": "Oracle data stale ({age_seconds}s old). Waiting for fresh price."
    },
    "PRICE_DEVIATION": {
        "category": "ORACLE",
        "icon": "📊",
        "template": "Price deviation {deviation:.1f}% detected. Halting trades."
    },
    "TVL_DROP": {
        "category": "ORACLE",
        "icon": "📉",
        "template": "TVL dropped {drop_pct:.1f}%. Monitoring for rug risk."
    },
    
    # [ROTATION] - Strategy Execution
    "ROTATION_BLOCKED": {
        "category": "GUARD",
        "icon": "🔒",
        "template": "Rotation blocked: {reason}"
    },
    "ROTATION_EXECUTED": {
        "category": "GUARD",
        "icon": "✅",
        "template": "Rotation complete: Moved ${amount:.2f} to {protocol}"
    },
    "HARVEST_TRIGGERED": {
        "category": "GUARD",
        "icon": "🌾",
        "template": "Harvest triggered. Collected ${rewards:.2f} in rewards."
    }
}


def map_technical_to_friendly(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform technical audit log entry to user-friendly format.
    """
    action = entry.get("action", "UNKNOWN")
    details = entry.get("details", {})
    
    mapping = REASON_MAPPINGS.get(action, {
        "category": "INFO",
        "icon": "ℹ️",
        "template": action
    })
    
    # Format template with available data
    try:
        message = mapping["template"].format(**details)
    except (KeyError, ValueError):
        message = mapping["template"]
    
    # Determine severity color
    category = mapping["category"]
    if category == "SECURITY":
        color = "red"
        severity = "critical"
    elif category == "GUARD":
        color = "yellow"
        severity = "warning"
    elif category == "PARK":
        color = "cyan"
        severity = "info"
    else:
        color = "green"
        severity = "info"
    
    return {
        "id": entry.get("id"),
        "timestamp": entry.get("timestamp"),
        "category": f"[{category}]",
        "icon": mapping["icon"],
        "message": message,
        "color": color,
        "severity": severity,
        "raw_action": action,
        "details": details
    }


@router.get("/recent")
async def get_recent_audit(limit: int = Query(10, le=100)):
    """
    Get recent audit log entries.
    Returns empty list if no entries yet.
    """
    entries = _audit_entries[-limit:] if _audit_entries else []
    
    return {
        "entries": entries,
        "total": len(_audit_entries),
        "limit": limit
    }


@router.get("/reasoning-logs")
async def get_reasoning_logs(
    user_address: Optional[str] = None,
    limit: int = Query(10, le=50)
):
    """
    Get Agent reasoning logs for display in Reasoning Terminal.
    Returns user-friendly formatted decision logs.
    """
    # First try Supabase via REST API (no pip dependency)
    try:
        import requests
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if url and key:
            headers = {
                'apikey': key,
                'Authorization': f'Bearer {key}'
            }
            
            api_url = f"{url}/rest/v1/audit_trail?order=created_at.desc&limit={limit}"
            if user_address:
                api_url += f"&user_address=eq.{user_address}"
            
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data:
                    # Map Supabase entries to friendly format
                    formatted = []
                    for entry in data:
                        mapped = {
                            "id": entry.get("id"),
                            "timestamp": entry.get("created_at"),
                            "action": entry.get("action", entry.get("event_type", "UNKNOWN")),
                            "details": {
                                "gas_cost": entry.get("gas_cost", 0) or 0,
                                "risk_score": entry.get("risk_score", 0) or 0,
                                "reason": entry.get("reason", ""),
                                "amount": entry.get("amount_usd", 0) or 0,
                                "protocol": entry.get("protocol", ""),
                                "profit": entry.get("profit_usd", 0) or 0,
                                "apy": entry.get("apy", 0) or 0,
                            }
                        }
                        formatted.append(map_technical_to_friendly(mapped))
                    
                    return {
                        "logs": formatted,
                        "source": "supabase",
                        "count": len(formatted)
                    }
    except Exception as e:
        print(f"Supabase not available: {e}")
    
    # Fallback to in-memory
    entries = _audit_entries[-limit:]
    if user_address:
        entries = [e for e in entries if e.get("wallet") == user_address]
    
    formatted = [map_technical_to_friendly(e) for e in entries]
    
    return {
        "logs": formatted,
        "source": "memory",
        "count": len(formatted)
    }


@router.get("/export")
async def export_audit(wallet: Optional[str] = None):
    """
    Export audit log for a wallet.
    """
    if wallet and wallet != 'all':
        filtered = [e for e in _audit_entries if e.get("wallet") == wallet]
    else:
        filtered = _audit_entries
    
    return {
        "entries": filtered,
        "wallet": wallet,
        "exported_at": datetime.now().isoformat()
    }


def log_audit_entry(
    action: str,
    wallet: str = None,
    details: dict = None,
    status: str = "success"
):
    """
    Add an entry to the audit log.
    Call this from other modules to record actions.
    """
    entry = {
        "id": len(_audit_entries) + 1,
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "wallet": wallet,
        "details": details or {},
        "status": status
    }
    _audit_entries.append(entry)
    
    # Keep only last 1000 entries
    if len(_audit_entries) > 1000:
        _audit_entries.pop(0)
    
    return entry


# Add some demo entries for testing
def _add_demo_entries():
    """Add demo entries to showcase Reasoning Terminal"""
    demos = [
        {"action": "PROFITABILITY_GATE", "details": {"gas_cost": 11.50, "profit": 8.20}},
        {"action": "SCAM_DETECTED", "details": {"risk_score": 85}},
        {"action": "PARKING_ENGAGED", "details": {"apy": 3.5}},
        {"action": "GAS_TOO_HIGH", "details": {"gas_cost": 45.00}},
        {"action": "ROTATION_BLOCKED", "details": {"reason": "APY below threshold"}},
    ]
    for demo in demos:
        log_audit_entry(demo["action"], wallet="demo", details=demo["details"])

# Uncomment to add demo data:
# _add_demo_entries()

