"""
Global Error Handling for Techne Finance
Production-grade exception handling with structured responses

Features:
- Custom exception classes
- Automatic error logging
- Structured JSON error responses
- Retry logic for external APIs
- Error tracking and aggregation
"""

import asyncio
import logging
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Type, TypeVar
from functools import wraps
from enum import Enum

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ErrorHandler")


# ============================================
# ERROR CODES
# ============================================

class ErrorCode(str, Enum):
    # Client errors (4xx)
    BAD_REQUEST = "BAD_REQUEST"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    PAYMENT_REQUIRED = "PAYMENT_REQUIRED"
    
    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    CACHE_ERROR = "CACHE_ERROR"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    BLOCKCHAIN_ERROR = "BLOCKCHAIN_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    
    # Business logic errors
    POOL_NOT_FOUND = "POOL_NOT_FOUND"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    TRANSACTION_FAILED = "TRANSACTION_FAILED"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"


# ============================================
# CUSTOM EXCEPTIONS
# ============================================

class TechneError(Exception):
    """Base exception for Techne Finance"""
    
    def __init__(
        self, 
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        details: Dict = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            "success": False,
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details,
                "timestamp": self.timestamp.isoformat()
            }
        }


class ValidationError(TechneError):
    """Input validation error"""
    def __init__(self, message: str, details: Dict = None):
        super().__init__(message, ErrorCode.VALIDATION_ERROR, 400, details)


class NotFoundError(TechneError):
    """Resource not found"""
    def __init__(self, resource: str, identifier: str = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} '{identifier}' not found"
        super().__init__(message, ErrorCode.NOT_FOUND, 404)


class UnauthorizedError(TechneError):
    """Authentication required"""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, ErrorCode.UNAUTHORIZED, 401)


class ForbiddenError(TechneError):
    """Access denied"""
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, ErrorCode.FORBIDDEN, 403)


class RateLimitError(TechneError):
    """Rate limit exceeded"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            f"Rate limit exceeded. Retry after {retry_after} seconds",
            ErrorCode.RATE_LIMITED,
            429,
            {"retry_after": retry_after}
        )


class PaymentRequiredError(TechneError):
    """Payment required for resource"""
    def __init__(self, resource: str, amount_usd: float):
        super().__init__(
            f"Payment required to access {resource}",
            ErrorCode.PAYMENT_REQUIRED,
            402,
            {"resource": resource, "amount_usd": amount_usd}
        )


class DatabaseError(TechneError):
    """Database operation failed"""
    def __init__(self, message: str, original_error: Exception = None):
        details = {}
        if original_error:
            details["original_error"] = str(original_error)
        super().__init__(message, ErrorCode.DATABASE_ERROR, 500, details)


class ExternalAPIError(TechneError):
    """External API call failed"""
    def __init__(self, api_name: str, status_code: int = None, message: str = None):
        details = {"api": api_name}
        if status_code:
            details["api_status_code"] = status_code
        super().__init__(
            message or f"External API '{api_name}' failed",
            ErrorCode.EXTERNAL_API_ERROR,
            502,
            details
        )


class BlockchainError(TechneError):
    """Blockchain operation failed"""
    def __init__(self, chain: str, message: str, tx_hash: str = None):
        details = {"chain": chain}
        if tx_hash:
            details["tx_hash"] = tx_hash
        super().__init__(message, ErrorCode.BLOCKCHAIN_ERROR, 500, details)


class LimitExceededError(TechneError):
    """Transaction or daily limit exceeded"""
    def __init__(self, limit_type: str, limit_value: float, current_value: float):
        super().__init__(
            f"{limit_type} limit exceeded",
            ErrorCode.LIMIT_EXCEEDED,
            400,
            {
                "limit_type": limit_type,
                "limit": limit_value,
                "current": current_value,
                "remaining": max(0, limit_value - current_value)
            }
        )


# ============================================
# ERROR TRACKING
# ============================================

class ErrorTracker:
    """Tracks and aggregates errors for monitoring"""
    
    def __init__(self, max_errors: int = 1000):
        self.errors: list = []
        self.max_errors = max_errors
        self.error_counts: Dict[str, int] = {}
    
    def track(self, error: Exception, request_path: str = None):
        """Track an error"""
        error_type = type(error).__name__
        
        # Increment count
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Store error details
        error_info = {
            "type": error_type,
            "message": str(error),
            "path": request_path,
            "timestamp": datetime.now().isoformat(),
            "traceback": traceback.format_exc() if not isinstance(error, TechneError) else None
        }
        
        if isinstance(error, TechneError):
            error_info["code"] = error.code.value
            error_info["details"] = error.details
        
        self.errors.append(error_info)
        
        # Trim if too many
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]
        
        # Log critical errors
        if not isinstance(error, TechneError) or error.status_code >= 500:
            logger.error(f"Error tracked: {error_type} - {str(error)[:200]}")
    
    def get_stats(self) -> Dict:
        """Get error statistics"""
        return {
            "total_errors": len(self.errors),
            "error_counts": self.error_counts,
            "recent_errors": self.errors[-10:],
            "timestamp": datetime.now().isoformat()
        }
    
    def clear(self):
        """Clear error history"""
        self.errors.clear()
        self.error_counts.clear()


# Global error tracker
error_tracker = ErrorTracker()


# ============================================
# RETRY LOGIC
# ============================================

T = TypeVar('T')


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for automatic retry with exponential backoff.
    
    Usage:
        @retry(max_attempts=3, delay=1.0)
        async def fetch_data():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        logger.warning(f"Retry {attempt + 1}/{max_attempts} for {func.__name__}: {e}")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All retries failed for {func.__name__}: {e}")
            
            raise last_exception
        
        return wrapper
    return decorator


def retry_sync(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Synchronous version of retry decorator"""
    import time
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        logger.warning(f"Retry {attempt + 1}/{max_attempts}: {e}")
                        time.sleep(current_delay)
                        current_delay *= backoff
            
            raise last_exception
        
        return wrapper
    return decorator


# ============================================
# FASTAPI EXCEPTION HANDLERS
# ============================================

async def techne_exception_handler(request: Request, exc: TechneError) -> JSONResponse:
    """Handle TechneError exceptions"""
    error_tracker.track(exc, str(request.url.path))
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPExceptions"""
    error_tracker.track(exc, str(request.url.path))
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": ErrorCode.BAD_REQUEST.value if exc.status_code < 500 else ErrorCode.INTERNAL_ERROR.value,
                "message": exc.detail,
                "timestamp": datetime.now().isoformat()
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    error_tracker.track(exc, str(request.url.path))
    
    # Log full traceback
    logger.error(f"Unhandled exception: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": ErrorCode.INTERNAL_ERROR.value,
                "message": "An unexpected error occurred",
                "timestamp": datetime.now().isoformat()
            }
        }
    )


def register_exception_handlers(app):
    """Register all exception handlers with FastAPI app"""
    app.add_exception_handler(TechneError, techne_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Exception handlers registered")


# ============================================
# ERROR MIDDLEWARE
# ============================================

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware that catches and formats all errors"""
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except TechneError as e:
            return await techne_exception_handler(request, e)
        except HTTPException as e:
            return await http_exception_handler(request, e)
        except Exception as e:
            return await general_exception_handler(request, e)
