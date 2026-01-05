"""
Memory API Router for Techne Finance
Exposes memory engine functionality via REST API
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
import logging

from agents.memory_engine import (
    memory_engine, 
    MemoryType, 
    MemoryTier,
    record_success,
    record_failure
)

logger = logging.getLogger("MemoryRouter")

router = APIRouter(prefix="/api/memory", tags=["Agent Memory"])


@router.get("/stats")
async def get_memory_stats(user_id: str = Query("default", description="User ID")):
    """Get memory statistics for a user"""
    try:
        stats = await memory_engine.get_stats(user_id)
        return {
            "success": True,
            "user_id": user_id,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recall")
async def recall_memories(
    query: Optional[str] = Query(None, description="Search query"),
    memory_type: Optional[str] = Query(None, description="Memory type filter"),
    user_id: str = Query("default", description="User ID"),
    limit: int = Query(10, description="Max results")
):
    """Recall memories matching query"""
    try:
        mem_type = MemoryType(memory_type) if memory_type else None
        memories = await memory_engine.recall(
            query=query,
            memory_type=mem_type,
            user_id=user_id,
            limit=limit
        )
        
        return {
            "success": True,
            "count": len(memories),
            "memories": [
                {
                    "id": m.id,
                    "tier": m.tier.value,
                    "type": m.memory_type.value,
                    "content": m.content,
                    "score": m.score,
                    "created_at": m.created_at.isoformat(),
                    "tags": m.tags
                }
                for m in memories
            ]
        }
    except Exception as e:
        logger.error(f"Error recalling memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/store")
async def store_memory(
    memory_type: str = Query(..., description="Memory type"),
    content: str = Query(..., description="Memory content (JSON)"),
    user_id: str = Query("default", description="User ID"),
    tags: Optional[str] = Query(None, description="Comma-separated tags")
):
    """Store a new memory"""
    try:
        import json
        content_dict = json.loads(content)
        tag_list = tags.split(",") if tags else []
        
        memory = await memory_engine.store(
            memory_type=MemoryType(memory_type),
            content=content_dict,
            user_id=user_id,
            tags=tag_list
        )
        
        return {
            "success": True,
            "memory_id": memory.id,
            "score": memory.score
        }
    except Exception as e:
        logger.error(f"Error storing memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outcome/{memory_id}")
async def record_outcome(
    memory_id: str,
    success: bool = Query(..., description="Was the memory helpful?")
):
    """Record outcome for a memory (the key to learning!)"""
    try:
        if success:
            new_score = await record_success(memory_id)
        else:
            new_score = await record_failure(memory_id)
        
        return {
            "success": True,
            "memory_id": memory_id,
            "outcome": "success" if success else "failure",
            "new_score": new_score
        }
    except Exception as e:
        logger.error(f"Error recording outcome: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/protocols/best")
async def get_best_protocols(
    user_id: str = Query("default", description="User ID"),
    chain: Optional[str] = Query(None, description="Filter by chain"),
    limit: int = Query(5, description="Max results")
):
    """Get highest-scoring protocols from memory"""
    try:
        protocols = await memory_engine.get_best_protocols(
            user_id=user_id,
            chain=chain,
            limit=limit
        )
        
        return {
            "success": True,
            "count": len(protocols),
            "protocols": protocols
        }
    except Exception as e:
        logger.error(f"Error getting best protocols: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preferences")
async def get_preferences(user_id: str = Query("default", description="User ID")):
    """Get all user preferences"""
    try:
        prefs = await memory_engine.get_user_preferences(user_id)
        return {
            "success": True,
            "user_id": user_id,
            "preferences": prefs
        }
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preferences")
async def set_preference(
    key: str = Query(..., description="Preference key"),
    value: str = Query(..., description="Preference value"),
    user_id: str = Query("default", description="User ID")
):
    """Set a user preference"""
    try:
        memory = await memory_engine.store_user_preference(
            preference_key=key,
            preference_value=value,
            user_id=user_id
        )
        
        return {
            "success": True,
            "key": key,
            "value": value
        }
    except Exception as e:
        logger.error(f"Error setting preference: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk-profile")
async def get_risk_profile(user_id: str = Query("default", description="User ID")):
    """Get learned risk profile for a user"""
    try:
        profile = await memory_engine.get_learned_risk_profile(user_id)
        return {
            "success": True,
            "user_id": user_id,
            "profile": profile
        }
    except Exception as e:
        logger.error(f"Error getting risk profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pool-outcome")
async def store_pool_outcome(
    pool_id: str = Query(..., description="Pool ID"),
    project: str = Query(..., description="Protocol name"),
    chain: str = Query(..., description="Chain"),
    predicted_apy: float = Query(..., description="Predicted APY"),
    actual_apy: float = Query(..., description="Actual APY"),
    profit_loss: float = Query(..., description="Profit/loss amount"),
    user_id: str = Query("default", description="User ID")
):
    """Store pool investment outcome"""
    try:
        memory = await memory_engine.store_pool_outcome(
            pool_id=pool_id,
            project=project,
            chain=chain,
            predicted_apy=predicted_apy,
            actual_apy=actual_apy,
            profit_loss=profit_loss,
            user_id=user_id
        )
        
        return {
            "success": True,
            "memory_id": memory.id,
            "profitable": profit_loss > 0,
            "score": memory.score
        }
    except Exception as e:
        logger.error(f"Error storing pool outcome: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_expired():
    """Clean up expired memories"""
    try:
        deleted = await memory_engine.cleanup_expired()
        return {
            "success": True,
            "deleted_count": deleted
        }
    except Exception as e:
        logger.error(f"Error cleaning up: {e}")
        raise HTTPException(status_code=500, detail=str(e))
