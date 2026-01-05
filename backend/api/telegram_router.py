"""
Techne Telegram Bot - API Router
FastAPI endpoints for Telegram integration
"""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telegram", tags=["Telegram"])


# ===========================================
# Models
# ===========================================

class WebhookUpdate(BaseModel):
    """Telegram webhook update"""
    update_id: int
    message: Optional[dict] = None
    callback_query: Optional[dict] = None


class AgentNotification(BaseModel):
    """Notification from agent system"""
    wallet_address: str
    event_type: str  # "deposit", "withdraw", "rebalance", "alert"
    protocol: Optional[str] = None
    symbol: Optional[str] = None
    amount: Optional[float] = None
    token: Optional[str] = None
    tx_hash: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None


class AlertBroadcast(BaseModel):
    """Broadcast alert to all users"""
    message: str
    premium_only: bool = False


class UserLookup(BaseModel):
    """Lookup user by wallet"""
    wallet_address: str


# ===========================================
# Endpoints
# ===========================================

@router.get("/health")
async def health():
    """Health check"""
    return {"status": "ok", "service": "techne-telegram-bot"}


@router.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Telegram webhook endpoint (for production deployment)
    """
    try:
        update = await request.json()
        
        # Process update in background
        from ..telegram.bot import get_bot
        bot = get_bot()
        
        # This would be implemented with aiogram's webhook handling
        # For now, we use polling mode
        
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notify/agent")
async def notify_agent_action(notification: AgentNotification, background_tasks: BackgroundTasks):
    """
    Send notification about agent action to user
    Called by the agent system when actions occur
    """
    try:
        from ..telegram.models.user_config import user_store
        from ..telegram.bot import get_bot
        from ..telegram.services.agent_status import format_agent_action
        
        # Find user by wallet
        # In production, we'd have a wallet->telegram_id mapping
        # For now, search all users
        users = await user_store.get_all_with_alerts()
        
        target_user = None
        for user in users:
            if user.wallet_address and user.wallet_address.lower() == notification.wallet_address.lower():
                target_user = user
                break
        
        if not target_user:
            return {"ok": False, "error": "User not found"}
        
        if not target_user.agent_notifications:
            return {"ok": False, "error": "User has agent notifications disabled"}
        
        # Format message
        message = format_agent_action({
            "type": notification.event_type,
            "protocol": notification.protocol,
            "symbol": notification.symbol,
            "amount": notification.amount,
            "token": notification.token,
            "tx_hash": notification.tx_hash,
            "status": notification.status
        })
        
        # Send in background
        async def send():
            bot = get_bot()
            await bot.send_alert(target_user.telegram_id, message)
        
        background_tasks.add_task(send)
        
        return {"ok": True, "sent_to": target_user.telegram_id}
        
    except Exception as e:
        logger.error(f"Agent notification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/broadcast")
async def broadcast_alert(data: AlertBroadcast, background_tasks: BackgroundTasks):
    """
    Broadcast alert to all users (admin only)
    """
    try:
        from ..telegram.bot import get_bot
        
        async def send():
            bot = get_bot()
            count = await bot.broadcast(data.message, data.premium_only)
            logger.info(f"Broadcast sent to {count} users")
        
        background_tasks.add_task(send)
        
        return {"ok": True, "status": "broadcasting"}
        
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{wallet_address}")
async def get_user_by_wallet(wallet_address: str):
    """
    Lookup Telegram user by wallet address
    """
    try:
        from ..telegram.models.user_config import user_store
        
        users = await user_store.get_all_with_alerts()
        
        for user in users:
            if user.wallet_address and user.wallet_address.lower() == wallet_address.lower():
                return {
                    "found": True,
                    "telegram_id": user.telegram_id,
                    "is_premium": user.is_premium,
                    "alerts_enabled": user.alerts_enabled
                }
        
        return {"found": False}
        
    except Exception as e:
        logger.error(f"User lookup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-premium")
async def verify_premium(wallet_address: str, telegram_id: int):
    """
    Verify premium subscription and link to Telegram
    Called from web app after successful payment
    """
    try:
        from ..telegram.models.user_config import user_store
        from ..telegram.bot import get_bot
        from datetime import datetime, timedelta
        
        # Get or create user config
        config = await user_store.get_or_create_config(telegram_id)
        
        # Update premium status
        config.is_premium = True
        config.wallet_address = wallet_address
        config.premium_expires = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        await user_store.save_config(config)
        
        # Send confirmation
        bot = get_bot()
        await bot.send_alert(
            telegram_id,
            "💎 *Premium Activated!*\n\n"
            f"Wallet: `{wallet_address[:10]}...`\n\n"
            "You now have access to:\n"
            "• 🐋 Whale alerts\n"
            "• 📊 Advanced analytics\n"
            "• ⚡ Priority notifications\n\n"
            "Use /premium to view your status."
        )
        
        return {"ok": True, "premium_until": config.premium_expires}
        
    except Exception as e:
        logger.error(f"Premium verification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_bot_stats():
    """
    Get bot usage statistics
    """
    try:
        from ..telegram.models.user_config import user_store
        
        all_users = await user_store.get_all_with_alerts()
        premium_users = await user_store.get_premium_users()
        
        return {
            "total_users": len(all_users),
            "premium_users": len(premium_users),
            "alerts_enabled": sum(1 for u in all_users if u.alerts_enabled),
            "agents_connected": sum(1 for u in all_users if u.wallet_address)
        }
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# Premium Codes Database (In-memory for MVP)
# ===========================================

import hashlib
import secrets
from datetime import datetime, timedelta

# Premium activation codes store
# In production, use a proper database
_premium_codes: dict = {}


def generate_premium_code(wallet_address: str, tx_hash: str) -> str:
    """
    Generate a unique premium activation code tied to a payment
    """
    # Create deterministic but unique code
    seed = f"{wallet_address}:{tx_hash}:{secrets.token_hex(4)}"
    code = hashlib.sha256(seed.encode()).hexdigest()[:12].upper()
    
    # Format as XXXX-XXXX-XXXX
    formatted = f"{code[:4]}-{code[4:8]}-{code[8:12]}"
    
    # Store with metadata
    _premium_codes[formatted] = {
        "wallet_address": wallet_address,
        "tx_hash": tx_hash,
        "created_at": datetime.utcnow().isoformat(),
        "used": False,
        "used_by": None
    }
    
    return formatted


def validate_premium_code(code: str) -> Optional[dict]:
    """
    Validate and consume a premium code
    """
    code = code.strip().upper()
    
    if code in _premium_codes:
        code_data = _premium_codes[code]
        if not code_data["used"]:
            return code_data
    
    return None


def mark_code_used(code: str, telegram_id: int):
    """
    Mark a code as used
    """
    code = code.strip().upper()
    if code in _premium_codes:
        _premium_codes[code]["used"] = True
        _premium_codes[code]["used_by"] = telegram_id


# ===========================================
# x402 Payment Verification
# ===========================================

class X402PaymentRequest(BaseModel):
    """x402 payment verification request"""
    wallet_address: str
    tx_hash: str
    amount_usdc: float
    chain: str = "base"


@router.post("/x402/verify-payment")
async def verify_x402_payment(payment: X402PaymentRequest, background_tasks: BackgroundTasks):
    """
    Verify x402 payment and generate premium activation code
    Called by web app after successful USDC payment
    """
    try:
        # Verify minimum payment (10 USDC for monthly)
        if payment.amount_usdc < 10:
            raise HTTPException(status_code=400, detail="Minimum payment is 10 USDC")
        
        # Generate activation code
        code = generate_premium_code(payment.wallet_address, payment.tx_hash)
        
        logger.info(f"Generated premium code {code} for wallet {payment.wallet_address[:10]}...")
        
        return {
            "ok": True,
            "activation_code": code,
            "message": f"Use this code in Telegram bot: /activate {code}",
            "valid_for": "30 days"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"x402 verification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/activate-by-code")
async def activate_premium_by_code(code: str, telegram_id: int, background_tasks: BackgroundTasks):
    """
    Activate premium using a code (called by bot's /activate command)
    """
    try:
        from ..telegram.models.user_config import user_store
        from ..telegram.bot import get_bot
        
        # Validate code
        code_data = validate_premium_code(code)
        
        if not code_data:
            return {"ok": False, "error": "Invalid or already used code"}
        
        # Get or create user config
        config = await user_store.get_or_create_config(telegram_id)
        
        # Activate premium
        config.is_premium = True
        config.wallet_address = code_data["wallet_address"]
        config.premium_expires = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        await user_store.save_config(config)
        
        # Mark code as used
        mark_code_used(code, telegram_id)
        
        # Send confirmation
        async def send_confirmation():
            try:
                bot = get_bot()
                await bot.send_alert(
                    telegram_id,
                    "💎 *Premium Activated!*\n\n"
                    f"Code: `{code}`\n"
                    f"Valid until: {config.premium_expires[:10]}\n\n"
                    "You now have full access to:\n"
                    "• 🎯 AI Recommendations\n"
                    "• 🐋 Whale alerts\n"
                    "• 📊 Advanced analytics\n"
                    "• ⚡ Real-time notifications\n\n"
                    "Use /recommend to get started!"
                )
            except Exception as e:
                logger.error(f"Failed to send confirmation: {e}")
        
        background_tasks.add_task(send_confirmation)
        
        return {
            "ok": True,
            "premium_until": config.premium_expires,
            "wallet": code_data["wallet_address"]
        }
        
    except Exception as e:
        logger.error(f"Code activation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/codes/{wallet_address}")
async def get_codes_for_wallet(wallet_address: str):
    """
    Get all codes generated for a wallet (for user reference)
    """
    wallet_codes = [
        {
            "code": code,
            "created_at": data["created_at"],
            "used": data["used"]
        }
        for code, data in _premium_codes.items()
        if data["wallet_address"].lower() == wallet_address.lower()
    ]
    
    return {"codes": wallet_codes}

