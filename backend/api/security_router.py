"""
Security API Router
Endpoints for API key management, rate limit status, and security configuration
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional, List, Set
from datetime import datetime

from security import (
    api_key_manager,
    rate_limiter,
    transaction_guard,
    input_validator,
)

router = APIRouter(prefix="/api/security", tags=["Security"])


# ============================================
# MODELS
# ============================================

class GenerateKeyRequest(BaseModel):
    user_id: str
    name: str
    permissions: Optional[List[str]] = ["read"]


class GenerateKeyResponse(BaseModel):
    api_key: str
    name: str
    permissions: List[str]
    message: str


class RateLimitStatus(BaseModel):
    ip: str
    is_blocked: bool
    is_whitelisted: bool
    requests_this_minute: int
    requests_this_hour: int
    limits: dict


class TransactionLimitStatus(BaseModel):
    user_id: str
    remaining_daily_usd: float
    remaining_tx_count: int
    max_per_tx_usd: float


# ============================================
# API KEY ENDPOINTS
# ============================================

@router.post("/keys/generate", response_model=GenerateKeyResponse)
async def generate_api_key(request: GenerateKeyRequest):
    """
    Generate a new API key for a user.
    
    WARNING: The API key is only shown ONCE. Store it securely!
    """
    try:
        # Validate inputs
        user_id = input_validator.sanitize_string(request.user_id, 100)
        name = input_validator.sanitize_string(request.name, 100)
        
        permissions = set(request.permissions) if request.permissions else {"read"}
        
        # Generate key
        raw_key = api_key_manager.generate_key(
            user_id=user_id,
            name=name,
            permissions=permissions
        )
        
        return GenerateKeyResponse(
            api_key=raw_key,
            name=name,
            permissions=list(permissions),
            message="API key generated. Store this key securely - it won't be shown again!"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keys/validate")
async def validate_api_key(request: Request):
    """Validate an API key from Authorization header"""
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header.startswith("Bearer "):
        return {"valid": False, "error": "No Bearer token provided"}
    
    raw_key = auth_header[7:]
    api_key = api_key_manager.validate_key(raw_key)
    
    if not api_key:
        return {"valid": False, "error": "Invalid or expired key"}
    
    return {
        "valid": True,
        "user_id": api_key.user_id,
        "name": api_key.name,
        "permissions": list(api_key.permissions),
        "created_at": api_key.created_at.isoformat()
    }


# ============================================
# RATE LIMIT ENDPOINTS
# ============================================

@router.get("/rate-limit/status", response_model=RateLimitStatus)
async def get_rate_limit_status(request: Request):
    """Get current rate limit status for your IP"""
    ip = request.client.host if request.client else "unknown"
    
    # Get forwarded IP if behind proxy
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    
    # Get current counts
    import time
    now = time.time()
    minute_key = f"min_{int(now / 60)}"
    hour_key = f"hour_{int(now / 3600)}"
    
    counts = rate_limiter.request_counts.get(ip, {})
    
    return RateLimitStatus(
        ip=ip,
        is_blocked=ip in rate_limiter.blocked_ips,
        is_whitelisted=ip in rate_limiter.whitelisted_ips,
        requests_this_minute=counts.get(minute_key, 0),
        requests_this_hour=counts.get(hour_key, 0),
        limits={
            "per_minute": rate_limiter.config.requests_per_minute,
            "per_hour": rate_limiter.config.requests_per_hour,
            "per_day": rate_limiter.config.requests_per_day,
            "burst": rate_limiter.config.burst_limit
        }
    )


# ============================================
# TRANSACTION LIMIT ENDPOINTS
# ============================================

@router.get("/transaction-limits/{user_id}", response_model=TransactionLimitStatus)
async def get_transaction_limits(user_id: str):
    """Get remaining transaction limits for a user"""
    user_id = input_validator.sanitize_string(user_id, 100)
    limits = transaction_guard.get_remaining_limits(user_id)
    
    return TransactionLimitStatus(
        user_id=user_id,
        **limits
    )


# ============================================
# SECURITY STATUS
# ============================================

@router.get("/status")
async def get_security_status():
    """Get overall security system status"""
    return {
        "status": "operational",
        "components": {
            "rate_limiter": {
                "enabled": True,
                "blocked_ips": len(rate_limiter.blocked_ips),
                "whitelisted_ips": len(rate_limiter.whitelisted_ips),
            },
            "api_key_auth": {
                "enabled": True,
                "active_keys": len([k for k in api_key_manager.keys.values() if k.is_active]),
            },
            "transaction_guard": {
                "enabled": True,
                "max_per_tx": transaction_guard.limits.max_per_tx_usd,
                "max_daily": transaction_guard.limits.max_daily_usd,
            },
            "input_validation": {
                "enabled": True,
            }
        },
        "timestamp": datetime.now().isoformat()
    }


# ============================================
# ADMIN ENDPOINTS (Protected)
# ============================================

@router.post("/admin/block-ip")
async def block_ip(ip: str, reason: str = "manual"):
    """Block an IP address (admin only)"""
    # TODO: Add admin authentication
    rate_limiter.block_ip(ip, reason)
    return {"success": True, "message": f"IP {ip} blocked"}


@router.post("/admin/unblock-ip")
async def unblock_ip(ip: str):
    """Unblock an IP address (admin only)"""
    # TODO: Add admin authentication
    rate_limiter.unblock_ip(ip)
    return {"success": True, "message": f"IP {ip} unblocked"}


@router.post("/admin/whitelist-ip")
async def whitelist_ip(ip: str):
    """Whitelist an IP address (admin only)"""
    # TODO: Add admin authentication
    rate_limiter.whitelist_ip(ip)
    return {"success": True, "message": f"IP {ip} whitelisted"}
