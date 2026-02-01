"""
ERC-8004 API Router
Agent identity and reputation endpoints

Endpoints:
- GET /api/agent-profile/{smart_account} - Get full identity + reputation
- GET /api/agent-reputation/{token_id} - Get reputation by token ID
- GET /api/agent-trust-score/{smart_account} - Get trust score only
- POST /api/agent-report-execution - Manually report execution (admin)
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger("ERC8004Router")

router = APIRouter(prefix="/api", tags=["ERC-8004"])


class ExecutionReport(BaseModel):
    """Request body for manual execution report"""
    token_id: int
    success: bool
    value_usd: float
    profit_usd: float = 0.0
    execution_type: str = "trade"


class AgentProfileResponse(BaseModel):
    """Agent profile response"""
    token_id: Optional[int] = None
    identity: Optional[dict] = None
    reputation: Optional[dict] = None


@router.get("/agent-profile/{smart_account}")
async def get_agent_profile(smart_account: str) -> AgentProfileResponse:
    """
    Get full ERC-8004 agent profile including identity and reputation.
    
    Args:
        smart_account: The smart account address
        
    Returns:
        Combined identity and reputation data
    """
    try:
        from services.reputation_service import get_agent_profile as fetch_profile
        
        profile = await fetch_profile(smart_account)
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail="No ERC-8004 identity found for this address"
            )
        
        return AgentProfileResponse(
            token_id=profile.get("token_id"),
            identity=profile.get("identity"),
            reputation=profile.get("reputation")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-reputation/{token_id}")
async def get_agent_reputation(token_id: int):
    """
    Get reputation metrics for an agent by token ID.
    
    Args:
        token_id: The ERC-8004 identity token ID
        
    Returns:
        Reputation metrics
    """
    try:
        from services.reputation_service import get_reputation_service
        
        service = get_reputation_service()
        reputation = await service.get_reputation(token_id)
        
        if not reputation:
            raise HTTPException(
                status_code=404,
                detail="No reputation found for this token ID"
            )
        
        return reputation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get reputation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-trust-score/{smart_account}")
async def get_trust_score(smart_account: str):
    """
    Get trust score for an agent by smart account address.
    Quick endpoint for UIs that just need the score.
    
    Args:
        smart_account: The smart account address
        
    Returns:
        Trust score (0-100)
    """
    try:
        from services.reputation_service import get_reputation_service
        
        service = get_reputation_service()
        
        token_id = await service.get_token_id_for_account(smart_account)
        if token_id is None:
            return {"trust_score": 0.0, "registered": False}
        
        trust_score = await service.get_trust_score(token_id)
        success_rate = await service.get_success_rate(token_id)
        
        return {
            "trust_score": trust_score,
            "success_rate": success_rate,
            "token_id": token_id,
            "registered": True
        }
        
    except Exception as e:
        logger.error(f"Failed to get trust score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-identity/{smart_account}")
async def get_agent_identity(smart_account: str):
    """
    Get just the identity data for an agent.
    
    Args:
        smart_account: The smart account address
        
    Returns:
        Identity struct
    """
    try:
        from services.reputation_service import get_reputation_service
        
        service = get_reputation_service()
        identity = await service.get_agent_identity(smart_account)
        
        if not identity:
            raise HTTPException(
                status_code=404,
                detail="No identity found for this address"
            )
        
        return identity
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get identity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent-report-execution")
async def report_execution(report: ExecutionReport):
    """
    Manually report an execution to the reputation registry.
    Admin endpoint for testing or manual corrections.
    
    Args:
        report: Execution report details
        
    Returns:
        Transaction hash if successful
    """
    try:
        from services.reputation_service import report_execution as do_report
        
        tx_hash = await do_report(
            token_id=report.token_id,
            success=report.success,
            value_usd=report.value_usd,
            profit_usd=report.profit_usd,
            execution_type=report.execution_type
        )
        
        if not tx_hash:
            raise HTTPException(
                status_code=500,
                detail="Failed to submit transaction - check reporter key config"
            )
        
        return {
            "success": True,
            "tx_hash": tx_hash,
            "token_id": report.token_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to report execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/erc8004-stats")
async def get_erc8004_stats():
    """
    Get overall ERC-8004 statistics for the platform.
    
    Returns:
        Platform-wide stats
    """
    # This would query contract for total stats
    # For now, return placeholder
    return {
        "total_agents": 0,
        "total_executions": 0,
        "total_value_managed_usd": 0.0,
        "average_trust_score": 0.0,
        "contracts": {
            "identity_registry": "",
            "reputation_registry": "",
            "factory_v4": ""
        }
    }
