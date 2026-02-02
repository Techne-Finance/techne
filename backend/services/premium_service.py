"""
Premium Subscription Service - Artisan Bot

Full vertical slice for paid subscriptions:
1. User pays 50 USDC → generates activation code
2. User activates code → creates agent wallet + session key
3. Artisan Bot executes trades via session keys
"""

import os
import secrets
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from supabase import create_client, Client

logger = logging.getLogger("PremiumService")

# Supabase config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Premium pricing
PREMIUM_PRICE_USDC = 50
PREMIUM_DURATION_DAYS = 30


@dataclass
class PremiumSubscription:
    """Premium subscription data"""
    id: int
    user_address: str
    activation_code: str
    telegram_chat_id: Optional[int]
    telegram_username: Optional[str]
    autonomy_mode: str
    agent_address: Optional[str]
    session_key_address: Optional[str]
    is_active: bool
    expires_at: datetime
    created_at: datetime


class PremiumService:
    """
    Manages premium subscriptions for Artisan Bot.
    
    Flow:
    1. generate_activation_code() - after payment confirmed
    2. validate_and_activate() - when user sends code to Telegram
    3. create_agent_wallet() - auto-creates agent with session keys
    4. execute_trade() - uses session keys for trading
    """
    
    def __init__(self):
        if SUPABASE_URL and SUPABASE_KEY:
            self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        else:
            self.supabase = None
            logger.warning("Supabase not configured - premium service disabled")
    
    def generate_activation_code(self, user_address: str, payment_tx_hash: str = None) -> Dict:
        """
        Generate activation code after successful payment.
        
        Returns: {"code": "ARTISAN-XXXX-XXXX", "expires_at": ...}
        """
        # Generate unique code
        code = f"ARTISAN-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
        expires_at = datetime.utcnow() + timedelta(days=PREMIUM_DURATION_DAYS)
        
        if self.supabase:
            try:
                result = self.supabase.table("premium_subscriptions").insert({
                    "user_address": user_address.lower(),
                    "activation_code": code,
                    "payment_tx_hash": payment_tx_hash,
                    "autonomy_mode": "advisor",  # Default mode
                    "is_active": False,  # Not active until Telegram linked
                    "expires_at": expires_at.isoformat(),
                    "created_at": datetime.utcnow().isoformat()
                }).execute()
                
                logger.info(f"Generated activation code for {user_address[:10]}...")
                
                return {
                    "success": True,
                    "code": code,
                    "expires_at": expires_at.isoformat(),
                    "message": "Send this code to @TechneArtisanBot on Telegram"
                }
            except Exception as e:
                logger.error(f"Failed to generate code: {e}")
                return {"success": False, "error": str(e)}
        
        # Fallback for testing without Supabase
        return {
            "success": True,
            "code": code,
            "expires_at": expires_at.isoformat(),
            "message": "Supabase not configured - code not persisted"
        }
    
    async def validate_and_activate(
        self,
        activation_code: str,
        telegram_chat_id: int,
        telegram_username: str = None
    ) -> Dict:
        """
        Validate code and link to Telegram + create agent wallet.
        
        This is called when user sends /start ARTISAN-XXXX-XXXX
        """
        if not self.supabase:
            return {"success": False, "error": "Supabase not configured"}
        
        try:
            # Find subscription by code
            result = self.supabase.table("premium_subscriptions").select("*").eq(
                "activation_code", activation_code.upper()
            ).execute()
            
            if not result.data:
                return {"success": False, "error": "Invalid activation code"}
            
            sub = result.data[0]
            
            # Check if already activated
            if sub.get("telegram_chat_id"):
                if sub["telegram_chat_id"] == telegram_chat_id:
                    return {
                        "success": True,
                        "message": "Already activated",
                        "user_address": sub["user_address"],
                        "agent_address": sub.get("agent_address")
                    }
                else:
                    return {"success": False, "error": "Code already used by another account"}
            
            # Check expiration
            expires_at = datetime.fromisoformat(sub["expires_at"].replace("Z", "+00:00"))
            if datetime.utcnow().replace(tzinfo=expires_at.tzinfo) > expires_at:
                return {"success": False, "error": "Activation code expired"}
            
            # Create agent wallet for this subscription
            agent_result = await self._create_subscription_agent(sub["user_address"])
            
            if not agent_result.get("success"):
                return {"success": False, "error": f"Failed to create agent: {agent_result.get('error')}"}
            
            # Update subscription with Telegram link and agent
            self.supabase.table("premium_subscriptions").update({
                "telegram_chat_id": telegram_chat_id,
                "telegram_username": telegram_username,
                "agent_address": agent_result["agent_address"],
                "session_key_address": agent_result.get("session_key_address"),
                "is_active": True,
                "activated_at": datetime.utcnow().isoformat()
            }).eq("id", sub["id"]).execute()
            
            logger.info(f"Activated subscription for chat {telegram_chat_id}")
            
            return {
                "success": True,
                "user_address": sub["user_address"],
                "agent_address": agent_result["agent_address"],
                "session_key_address": agent_result.get("session_key_address"),
                "autonomy_mode": sub.get("autonomy_mode", "advisor"),
                "expires_at": sub["expires_at"]
            }
            
        except Exception as e:
            logger.error(f"Activation error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _create_subscription_agent(self, user_address: str) -> Dict:
        """
        Create agent wallet and session key for premium subscriber.
        """
        try:
            # Import services
            from services.agent_service import agent_service, AgentConfig
            from services.smart_account_service import SmartAccountService
            from eth_account import Account
            
            smart_account = SmartAccountService()
            
            # Generate agent ID for this subscription
            agent_id = f"artisan-{secrets.token_hex(8)}"
            
            # Get counterfactual smart account address
            account_result = smart_account.create_account(user_address, agent_id)
            
            if not account_result.get("success"):
                return {"success": False, "error": "Failed to create smart account"}
            
            agent_address = account_result["account_address"]
            
            # Generate session key for backend execution
            session_key = Account.create()
            session_key_address = session_key.address
            session_key_private = session_key.key.hex()
            
            # Store agent in database
            config = AgentConfig(
                chain="base",
                preset="artisan",
                risk_level="moderate"
            )
            
            await agent_service.create_agent(
                user_address=user_address,
                agent_address=agent_address,
                encrypted_private_key=session_key_private,  # Session key, not full control
                config=config,
                agent_name=agent_id
            )
            
            logger.info(f"Created agent {agent_address[:10]} for {user_address[:10]}")
            
            return {
                "success": True,
                "agent_address": agent_address,
                "session_key_address": session_key_address,
                "session_key_private": session_key_private,  # Store encrypted!
                "agent_id": agent_id
            }
            
        except Exception as e:
            logger.error(f"Agent creation error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_subscription_by_chat(self, telegram_chat_id: int) -> Optional[Dict]:
        """Get subscription by Telegram chat ID"""
        if not self.supabase:
            return None
        
        try:
            result = self.supabase.table("premium_subscriptions").select("*").eq(
                "telegram_chat_id", telegram_chat_id
            ).eq("is_active", True).execute()
            
            if result.data:
                sub = result.data[0]
                return {
                    "found": True,
                    "user_address": sub["user_address"],
                    "agent_address": sub.get("agent_address"),
                    "session_key_address": sub.get("session_key_address"),
                    "autonomy_mode": sub.get("autonomy_mode", "advisor"),
                    "expires_at": sub["expires_at"]
                }
            return {"found": False}
        except Exception as e:
            logger.error(f"Get subscription error: {e}")
            return None
    
    def change_autonomy_mode(self, user_address: str, mode: str) -> bool:
        """Change autonomy mode for subscription"""
        valid_modes = ["observer", "advisor", "copilot", "full_auto"]
        if mode not in valid_modes:
            return False
        
        if not self.supabase:
            return False
        
        try:
            self.supabase.table("premium_subscriptions").update({
                "autonomy_mode": mode
            }).eq("user_address", user_address.lower()).execute()
            return True
        except:
            return False
    
    async def execute_trade(
        self,
        user_address: str,
        action: str,  # "enter", "exit", "swap"
        pool_id: str,
        amount_usd: float,
        autonomy_mode: str
    ) -> Dict:
        """
        Execute trade via session key.
        
        Safety checks:
        - observer/advisor: blocked
        - copilot: max $1000
        - full_auto: max $10000
        """
        # Import trade limits
        TRADE_LIMITS = {
            "observer": 0,
            "advisor": 0,
            "copilot": 1000,
            "full_auto": 10000
        }
        
        limit = TRADE_LIMITS.get(autonomy_mode, 0)
        
        if limit == 0:
            return {
                "success": False,
                "blocked": True,
                "error": f"Trading not allowed in {autonomy_mode} mode"
            }
        
        if amount_usd > limit:
            return {
                "success": False,
                "blocked": True,
                "needs_confirmation": True,
                "error": f"Trade ${amount_usd:,.0f} exceeds {autonomy_mode} limit (${limit:,.0f})"
            }
        
        # Get subscription with session key
        sub = self._get_subscription_by_address(user_address)
        if not sub:
            return {"success": False, "error": "No active subscription"}
        
        try:
            from services.smart_account_service import SmartAccountService
            from services.aerodrome_lp import AerodromeLPService
            
            smart_account = SmartAccountService()
            lp_service = AerodromeLPService()
            
            if action == "enter":
                # Build enter position calldata
                calldata = lp_service.build_enter_calldata(pool_id, amount_usd)
                target = lp_service.get_pool_address(pool_id)
            elif action == "exit":
                calldata = lp_service.build_exit_calldata(pool_id)
                target = lp_service.get_pool_address(pool_id)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
            
            # Execute via session key
            result = smart_account.execute_with_session_key(
                smart_account=sub["agent_address"],
                target=target,
                value=0,
                calldata=calldata,
                session_key_private=sub["session_key_private"],
                estimated_value_usd=int(amount_usd)
            )
            
            if result.get("success"):
                logger.info(f"Trade executed: {action} ${amount_usd} on {pool_id}")
                return {
                    "success": True,
                    "tx_hash": result.get("tx_hash"),
                    "action": action,
                    "amount_usd": amount_usd,
                    "pool_id": pool_id
                }
            else:
                return {"success": False, "error": result.get("error")}
                
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_subscription_by_address(self, user_address: str) -> Optional[Dict]:
        """Get subscription with session key by user address"""
        if not self.supabase:
            return None
        
        try:
            result = self.supabase.table("premium_subscriptions").select("*").eq(
                "user_address", user_address.lower()
            ).eq("is_active", True).execute()
            
            if result.data:
                return result.data[0]
            return None
        except:
            return None


# Singleton
_premium_service: Optional[PremiumService] = None

def get_premium_service() -> PremiumService:
    """Get or create premium service singleton"""
    global _premium_service
    if _premium_service is None:
        _premium_service = PremiumService()
    return _premium_service
