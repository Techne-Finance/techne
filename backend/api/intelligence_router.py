"""
Intelligence API Router
Endpoints for AI predictions, recommendations, and learning
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

router = APIRouter(prefix="/api/intelligence", tags=["Intelligence"])


# Lazy import to avoid circular dependencies
def get_intelligence():
    from agents.intelligence_engine import intelligence
    return intelligence


# ============================================
# MODELS
# ============================================

class PoolPredictionRequest(BaseModel):
    pool_id: str
    project: str
    chain: str
    apy: float
    tvlUsd: float
    risk_level: Optional[str] = "medium"


class OutcomeRecordRequest(BaseModel):
    pool_id: str
    protocol: str
    chain: str
    entry_apy: float
    exit_apy: float
    actual_return: float
    expected_return: float
    duration_days: int
    outcome: str  # success, failure, neutral


class UserPreferenceUpdate(BaseModel):
    user_id: str
    key: str
    value: Any


class RecommendationRequest(BaseModel):
    user_id: str
    pools: List[Dict]
    limit: int = 10


class AgentInsightRequest(BaseModel):
    source_agent: str
    insight_type: str
    content: Dict


# ============================================
# PREDICTION ENDPOINTS
# ============================================

@router.post("/predict/pool")
async def predict_pool(request: PoolPredictionRequest):
    """
    Get AI predictions for a pool.
    
    Returns APY sustainability and protocol safety predictions.
    """
    try:
        intel = get_intelligence()
        
        pool = {
            "pool": request.pool_id,
            "project": request.project,
            "chain": request.chain,
            "apy": request.apy,
            "tvlUsd": request.tvlUsd,
            "risk_level": request.risk_level
        }
        
        predictions = intel.get_predictions(pool)
        
        return {
            "success": True,
            "predictions": predictions,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predict/protocol/{protocol}")
async def predict_protocol_safety(protocol: str):
    """
    Get safety prediction for a protocol.
    
    Based on historical success/failure data.
    """
    try:
        intel = get_intelligence()
        trust = intel.get_protocol_trust(protocol)
        
        prediction = intel.prediction_engine.predict_protocol_safety(protocol, trust)
        
        return {
            "success": True,
            "prediction": prediction,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# LEARNING ENDPOINTS
# ============================================

@router.post("/learn/outcome")
async def record_outcome(request: OutcomeRecordRequest):
    """
    Record a pool outcome for learning.
    
    This updates protocol trust scores and memory.
    """
    try:
        from agents.intelligence_engine import PoolOutcome, OutcomeType
        
        intel = get_intelligence()
        
        outcome = PoolOutcome(
            pool_id=request.pool_id,
            protocol=request.protocol,
            chain=request.chain,
            entry_apy=request.entry_apy,
            exit_apy=request.exit_apy,
            actual_return=request.actual_return,
            expected_return=request.expected_return,
            duration_days=request.duration_days,
            outcome=OutcomeType(request.outcome)
        )
        
        intel.record_outcome(outcome)
        
        # Return updated trust score
        trust = intel.get_protocol_trust(request.protocol)
        
        return {
            "success": True,
            "message": f"Recorded {request.outcome} outcome",
            "protocol_trust_updated": trust.trust_score if trust else None,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learn/action")
async def learn_from_action(user_id: str, action: str, context: Dict = None):
    """
    Learn from user action to improve personalization.
    
    Actions: deposit, withdraw, avoid_pool, favorite_pool
    """
    try:
        intel = get_intelligence()
        intel.learn_from_user_action(user_id, action, context or {})
        
        return {
            "success": True,
            "message": f"Learned from action: {action}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# RECOMMENDATION ENDPOINTS
# ============================================

@router.post("/recommendations")
async def get_recommendations(request: RecommendationRequest):
    """
    Get personalized pool recommendations for a user.
    
    Takes user preferences and historical learning into account.
    """
    try:
        intel = get_intelligence()
        
        recommendations = intel.get_recommendations(
            user_id=request.user_id,
            available_pools=request.pools,
            limit=request.limit
        )
        
        return {
            "success": True,
            "recommendations": recommendations,
            "count": len(recommendations),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# USER PREFERENCE ENDPOINTS
# ============================================

@router.get("/preferences/{user_id}")
async def get_user_preferences(user_id: str):
    """Get user's learned preferences"""
    try:
        intel = get_intelligence()
        prefs = intel.get_user_preferences(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "preferences": prefs,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preferences")
async def update_user_preference(request: UserPreferenceUpdate):
    """Update a user preference"""
    try:
        intel = get_intelligence()
        intel.update_user_preference(request.user_id, request.key, request.value)
        
        return {
            "success": True,
            "message": f"Updated preference: {request.key}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# CROSS-AGENT ENDPOINTS
# ============================================

@router.post("/insights/share")
async def share_agent_insight(request: AgentInsightRequest):
    """
    Share insight between agents.
    
    Enables cross-agent learning and collaboration.
    """
    try:
        intel = get_intelligence()
        intel.share_insight(
            source_agent=request.source_agent,
            insight_type=request.insight_type,
            content=request.content
        )
        
        return {
            "success": True,
            "message": f"Insight shared from {request.source_agent}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights")
async def get_agent_insights(agent: str = "system", limit: int = 50):
    """Get insights from other agents"""
    try:
        intel = get_intelligence()
        insights = intel.get_agent_insights(agent, limit=limit)
        
        return {
            "success": True,
            "insights": [m.to_dict() for m in insights],
            "count": len(insights),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# STATS ENDPOINTS
# ============================================

@router.get("/stats")
async def get_intelligence_stats():
    """Get intelligence engine statistics"""
    try:
        intel = get_intelligence()
        stats = intel.get_stats()
        
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/protocols")
async def get_protocol_rankings():
    """Get all tracked protocols with trust scores"""
    try:
        intel = get_intelligence()
        
        protocols = []
        for name, trust in intel.protocol_trust.items():
            protocols.append({
                "protocol": name,
                "trust_score": trust.trust_score,
                "success_count": trust.success_count,
                "failure_count": trust.failure_count,
                "success_rate": trust.success_count / max(trust.success_count + trust.failure_count, 1),
                "last_updated": trust.last_updated.isoformat()
            })
        
        # Sort by trust score
        protocols.sort(key=lambda p: p["trust_score"], reverse=True)
        
        return {
            "success": True,
            "protocols": protocols,
            "count": len(protocols),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
