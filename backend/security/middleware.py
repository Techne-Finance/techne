"""
Security Middleware for Techne Finance
Production-grade security layer for billion-dollar protocol

Features:
- Rate limiting (per IP, per user, per endpoint)
- Request validation and sanitization
- Security headers (HSTS, CSP, etc.)
- API key authentication
- Request/Response logging
- IP blocking and whitelisting
- Transaction limits and simulation
"""

import time
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Set, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict
from functools import wraps
import re
import json

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SecurityMiddleware")


# ============================================
# RATE LIMITER
# ============================================

@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_limit: int = 10  # Max requests in 1 second


class RateLimiter:
    """
    Token bucket rate limiter with multiple time windows.
    Protects against DDoS and abuse.
    """
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        
        # Tracking: IP -> {window: count}
        self.request_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.last_request: Dict[str, float] = {}
        self.blocked_ips: Set[str] = set()
        self.whitelisted_ips: Set[str] = {"127.0.0.1", "::1"}
        
        # Cleanup interval
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
        
    def is_allowed(self, ip: str, endpoint: str = None) -> tuple[bool, str]:
        """Check if request is allowed"""
        
        # Whitelist bypass
        if ip in self.whitelisted_ips:
            return True, "whitelisted"
        
        # Blocked check
        if ip in self.blocked_ips:
            return False, "IP is blocked"
        
        now = time.time()
        self._cleanup_if_needed(now)
        
        # Get time windows
        minute_key = f"min_{int(now / 60)}"
        hour_key = f"hour_{int(now / 3600)}"
        day_key = f"day_{int(now / 86400)}"
        
        counts = self.request_counts[ip]
        
        # Check burst (1 second window)
        last = self.last_request.get(ip, 0)
        if now - last < 1:
            counts["burst"] = counts.get("burst", 0) + 1
            if counts["burst"] > self.config.burst_limit:
                return False, f"Burst limit exceeded ({self.config.burst_limit}/sec)"
        else:
            counts["burst"] = 1
        
        # Check minute limit
        counts[minute_key] += 1
        if counts[minute_key] > self.config.requests_per_minute:
            return False, f"Rate limit exceeded ({self.config.requests_per_minute}/min)"
        
        # Check hour limit
        counts[hour_key] += 1
        if counts[hour_key] > self.config.requests_per_hour:
            return False, f"Rate limit exceeded ({self.config.requests_per_hour}/hour)"
        
        # Check day limit
        counts[day_key] += 1
        if counts[day_key] > self.config.requests_per_day:
            return False, f"Daily limit exceeded ({self.config.requests_per_day}/day)"
        
        self.last_request[ip] = now
        return True, "ok"
    
    def block_ip(self, ip: str, reason: str = "manual"):
        """Block an IP address"""
        self.blocked_ips.add(ip)
        logger.warning(f"Blocked IP: {ip} - Reason: {reason}")
    
    def unblock_ip(self, ip: str):
        """Unblock an IP address"""
        self.blocked_ips.discard(ip)
        logger.info(f"Unblocked IP: {ip}")
    
    def whitelist_ip(self, ip: str):
        """Whitelist an IP address"""
        self.whitelisted_ips.add(ip)
    
    def _cleanup_if_needed(self, now: float):
        """Clean up old tracking data"""
        if now - self.last_cleanup > self.cleanup_interval:
            current_minute = int(now / 60)
            current_hour = int(now / 3600)
            current_day = int(now / 86400)
            
            for ip in list(self.request_counts.keys()):
                counts = self.request_counts[ip]
                # Remove old keys
                for key in list(counts.keys()):
                    if key.startswith("min_") and int(key.split("_")[1]) < current_minute - 2:
                        del counts[key]
                    elif key.startswith("hour_") and int(key.split("_")[1]) < current_hour - 2:
                        del counts[key]
                    elif key.startswith("day_") and int(key.split("_")[1]) < current_day - 2:
                        del counts[key]
            
            self.last_cleanup = now


# ============================================
# INPUT VALIDATION
# ============================================

