"""
Agent Service Router - API endpoints for scalable agent management
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import logging

from services.agent_service import agent_service, AgentConfig

logger = logging.getLogger("AgentServiceRouter")
router = APIRouter(prefix="/api/agents", tags=["agents"])


# ==========================================
# Request/Response Models
# ==========================================

class CreateAgentRequest(BaseModel):
    user_address: str
    agent_address: str
    encrypted_private_key: str
    agent_name: Optional[str] = None
    chain: str = "base"
    preset: str = "balanced"
    pool_type: str = "single"
    risk_level: str = "moderate"
    min_apy: float = 5.0
    max_apy: float = 1000.0
    protocols: Optional[List[str]] = None
    preferred_assets: Optional[List[str]] = None
    is_pro_mode: bool = False


class UpdateAgentRequest(BaseModel):
    is_active: Optional[bool] = None
    status: Optional[str] = None
    min_apy: Optional[float] = None
    max_apy: Optional[float] = None
    risk_level: Optional[str] = None
    protocols: Optional[List[str]] = None
    preferred_assets: Optional[List[str]] = None
    settings: Optional[dict] = None


class RecordTransactionRequest(BaseModel):
    user_address: str
    agent_address: str
    tx_type: str
    token: str
    amount: float
    tx_hash: Optional[str] = None
    status: str = "completed"
    destination: Optional[str] = None
    pool_id: Optional[str] = None
    metadata: Optional[dict] = None


class CreatePositionRequest(BaseModel):
    agent_address: str
    user_address: str
    protocol: str
    pool_address: str
    pool_name: str
    entry_value_usd: float
    token0: Optional[str] = None
    token1: Optional[str] = None
    amount0: float = 0
    amount1: float = 0
    lp_tokens: float = 0
    apy: float = 0


# ==========================================
# Agent CRUD Endpoints
# ==========================================

@router.post("/create")
async def create_agent(request: CreateAgentRequest):
    """Create a new agent for user"""
    config = AgentConfig(
        chain=request.chain,
        preset=request.preset,
        pool_type=request.pool_type,
        risk_level=request.risk_level,
        min_apy=request.min_apy,
        max_apy=request.max_apy,
        protocols=request.protocols,
        preferred_assets=request.preferred_assets,
        is_pro_mode=request.is_pro_mode
    )
    
    result = await agent_service.create_agent(
        user_address=request.user_address,
        agent_address=request.agent_address,
        encrypted_private_key=request.encrypted_private_key,
        config=config,
        agent_name=request.agent_name
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/user/{user_address}")
async def get_user_agents(user_address: str):
    """Get all agents for a user"""
    agents = await agent_service.get_user_agents(user_address)
    return {
        "success": True,
        "user_address": user_address,
        "agents": agents,
        "count": len(agents)
    }


@router.get("/details/{agent_address}")
async def get_agent_details(agent_address: str):
    """Get single agent details"""
    agent = await agent_service.get_agent(agent_address)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Get additional data
    balances = await agent_service.get_agent_balances(agent_address)
    positions = await agent_service.get_agent_positions(agent_address)
    recent_txs = await agent_service.get_agent_transactions(agent_address, limit=10)
    
    return {
        "success": True,
        "agent": agent,
        "balances": balances,
        "positions": positions,
        "recent_transactions": recent_txs
    }


@router.put("/{agent_address}")
async def update_agent(agent_address: str, request: UpdateAgentRequest):
    """Update agent configuration"""
    updates = {k: v for k, v in request.dict().items() if v is not None}
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    success = await agent_service.update_agent(agent_address, updates)
    
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found or update failed")
    
    return {"success": True, "message": "Agent updated"}


@router.post("/{agent_address}/pause")
async def pause_agent(agent_address: str):
    """Pause agent (stop executing strategies)"""
    success = await agent_service.set_agent_status(agent_address, "paused", is_active=False)
    
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Log to audit
    agent = await agent_service.get_agent(agent_address)
    if agent:
        await agent_service.log_audit(
            agent_address=agent_address,
            user_address=agent["user_address"],
            action="pause",
            message="Agent paused by user",
            severity="warning"
        )
    
    return {"success": True, "message": "Agent paused"}


@router.post("/{agent_address}/resume")
async def resume_agent(agent_address: str):
    """Resume agent"""
    success = await agent_service.set_agent_status(agent_address, "active", is_active=True)
    
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Log to audit
    agent = await agent_service.get_agent(agent_address)
    if agent:
        await agent_service.log_audit(
            agent_address=agent_address,
            user_address=agent["user_address"],
            action="resume",
            message="Agent resumed by user",
            severity="success"
        )
    
    return {"success": True, "message": "Agent resumed"}


# ==========================================
# Transaction Endpoints
# ==========================================

@router.post("/transactions/record")
async def record_transaction(request: RecordTransactionRequest):
    """Record a transaction"""
    result = await agent_service.record_transaction(
        user_address=request.user_address,
        agent_address=request.agent_address,
        tx_type=request.tx_type,
        token=request.token,
        amount=request.amount,
        tx_hash=request.tx_hash,
        status=request.status,
        destination=request.destination,
        pool_id=request.pool_id,
        metadata=request.metadata
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/{agent_address}/transactions")
async def get_transactions(
    agent_address: str,
    limit: int = Query(50, ge=1, le=200),
    tx_type: Optional[str] = None
):
    """Get transaction history"""
    txs = await agent_service.get_agent_transactions(agent_address, limit, tx_type)
    return {
        "success": True,
        "agent_address": agent_address,
        "transactions": txs,
        "count": len(txs)
    }


# ==========================================
# Balance Endpoints
# ==========================================

@router.get("/{agent_address}/balances")
async def get_balances(agent_address: str):
    """Get agent balances"""
    balances = await agent_service.get_agent_balances(agent_address)
    return {
        "success": True,
        "agent_address": agent_address,
        "balances": balances
    }


@router.post("/{agent_address}/balances/sync")
async def sync_balances(agent_address: str):
    """Sync balances from blockchain (placeholder for on-chain sync)"""
    # TODO: Implement on-chain balance sync
    return {
        "success": True,
        "message": "Balance sync queued"
    }


# ==========================================
# Position Endpoints
# ==========================================

@router.post("/positions/create")
async def create_position(request: CreatePositionRequest):
    """Create a new position"""
    result = await agent_service.create_position(
        agent_address=request.agent_address,
        user_address=request.user_address,
        protocol=request.protocol,
        pool_address=request.pool_address,
        pool_name=request.pool_name,
        entry_value_usd=request.entry_value_usd,
        token0=request.token0,
        token1=request.token1,
        amount0=request.amount0,
        amount1=request.amount1,
        lp_tokens=request.lp_tokens,
        apy=request.apy
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/{agent_address}/positions")
async def get_positions(agent_address: str, status: str = "active"):
    """Get agent positions"""
    positions = await agent_service.get_agent_positions(agent_address, status)
    return {
        "success": True,
        "agent_address": agent_address,
        "positions": positions,
        "count": len(positions)
    }


@router.post("/positions/{position_id}/close")
async def close_position(position_id: int, exit_value_usd: Optional[float] = None):
    """Close a position"""
    success = await agent_service.close_position(position_id, exit_value_usd)
    
    if not success:
        raise HTTPException(status_code=404, detail="Position not found")
    
    return {"success": True, "message": "Position closed"}


# ==========================================
# Audit Trail Endpoints
# ==========================================

@router.get("/{agent_address}/audit")
async def get_audit_trail(
    agent_address: str,
    limit: int = Query(100, ge=1, le=500)
):
    """Get audit trail for agent"""
    entries = await agent_service.get_audit_trail(agent_address=agent_address, limit=limit)
    return {
        "success": True,
        "agent_address": agent_address,
        "audit_trail": entries,
        "count": len(entries)
    }


@router.get("/user/{user_address}/audit")
async def get_user_audit_trail(
    user_address: str,
    limit: int = Query(100, ge=1, le=500)
):
    """Get audit trail for all user's agents"""
    entries = await agent_service.get_audit_trail(user_address=user_address, limit=limit)
    return {
        "success": True,
        "user_address": user_address,
        "audit_trail": entries,
        "count": len(entries)
    }


# ==========================================
# Portfolio Summary
# ==========================================

@router.get("/user/{user_address}/summary")
async def get_portfolio_summary(user_address: str):
    """Get portfolio summary across all agents"""
    summary = await agent_service.get_user_portfolio_summary(user_address)
    return {
        "success": True,
        **summary
    }
