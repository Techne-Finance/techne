"""
Premium Subscription API Router
Handles Techne Artisan ($99/mo) subscriptions with Artisan Agent
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import secrets
import logging
import os
import httpx


logger = logging.getLogger("PremiumAPI")

router = APIRouter(prefix="/api/premium", tags=["Premium"])

# ============================================
# MODELS
# ============================================

class SubscribeRequest(BaseModel):
    """Request to subscribe to Premium"""
    user_address: str
    x402_payment_id: Optional[str] = None  # Meridian payment ID

class ValidateCodeRequest(BaseModel):
    """Validate activation code from Telegram"""
    activation_code: str
    telegram_chat_id: int
    telegram_username: Optional[str] = None

class ChangeAutonomyRequest(BaseModel):
    """Change autonomy mode"""
    user_address: str
    mode: str  # observer, advisor, copilot, full_auto

class DisconnectRequest(BaseModel):
    """Disconnect/cancel subscription"""
    user_address: str


class ValidateSessionRequest(BaseModel):
    """Validate session key from OpenClaw"""
    session_key: str


# ============================================
# HELPERS
# ============================================

def get_supabase():
    """Get Supabase REST client (shared module, no SDK dependency)"""
    from infrastructure.supabase_rest import SupabaseREST
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    return SupabaseREST(url, key)

def generate_activation_code() -> str:
    """Generate unique activation code: ARTISAN-XXXX-XXXX"""
    part1 = secrets.token_hex(2).upper()
    part2 = secrets.token_hex(2).upper()
    return f"ARTISAN-{part1}-{part2}"

# ============================================
# ENDPOINTS
# ============================================

# Treasury address for receiving payments
TREASURY_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f8fE00"  # TODO: Update to your treasury
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
SUBSCRIPTION_PRICE_USDC = 99_000_000  # $99 in USDC (6 decimals)


@router.get("/payment-requirements")
async def get_payment_requirements():
    """
    Get x402 payment requirements for $99 Artisan Bot subscription.
    Frontend uses this to build EIP-712 signature request.
    """
    return {
        "usdcAddress": USDC_BASE,
        "recipientAddress": TREASURY_ADDRESS,
        "amount": str(SUBSCRIPTION_PRICE_USDC),
        "chainId": 8453,  # Base
        "productName": "Artisan Bot",
        "productDescription": "AI Trading Agent - 30 day subscription",
        "priceUsd": "99.00"
    }


class SubscribeWithPaymentRequest(BaseModel):
    """Subscribe request with x402 payment payload"""
    wallet_address: str
    paymentPayload: dict  # x402 payload from frontend
    meridian_tx: Optional[str] = None  # Meridian transaction hash after settlement


@router.post("/subscribe")
async def subscribe_premium(request: SubscribeWithPaymentRequest):
    """
    Subscribe to Techne Artisan Bot ($99/mo) via x402 Meridian payment.
    
    Flow:
    1. Frontend signs EIP-712 TransferWithAuthorization
    2. Frontend calls this with payment payload
    3. We verify and settle via Meridian (or direct)
    4. Generate activation code
    5. User enters code in Telegram bot
    """
    try:
        supabase = get_supabase()
        user_address = request.wallet_address.lower()
        
        # Extract payment info for logging
        payment_sig = request.paymentPayload.get("payload", {}).get("signature", "")[:20]
        
        # ── PRE-CHECK: Don't charge if already active ──
        existing = supabase.table("premium_subscriptions").select("*").eq(
            "user_address", user_address
        ).execute()
        
        if existing.data:
            sub = existing.data[0]
            if sub["status"] == "active":
                return {
                    "success": True,
                    "already_subscribed": True,
                    "activation_code": sub["activation_code"],
                    "expires_at": sub["expires_at"],
                    "message": "Already subscribed! Use your existing code."
                }
        
        # ── STEP 1: Verify & settle payment through Meridian ──
        # Without this, anyone could send a fake payload and get free premium
        MERIDIAN_API_URL = "https://api.mrdn.finance/v1"
        MERIDIAN_PK = os.getenv("MERIDIAN_PUBLIC_KEY", "pk_9e408b7d2b5068cc1b5e2d9c01c62660ac3705d6f3173bbeea729b647450e16f")
        MERIDIAN_CONTRACT = "0x8E7769D440b3460b92159Dd9C6D17302b036e2d6"
        MERIDIAN_RECIPIENT = os.getenv("MERIDIAN_RECIPIENT", "0xa30A689ec0F9D717C5bA1098455B031b868B720f")
        
        payment_requirements = {
            "recipient": MERIDIAN_RECIPIENT,
            "network": "base",
            "asset": USDC_BASE,
            "scheme": "exact",
            "payTo": MERIDIAN_CONTRACT,
            "maxTimeoutSeconds": 3600,
            "resource": "https://techne.finance/premium",
            "description": "Artisan Bot - 30 day subscription",
            "mimeType": "application/json",
            "amount": str(SUBSCRIPTION_PRICE_USDC),
            "maxAmountRequired": str(SUBSCRIPTION_PRICE_USDC)
        }
        
        meridian_tx = None
        async with httpx.AsyncClient(timeout=30) as client:
            # Verify payment signature
            logger.info(f"[Premium] Verifying payment for {user_address[:10]}...")
            verify_resp = await client.post(
                f"{MERIDIAN_API_URL}/verify",
                headers={
                    "Authorization": f"Bearer {MERIDIAN_PK}",
                    "Content-Type": "application/json"
                },
                json={
                    "paymentPayload": request.paymentPayload,
                    "paymentRequirements": payment_requirements
                }
            )
            verify_data = verify_resp.json()
            logger.info(f"[Premium] Verify response: {verify_data}")
            
            if not verify_data.get("isValid"):
                raise HTTPException(
                    status_code=402,
                    detail=f"Payment invalid: {verify_data.get('invalidReason', 'Unknown')}"
                )
            
            # Settle payment (actually move the USDC)
            logger.info(f"[Premium] Settling payment for {user_address[:10]}...")
            settle_resp = await client.post(
                f"{MERIDIAN_API_URL}/settle",
                headers={
                    "Authorization": f"Bearer {MERIDIAN_PK}",
                    "Content-Type": "application/json"
                },
                json={
                    "paymentPayload": request.paymentPayload,
                    "paymentRequirements": payment_requirements
                }
            )
            settle_data = settle_resp.json()
            logger.info(f"[Premium] Settle response: {settle_data}")
            
            if not settle_data.get("success"):
                error_msg = settle_data.get('errorReason') or settle_data.get('error') or 'Settlement failed'
                raise HTTPException(status_code=402, detail=f"Payment settlement failed: {error_msg}")
            
            meridian_tx = settle_data.get("transaction", "")
            logger.info(f"[Premium] ✅ Payment settled! TX: {meridian_tx}")
        
        # ── STEP 2: Payment verified — now create/reactivate subscription ──
        
        if existing.data:
            # Reactivate expired/cancelled subscription
            sub = existing.data[0]
            code = generate_activation_code()
            supabase.table("premium_subscriptions").update({
                "status": "active",
                "activation_code": code,
                "code_used_at": None,
                "telegram_chat_id": None,
                "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
                "x402_payment_id": meridian_tx or payment_sig
            }).eq("user_address", user_address).execute()
            
            return {
                "success": True,
                "already_subscribed": False,
                "activation_code": code,
                "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
                "message": "Subscription reactivated!"
            }
        
        # Create new subscription
        code = generate_activation_code()
        expires_at = datetime.now() + timedelta(days=30)
        
        supabase.table("premium_subscriptions").insert({
            "user_address": user_address,
            "status": "active",
            "autonomy_mode": "advisor",  # Default mode
            "activation_code": code,
            "expires_at": expires_at.isoformat(),
            "x402_payment_id": meridian_tx or payment_sig
        }).execute()
        
        logger.info(f"[Premium] New subscription: {user_address[:10]}... code: {code}")
        
        return {
            "success": True,
            "already_subscribed": False,
            "activation_code": code,
            "expires_at": expires_at.isoformat(),
            "telegram_bot": "@TechneArtisanBot",
            "message": "Welcome to Techne Premium! Enter your code in Telegram to activate."
        }
        
    except Exception as e:
        logger.error(f"Subscribe error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-code")
async def validate_activation_code(request: ValidateCodeRequest):
    """
    Validate activation code from Telegram bot.
    Links Telegram chat to subscription AND creates agent wallet.
    
    Full flow:
    1. Validate code exists and not used
    2. Create agent wallet (smart account)
    3. Generate session key for backend execution
    4. Link everything together
    """
    try:
        supabase = get_supabase()
        code = request.activation_code.upper().strip()
        
        # Find subscription by code
        result = supabase.table("premium_subscriptions").select("*").eq(
            "activation_code", code
        ).execute()
        
        if not result.data:
            return {
                "success": False,
                "error": "Invalid activation code"
            }
        
        sub = result.data[0]
        
        # Check if already used
        if sub.get("code_used_at"):
            # If same chat, just return success
            if sub.get("telegram_chat_id") == request.telegram_chat_id:
                return {
                    "success": True,
                    "user_address": sub["user_address"],
                    "agent_address": sub.get("agent_address"),
                    "autonomy_mode": sub["autonomy_mode"],
                    "expires_at": sub["expires_at"],
                    "message": "Already activated!"
                }
            return {
                "success": False,
                "error": "Code already used by another account"
            }
        
        # Check if expired
        if sub["status"] != "active":
            return {
                "success": False,
                "error": "Subscription is not active"
            }
        
        # Link Telegram to subscription
        # NOTE: Agent + session key are NOT created here.
        # They are created later by the TG bot when user first requests execution.
        # This builds trust progressively: observe → execute → auto-renew.
        update_data = {
            "telegram_chat_id": request.telegram_chat_id,
            "telegram_username": request.telegram_username,
            "code_used_at": datetime.now().isoformat()
        }
        
        supabase.table("premium_subscriptions").update(update_data).eq(
            "id", sub["id"]
        ).execute()
        
        logger.info(f"[Premium] Code validated: {code} → chat {request.telegram_chat_id}")
        
        return {
            "success": True,
            "user_address": sub["user_address"],
            "autonomy_mode": sub["autonomy_mode"],
            "expires_at": sub["expires_at"],
            "message": "Welcome to Artisan! 🤖 Use me for portfolio analysis. When you're ready to execute trades, I'll set up your agent wallet."
        }
        
    except Exception as e:
        logger.error(f"Validate code error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_subscription_status(user_address: str = Query(...)):
    """Get subscription status for user"""
    try:
        supabase = get_supabase()
        user_address = user_address.lower()
        
        result = supabase.table("premium_subscriptions").select("*").eq(
            "user_address", user_address
        ).execute()
        
        if not result.data:
            return {
                "subscribed": False,
                "message": "No active subscription"
            }
        
        sub = result.data[0]
        is_active = sub["status"] == "active"
        is_connected = sub["telegram_chat_id"] is not None
        
        return {
            "subscribed": is_active,
            "status": sub["status"],
            "autonomy_mode": sub["autonomy_mode"],
            "telegram_connected": is_connected,
            "telegram_username": sub.get("telegram_username"),
            "expires_at": sub["expires_at"],
            "activation_code": sub["activation_code"] if not is_connected else None
        }
        
    except Exception as e:
        logger.error(f"Status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/change-mode")
async def change_autonomy_mode(request: ChangeAutonomyRequest):
    """Change autonomy mode"""
    try:
        valid_modes = ["observer", "advisor", "copilot", "full_auto"]
        if request.mode not in valid_modes:
            raise HTTPException(status_code=400, detail=f"Invalid mode. Must be one of: {valid_modes}")
        
        supabase = get_supabase()
        user_address = request.user_address.lower()
        
        result = supabase.table("premium_subscriptions").update({
            "autonomy_mode": request.mode
        }).eq("user_address", user_address).eq("status", "active").execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        logger.info(f"[Premium] Mode changed: {user_address[:10]}... → {request.mode}")
        
        return {
            "success": True,
            "mode": request.mode,
            "message": f"Autonomy mode changed to: {request.mode}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change mode error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unsubscribe")
async def unsubscribe(request: DisconnectRequest):
    """Unsubscribe - cancel subscription but keep data for 30 days"""
    try:
        supabase = get_supabase()
        user_address = request.user_address.lower()
        
        # Set data retention: 30 days from now
        from datetime import datetime, timedelta
        data_expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        result = supabase.table("premium_subscriptions").update({
            "status": "cancelled",
            "telegram_chat_id": None,
            "telegram_username": None,
            "data_expires_at": data_expires_at
        }).eq("user_address", user_address).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="No subscription found")
        
        logger.info(f"[Premium] Unsubscribed: {user_address[:10]}... (data kept until {data_expires_at[:10]})")
        
        return {
            "success": True,
            "message": "Subscription cancelled. Your data will be kept for 30 days.",
            "data_expires_at": data_expires_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unsubscribe error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete")
async def delete_subscription(request: DisconnectRequest):
    """Permanently delete subscription and all associated data"""
    try:
        supabase = get_supabase()
        user_address = request.user_address.lower()
        
        # Get subscription first for related cleanup
        sub_result = supabase.table("premium_subscriptions").select("*").eq(
            "user_address", user_address
        ).execute()
        
        if not sub_result.data:
            raise HTTPException(status_code=404, detail="No subscription found")
        
        # Delete related data (conversations, actions, memory)
        try:
            supabase.table("artisan_conversations").delete().eq(
                "user_address", user_address
            ).execute()
            
            supabase.table("artisan_actions").delete().eq(
                "user_address", user_address  
            ).execute()
            
            supabase.table("artisan_memory").delete().eq(
                "user_address", user_address
            ).execute()
            
            supabase.table("artisan_strategies").delete().eq(
                "user_address", user_address
            ).execute()
        except Exception as e:
            logger.warning(f"Some related data may not exist: {e}")
        
        # Delete subscription
        supabase.table("premium_subscriptions").delete().eq(
            "user_address", user_address
        ).execute()
        
        logger.info(f"[Premium] DELETED: {user_address[:10]}... (full removal)")
        
        return {
            "success": True,
            "message": "Subscription and all data permanently deleted."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscription-by-chat")
async def get_subscription_by_telegram(chat_id: int = Query(...)):
    """Get subscription by Telegram chat ID (used by bot)"""
    try:
        supabase = get_supabase()
        
        result = supabase.table("premium_subscriptions").select("*").eq(
            "telegram_chat_id", chat_id
        ).eq("status", "active").execute()
        
        if not result.data:
            return {"found": False}
        
        sub = result.data[0]
        return {
            "found": True,
            "user_address": sub["user_address"],
            "autonomy_mode": sub["autonomy_mode"],
            "expires_at": sub["expires_at"]
        }
        
    except Exception as e:
        logger.error(f"Get by chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-session")
async def validate_session(request: ValidateSessionRequest):
    """
    Validate session key from OpenClaw bridge.
    Returns agent info if valid, for tool execution authentication.
    
    Session key format: ARTISAN-XXXX-XXXX (same as activation code for simplicity)
    """
    try:
        supabase = get_supabase()
        session_key = request.session_key.upper().strip()
        
        # Look up by activation code (for now, session_key = activation_code)
        result = supabase.table("premium_subscriptions").select("*").eq(
            "activation_code", session_key
        ).eq("status", "active").execute()
        
        if not result.data:
            return {
                "success": False,
                "error": "Invalid or expired session key"
            }
        
        sub = result.data[0]
        
        # Check if subscription has been activated (code used)
        if not sub.get("code_used_at"):
            return {
                "success": False,
                "error": "Session key not yet activated. Use /start in Telegram first."
            }
        
        logger.info(f"[OpenClaw] Session validated: {session_key[:10]}... → {sub['user_address'][:10]}")
        
        return {
            "success": True,
            "user_address": sub["user_address"],
            "agent_address": sub.get("agent_address"),
            "autonomy_mode": sub.get("autonomy_mode", "advisor"),
            "expires_at": sub["expires_at"],
            "telegram_connected": sub.get("telegram_chat_id") is not None
        }
        
    except Exception as e:
        logger.error(f"Validate session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ImportAgentRequest(BaseModel):
    """Import deployed agent wallet"""
    user_address: str
    agent_address: str


@router.post("/import-agent")
async def import_agent(request: ImportAgentRequest):
    """
    Import deployed agent wallet for trade execution.
    Called by OpenClaw bridge after user activates their code.
    """
    try:
        supabase = get_supabase()
        user_address = request.user_address.lower()
        agent_address = request.agent_address.lower()
        
        # Validate agent address format
        if not agent_address.startswith("0x") or len(agent_address) != 42:
            return {
                "success": False,
                "error": "Invalid agent address format"
            }
        
        # Find active subscription
        result = supabase.table("premium_subscriptions").select("*").eq(
            "user_address", user_address
        ).eq("status", "active").execute()
        
        if not result.data:
            return {
                "success": False,
                "error": "No active subscription found for this address"
            }
        
        sub = result.data[0]
        
        # Update subscription with agent address
        supabase.table("premium_subscriptions").update({
            "agent_address": agent_address
        }).eq("id", sub["id"]).execute()
        
        logger.info(f"[OpenClaw] Agent imported: {agent_address[:10]}... → {user_address[:10]}")
        
        return {
            "success": True,
            "agent_address": agent_address,
            "user_address": user_address,
            "autonomy_mode": sub.get("autonomy_mode", "advisor"),
            "message": "Agent wallet linked successfully"
        }
        
    except Exception as e:
        logger.error(f"Import agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# AUTO-RENEWAL VIA SESSION KEYS
# ============================================

class AutoRenewalToggleRequest(BaseModel):
    """Toggle auto-renewal on/off"""
    user_address: str
    enabled: bool


@router.put("/auto-renewal")
async def toggle_auto_renewal(request: AutoRenewalToggleRequest):
    """
    Enable/disable auto-renewal from agent Smart Account.
    
    When enabled, the bot will use the trading session key to send
    $99 USDC from the user's Smart Account to Treasury before expiry.
    """
    try:
        supabase = get_supabase()
        user_address = request.user_address.lower()
        
        # Find active subscription
        result = supabase.table("premium_subscriptions").select("*").eq(
            "user_address", user_address
        ).eq("status", "active").execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="No active subscription")
        
        sub = result.data[0]
        
        # Cannot enable without a deployed agent with session key
        if request.enabled:
            agents_result = supabase.table("agents").select(
                "smart_account_address"
            ).eq("user_address", user_address).execute()
            
            if not agents_result.data:
                raise HTTPException(
                    status_code=400,
                    detail="No deployed agent found. Deploy an agent via Build page first."
                )
        
        # Update
        supabase.table("premium_subscriptions").update({
            "auto_renewal_enabled": request.enabled
        }).eq("id", sub["id"]).execute()
        
        status = "enabled" if request.enabled else "disabled"
        logger.info(f"[Premium] Auto-renewal {status} for {user_address[:10]}...")
        
        return {
            "success": True,
            "auto_renewal_enabled": request.enabled,
            "agent_address": sub.get("agent_address"),
            "message": f"Auto-renewal {status}. Bot will {'pay $99 USDC from your agent wallet before expiry' if request.enabled else 'no longer auto-renew'}."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Toggle auto-renewal error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-renewals")
async def process_renewals(
    api_key: str = Query(..., alias="key")
):
    """
    Process all due auto-renewals. Protected by API key.
    Called by external cron (Vercel/GitHub Actions/PM2).
    
    Finds subscriptions expiring within 5 days with auto_renewal_enabled,
    then executes $99 USDC transfer from each user's Smart Account to Treasury.
    """
    # Verify API key
    expected_key = os.getenv("CRON_API_KEY", "techne-cron-secret")
    if api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    try:
        supabase = get_supabase()
        
        # Find subscriptions due for renewal (expiring in ≤ 5 days)
        from datetime import timezone
        cutoff = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        
        result = supabase.table("premium_subscriptions").select("*").eq(
            "auto_renewal_enabled", True
        ).eq("status", "active").lt(
            "expires_at", cutoff
        ).execute()
        
        if not result.data:
            return {"success": True, "processed": 0, "message": "No renewals due"}
        
        # Process each renewal
        results = []
        
        for sub in result.data:
            renewal_result = await _process_single_renewal(supabase, sub)
            results.append(renewal_result)
        
        succeeded = sum(1 for r in results if r["success"])
        failed = len(results) - succeeded
        
        logger.info(f"[Premium] Renewals processed: {succeeded} OK, {failed} failed")
        
        return {
            "success": True,
            "processed": len(results),
            "succeeded": succeeded,
            "failed": failed,
            "details": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Process renewals error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _process_single_renewal(supabase, sub: dict) -> dict:
    """
    Process a single auto-renewal payment.
    
    Builds USDC transfer calldata → executes via session key → extends subscription.
    """
    user_address = sub["user_address"]
    agent_address = sub.get("agent_address")
    sub_id = sub["id"]
    
    try:
        # Skip if renewal failed recently (1 hour backoff)
        if sub.get("renewal_failed_at"):
            from datetime import timezone
            failed_at = datetime.fromisoformat(sub["renewal_failed_at"].replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - failed_at).total_seconds() < 3600:
                return {
                    "success": False,
                    "user": user_address[:10],
                    "reason": "Backoff — failed recently, retrying later"
                }
        
        # Get agent + session key from agents table (deployed via Build page)
        agents_result = supabase.table("agents").select(
            "encrypted_private_key, smart_account_address"
        ).eq("user_address", user_address).execute()
        
        if not agents_result.data:
            return {
                "success": False,
                "user": user_address[:10],
                "reason": "No deployed agent found — user needs to deploy via Build page first"
            }
        
        agent_record = agents_result.data[0]
        session_key_private = agent_record["encrypted_private_key"]
        agent_address = agent_record["smart_account_address"]
        
        # Build USDC transfer calldata: transfer(Treasury, $99)
        from web3 import Web3
        
        ERC20_TRANSFER_ABI = [{
            "inputs": [
                {"name": "to", "type": "address"},
                {"name": "amount", "type": "uint256"}
            ],
            "name": "transfer",
            "outputs": [{"name": "", "type": "bool"}],
            "stateMutability": "nonpayable",
            "type": "function"
        }]
        
        w3 = Web3()
        usdc = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_BASE),
            abi=ERC20_TRANSFER_ABI
        )
        
        calldata = usdc.functions.transfer(
            Web3.to_checksum_address(TREASURY_ADDRESS),
            SUBSCRIPTION_PRICE_USDC  # $99 in 6 decimals
        )._encode_transaction_data()
        
        # Execute via session key
        from services.smart_account_service import SmartAccountService
        smart_account = SmartAccountService()
        
        tx_result = smart_account.execute_with_session_key(
            smart_account=agent_address,
            target=USDC_BASE,
            value=0,
            calldata=bytes.fromhex(calldata[2:]),  # Strip 0x prefix
            session_key_private=session_key_private,
            estimated_value_usd=99
        )
        
        if tx_result.get("success"):
            # Extend subscription by 30 days
            new_expiry = datetime.now() + timedelta(days=30)
            
            supabase.table("premium_subscriptions").update({
                "expires_at": new_expiry.isoformat(),
                "last_renewal_tx": tx_result["tx_hash"],
                "renewal_failed_at": None
            }).eq("id", sub_id).execute()
            
            # Log to audit trail
            supabase.table("artisan_actions").insert({
                "subscription_id": sub_id,
                "action_type": "auto_renewal",
                "details": {
                    "amount_usdc": 99,
                    "tx_hash": tx_result["tx_hash"],
                    "new_expiry": new_expiry.isoformat(),
                    "treasury": TREASURY_ADDRESS
                },
                "tx_hash": tx_result["tx_hash"],
                "executed": True,
                "executed_at": datetime.utcnow().isoformat()
            }).execute()
            
            logger.info(
                f"[Premium] Auto-renewed {user_address[:10]} → TX: {tx_result['tx_hash']}"
            )
            
            return {
                "success": True,
                "user": user_address[:10],
                "tx_hash": tx_result["tx_hash"],
                "new_expiry": new_expiry.isoformat()
            }
        else:
            # Mark failed
            supabase.table("premium_subscriptions").update({
                "renewal_failed_at": datetime.utcnow().isoformat()
            }).eq("id", sub_id).execute()
            
            return {
                "success": False,
                "user": user_address[:10],
                "reason": tx_result.get("message", "TX failed")
            }
            
    except Exception as e:
        # Mark failed with backoff
        try:
            supabase.table("premium_subscriptions").update({
                "renewal_failed_at": datetime.utcnow().isoformat()
            }).eq("id", sub_id).execute()
        except:
            pass
        
        logger.error(f"[Premium] Renewal failed for {user_address[:10]}: {e}")
        return {
            "success": False,
            "user": user_address[:10],
            "reason": str(e)
        }


@router.get("/renewal-status")
async def get_renewal_status(user_address: str = Query(...)):
    """Get auto-renewal status for a user"""
    try:
        supabase = get_supabase()
        
        result = supabase.table("premium_subscriptions").select(
            "auto_renewal_enabled, last_renewal_tx, renewal_failed_at, expires_at"
        ).eq(
            "user_address", user_address.lower()
        ).eq("status", "active").execute()
        
        if not result.data:
            return {
                "auto_renewal_enabled": False,
                "can_enable": False,
                "reason": "No active subscription"
            }
        
        sub = result.data[0]
        
        # Check for deployed agent (from Build page)
        agents_result = supabase.table("agents").select(
            "smart_account_address"
        ).eq("user_address", user_address.lower()).execute()
        
        has_agent = bool(agents_result.data)
        agent_address = agents_result.data[0]["smart_account_address"] if has_agent else None
        
        return {
            "auto_renewal_enabled": sub.get("auto_renewal_enabled", False),
            "can_enable": has_agent,
            "agent_address": agent_address,
            "expires_at": sub.get("expires_at"),
            "last_renewal_tx": sub.get("last_renewal_tx"),
            "last_failed": sub.get("renewal_failed_at"),
            "renewal_cost_usdc": 99,
            "missing": [] if has_agent else ["deployed_agent"]
        }
