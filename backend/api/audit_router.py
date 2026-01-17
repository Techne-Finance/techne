"""
Audit Router - Transaction history and audit logs
"""

from fastapi import APIRouter, Query
from datetime import datetime
from typing import List, Optional

router = APIRouter(prefix="/api/audit", tags=["Audit"])


# In-memory audit log (in production, use database)
_audit_entries = []


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
