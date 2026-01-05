"""
Revenue Engine for Techne Finance
Complete revenue model with subscriptions, fees, and analytics

Revenue Streams:
1. Subscriptions: $10/$50/$200/month (Pro/Teams/Enterprise)
2. Performance Fees: 0.5% of profits on managed strategies
3. Micropayments: $0.10 per premium query via x402
4. API Access: $500/month for enterprise API

This is how Techne makes money.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import hashlib
import secrets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RevenueEngine")


# ============================================
# SUBSCRIPTION TIERS
# ============================================

class SubscriptionTier(str, Enum):
    FREE = "free"
    PREMIUM = "premium"  # Only one paid tier at $10/month


@dataclass
class TierFeatures:
    """Features available in each tier"""
    tier: SubscriptionTier
    price_monthly_usd: float
    price_yearly_usd: float  # ~17% discount
    
    # Limits
    pools_visible: int  # -1 = unlimited
    ai_queries_per_day: int
    api_calls_per_day: int
    positions_tracked: int
    alerts_per_day: int
    
    # Features
    basic_recommendations: bool = True
    ai_predictions: bool = False
    custom_strategies: bool = False
    priority_support: bool = False
    telegram_alerts: bool = False


# Define tier configurations - Only 2 tiers: Free and Premium
TIER_CONFIGS = {
    SubscriptionTier.FREE: TierFeatures(
        tier=SubscriptionTier.FREE,
        price_monthly_usd=0,
        price_yearly_usd=0,
        pools_visible=20,
        ai_queries_per_day=5,
        api_calls_per_day=100,
        positions_tracked=3,
        alerts_per_day=3,
        basic_recommendations=True,
    ),
    SubscriptionTier.PREMIUM: TierFeatures(
        tier=SubscriptionTier.PREMIUM,
        price_monthly_usd=10,
        price_yearly_usd=100,  # 2 months free
        pools_visible=-1,  # Unlimited
        ai_queries_per_day=200,
        api_calls_per_day=10000,
        positions_tracked=-1,  # Unlimited
        alerts_per_day=-1,  # Unlimited
        basic_recommendations=True,
        ai_predictions=True,
        custom_strategies=True,
        priority_support=True,
        telegram_alerts=True,
    ),
}


# ============================================
# SUBSCRIPTION MANAGEMENT
# ============================================

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    TRIAL = "trial"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass
class Subscription:
    """User subscription"""
    id: str
    user_id: str
    tier: SubscriptionTier
    status: SubscriptionStatus
    
    # Billing
    billing_cycle: str  # "monthly" or "yearly"
    price_usd: float
    currency: str = "USDC"
    
    # Dates
    created_at: datetime = field(default_factory=datetime.now)
    current_period_start: datetime = field(default_factory=datetime.now)
    current_period_end: datetime = field(default_factory=lambda: datetime.now() + timedelta(days=30))
    trial_ends_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    # Payment
    payment_method: str = "x402"  # x402, stripe, crypto
    last_payment_at: Optional[datetime] = None
    next_payment_at: Optional[datetime] = None
    
    # Meta
    auto_renew: bool = True
    payment_history: List[str] = field(default_factory=list)
    
    @property
    def is_active(self) -> bool:
        return self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]
    
    @property
    def days_remaining(self) -> int:
        return max(0, (self.current_period_end - datetime.now()).days)


class SubscriptionManager:
    """Manages all subscriptions"""
    
    def __init__(self):
        self.subscriptions: Dict[str, Subscription] = {}  # subscription_id -> Subscription
        self.user_subscriptions: Dict[str, str] = {}  # user_id -> subscription_id
        
        # Trial settings
        self.trial_days = 7
        self.grace_period_days = 3
    
    def create_subscription(
        self,
        user_id: str,
        tier: SubscriptionTier,
        billing_cycle: str = "monthly",
        start_trial: bool = True
    ) -> Subscription:
        """Create a new subscription"""
        
        # Check if user already has subscription
        if user_id in self.user_subscriptions:
            existing = self.subscriptions.get(self.user_subscriptions[user_id])
            if existing and existing.is_active:
                raise ValueError("User already has active subscription")
        
        tier_config = TIER_CONFIGS[tier]
        
        if billing_cycle == "yearly":
            price = tier_config.price_yearly_usd
            period_days = 365
        else:
            price = tier_config.price_monthly_usd
            period_days = 30
        
        sub_id = self._generate_id("sub")
        now = datetime.now()
        
        subscription = Subscription(
            id=sub_id,
            user_id=user_id,
            tier=tier,
            status=SubscriptionStatus.TRIAL if start_trial and tier != SubscriptionTier.FREE else SubscriptionStatus.ACTIVE,
            billing_cycle=billing_cycle,
            price_usd=price,
            current_period_start=now,
            current_period_end=now + timedelta(days=period_days),
            trial_ends_at=now + timedelta(days=self.trial_days) if start_trial else None,
            next_payment_at=now + timedelta(days=self.trial_days) if start_trial else now,
        )
        
        self.subscriptions[sub_id] = subscription
        self.user_subscriptions[user_id] = sub_id
        
        logger.info(f"Created subscription {sub_id} for user {user_id}: {tier.value}")
        
        return subscription
    
    def get_user_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get user's current subscription"""
        sub_id = self.user_subscriptions.get(user_id)
        if not sub_id:
            return None
        return self.subscriptions.get(sub_id)
    
    def get_user_tier(self, user_id: str) -> SubscriptionTier:
        """Get user's current tier"""
        sub = self.get_user_subscription(user_id)
        if not sub or not sub.is_active:
            return SubscriptionTier.FREE
        return sub.tier
    
    def get_user_features(self, user_id: str) -> TierFeatures:
        """Get features available to user"""
        tier = self.get_user_tier(user_id)
        return TIER_CONFIGS[tier]
    
    def upgrade_subscription(self, user_id: str, new_tier: SubscriptionTier) -> Subscription:
        """Upgrade user's subscription"""
        sub = self.get_user_subscription(user_id)
        
        if not sub:
            return self.create_subscription(user_id, new_tier, start_trial=False)
        
        old_tier = sub.tier
        sub.tier = new_tier
        sub.price_usd = TIER_CONFIGS[new_tier].price_monthly_usd
        sub.status = SubscriptionStatus.ACTIVE
        
        logger.info(f"Upgraded {user_id} from {old_tier.value} to {new_tier.value}")
        
        return sub
    
    def cancel_subscription(self, user_id: str, immediate: bool = False) -> bool:
        """Cancel user's subscription"""
        sub = self.get_user_subscription(user_id)
        if not sub:
            return False
        
        sub.cancelled_at = datetime.now()
        sub.auto_renew = False
        
        if immediate:
            sub.status = SubscriptionStatus.CANCELLED
            sub.current_period_end = datetime.now()
        else:
            # Cancel at end of billing period
            sub.status = SubscriptionStatus.ACTIVE  # Still active until period ends
        
        logger.info(f"Cancelled subscription for {user_id}, immediate={immediate}")
        
        return True
    
    def process_payment(self, user_id: str, tx_hash: str, amount_usd: float) -> bool:
        """Process subscription payment"""
        sub = self.get_user_subscription(user_id)
        if not sub:
            return False
        
        sub.last_payment_at = datetime.now()
        sub.payment_history.append(tx_hash)
        
        # Extend subscription period
        if sub.billing_cycle == "yearly":
            sub.current_period_end = datetime.now() + timedelta(days=365)
        else:
            sub.current_period_end = datetime.now() + timedelta(days=30)
        
        sub.status = SubscriptionStatus.ACTIVE
        sub.next_payment_at = sub.current_period_end
        
        logger.info(f"Processed payment for {user_id}: ${amount_usd}")
        
        return True
    
    def check_limits(self, user_id: str, limit_type: str, current_usage: int) -> tuple[bool, int]:
        """Check if user is within tier limits"""
        features = self.get_user_features(user_id)
        
        limit_map = {
            "pools": features.pools_visible,
            "ai_queries": features.ai_queries_per_day,
            "api_calls": features.api_calls_per_day,
            "positions": features.positions_tracked,
            "alerts": features.alerts_per_day,
        }
        
        limit = limit_map.get(limit_type, 0)
        
        if limit == -1:  # Unlimited
            return True, -1
        
        return current_usage < limit, limit - current_usage
    
    def _generate_id(self, prefix: str) -> str:
        return f"{prefix}_{secrets.token_hex(8)}"


