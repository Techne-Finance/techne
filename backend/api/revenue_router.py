"""
Revenue API Router
Endpoints for subscriptions, payments, and revenue analytics
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

router = APIRouter(prefix="/api/revenue", tags=["Revenue"])


# Lazy imports
def get_managers():
    from revenue import subscription_manager, fee_collector, micropayment_engine, revenue_analytics
    return subscription_manager, fee_collector, micropayment_engine, revenue_analytics


# ============================================
# MODELS
# ============================================

class CreateSubscriptionRequest(BaseModel):
    user_id: str
    tier: str  # free or premium
    billing_cycle: str = "monthly"
    start_trial: bool = True


class UpgradeSubscriptionRequest(BaseModel):
    user_id: str
    new_tier: str


class PaymentConfirmRequest(BaseModel):
    user_id: str
    tx_hash: str
    amount_usd: float


class MicropaymentRequest(BaseModel):
    user_id: str
    feature: str


class RecordProfitRequest(BaseModel):
    user_id: str
    pool_id: str
    protocol: str
    initial_value_usd: float
    final_value_usd: float
    period_days: int


# ============================================
# PRICING & TIERS
# ============================================

@router.get("/tiers")
async def get_subscription_tiers():
    """Get subscription tiers: Free and Premium ($10/mo)"""
    from revenue import TIER_CONFIGS, SubscriptionTier
    
    tiers = []
    for tier in SubscriptionTier:
        config = TIER_CONFIGS[tier]
        tiers.append({
            "tier": tier.value,
            "price_monthly": config.price_monthly_usd,
            "price_yearly": config.price_yearly_usd,
            "yearly_savings": round((config.price_monthly_usd * 12 - config.price_yearly_usd), 2),
            "features": {
                "pools_visible": "Unlimited" if config.pools_visible == -1 else config.pools_visible,
                "ai_queries_per_day": "Unlimited" if config.ai_queries_per_day == -1 else config.ai_queries_per_day,
                "api_calls_per_day": "Unlimited" if config.api_calls_per_day == -1 else config.api_calls_per_day,
                "positions_tracked": "Unlimited" if config.positions_tracked == -1 else config.positions_tracked,
                "alerts_per_day": "Unlimited" if config.alerts_per_day == -1 else config.alerts_per_day,
                "ai_predictions": config.ai_predictions,
                "custom_strategies": config.custom_strategies,
                "priority_support": config.priority_support,
                "telegram_alerts": getattr(config, 'telegram_alerts', False),
            }
        })
    
    return {
        "success": True,
        "tiers": tiers,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/micropayments/prices")
async def get_micropayment_prices():
    """Get prices for micropayment features"""
    from revenue import MicropaymentEngine
    
    return {
        "success": True,
        "prices": MicropaymentEngine.FEATURE_PRICES,
        "currency": "USD",
        "payment_method": "x402 (USDC on Base)",
        "timestamp": datetime.now().isoformat()
    }


# ============================================
# SUBSCRIPTION MANAGEMENT
# ============================================

@router.post("/subscriptions/create")
async def create_subscription(request: CreateSubscriptionRequest):
    """Create a new subscription for a user"""
    try:
        from revenue import SubscriptionTier
        
        sub_manager, _, _, _ = get_managers()
        
        tier = SubscriptionTier(request.tier)
        
        subscription = sub_manager.create_subscription(
            user_id=request.user_id,
            tier=tier,
            billing_cycle=request.billing_cycle,
            start_trial=request.start_trial
        )
        
        return {
            "success": True,
            "subscription": {
                "id": subscription.id,
                "tier": subscription.tier.value,
                "status": subscription.status.value,
                "price_usd": subscription.price_usd,
                "billing_cycle": subscription.billing_cycle,
                "current_period_end": subscription.current_period_end.isoformat(),
                "trial_ends_at": subscription.trial_ends_at.isoformat() if subscription.trial_ends_at else None,
            },
            "timestamp": datetime.now().isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscriptions/{user_id}")
async def get_user_subscription(user_id: str):
    """Get user's current subscription"""
    sub_manager, _, _, _ = get_managers()
    
    subscription = sub_manager.get_user_subscription(user_id)
    features = sub_manager.get_user_features(user_id)
    
    if not subscription:
        return {
            "success": True,
            "subscription": None,
            "tier": "free",
            "features": {
                "pools_visible": features.pools_visible,
                "ai_queries_per_day": features.ai_queries_per_day,
            },
            "timestamp": datetime.now().isoformat()
        }
    
    return {
        "success": True,
        "subscription": {
            "id": subscription.id,
            "tier": subscription.tier.value,
            "status": subscription.status.value,
            "is_active": subscription.is_active,
            "price_usd": subscription.price_usd,
            "billing_cycle": subscription.billing_cycle,
            "days_remaining": subscription.days_remaining,
            "current_period_end": subscription.current_period_end.isoformat(),
            "auto_renew": subscription.auto_renew,
        },
        "features": {
            "pools_visible": "Unlimited" if features.pools_visible == -1 else features.pools_visible,
            "ai_queries_per_day": "Unlimited" if features.ai_queries_per_day == -1 else features.ai_queries_per_day,
            "ai_predictions": features.ai_predictions,
            "custom_strategies": features.custom_strategies,
        },
        "timestamp": datetime.now().isoformat()
    }


