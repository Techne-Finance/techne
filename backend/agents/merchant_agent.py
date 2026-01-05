"""
Merchant Agent - "The Wallet" of Artisan System
Handles all payment processing via x402/Meridian

Responsibilities:
- Generate payment requests (invoices)
- Listen for payments on Base/Meridian
- Manage subscriptions ($10/month)
- Track micropayments ($0.10)
- Grant access after payment confirmation
- Track payment outcomes via Memory Engine
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import secrets

# Observability integration
try:
    from agents.observability_engine import observability, traced, SpanStatus
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False
    def traced(agent, op):
        def decorator(func): return func
        return decorator

# Memory integration
try:
    from agents.memory_engine import memory_engine, MemoryType
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MerchantAgent")


class PaymentType(Enum):
    MICROPAYMENT = "micropayment"      # $0.10 one-time
    SUBSCRIPTION = "subscription"       # $10/month
    PREMIUM_QUERY = "premium_query"     # $0.50 for deep analysis


class PaymentStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    FAILED = "failed"


@dataclass
class PaymentRequest:
    id: str
    user_id: str
    payment_type: PaymentType
    amount_usd: float
    amount_usdc: float  # In USDC (6 decimals)
    recipient_address: str
    created_at: datetime
    expires_at: datetime
    status: PaymentStatus = PaymentStatus.PENDING
    tx_hash: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass 
class Subscription:
    user_id: str
    tier: str  # "free", "pro", "enterprise"
    start_date: datetime
    end_date: datetime
    auto_renew: bool = True
    payment_history: List[str] = field(default_factory=list)


class MerchantAgent:
    """
    The Merchant - Payment Processing Agent
    Isolated from other agents for security
    """
    
    def __init__(self):
        # Recipient address for payments
        self.recipient_address = "0x..."  # Set your USDC recipient address
        
        # Pricing
        self.pricing = {
            PaymentType.MICROPAYMENT: 0.10,
            PaymentType.SUBSCRIPTION: 10.00,
            PaymentType.PREMIUM_QUERY: 0.50,
        }
        
        # Storage (in production, use database)
        self.pending_payments: Dict[str, PaymentRequest] = {}
        self.confirmed_payments: Dict[str, PaymentRequest] = {}
        self.subscriptions: Dict[str, Subscription] = {}
        self.access_grants: Dict[str, List[str]] = {}  # user_id -> [pool_ids]
        
        # Meridian x402 config
        self.x402_config = {
            "network": "base",
            "token": "USDC",
            "token_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "decimals": 6,
        }
        
        # Payment expiration
        self.payment_expiry_minutes = 15
        
    # ===========================================
    # PAYMENT REQUEST GENERATION
    # ===========================================
    
    def create_payment_request(
        self, 
        user_id: str, 
        payment_type: PaymentType,
        metadata: Optional[Dict] = None
    ) -> PaymentRequest:
        """Create a new payment request (invoice)"""
        
        payment_id = self._generate_payment_id()
        amount_usd = self.pricing[payment_type]
        
        request = PaymentRequest(
            id=payment_id,
            user_id=user_id,
            payment_type=payment_type,
            amount_usd=amount_usd,
            amount_usdc=self._usd_to_usdc(amount_usd),
            recipient_address=self.recipient_address,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=self.payment_expiry_minutes),
            metadata=metadata or {}
        )
        
        self.pending_payments[payment_id] = request
        logger.info(f"💰 Created payment request {payment_id}: ${amount_usd} for {user_id}")
        
        return request
    
    def create_pool_access_request(self, user_id: str, pool_id: str) -> PaymentRequest:
        """Create $0.10 micropayment for pool access"""
        return self.create_payment_request(
            user_id=user_id,
            payment_type=PaymentType.MICROPAYMENT,
            metadata={"pool_id": pool_id, "access_type": "pool_details"}
        )
    
    def create_subscription_request(self, user_id: str, tier: str = "pro") -> PaymentRequest:
        """Create $10/month subscription request"""
        return self.create_payment_request(
            user_id=user_id,
            payment_type=PaymentType.SUBSCRIPTION,
            metadata={"tier": tier, "duration_days": 30}
        )
    
    # ===========================================
    # PAYMENT VERIFICATION
    # ===========================================
    
    async def check_payment(self, payment_id: str) -> PaymentStatus:
        """Check if a payment has been received"""
        if payment_id not in self.pending_payments:
            return PaymentStatus.EXPIRED
        
        request = self.pending_payments[payment_id]
        
        # Check if expired
        if datetime.now() > request.expires_at:
            request.status = PaymentStatus.EXPIRED
            return PaymentStatus.EXPIRED
        
        # In production: Query blockchain for incoming USDC transfer
        # For now, simulate payment verification
        is_paid = await self._verify_on_chain(request)
        
        if is_paid:
            request.status = PaymentStatus.CONFIRMED
            self._process_confirmed_payment(request)
            return PaymentStatus.CONFIRMED
        
        return PaymentStatus.PENDING
    
    async def _verify_on_chain(self, request: PaymentRequest) -> bool:
        """
        Verify payment on blockchain
        In production: Use ethers/web3 to check for USDC transfer
        """
        # Placeholder - would query Base/Meridian for:
        # - USDC transfer to recipient_address
        # - Amount matches request.amount_usdc
        # - Memo/data contains payment_id
        
        # For MVP testing, you could manually confirm payments
        return False
    
    def manually_confirm_payment(self, payment_id: str, tx_hash: str) -> bool:
        """Manually confirm a payment (for testing/admin)"""
        if payment_id not in self.pending_payments:
            return False
        
        request = self.pending_payments[payment_id]
        request.status = PaymentStatus.CONFIRMED
        request.tx_hash = tx_hash
        
        self._process_confirmed_payment(request)
        logger.info(f"✅ Manually confirmed payment {payment_id}")
        return True
    
    def _process_confirmed_payment(self, request: PaymentRequest):
        """Process a confirmed payment - grant access"""
        # Move to confirmed
        self.confirmed_payments[request.id] = request
        if request.id in self.pending_payments:
            del self.pending_payments[request.id]
        
        # Grant access based on payment type
        if request.payment_type == PaymentType.MICROPAYMENT:
            # Grant access to specific pool
            pool_id = request.metadata.get("pool_id")
            if pool_id:
                self._grant_pool_access(request.user_id, pool_id)
        
        elif request.payment_type == PaymentType.SUBSCRIPTION:
            # Create subscription
            self._activate_subscription(request)
        
        logger.info(f"💚 Payment processed: {request.id} for {request.user_id}")
    
    # ===========================================
    # ACCESS MANAGEMENT
    # ===========================================
    
    def _grant_pool_access(self, user_id: str, pool_id: str):
        """Grant user access to pool details"""
        if user_id not in self.access_grants:
            self.access_grants[user_id] = []
        
        if pool_id not in self.access_grants[user_id]:
            self.access_grants[user_id].append(pool_id)
    
    def _activate_subscription(self, request: PaymentRequest):
        """Activate user subscription"""
        tier = request.metadata.get("tier", "pro")
        duration = request.metadata.get("duration_days", 30)
        
        subscription = Subscription(
            user_id=request.user_id,
            tier=tier,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=duration)
        )
        subscription.payment_history.append(request.id)
        
        self.subscriptions[request.user_id] = subscription
        logger.info(f"🌟 Activated {tier} subscription for {request.user_id}")
    
    def has_pool_access(self, user_id: str, pool_id: str) -> bool:
        """Check if user has access to pool details"""
        # TESTING MODE - Set to True to bypass payments
        FREE_ACCESS_MODE = True
        if FREE_ACCESS_MODE:
            return True  # Everyone has access during testing
        
        # Subscribers have unlimited access
        if self.is_subscriber(user_id):
            return True
        
        # Check individual access
        return pool_id in self.access_grants.get(user_id, [])
    
    def is_subscriber(self, user_id: str) -> bool:
        """Check if user has active subscription"""
        if user_id not in self.subscriptions:
            return False
        
        sub = self.subscriptions[user_id]
        return datetime.now() < sub.end_date
    
    def get_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get user subscription details"""
        return self.subscriptions.get(user_id)
    
    # ===========================================
    # HELPERS
    # ===========================================
    
    def _generate_payment_id(self) -> str:
        """Generate unique payment ID"""
        random_bytes = secrets.token_bytes(16)
        return hashlib.sha256(random_bytes).hexdigest()[:16]
    
    def _usd_to_usdc(self, usd: float) -> float:
        """Convert USD to USDC (6 decimals)"""
        return usd * (10 ** self.x402_config["decimals"])
    
    def get_payment_status(self, payment_id: str) -> Dict:
        """Get payment status for API response"""
        if payment_id in self.confirmed_payments:
            p = self.confirmed_payments[payment_id]
            status = "confirmed"
        elif payment_id in self.pending_payments:
            p = self.pending_payments[payment_id]
            status = "pending" if datetime.now() < p.expires_at else "expired"
        else:
            return {"status": "not_found"}
        
        return {
            "payment_id": p.id,
            "status": status,
            "amount_usd": p.amount_usd,
            "recipient": p.recipient_address,
            "expires_at": p.expires_at.isoformat() if status == "pending" else None,
            "tx_hash": p.tx_hash
        }
    
    def generate_x402_header(self, payment_request: PaymentRequest) -> Dict:
        """Generate x402 payment required header"""
        return {
            "X-Payment-Required": "true",
            "X-Payment-Amount": str(payment_request.amount_usdc),
            "X-Payment-Token": self.x402_config["token"],
            "X-Payment-Network": self.x402_config["network"],
            "X-Payment-Recipient": self.recipient_address,
            "X-Payment-Id": payment_request.id,
            "X-Payment-Expires": payment_request.expires_at.isoformat()
        }


# Singleton instance
merchant = MerchantAgent()
