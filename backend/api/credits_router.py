"""
Credits API Router — Per-wallet credit balance stored in Supabase
Endpoints: GET balance, POST add, POST use, POST init (welcome bonus)
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

from infrastructure.supabase_rest import get_supabase_rest

logger = logging.getLogger("CreditsAPI")
router = APIRouter(prefix="/api/credits", tags=["Credits"])

# Constants (mirrored from frontend CREDIT_COSTS)
WELCOME_BONUS = 50
PREMIUM_DAILY = 500


class CreditUpdate(BaseModel):
    user_address: str
    amount: int


class CreditUse(BaseModel):
    user_address: str
    cost: int


# ── GET /api/credits?user_address=0x... ──
@router.get("")
async def get_credits(user_address: str = Query(...)):
    """Get credit balance for a wallet address"""
    sb = get_supabase_rest()
    result = sb.table("user_credits") \
        .select("credits,welcome_bonus_claimed") \
        .eq("user_address", user_address.lower()) \
        .execute()

    if result.data:
        row = result.data[0] if isinstance(result.data, list) else result.data
        return {
            "credits": row.get("credits", 0),
            "welcome_bonus_claimed": row.get("welcome_bonus_claimed", False)
        }
    return {"credits": 0, "welcome_bonus_claimed": False}


# ── POST /api/credits/init ──
@router.post("/init")
async def init_credits(body: CreditUpdate):
    """Initialize credits for new wallet (welcome bonus)"""
    addr = body.user_address.lower()
    sb = get_supabase_rest()

    # Check if user already exists
    existing = sb.table("user_credits") \
        .select("credits,welcome_bonus_claimed") \
        .eq("user_address", addr) \
        .execute()

    if existing.data:
        row = existing.data[0] if isinstance(existing.data, list) else existing.data
        if row.get("welcome_bonus_claimed"):
            return {"credits": row.get("credits", 0), "bonus_given": False}

        # Existing user who hasn't claimed bonus yet
        new_credits = row.get("credits", 0) + WELCOME_BONUS
        sb.table("user_credits") \
            .update({"credits": new_credits, "welcome_bonus_claimed": True, "updated_at": datetime.now().isoformat()}) \
            .eq("user_address", addr) \
            .execute()
        return {"credits": new_credits, "bonus_given": True}

    # New user — create with welcome bonus
    sb.table("user_credits") \
        .insert({
            "user_address": addr,
            "credits": WELCOME_BONUS,
            "welcome_bonus_claimed": True,
        }) \
        .execute()
    return {"credits": WELCOME_BONUS, "bonus_given": True}


# ── POST /api/credits/add ──
@router.post("/add")
async def add_credits(body: CreditUpdate):
    """Add credits to a wallet (purchase, premium daily, etc.)"""
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    addr = body.user_address.lower()
    sb = get_supabase_rest()

    existing = sb.table("user_credits") \
        .select("credits") \
        .eq("user_address", addr) \
        .execute()

    if existing.data:
        row = existing.data[0] if isinstance(existing.data, list) else existing.data
        new_credits = row.get("credits", 0) + body.amount
        sb.table("user_credits") \
            .update({"credits": new_credits, "updated_at": datetime.now().isoformat()}) \
            .eq("user_address", addr) \
            .execute()
    else:
        new_credits = body.amount
        sb.table("user_credits") \
            .insert({"user_address": addr, "credits": new_credits}) \
            .execute()

    return {"credits": new_credits}


# ── POST /api/credits/use ──
@router.post("/use")
async def use_credits(body: CreditUse):
    """Use credits from a wallet balance"""
    if body.cost <= 0:
        raise HTTPException(status_code=400, detail="Cost must be positive")

    addr = body.user_address.lower()
    sb = get_supabase_rest()

    existing = sb.table("user_credits") \
        .select("credits") \
        .eq("user_address", addr) \
        .execute()

    if not existing.data:
        raise HTTPException(status_code=402, detail="Insufficient credits")

    row = existing.data[0] if isinstance(existing.data, list) else existing.data
    current = row.get("credits", 0)

    if current < body.cost:
        raise HTTPException(status_code=402, detail="Insufficient credits")

    new_credits = current - body.cost
    sb.table("user_credits") \
        .update({"credits": new_credits, "updated_at": datetime.now().isoformat()}) \
        .eq("user_address", addr) \
        .execute()

    return {"credits": new_credits, "used": body.cost}