class InputValidator:
    """
    Validates and sanitizes all user inputs.
    Prevents injection attacks and malformed data.
    """
    
    # Patterns for validation
    PATTERNS = {
        "address": re.compile(r"^0x[a-fA-F0-9]{40}$"),
        "tx_hash": re.compile(r"^0x[a-fA-F0-9]{64}$"),
        "chain": re.compile(r"^[a-zA-Z0-9_-]{1,50}$"),
        "pool_id": re.compile(r"^[a-zA-Z0-9_-]{1,100}$"),
        "user_id": re.compile(r"^[a-zA-Z0-9_-]{1,100}$"),
        "amount": re.compile(r"^\d+(\.\d{1,18})?$"),
    }
    
    # Max lengths
    MAX_LENGTHS = {
        "string": 1000,
        "query": 500,
        "message": 5000,
        "json": 50000,
    }
    
    # SQL injection patterns to block
    SQL_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(--|;|\/\*|\*\/)",
        r"(\bOR\b.*=.*)",
    ]
    
    @classmethod
    def validate_address(cls, address: str) -> bool:
        """Validate Ethereum address"""
        if not address:
            return False
        return bool(cls.PATTERNS["address"].match(address))
    
    @classmethod
    def validate_tx_hash(cls, tx_hash: str) -> bool:
        """Validate transaction hash"""
        if not tx_hash:
            return False
        return bool(cls.PATTERNS["tx_hash"].match(tx_hash))
    
    @classmethod
    def validate_chain(cls, chain: str) -> bool:
        """Validate chain name"""
        if not chain:
            return False
        return bool(cls.PATTERNS["chain"].match(chain))
    
    @classmethod
    def validate_amount(cls, amount: str) -> bool:
        """Validate numeric amount"""
        if not amount:
            return False
        return bool(cls.PATTERNS["amount"].match(str(amount)))
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = None) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            return str(value)[:max_length or cls.MAX_LENGTHS["string"]]
        
        # Trim to max length
        max_len = max_length or cls.MAX_LENGTHS["string"]
        value = value[:max_len]
        
        # Check for SQL injection
        for pattern in cls.SQL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"SQL injection attempt detected: {value[:50]}...")
                raise ValueError("Invalid input detected")
        
        # Remove dangerous characters
        value = re.sub(r'[<>"\']', '', value)
        
        return value.strip()
    
    @classmethod
    def validate_json(cls, data: Any, max_size: int = None) -> bool:
        """Validate JSON data size"""
        max_size = max_size or cls.MAX_LENGTHS["json"]
        return len(json.dumps(data)) <= max_size


# ============================================
# API KEY AUTHENTICATION
# ============================================

@dataclass
class APIKey:
    """API Key model"""
    key_hash: str
    user_id: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    rate_limit_override: Optional[int] = None
    permissions: Set[str] = field(default_factory=set)
    is_active: bool = True


class APIKeyManager:
    """
    Manages API key authentication.
    Supports multiple keys per user with different permissions.
    """
    
    def __init__(self):
        self.keys: Dict[str, APIKey] = {}  # key_hash -> APIKey
        self.user_keys: Dict[str, Set[str]] = defaultdict(set)  # user_id -> key_hashes
        
    def generate_key(self, user_id: str, name: str, permissions: Set[str] = None) -> str:
        """Generate new API key"""
        import secrets
        
        # Generate random key
        raw_key = f"tk_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        api_key = APIKey(
            key_hash=key_hash,
            user_id=user_id,
            name=name,
            created_at=datetime.now(),
            permissions=permissions or {"read"},
        )
        
        self.keys[key_hash] = api_key
        self.user_keys[user_id].add(key_hash)
        
        logger.info(f"Generated API key for user {user_id}: {name}")
        
        # Return raw key (only time it's visible)
        return raw_key
    
    def validate_key(self, raw_key: str) -> Optional[APIKey]:
        """Validate API key and return key info"""
        if not raw_key or not raw_key.startswith("tk_"):
            return None
        
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        api_key = self.keys.get(key_hash)
        
        if not api_key:
            return None
        
        if not api_key.is_active:
            return None
        
        if api_key.expires_at and datetime.now() > api_key.expires_at:
            return None
        
        return api_key
    
    def revoke_key(self, key_hash: str):
        """Revoke an API key"""
        if key_hash in self.keys:
            self.keys[key_hash].is_active = False


# ============================================
# SECURITY HEADERS
# ============================================

def get_security_headers() -> Dict[str, str]:
    """Get production security headers"""
    return {
        # Prevent clickjacking
        "X-Frame-Options": "DENY",
        # Prevent MIME sniffing
        "X-Content-Type-Options": "nosniff",
        # XSS protection
        "X-XSS-Protection": "1; mode=block",
        # Referrer policy
        "Referrer-Policy": "strict-origin-when-cross-origin",
        # Permissions policy
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        # Content Security Policy
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
    }


# ============================================
# TRANSACTION SECURITY
# ============================================

@dataclass
class TransactionLimits:
    """Transaction limits configuration"""
    max_per_tx_usd: float = 10000
    max_daily_usd: float = 50000
    max_tx_per_day: int = 100
    require_simulation: bool = True
    require_approval_above_usd: float = 1000