# ============================================
# PERFORMANCE FEES
# ============================================

@dataclass
class PerformanceFee:
    """Performance fee record"""
    id: str
    user_id: str
    pool_id: str
    protocol: str
    
    # Performance
    initial_value_usd: float
    final_value_usd: float
    profit_usd: float
    
    # Fee calculation
    fee_percentage: float  # e.g., 0.5%
    fee_amount_usd: float
    
    # Meta
    period_start: datetime
    period_end: datetime
    collected: bool = False
    collected_at: Optional[datetime] = None
    tx_hash: Optional[str] = None


class FeeCollector:
    """Collects and tracks performance fees"""
    
    def __init__(self, default_fee_percentage: float = 0.5):
        self.default_fee_percentage = default_fee_percentage
        self.fees: Dict[str, PerformanceFee] = {}
        self.user_fees: Dict[str, List[str]] = defaultdict(list)
        
        # Fee tiers (higher profit = lower fee for loyalty)
        self.fee_tiers = {
            0: 0.5,       # Default
            10000: 0.4,   # $10K+ profit: 0.4%
            50000: 0.3,   # $50K+ profit: 0.3%
            100000: 0.25, # $100K+ profit: 0.25%
        }
    
    def calculate_fee(self, user_id: str, profit_usd: float) -> float:
        """Calculate fee percentage based on user history"""
        # Get total historical profit
        total_profit = sum(
            self.fees[fee_id].profit_usd 
            for fee_id in self.user_fees.get(user_id, [])
        )
        
        # Find applicable tier
        applicable_rate = self.default_fee_percentage
        for threshold, rate in sorted(self.fee_tiers.items()):
            if total_profit >= threshold:
                applicable_rate = rate
        
        return applicable_rate
    
    def record_profit(
        self,
        user_id: str,
        pool_id: str,
        protocol: str,
        initial_value: float,
        final_value: float,
        period_start: datetime,
        period_end: datetime
    ) -> Optional[PerformanceFee]:
        """Record profit and calculate fee"""
        
        profit = final_value - initial_value
        
        if profit <= 0:
            return None  # No fee on losses
        
        fee_percentage = self.calculate_fee(user_id, profit)
        fee_amount = profit * (fee_percentage / 100)
        
        fee_id = f"fee_{secrets.token_hex(8)}"
        
        fee = PerformanceFee(
            id=fee_id,
            user_id=user_id,
            pool_id=pool_id,
            protocol=protocol,
            initial_value_usd=initial_value,
            final_value_usd=final_value,
            profit_usd=profit,
            fee_percentage=fee_percentage,
            fee_amount_usd=fee_amount,
            period_start=period_start,
            period_end=period_end
        )
        
        self.fees[fee_id] = fee
        self.user_fees[user_id].append(fee_id)
        
        logger.info(f"Recorded fee for {user_id}: ${fee_amount:.2f} ({fee_percentage}% of ${profit:.2f})")
        
        return fee
    
    def get_pending_fees(self, user_id: str = None) -> List[PerformanceFee]:
        """Get uncollected fees"""
        if user_id:
            fee_ids = self.user_fees.get(user_id, [])
            return [self.fees[fid] for fid in fee_ids if not self.fees[fid].collected]
        else:
            return [f for f in self.fees.values() if not f.collected]
    
    def mark_collected(self, fee_id: str, tx_hash: str) -> bool:
        """Mark fee as collected"""
        if fee_id not in self.fees:
            return False
        
        fee = self.fees[fee_id]
        fee.collected = True
        fee.collected_at = datetime.now()
        fee.tx_hash = tx_hash
        
        return True