@router.post("/subscriptions/upgrade")
async def upgrade_subscription(request: UpgradeSubscriptionRequest):
    """Upgrade user's subscription"""
    try:
        from revenue import SubscriptionTier
        
        sub_manager, _, _, _ = get_managers()
        
        new_tier = SubscriptionTier(request.new_tier)
        subscription = sub_manager.upgrade_subscription(request.user_id, new_tier)
        
        return {
            "success": True,
            "subscription": {
                "id": subscription.id,
                "tier": subscription.tier.value,
                "price_usd": subscription.price_usd,
            },
            "message": f"Upgraded to {new_tier.value}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions/cancel")
async def cancel_subscription(user_id: str, immediate: bool = False):
    """Cancel user's subscription"""
    sub_manager, _, _, _ = get_managers()
    
    success = sub_manager.cancel_subscription(user_id, immediate)
    
    return {
        "success": success,
        "message": "Subscription cancelled" if success else "No subscription found",
        "immediate": immediate,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/subscriptions/payment")
async def process_subscription_payment(request: PaymentConfirmRequest):
    """Process subscription payment"""
    sub_manager, _, _, _ = get_managers()
    
    success = sub_manager.process_payment(
        request.user_id,
        request.tx_hash,
        request.amount_usd
    )
    
    return {
        "success": success,
        "message": "Payment processed" if success else "Payment failed",
        "timestamp": datetime.now().isoformat()
    }


# ============================================
# MICROPAYMENTS
# ============================================

@router.post("/micropayments/request")
async def create_micropayment(request: MicropaymentRequest):
    """Create a micropayment request (x402)"""
    _, _, mp_engine, _ = get_managers()
    
    payment_request = mp_engine.create_payment_request(
        user_id=request.user_id,
        feature=request.feature
    )
    
    return {
        "success": True,
        "payment_request": payment_request,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/micropayments/confirm")
async def confirm_micropayment(payment_id: str, tx_hash: str):
    """Confirm micropayment received"""
    _, _, mp_engine, _ = get_managers()
    
    success = mp_engine.confirm_payment(payment_id, tx_hash)
    
    return {
        "success": success,
        "message": "Payment confirmed" if success else "Payment not found",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/micropayments/access")
async def check_feature_access(user_id: str, feature: str, payment_id: str = None):
    """Check if user has access to a paid feature"""
    _, _, mp_engine, _ = get_managers()
    
    has_access = mp_engine.has_access(user_id, feature, payment_id)
    
    return {
        "success": True,
        "has_access": has_access,
        "feature": feature,
        "price_if_not": mp_engine.get_price(feature) if not has_access else None,
        "timestamp": datetime.now().isoformat()
    }


# ============================================
# PERFORMANCE FEES
# ============================================

@router.post("/fees/record-profit")
async def record_profit(request: RecordProfitRequest):
    """Record profit and calculate performance fee"""
    _, fee_collector, _, _ = get_managers()
    
    fee = fee_collector.record_profit(
        user_id=request.user_id,
        pool_id=request.pool_id,
        protocol=request.protocol,
        initial_value=request.initial_value_usd,
        final_value=request.final_value_usd,
        period_start=datetime.now() - timedelta(days=request.period_days),
        period_end=datetime.now()
    )
    
    if not fee:
        return {
            "success": True,
            "message": "No profit to record fee",
            "timestamp": datetime.now().isoformat()
        }
    
    return {
        "success": True,
        "fee": {
            "id": fee.id,
            "profit_usd": fee.profit_usd,
            "fee_percentage": fee.fee_percentage,
            "fee_amount_usd": fee.fee_amount_usd,
        },
        "timestamp": datetime.now().isoformat()
    }


@router.get("/fees/pending")
async def get_pending_fees(user_id: str = None):
    """Get pending (uncollected) fees"""
    _, fee_collector, _, _ = get_managers()
    
    fees = fee_collector.get_pending_fees(user_id)
    
    return {
        "success": True,
        "fees": [
            {
                "id": f.id,
                "pool_id": f.pool_id,
                "protocol": f.protocol,
                "profit_usd": f.profit_usd,
                "fee_amount_usd": f.fee_amount_usd,
            }
            for f in fees
        ],
        "total_pending_usd": sum(f.fee_amount_usd for f in fees),
        "timestamp": datetime.now().isoformat()
    }


# ============================================
# ANALYTICS
# ============================================

@router.get("/analytics")
async def get_revenue_analytics():
    """Get revenue analytics (admin)"""
    _, _, _, analytics = get_managers()
    
    breakdown = analytics.get_revenue_breakdown()
    conversion = analytics.get_conversion_metrics()
    
    return {
        "success": True,
        "revenue": breakdown,
        "conversion": conversion,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/analytics/user/{user_id}")
async def get_user_ltv(user_id: str):
    """Get user Lifetime Value"""
    _, _, _, analytics = get_managers()
    
    ltv = analytics.get_user_ltv(user_id)
    
    return {
        "success": True,
        "user_id": user_id,
        "ltv_usd": ltv,
        "timestamp": datetime.now().isoformat()
    }


# Import timedelta for fees endpoint
from datetime import timedelta