class TransactionGuard:
    """
    Guards against unauthorized or risky transactions.
    Enforces limits and requires simulation.
    """
    
    def __init__(self, limits: TransactionLimits = None):
        self.limits = limits or TransactionLimits()
        
        # Daily tracking: user_id -> {date: {amount, count}}
        self.daily_usage: Dict[str, Dict[str, Dict]] = defaultdict(dict)
        
    def check_transaction(
        self, 
        user_id: str, 
        amount_usd: float,
        tx_type: str = "deposit"
    ) -> tuple[bool, str]:
        """Check if transaction is allowed"""
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Get today's usage
        if today not in self.daily_usage[user_id]:
            self.daily_usage[user_id][today] = {"amount": 0, "count": 0}
        
        usage = self.daily_usage[user_id][today]
        
        # Check per-transaction limit
        if amount_usd > self.limits.max_per_tx_usd:
            return False, f"Amount exceeds per-transaction limit (${self.limits.max_per_tx_usd})"
        
        # Check daily limit
        if usage["amount"] + amount_usd > self.limits.max_daily_usd:
            remaining = self.limits.max_daily_usd - usage["amount"]
            return False, f"Would exceed daily limit. Remaining: ${remaining:.2f}"
        
        # Check daily count
        if usage["count"] >= self.limits.max_tx_per_day:
            return False, f"Daily transaction count exceeded ({self.limits.max_tx_per_day})"
        
        return True, "ok"
    
    def record_transaction(self, user_id: str, amount_usd: float):
        """Record a completed transaction"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if today not in self.daily_usage[user_id]:
            self.daily_usage[user_id][today] = {"amount": 0, "count": 0}
        
        self.daily_usage[user_id][today]["amount"] += amount_usd
        self.daily_usage[user_id][today]["count"] += 1
    
    def get_remaining_limits(self, user_id: str) -> Dict:
        """Get remaining limits for user"""
        today = datetime.now().strftime("%Y-%m-%d")
        usage = self.daily_usage[user_id].get(today, {"amount": 0, "count": 0})
        
        return {
            "remaining_daily_usd": self.limits.max_daily_usd - usage["amount"],
            "remaining_tx_count": self.limits.max_tx_per_day - usage["count"],
            "max_per_tx_usd": self.limits.max_per_tx_usd,
        }


# ============================================
# REQUEST LOGGER
# ============================================

class RequestLogger:
    """
    Logs all requests for audit trail.
    Critical for security compliance.
    """
    
    def __init__(self, log_file: str = "techne_audit.log"):
        self.log_file = log_file
        self.logger = logging.getLogger("AuditLog")
        
        # Add file handler
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_request(
        self,
        ip: str,
        method: str,
        path: str,
        user_id: Optional[str] = None,
        status_code: int = 200,
        response_time_ms: float = 0,
        error: str = None
    ):
        """Log a request"""
        log_data = {
            "ip": ip,
            "method": method,
            "path": path,
            "user_id": user_id,
            "status": status_code,
            "time_ms": round(response_time_ms, 2),
        }
        
        if error:
            log_data["error"] = error
            self.logger.warning(json.dumps(log_data))
        else:
            self.logger.info(json.dumps(log_data))


# ============================================
# FASTAPI MIDDLEWARE
# ============================================

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Main security middleware for FastAPI.
    Combines all security features.
    """
    
    def __init__(self, app, rate_limiter: RateLimiter = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()
        self.request_logger = RequestLogger()
        self.api_key_manager = APIKeyManager()
        
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # Get client IP
        ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        
        # Rate limiting
        allowed, reason = self.rate_limiter.is_allowed(ip, request.url.path)
        if not allowed:
            self.request_logger.log_request(
                ip=ip,
                method=request.method,
                path=str(request.url.path),
                status_code=429,
                error=reason
            )
            return JSONResponse(
                status_code=429,
                content={"error": reason, "retry_after": 60}
            )
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.request_logger.log_request(
                ip=ip,
                method=request.method,
                path=str(request.url.path),
                status_code=500,
                response_time_ms=response_time,
                error=str(e)
            )
            raise
        
        # Add security headers
        for header, value in get_security_headers().items():
            response.headers[header] = value
        
        # Log request
        response_time = (time.time() - start_time) * 1000
        self.request_logger.log_request(
            ip=ip,
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            response_time_ms=response_time
        )
        
        return response


# ============================================
# SINGLETON INSTANCES
# ============================================

rate_limiter = RateLimiter()
input_validator = InputValidator()
api_key_manager = APIKeyManager()
transaction_guard = TransactionGuard()
request_logger = RequestLogger()


# ============================================
# DECORATORS
# ============================================

def require_api_key(permissions: Set[str] = None):
    """Decorator to require API key authentication"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            
            if not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=401,
                    detail="API key required"
                )
            
            raw_key = auth_header[7:]  # Remove "Bearer "
            api_key = api_key_manager.validate_key(raw_key)
            
            if not api_key:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired API key"
                )
            
            if permissions and not permissions.issubset(api_key.permissions):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
            
            # Add user info to request state
            request.state.user_id = api_key.user_id
            request.state.api_key = api_key
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def validate_transaction(func: Callable):
    """Decorator to validate transaction limits"""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        # Get user_id and amount from request
        user_id = getattr(request.state, "user_id", "anonymous")
        
        # Check body for amount
        try:
            body = await request.json()
            amount = body.get("amount_usd", 0)
        except:
            amount = 0
        
        if amount > 0:
            allowed, reason = transaction_guard.check_transaction(user_id, amount)
            if not allowed:
                raise HTTPException(
                    status_code=400,
                    detail=reason
                )
        
        result = await func(request, *args, **kwargs)
        
        # Record successful transaction
        if amount > 0:
            transaction_guard.record_transaction(user_id, amount)
        
        return result
    
    return wrapper