# ============================================
# MICROPAYMENTS (x402)
# ============================================

@dataclass
class Micropayment:
    """Single micropayment record"""
    id: str
    user_id: str
    feature: str  # What they're paying for
    amount_usd: float
    
    # Status
    status: str  # pending, confirmed, failed
    created_at: datetime = field(default_factory=datetime.now)
    confirmed_at: Optional[datetime] = None
    tx_hash: Optional[str] = None


class MicropaymentEngine:
    """Handles x402 micropayments for premium features"""
    
    # Feature prices
    FEATURE_PRICES = {
        "ai_query": 0.10,           # Single AI query
        "deep_analysis": 0.50,      # Full pool analysis
        "strategy_backtest": 1.00,  # Backtest a strategy
        "whale_alert": 0.25,        # Instant whale alert
        "pool_unlock": 0.10,        # Unlock pool details
        "priority_data": 0.05,      # Priority data refresh
    }
    
    def __init__(self):
        self.payments: Dict[str, Micropayment] = {}
        self.user_credits: Dict[str, float] = defaultdict(float)  # Prepaid credits
        self.user_payments: Dict[str, List[str]] = defaultdict(list)
    
    def get_price(self, feature: str) -> float:
        """Get price for a feature"""
        return self.FEATURE_PRICES.get(feature, 0.10)
    
    def create_payment_request(
        self,
        user_id: str,
        feature: str
    ) -> Dict:
        """Create x402 payment request"""
        
        price = self.get_price(feature)
        payment_id = f"mp_{secrets.token_hex(8)}"
        
        payment = Micropayment(
            id=payment_id,
            user_id=user_id,
            feature=feature,
            amount_usd=price,
            status="pending"
        )
        
        self.payments[payment_id] = payment
        self.user_payments[user_id].append(payment_id)
        
        # Return x402 headers format
        return {
            "payment_id": payment_id,
            "amount_usd": price,
            "amount_usdc": price * 1_000_000,  # USDC has 6 decimals
            "recipient": "0x742d35Cc6634C0532925a3b844Bc9e7595f",  # Treasury
            "network": "base",
            "token": "USDC",
            "expires_at": (datetime.now() + timedelta(minutes=15)).isoformat(),
            "x402_header": {
                "X-Payment-Required": "true",
                "X-Payment-Amount": str(int(price * 1_000_000)),
                "X-Payment-Token": "USDC",
                "X-Payment-Network": "base",
            }
        }
    
    def confirm_payment(self, payment_id: str, tx_hash: str) -> bool:
        """Confirm payment received"""
        if payment_id not in self.payments:
            return False
        
        payment = self.payments[payment_id]
        payment.status = "confirmed"
        payment.confirmed_at = datetime.now()
        payment.tx_hash = tx_hash
        
        logger.info(f"Micropayment confirmed: {payment_id} for {payment.feature}")
        
        return True
    
    def has_access(self, user_id: str, feature: str, payment_id: str = None) -> bool:
        """Check if user has paid for feature"""
        if payment_id:
            payment = self.payments.get(payment_id)
            return payment and payment.status == "confirmed" and payment.feature == feature
        
        # Check for any recent confirmed payment for this feature
        for pid in self.user_payments.get(user_id, []):
            payment = self.payments[pid]
            if payment.feature == feature and payment.status == "confirmed":
                # Check if payment is recent (last 24 hours)
                if payment.confirmed_at and (datetime.now() - payment.confirmed_at).days < 1:
                    return True
        
        return False
    
    def add_credits(self, user_id: str, amount_usd: float) -> float:
        """Add prepaid credits to user account"""
        self.user_credits[user_id] += amount_usd
        return self.user_credits[user_id]
    
    def use_credits(self, user_id: str, feature: str) -> bool:
        """Use credits for a feature"""
        price = self.get_price(feature)
        
        if self.user_credits[user_id] >= price:
            self.user_credits[user_id] -= price
            logger.info(f"Used ${price} credits for {user_id}: {feature}")
            return True
        
        return False


