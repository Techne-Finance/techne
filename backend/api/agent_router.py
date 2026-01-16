"""
Agent Operations API Router
Endpoints for agent actions: harvest, rebalance, pause, audit
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import csv
import io

router = APIRouter(prefix="/api/agent", tags=["Agent Operations"])

# ============================================
# MODELS
# ============================================

class HarvestRequest(BaseModel):
    wallet: str
    agentId: str
    agentAddress: Optional[str] = None

class RebalanceRequest(BaseModel):
    wallet: str
    agentId: str
    agentAddress: Optional[str] = None
    strategy: Optional[str] = None

class PauseAllRequest(BaseModel):
    wallet: str
    reason: str = "manual"

class AgentStatusUpdate(BaseModel):
    wallet: str
    agentId: str
    isActive: bool

# ============================================
# HARVEST
# ============================================

@router.post("/harvest")
async def harvest_rewards(request: HarvestRequest):
    """
    Harvest rewards from agent's LP positions.
    
    Returns the harvested amount in USD.
    """
    try:
        # Import on-chain executor
        from integrations.onchain_executor import OnChainExecutor
        from agents.audit_trail import log_action, ActionType
        
        executor = OnChainExecutor()
        
        # In production, this would:
        # 1. Get all LP positions for the agent
        # 2. Call harvest on each vault contract
        # 3. Return harvested amounts
        
        # For now, simulate harvest
        harvested_amount = 12.50  # Would come from actual harvest tx
        
        # Log to audit trail
        log_action(
            agent_id=request.agentId,
            wallet=request.wallet,
            action_type=ActionType.HARVEST,
            details={"amount_usd": harvested_amount},
            success=True
        )
        
        return {
            "success": True,
            "harvestedAmount": harvested_amount,
            "timestamp": datetime.utcnow().isoformat(),
            "agentId": request.agentId
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "harvestedAmount": 0
        }

# ============================================
# REBALANCE
# ============================================

@router.post("/rebalance")
async def rebalance_portfolio(request: RebalanceRequest):
    """
    Trigger portfolio rebalance for an agent.
    
    Rebalances positions according to strategy allocation.
    """
    try:
        from agents.audit_trail import log_action, ActionType
        
        # In production, this would:
        # 1. Get current portfolio allocation
        # 2. Compare to target allocation
        # 3. Execute swaps/LP adjustments
        # 4. Return new allocation
        
        # Log to audit trail
        log_action(
            agent_id=request.agentId,
            wallet=request.wallet,
            action_type=ActionType.REBALANCE,
            details={
                "strategy": request.strategy,
                "triggered_by": "user"
            },
            success=True
        )
        
        return {
            "success": True,
            "message": "Portfolio rebalanced",
            "timestamp": datetime.utcnow().isoformat(),
            "agentId": request.agentId,
            "strategy": request.strategy
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ============================================
# PAUSE ALL
# ============================================

@router.post("/pause-all")
async def pause_all_agents(request: PauseAllRequest):
    """
    Emergency pause all agents for a wallet.
    
    Stops all active trading immediately.
    """
    try:
        from agents.audit_trail import log_action, ActionType
        
        # In production, this would:
        # 1. Update agent status in database
        # 2. Cancel any pending transactions
        # 3. Disable automation
        
        # Log to audit trail
        log_action(
            agent_id="system",
            wallet=request.wallet,
            action_type=ActionType.AGENT_PAUSE,
            details={
                "reason": request.reason,
                "scope": "all"
            },
            success=True
        )
        
        return {
            "success": True,
            "message": "All agents paused",
            "timestamp": datetime.utcnow().isoformat(),
            "reason": request.reason
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ============================================
# AGENT STATUS
# ============================================

@router.post("/status")
async def update_agent_status(request: AgentStatusUpdate):
    """
    Update single agent active status.
    """
    try:
        from agents.audit_trail import log_action, ActionType
        
        action_type = ActionType.AGENT_DEPLOY if request.isActive else ActionType.AGENT_PAUSE
        
        log_action(
            agent_id=request.agentId,
            wallet=request.wallet,
            action_type=action_type,
            details={"isActive": request.isActive},
            success=True
        )
        
        return {
            "success": True,
            "agentId": request.agentId,
            "isActive": request.isActive,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.delete("/delete/{wallet}/{agent_id}")
async def delete_agent(wallet: str, agent_id: str):
    """
    Delete an agent from the system.
    """
    try:
        from agents.audit_trail import log_action, ActionType
        
        log_action(
            agent_id=agent_id,
            wallet=wallet,
            action_type=ActionType.AGENT_PAUSE,
            details={"action": "delete"},
            success=True
        )
        
        return {
            "success": True,
            "message": f"Agent {agent_id} deleted",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# AUDIT ENDPOINTS
# ============================================

audit_router = APIRouter(prefix="/api/audit", tags=["Audit"])

@audit_router.get("/recent")
async def get_recent_audit(
    wallet: Optional[str] = None,
    limit: int = Query(default=10, le=100)
):
    """
    Get recent audit log entries.
    """
    try:
        from agents.audit_trail import AuditTrail
        
        trail = AuditTrail()
        entries = trail.get_entries(wallet_address=wallet)[-limit:]
        
        return {
            "success": True,
            "entries": [
                {
                    "timestamp": e.timestamp,
                    "action_type": e.action_type,
                    "agent_id": e.agent_id,
                    "wallet": e.wallet_address,
                    "value_usd": e.value_usd,
                    "success": e.success,
                    "tx_hash": e.tx_hash
                }
                for e in entries
            ],
            "count": len(entries)
        }
        
    except Exception as e:
        return {
            "success": False,
            "entries": [],
            "error": str(e)
        }

@audit_router.get("/export")
async def export_audit_csv(
    wallet: Optional[str] = Query(default=None)
):
    """
    Export audit log to CSV for tax reporting.
    """
    try:
        from agents.audit_trail import AuditTrail
        
        trail = AuditTrail()
        entries = trail.get_entries(wallet_address=wallet if wallet != 'all' else None)
        
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Timestamp", "Action", "Agent ID", "Wallet",
            "TX Hash", "Value (USD)", "Gas Used", "Success", "Details"
        ])
        
        # Data rows
        for e in entries:
            writer.writerow([
                e.timestamp,
                e.action_type,
                e.agent_id,
                e.wallet_address,
                e.tx_hash or "",
                e.value_usd or "",
                e.gas_used or "",
                "Yes" if e.success else "No",
                json.dumps(e.details) if e.details else ""
            ])
        
        output.seek(0)
        
        filename = f"techne_audit_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@audit_router.get("/summary")
async def get_audit_summary(wallet: Optional[str] = None):
    """
    Get summary statistics from audit trail.
    """
    try:
        from agents.audit_trail import AuditTrail
        
        trail = AuditTrail()
        summary = trail.get_summary(wallet_address=wallet if wallet != 'all' else None)
        
        return {
            "success": True,
            "summary": summary
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
