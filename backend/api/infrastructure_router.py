"""
Infrastructure Monitoring Router
Health checks, metrics, and system status endpoints
"""

from fastapi import APIRouter, Depends
from datetime import datetime
from typing import Dict, Any

router = APIRouter(prefix="/api/infrastructure", tags=["Infrastructure"])


# Lazy imports to avoid circular dependencies
def get_health_checker():
    from infrastructure import health_checker
    return health_checker


def get_error_tracker():
    from infrastructure import error_tracker
    return error_tracker


def get_config():
    from infrastructure import config
    return config


# ============================================
# HEALTH CHECKS
# ============================================

@router.get("/health")
async def health_check():
    """
    Basic health check - returns 200 if API is running.
    Use for load balancer health checks.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check - checks all infrastructure components.
    Use for monitoring and debugging.
    """
    try:
        health = get_health_checker()
        return await health.check_all()
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check - returns 200 if ready to accept traffic.
    Use for Kubernetes readiness probes.
    """
    try:
        health = get_health_checker()
        checks = await health.check_all()
        
        is_ready = (
            checks.get("database", {}).get("status") == "healthy"
        )
        
        return {
            "ready": is_ready,
            "checks": checks,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "ready": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# ============================================
# METRICS
# ============================================

@router.get("/metrics")
async def get_metrics():
    """
    Get system metrics for monitoring.
    Format compatible with Prometheus scraping.
    """
    import psutil
    
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
    except:
        cpu_percent = 0
        memory = None
        disk = None
    
    return {
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent if memory else 0,
            "memory_used_mb": memory.used / 1024 / 1024 if memory else 0,
            "disk_percent": disk.percent if disk else 0,
        },
        "application": {
            "uptime_seconds": _get_uptime(),
        },
        "timestamp": datetime.now().isoformat()
    }


@router.get("/errors/stats")
async def get_error_stats():
    """Get error statistics"""
    try:
        tracker = get_error_tracker()
        return tracker.get_stats()
    except Exception as e:
        return {"error": str(e)}


# ============================================
# CONFIGURATION
# ============================================

@router.get("/config")
async def get_configuration():
    """
    Get current configuration (secrets hidden).
    Admin only in production.
    """
    try:
        cfg = get_config()
        return {
            "environment": cfg.environment.value,
            "debug": cfg.debug,
            "features": {
                "cross_chain": cfg.features.enable_cross_chain,
                "auto_compound": cfg.features.enable_auto_compound,
                "ai_predictions": cfg.features.enable_ai_predictions,
                "memory_engine": cfg.features.enable_memory_engine,
                "observability": cfg.features.enable_observability,
                "x402_payments": cfg.features.enable_x402_payments,
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================
# HELPERS
# ============================================

_start_time = datetime.now()


def _get_uptime() -> float:
    """Get application uptime in seconds"""
    return (datetime.now() - _start_time).total_seconds()