# ============================================
# REVENUE ANALYTICS
# ============================================

class RevenueAnalytics:
    """Tracks revenue metrics"""
    
    def __init__(
        self,
        subscription_manager: SubscriptionManager,
        fee_collector: FeeCollector,
        micropayment_engine: MicropaymentEngine
    ):
        self.subscriptions = subscription_manager
        self.fees = fee_collector
        self.micropayments = micropayment_engine
    
    def get_mrr(self) -> float:
        """Calculate Monthly Recurring Revenue"""
        mrr = 0
        for sub in self.subscriptions.subscriptions.values():
            if sub.is_active:
                if sub.billing_cycle == "yearly":
                    mrr += sub.price_usd / 12
                else:
                    mrr += sub.price_usd
        return mrr
    
    def get_arr(self) -> float:
        """Calculate Annual Recurring Revenue"""
        return self.get_mrr() * 12
    
    def get_revenue_breakdown(self) -> Dict:
        """Get revenue by source"""
        subscription_revenue = sum(
            s.price_usd for s in self.subscriptions.subscriptions.values()
            if s.last_payment_at and (datetime.now() - s.last_payment_at).days < 30
        )
        
        fee_revenue = sum(
            f.fee_amount_usd for f in self.fees.fees.values()
            if f.collected and f.collected_at and (datetime.now() - f.collected_at).days < 30
        )
        
        micropayment_revenue = sum(
            p.amount_usd for p in self.micropayments.payments.values()
            if p.status == "confirmed" and (datetime.now() - p.confirmed_at).days < 30
        )
        
        total = subscription_revenue + fee_revenue + micropayment_revenue
        
        return {
            "total_30d": total,
            "subscriptions": subscription_revenue,
            "performance_fees": fee_revenue,
            "micropayments": micropayment_revenue,
            "mrr": self.get_mrr(),
            "arr": self.get_arr(),
        }
    
    def get_user_ltv(self, user_id: str) -> float:
        """Calculate user Lifetime Value"""
        # Subscription revenue
        sub = self.subscriptions.get_user_subscription(user_id)
        sub_ltv = 0
        if sub:
            payments = len(sub.payment_history)
            sub_ltv = sub.price_usd * payments
        
        # Fee revenue
        fee_ltv = sum(
            self.fees.fees[fid].fee_amount_usd
            for fid in self.fees.user_fees.get(user_id, [])
            if self.fees.fees[fid].collected
        )
        
        # Micropayment revenue
        mp_ltv = sum(
            self.micropayments.payments[pid].amount_usd
            for pid in self.micropayments.user_payments.get(user_id, [])
            if self.micropayments.payments[pid].status == "confirmed"
        )
        
        return sub_ltv + fee_ltv + mp_ltv
    
    def get_conversion_metrics(self) -> Dict:
        """Get conversion funnel metrics"""
        total_users = len(self.subscriptions.user_subscriptions)
        
        free_users = sum(1 for s in self.subscriptions.subscriptions.values() if s.tier == SubscriptionTier.FREE)
        premium_users = sum(1 for s in self.subscriptions.subscriptions.values() if s.tier == SubscriptionTier.PREMIUM)
        
        return {
            "total_users": total_users,
            "free_users": free_users,
            "premium_users": premium_users,
            "conversion_rate": (premium_users / total_users * 100) if total_users > 0 else 0,
            "by_tier": {
                "free": free_users,
                "premium": premium_users,
            }
        }


# ============================================
# GLOBAL INSTANCES
# ============================================

subscription_manager = SubscriptionManager()
fee_collector = FeeCollector()
micropayment_engine = MicropaymentEngine()
revenue_analytics = RevenueAnalytics(subscription_manager, fee_collector, micropayment_engine)


def get_subscription_manager() -> SubscriptionManager:
    return subscription_manager


def get_fee_collector() -> FeeCollector:
    return fee_collector


def get_micropayment_engine() -> MicropaymentEngine:
    return micropayment_engine


def get_revenue_analytics() -> RevenueAnalytics:
    return revenue_analytics
