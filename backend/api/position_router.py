"""
Position Router - API endpoints for position tracking and alerts
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict
import logging

logger = logging.getLogger("PositionRouter")

router = APIRouter(prefix="/api/positions", tags=["Positions"])


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class AddPositionRequest(BaseModel):
    user_id: str
    pool_address: str
    chain: str = "base"
    protocol: str
    symbol: str
    pool_type: str = "lp"
    deposit_amount_usd: float
    current_apy: float
    current_tvl: float
    alert_thresholds: Optional[Dict] = None


class PositionResponse(BaseModel):
    id: str
    user_id: str
    pool_address: str
    chain: str
    protocol: str
    symbol: str
    pool_type: str
    deposit_amount_usd: float
    deposit_timestamp: int
    initial_apy: float
    initial_tvl: float
    current_apy: float
    current_tvl: float
    unclaimed_rewards_usd: float
    apy_change_pct: float
    tvl_change_pct: float


class AlertResponse(BaseModel):
    id: str
    position_id: str
    alert_type: str
    severity: str
    title: str
    message: str
    data: Dict
    created_at: int
    read: bool


class UpdateThresholdsRequest(BaseModel):
    apy_drop_pct: Optional[float] = None
    tvl_drop_pct: Optional[float] = None
    epoch_hours: Optional[float] = None
    harvest_usd: Optional[float] = None


# ============================================
# ENDPOINTS
# ============================================

@router.post("/add", response_model=PositionResponse)
async def add_position(request: AddPositionRequest):
    """
    Add a new position to track.
    Called after user deposits into a pool/vault.
    """
    from agents.position_tracker import position_tracker
    
    try:
        await position_tracker.initialize()
        
        position = await position_tracker.add_position(
            user_id=request.user_id,
            pool_address=request.pool_address,
            chain=request.chain,
            protocol=request.protocol,
            symbol=request.symbol,
            pool_type=request.pool_type,
            deposit_amount_usd=request.deposit_amount_usd,
            current_apy=request.current_apy,
            current_tvl=request.current_tvl,
            alert_thresholds=request.alert_thresholds
        )
        
        return PositionResponse(
            id=position.id,
            user_id=position.user_id,
            pool_address=position.pool_address,
            chain=position.chain,
            protocol=position.protocol,
            symbol=position.symbol,
            pool_type=position.pool_type,
            deposit_amount_usd=position.deposit_amount_usd,
            deposit_timestamp=position.deposit_timestamp,
            initial_apy=position.initial_apy,
            initial_tvl=position.initial_tvl,
            current_apy=position.current_apy,
            current_tvl=position.current_tvl,
            unclaimed_rewards_usd=0,
            apy_change_pct=0,
            tvl_change_pct=0
        )
        
    except Exception as e:
        logger.error(f"Failed to add position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}", response_model=List[PositionResponse])
async def get_user_positions(
    user_id: str,
    status: str = Query("active", description="Filter by status: active, closed, all")
):
    """Get all positions for a user"""
    from agents.position_tracker import position_tracker
    
    try:
        await position_tracker.initialize()
        positions = await position_tracker.get_user_positions(user_id, status)
        
        results = []
        for p in positions:
            # Calculate changes
            apy_change = ((p.current_apy - p.initial_apy) / p.initial_apy * 100) if p.initial_apy > 0 else 0
            tvl_change = ((p.current_tvl - p.initial_tvl) / p.initial_tvl * 100) if p.initial_tvl > 0 else 0
            
            results.append(PositionResponse(
                id=p.id,
                user_id=p.user_id,
                pool_address=p.pool_address,
                chain=p.chain,
                protocol=p.protocol,
                symbol=p.symbol,
                pool_type=p.pool_type,
                deposit_amount_usd=p.deposit_amount_usd,
                deposit_timestamp=p.deposit_timestamp,
                initial_apy=p.initial_apy,
                initial_tvl=p.initial_tvl,
                current_apy=p.current_apy,
                current_tvl=p.current_tvl,
                unclaimed_rewards_usd=p.unclaimed_rewards_usd,
                apy_change_pct=round(apy_change, 1),
                tvl_change_pct=round(tvl_change, 1)
            ))
        
        return results
        
    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{position_id}/close")
async def close_position(position_id: str):
    """Mark a position as closed (withdrawn)"""
    from agents.position_tracker import position_tracker
    
    try:
        await position_tracker.initialize()
        await position_tracker.close_position(position_id)
        return {"success": True, "message": "Position closed"}
        
    except Exception as e:
        logger.error(f"Failed to close position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{position_id}/check")
async def check_position_now(position_id: str):
    """Manually trigger a position check"""
    from agents.position_tracker import position_tracker
    
    try:
        await position_tracker.initialize()
        
        # Get position
        cursor = await position_tracker._db.execute(
            "SELECT * FROM positions WHERE id = ?", (position_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Position not found")
        
        from agents.position_tracker import Position
        import json
        
        position = Position(
            id=row["id"],
            user_id=row["user_id"],
            pool_address=row["pool_address"],
            chain=row["chain"],
            protocol=row["protocol"],
            symbol=row["symbol"],
            pool_type=row["pool_type"],
            deposit_amount_usd=row["deposit_amount_usd"],
            deposit_timestamp=row["deposit_timestamp"],
            initial_apy=row["initial_apy"],
            initial_tvl=row["initial_tvl"],
            current_apy=row["current_apy"],
            current_tvl=row["current_tvl"],
            alerts_enabled=bool(row["alerts_enabled"]),
            alert_thresholds=json.loads(row["alert_thresholds"]) if row["alert_thresholds"] else None
        )
        
        alerts = await position_tracker.check_position(position)
        
        return {
            "success": True,
            "alerts_generated": len(alerts),
            "alerts": [{"title": a.title, "severity": a.severity.value} for a in alerts]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{position_id}/thresholds")
async def update_alert_thresholds(position_id: str, request: UpdateThresholdsRequest):
    """Update alert thresholds for a position"""
    from agents.position_tracker import position_tracker
    import json
    
    try:
        await position_tracker.initialize()
        
        # Get current thresholds
        cursor = await position_tracker._db.execute(
            "SELECT alert_thresholds FROM positions WHERE id = ?", (position_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Position not found")
        
        current = json.loads(row["alert_thresholds"]) if row["alert_thresholds"] else {}
        
        # Update with new values
        if request.apy_drop_pct is not None:
            current["apy_drop_pct"] = request.apy_drop_pct
        if request.tvl_drop_pct is not None:
            current["tvl_drop_pct"] = request.tvl_drop_pct
        if request.epoch_hours is not None:
            current["epoch_hours"] = request.epoch_hours
        if request.harvest_usd is not None:
            current["harvest_usd"] = request.harvest_usd
        
        await position_tracker._db.execute(
            "UPDATE positions SET alert_thresholds = ? WHERE id = ?",
            (json.dumps(current), position_id)
        )
        await position_tracker._db.commit()
        
        return {"success": True, "thresholds": current}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update thresholds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ALERTS ENDPOINTS
# ============================================

@router.get("/alerts/{user_id}", response_model=List[AlertResponse])
async def get_user_alerts(
    user_id: str,
    unread_only: bool = Query(False, description="Only return unread alerts"),
    limit: int = Query(50, description="Max alerts to return")
):
    """Get alerts for a user"""
    from agents.position_tracker import position_tracker
    
    try:
        await position_tracker.initialize()
        alerts = await position_tracker.get_user_alerts(user_id, unread_only, limit)
        
        return [
            AlertResponse(
                id=a.id,
                position_id=a.position_id,
                alert_type=a.alert_type.value,
                severity=a.severity.value,
                title=a.title,
                message=a.message,
                data=a.data,
                created_at=a.created_at,
                read=a.read
            )
            for a in alerts
        ]
        
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: str):
    """Mark an alert as read"""
    from agents.position_tracker import position_tracker
    
    try:
        await position_tracker.initialize()
        await position_tracker.mark_alert_read(alert_id)
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Failed to mark alert read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/{user_id}/unread-count")
async def get_unread_count(user_id: str):
    """Get count of unread alerts"""
    from agents.position_tracker import position_tracker
    
    try:
        await position_tracker.initialize()
        
        cursor = await position_tracker._db.execute(
            "SELECT COUNT(*) as count FROM alerts WHERE user_id = ? AND read = 0",
            (user_id,)
        )
        row = await cursor.fetchone()
        
        return {"unread_count": row["count"] if row else 0}
        
    except Exception as e:
        logger.error(f"Failed to get unread count: {e}")
        raise HTTPException(status_code=500, detail=str(e))
