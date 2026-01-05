"""
Observability API Router for Techne Finance
Exposes agent tracing and metrics via REST API
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import logging

from agents.observability_engine import observability, SpanStatus

logger = logging.getLogger("ObservabilityRouter")

router = APIRouter(prefix="/api/observability", tags=["Agent Observability"])


@router.get("/dashboard")
async def get_dashboard():
    """Get aggregated dashboard data for all agents"""
    try:
        data = await observability.get_dashboard_data()
        return {"success": True, **data}
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent}/metrics")
async def get_agent_metrics(
    agent: str,
    hours: int = Query(24, description="Hours of data to fetch")
):
    """Get metrics for a specific agent"""
    try:
        metrics = await observability.get_agent_metrics(agent, hours)
        return {"success": True, **metrics}
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traces/{trace_id}")
async def get_trace_details(trace_id: str):
    """Get detailed view of a trace with all spans"""
    try:
        trace = await observability.get_trace_details(trace_id)
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")
        return {"success": True, "trace": trace}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trace details error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/traces/start")
async def start_trace(
    agent: str = Query(..., description="Agent name"),
    operation: str = Query(..., description="Operation name"),
    user_id: str = Query("default", description="User ID")
):
    """Start a new trace manually"""
    try:
        trace_id = observability.start_trace(agent, operation, user_id)
        return {"success": True, "trace_id": trace_id}
    except Exception as e:
        logger.error(f"Start trace error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/traces/{trace_id}/end")
async def end_trace(
    trace_id: str,
    success: bool = Query(True, description="Was the operation successful?")
):
    """End a trace"""
    try:
        status = SpanStatus.SUCCESS if success else SpanStatus.ERROR
        observability.end_trace(trace_id, status)
        return {"success": True, "trace_id": trace_id}
    except Exception as e:
        logger.error(f"End trace error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spans/start")
async def start_span(
    trace_id: str = Query(..., description="Parent trace ID"),
    agent: str = Query(..., description="Agent name"),
    operation: str = Query(..., description="Operation name"),
    parent_id: Optional[str] = Query(None, description="Parent span ID")
):
    """Start a new span within a trace"""
    try:
        span_id = observability.start_span(trace_id, agent, operation, parent_id)
        return {"success": True, "span_id": span_id}
    except Exception as e:
        logger.error(f"Start span error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spans/{span_id}/end")
async def end_span(
    span_id: str,
    success: bool = Query(True, description="Was the span successful?"),
    error: Optional[str] = Query(None, description="Error message if failed")
):
    """End a span"""
    try:
        status = SpanStatus.SUCCESS if success else SpanStatus.ERROR
        observability.end_span(span_id, status, error)
        return {"success": True, "span_id": span_id}
    except Exception as e:
        logger.error(f"End span error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events")
async def log_event(
    agent: str = Query(..., description="Agent name"),
    event_type: str = Query(..., description="Event type"),
    message: str = Query(..., description="Event message"),
    trace_id: Optional[str] = Query(None, description="Related trace ID"),
    level: str = Query("info", description="Log level")
):
    """Log a structured event"""
    try:
        observability.log_event(
            agent=agent,
            event_type=event_type,
            message=message,
            trace_id=trace_id,
            level=level
        )
        return {"success": True}
    except Exception as e:
        logger.error(f"Log event error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check for observability system"""
    try:
        # Quick test - get dashboard data
        data = await observability.get_dashboard_data()
        return {
            "success": True,
            "status": "healthy",
            "agents_tracked": len(data.get("agents", [])),
            "recent_traces": len(data.get("recent_traces", []))
        }
    except Exception as e:
        return {
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }
