"""
Pydantic Validation Models for Techne Finance
Comprehensive input validation for production-grade API

All user inputs must be validated before processing.
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import re


# ============================================
# CUSTOM VALIDATORS
# ============================================

def validate_ethereum_address(address: str) -> str:
    """Validate Ethereum address format"""
    if not address:
        raise ValueError("Address is required")
    if not re.match(r"^0x[a-fA-F0-9]{40}$", address):
        raise ValueError("Invalid Ethereum address format")
    return address.lower()


def validate_tx_hash(tx_hash: str) -> str:
    """Validate transaction hash format"""
    if not tx_hash:
        raise ValueError("Transaction hash is required")
    if not re.match(r"^0x[a-fA-F0-9]{64}$", tx_hash):
        raise ValueError("Invalid transaction hash format")
    return tx_hash.lower()


def validate_chain(chain: str) -> str:
    """Validate chain name"""
    allowed_chains = [
        "ethereum", "base", "arbitrum", "optimism", 
        "polygon", "avalanche", "solana", "bsc"
    ]
    chain_lower = chain.lower()
    if chain_lower not in allowed_chains:
        raise ValueError(f"Chain must be one of: {', '.join(allowed_chains)}")
    return chain_lower


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize and limit string length"""
    if not isinstance(value, str):
        return str(value)[:max_length]
    # Remove potential SQL injection characters
    dangerous_patterns = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b)",
        r"(--|;|\/\*|\*\/)",
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            raise ValueError("Invalid characters detected")
    return value[:max_length].strip()


# ============================================
# ENUMS
# ============================================

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AssetType(str, Enum):
    STABLECOIN = "stablecoin"
    VOLATILE = "volatile"
    ALL = "all"


class PoolType(str, Enum):
    SINGLE = "single"
    DUAL = "dual"
    ALL = "all"


class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    SWAP = "swap"
    BRIDGE = "bridge"


# ============================================
# POOL MODELS
# ============================================

class PoolFilter(BaseModel):
    """Filter parameters for pool queries"""
    chain: Optional[str] = Field(default="all", max_length=50)
    asset_type: Optional[AssetType] = Field(default=AssetType.ALL)
    pool_type: Optional[PoolType] = Field(default=PoolType.ALL)
    min_tvl: Optional[float] = Field(default=100000, ge=0, le=1e12)
    max_tvl: Optional[float] = Field(default=None, ge=0, le=1e12)
    min_apy: Optional[float] = Field(default=0, ge=0, le=10000)
    max_apy: Optional[float] = Field(default=1000, ge=0, le=10000)
    risk_level: Optional[RiskLevel] = Field(default=None)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    
    @validator("chain")
    def validate_chain_name(cls, v):
        if v and v != "all":
            return validate_chain(v)
        return v


class PoolDetailRequest(BaseModel):
    """Request for detailed pool information"""
    pool_id: str = Field(..., min_length=1, max_length=200)
    include_history: bool = Field(default=False)
    include_alternatives: bool = Field(default=False)
    
    @validator("pool_id")
    def sanitize_pool_id(cls, v):
        return sanitize_string(v, 200)


# ============================================
# TRANSACTION MODELS
# ============================================

class DepositRequest(BaseModel):
    """Request to deposit into a pool"""
    pool_id: str = Field(..., min_length=1, max_length=200)
    amount: float = Field(..., gt=0, le=1e9)
    token_address: str = Field(...)
    slippage_tolerance: float = Field(default=0.5, ge=0.1, le=5.0)
    deadline_minutes: int = Field(default=30, ge=5, le=120)
    
    @validator("token_address")
    def validate_token(cls, v):
        return validate_ethereum_address(v)
    
    @validator("pool_id")
    def sanitize_pool_id(cls, v):
        return sanitize_string(v, 200)


class WithdrawRequest(BaseModel):
    """Request to withdraw from a pool"""
    pool_id: str = Field(..., min_length=1, max_length=200)
    shares: float = Field(..., gt=0, le=1e18)
    min_output: float = Field(default=0, ge=0)
    
    @validator("pool_id")
    def sanitize_pool_id(cls, v):
        return sanitize_string(v, 200)


class TransactionStatus(BaseModel):
    """Transaction status response"""
    tx_hash: str
    status: str
    confirmations: int
    gas_used: Optional[int] = None
    effective_gas_price: Optional[int] = None
    timestamp: datetime


# ============================================
# USER MODELS
# ============================================

class UserPreferences(BaseModel):
    """User preference settings"""
    risk_tolerance: RiskLevel = Field(default=RiskLevel.MEDIUM)
    preferred_chains: List[str] = Field(default_factory=list, max_items=10)
    min_apy_threshold: float = Field(default=5.0, ge=0, le=1000)
    notification_enabled: bool = Field(default=True)
    
    @validator("preferred_chains", each_item=True)
    def validate_chains(cls, v):
        return validate_chain(v)


class PositionCreate(BaseModel):
    """Create a new position to monitor"""
    pool_id: str = Field(..., min_length=1, max_length=200)
    amount: float = Field(..., gt=0, le=1e9)
    stop_loss_percent: Optional[float] = Field(default=None, ge=-100, le=0)
    take_profit_percent: Optional[float] = Field(default=None, ge=0, le=1000)
    apy_floor: Optional[float] = Field(default=None, ge=0, le=100)
    
    @validator("pool_id")
    def sanitize_pool_id(cls, v):
        return sanitize_string(v, 200)


# ============================================
# CHAT MODELS
# ============================================

class ChatMessage(BaseModel):
    """Chat message input"""
    message: str = Field(..., min_length=1, max_length=2000)
    context: Optional[Dict[str, Any]] = Field(default=None)
    
    @validator("message")
    def sanitize_message(cls, v):
        return sanitize_string(v, 2000)
    
    @validator("context")
    def validate_context(cls, v):
        if v and len(str(v)) > 5000:
            raise ValueError("Context too large")
        return v


class ChatResponse(BaseModel):
    """Chat response output"""
    text: str
    intent: str
    confidence: float = Field(ge=0, le=1)
    data: Optional[Dict[str, Any]] = None
    suggestions: List[str] = Field(default_factory=list)


# ============================================
# MEMORY MODELS
# ============================================

class MemoryStoreRequest(BaseModel):
    """Store memory request"""
    memory_type: str = Field(..., max_length=50)
    content: Dict[str, Any]
    user_id: str = Field(default="default", max_length=100)
    agent_id: str = Field(default="system", max_length=100)
    
    @validator("memory_type")
    def validate_memory_type(cls, v):
        allowed = ["pool_result", "strategy", "preference", "conversation"]
        if v not in allowed:
            raise ValueError(f"Memory type must be one of: {', '.join(allowed)}")
        return v


class MemoryRecallRequest(BaseModel):
    """Recall memory request"""
    query: str = Field(..., min_length=1, max_length=500)
    memory_types: Optional[List[str]] = Field(default=None, max_items=5)
    limit: int = Field(default=10, ge=1, le=50)
    
    @validator("query")
    def sanitize_query(cls, v):
        return sanitize_string(v, 500)


# ============================================
# PAYMENT MODELS
# ============================================

class PaymentRequest(BaseModel):
    """Payment request creation"""
    payment_type: str = Field(..., max_length=50)
    pool_id: Optional[str] = Field(default=None, max_length=200)
    
    @validator("payment_type")
    def validate_payment_type(cls, v):
        allowed = ["micropayment", "subscription", "premium_query"]
        if v not in allowed:
            raise ValueError(f"Payment type must be one of: {', '.join(allowed)}")
        return v


class PaymentVerification(BaseModel):
    """Payment verification request"""
    payment_id: str = Field(..., min_length=1, max_length=100)
    tx_hash: str = Field(...)
    
    @validator("tx_hash")
    def validate_hash(cls, v):
        return validate_tx_hash(v)


# ============================================
# API RESPONSE MODELS
# ============================================

class APIResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    success: bool = True
    data: List[Any]
    total: int
    limit: int
    offset: int
    has_more: bool


class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    error: str
    code: str
    details: Optional[Dict[str, Any]] = None
