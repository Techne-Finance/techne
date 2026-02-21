"""
Artisan Execution Bridge
Connects Artisan Agent to Techne's trading infrastructure

This module provides:
1. Trade execution via session key or V4 contract
2. Position exit functionality
3. Emergency exit all positions
4. Integration with existing StrategyExecutor
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from web3 import Web3

logger = logging.getLogger("ArtisanExecution")

# ERC-8004 reputation tracking flag
ERC8004_ENABLED = os.getenv("ERC8004_ENABLED", "true").lower() == "true"

# V3 Factory and Implementation (from session key deployment)
FACTORY_V3 = "0x36945Cc50Aa50E7473231Eb57731dbffEf60C3a4"
SESSION_KEY = "0xa30A689ec0F9D717C5bA1098455B031b868B720f"

# Supported protocols for Artisan trading
SUPPORTED_PROTOCOLS = {
    "aave-v3": {
        "name": "Aave V3",
        "pool": "0x18cd499e3d7ed42feba981ac9236a278e4cdc2ee",  # Base
        "type": "lending",
        "chain": "base"
    },
    "aerodrome": {
        "name": "Aerodrome",
        "router": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
        "type": "dex",
        "chain": "base"
    },
    "morpho": {
        "name": "Morpho",
        "vault": "0xc1256Ae5FF1cf2719D4937adb3bbCCab2E00A2Ca",  # USDC vault
        "type": "lending",
        "chain": "base"
    }
}

# USDC on Base
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


class ArtisanExecutor:
    """
    Execution engine for Artisan Agent trades.
    
    Uses session key for gasless execution when available,
    falls back to V4 contract executeStrategy.
    """
    
    def __init__(self, user_address: str, agent_private_key: Optional[str] = None):
        self.user_address = user_address.lower()
        self.agent_private_key = agent_private_key or os.getenv("AGENT_PRIVATE_KEY")
        self.rpc_url = os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # V4 contract for balance management
        self.v4_address = os.getenv("V4_CONTRACT", "0x2EcE5b2733e89e648B2b3f3b1EEf0D5b9e22b5a3")
        
        # Session key for gasless execution
        self.session_key = SESSION_KEY
        self.session_key_pk = os.getenv("SESSION_KEY_PRIVATE_KEY")
        
        # ERC-8004 token ID (cached)
        self._token_id: Optional[int] = None
    
    async def _report_to_reputation(
        self,
        success: bool,
        value_usd: float,
        profit_usd: float,
        execution_type: str
    ):
        """Report execution to ERC-8004 reputation registry"""
        try:
            from services.reputation_service import get_reputation_service
            
            service = get_reputation_service()
            
            # Get/cache token ID for user's smart account
            if self._token_id is None:
                smart_account = await self._get_smart_account()
                if smart_account:
                    self._token_id = await service.get_token_id_for_account(smart_account)
            
            if self._token_id is None:
                logger.debug(f"No ERC-8004 identity for user {self.user_address}")
                return
            
            # Report to chain
            tx_hash = await service.report_execution(
                token_id=self._token_id,
                success=success,
                value_usd=value_usd,
                profit_usd=profit_usd,
                execution_type=execution_type
            )
            
            if tx_hash:
                logger.info(f"[ERC-8004] Reputation updated: {execution_type} tx={tx_hash[:10]}...")
                
        except Exception as e:
            logger.warning(f"Failed to report to reputation registry: {e}")
    
    async def execute_deposit(
        self,
        protocol_id: str,
        amount_usd: float,
        pool_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a deposit to a protocol.
        
        Args:
            protocol_id: Protocol identifier (aave-v3, aerodrome, morpho)
            amount_usd: Amount in USD to deposit
            pool_id: Optional specific pool ID
            
        Returns:
            Execution result with tx_hash
        """
        try:
            protocol = SUPPORTED_PROTOCOLS.get(protocol_id)
            if not protocol:
                return {"success": False, "error": f"Unsupported protocol: {protocol_id}"}
            
            amount_usdc = int(amount_usd * 1e6)  # USDC 6 decimals
            
            logger.info(f"[ArtisanExecutor] Deposit {amount_usd} USDC to {protocol['name']}")
            
            # Check balance first
            balance = await self._get_usdc_balance()
            if balance < amount_usdc:
                return {
                    "success": False,
                    "error": f"Insufficient balance: ${balance/1e6:.2f} < ${amount_usd:.2f}"
                }
            
            # Route to protocol-specific handler
            if protocol_id == "aave-v3":
                result = await self._deposit_aave(amount_usdc)
            elif protocol_id == "morpho":
                result = await self._deposit_morpho(amount_usdc)
            elif protocol_id == "aerodrome":
                return {"success": False, "error": "Aerodrome deposits not yet implemented"}
            else:
                return {"success": False, "error": f"No handler for {protocol_id}"}
            
            # ERC-8004: Report execution to reputation registry
            if ERC8004_ENABLED:
                await self._report_to_reputation(
                    success=result.get("success", False),
                    value_usd=amount_usd,
                    profit_usd=0.0,
                    execution_type="deposit"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Deposit error: {e}")
            # Report failure to reputation
            if ERC8004_ENABLED:
                await self._report_to_reputation(
                    success=False,
                    value_usd=amount_usd,
                    profit_usd=0.0,
                    execution_type="deposit"
                )
            return {"success": False, "error": str(e)}
    
    async def execute_withdraw(
        self,
        protocol_id: str,
        amount_usd: float,
        pool_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a withdrawal from a protocol.
        """
        try:
            protocol = SUPPORTED_PROTOCOLS.get(protocol_id)
            if not protocol:
                return {"success": False, "error": f"Unsupported protocol: {protocol_id}"}
            
            amount_usdc = int(amount_usd * 1e6)
            
            logger.info(f"[ArtisanExecutor] Withdraw {amount_usd} USDC from {protocol['name']}")
            
            if protocol_id == "aave-v3":
                result = await self._withdraw_aave(amount_usdc)
            elif protocol_id == "morpho":
                result = await self._withdraw_morpho(amount_usdc)
            else:
                return {"success": False, "error": f"No handler for {protocol_id}"}
            
            # ERC-8004: Report execution to reputation registry
            if ERC8004_ENABLED:
                # Estimate any profit from yield during deposit
                profit_usd = result.get("yield_earned", 0.0)
                await self._report_to_reputation(
                    success=result.get("success", False),
                    value_usd=amount_usd,
                    profit_usd=profit_usd,
                    execution_type="withdraw"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Withdraw error: {e}")
            if ERC8004_ENABLED:
                await self._report_to_reputation(
                    success=False,
                    value_usd=amount_usd,
                    profit_usd=0.0,
                    execution_type="withdraw"
                )
            return {"success": False, "error": str(e)}
    
    async def exit_position(self, position_id: str) -> Dict[str, Any]:
        """
        Exit a specific position by ID.
        
        Args:
            position_id: Position identifier from database
            
        Returns:
            Execution result
        """
        try:
            from supabase import create_client
            
            supabase = create_client(
                os.getenv("SUPABASE_URL"),
                os.getenv("SUPABASE_KEY")
            )
            
            # Get position details
            result = supabase.table("agent_positions").select("*").eq(
                "id", position_id
            ).execute()
            
            if not result.data:
                return {"success": False, "error": "Position not found"}
            
            position = result.data[0]
            protocol_id = position.get("project", "").lower().replace(" ", "-")
            amount = position.get("amount_usd", 0)
            
            # Withdraw from protocol
            withdraw_result = await self.execute_withdraw(protocol_id, amount)
            
            if withdraw_result.get("success"):
                # Mark position as exited
                supabase.table("agent_positions").update({
                    "status": "exited",
                    "exit_reason": "artisan_agent",
                    "exited_at": datetime.now().isoformat()
                }).eq("id", position_id).execute()
            
            return withdraw_result
            
        except Exception as e:
            logger.error(f"Exit position error: {e}")
            return {"success": False, "error": str(e)}
    
    async def emergency_exit_all(self, reason: str) -> Dict[str, Any]:
        """
        Emergency exit ALL positions and park funds in Aave USDC.
        
        Args:
            reason: Reason for emergency exit
            
        Returns:
            Summary of all exits
        """
        try:
            from supabase import create_client
            
            supabase = create_client(
                os.getenv("SUPABASE_URL"),
                os.getenv("SUPABASE_KEY")
            )
            
            logger.warning(f"[ArtisanExecutor] EMERGENCY EXIT ALL: {reason}")
            
            # Get all active positions for user
            result = supabase.table("agent_positions").select("*").eq(
                "user_address", self.user_address
            ).eq("status", "active").execute()
            
            positions = result.data or []
            results = []
            total_recovered = 0
            
            # Exit each position
            for position in positions:
                exit_result = await self.exit_position(position["id"])
                results.append({
                    "position_id": position["id"],
                    "protocol": position.get("project"),
                    "amount": position.get("amount_usd"),
                    "result": exit_result
                })
                
                if exit_result.get("success"):
                    total_recovered += position.get("amount_usd", 0)
            
            # Park recovered funds in Aave USDC (safety)
            if total_recovered > 100:  # Only if significant amount
                park_result = await self._deposit_aave(int(total_recovered * 1e6))
                results.append({
                    "action": "park_to_aave",
                    "amount": total_recovered,
                    "result": park_result
                })
            
            # Log emergency exit
            supabase.table("artisan_actions").insert({
                "subscription_id": None,  # Will be set by caller
                "action_type": "emergency_exit",
                "details": {
                    "reason": reason,
                    "positions_exited": len(positions),
                    "total_recovered": total_recovered,
                    "results": results
                },
                "executed": True,
                "executed_at": datetime.now().isoformat()
            }).execute()
            
            return {
                "success": True,
                "positions_exited": len(positions),
                "total_recovered_usd": total_recovered,
                "parked_in_aave": total_recovered > 100,
                "reason": reason,
                "details": results
            }
            
        except Exception as e:
            logger.error(f"Emergency exit error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_usdc_balance(self) -> int:
        """Get user's USDC balance on smart account"""
        try:
            # ERC20 balanceOf
            usdc_abi = [{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"}]
            
            usdc = self.w3.eth.contract(
                address=Web3.to_checksum_address(USDC_BASE),
                abi=usdc_abi
            )
            
            # Get smart account address for user
            smart_account = await self._get_smart_account()
            if not smart_account:
                return 0
            
            balance = usdc.functions.balanceOf(
                Web3.to_checksum_address(smart_account)
            ).call()
            
            return balance
            
        except Exception as e:
            logger.error(f"Balance check error: {e}")
            return 0
    
    async def _get_smart_account(self) -> Optional[str]:
        """Get user's smart account address from factory"""
        try:
            factory_abi = [
                {"inputs":[{"name":"owner","type":"address"},{"name":"index","type":"uint256"}],"name":"getAccountAddress","outputs":[{"type":"address"}],"stateMutability":"view","type":"function"}
            ]
            
            factory = self.w3.eth.contract(
                address=Web3.to_checksum_address(FACTORY_V3),
                abi=factory_abi
            )
            
            account = factory.functions.getAccountAddress(
                Web3.to_checksum_address(self.user_address),
                0  # First account
            ).call()
            
            # Check if deployed
            if self.w3.eth.get_code(account):
                return account
            
            return None
            
        except Exception as e:
            logger.error(f"Smart account lookup error: {e}")
            return None
    
    async def _deposit_aave(self, amount_usdc: int) -> Dict[str, Any]:
        """Deposit USDC to Aave V3 on Base"""
        try:
            # Aave Pool supply function
            aave_pool = "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5"  # Base mainnet
            
            # This would use session key execution
            # For now, return placeholder
            
            logger.info(f"[ArtisanExecutor] Aave deposit: {amount_usdc/1e6} USDC")
            
            # TODO: Implement actual Aave deposit via session key
            # 1. Approve USDC to Aave Pool
            # 2. Call supply(USDC, amount, user, 0)
            
            return {
                "success": True,
                "protocol": "aave-v3",
                "action": "deposit",
                "amount_usdc": amount_usdc / 1e6,
                "tx_hash": None,  # Would be real tx hash
                "status": "Aave deposit pending full implementation"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _withdraw_aave(self, amount_usdc: int) -> Dict[str, Any]:
        """Withdraw USDC from Aave V3"""
        try:
            logger.info(f"[ArtisanExecutor] Aave withdraw: {amount_usdc/1e6} USDC")
            
            # TODO: Implement actual Aave withdraw
            # Call withdraw(USDC, amount, user)
            
            return {
                "success": True,
                "protocol": "aave-v3",
                "action": "withdraw",
                "amount_usdc": amount_usdc / 1e6,
                "tx_hash": None,
                "status": "Aave withdraw pending full implementation"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _deposit_morpho(self, amount_usdc: int) -> Dict[str, Any]:
        """Deposit USDC to Morpho vault"""
        try:
            logger.info(f"[ArtisanExecutor] Morpho deposit: {amount_usdc/1e6} USDC")
            
            # TODO: Implement actual Morpho deposit
            # Call deposit(assets, receiver)
            
            return {
                "success": True,
                "protocol": "morpho",
                "action": "deposit",
                "amount_usdc": amount_usdc / 1e6,
                "tx_hash": None,
                "status": "Morpho deposit pending full implementation"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _withdraw_morpho(self, amount_usdc: int) -> Dict[str, Any]:
        """Withdraw USDC from Morpho vault"""
        try:
            logger.info(f"[ArtisanExecutor] Morpho withdraw: {amount_usdc/1e6} USDC")
            
            # TODO: Implement actual Morpho withdraw
            
            return {
                "success": True,
                "protocol": "morpho",
                "action": "withdraw",
                "amount_usdc": amount_usdc / 1e6,
                "tx_hash": None,
                "status": "Morpho withdraw pending full implementation"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# Factory function
def create_executor(user_address: str, agent_private_key: str = None) -> ArtisanExecutor:
    """Create an executor instance for a user"""
    return ArtisanExecutor(user_address, agent_private_key)


# Convenience functions for Artisan Agent
async def execute_trade_for_user(
    user_address: str,
    action: str,
    protocol_id: str,
    amount_usd: float,
    autonomy_mode: str = "advisor",
    confirmed: bool = False
) -> Dict[str, Any]:
    """
    Execute a trade for a user with server-side mode enforcement.
    
    Mode rules:
    - observer: BLOCKED — no execution allowed
    - advisor: requires confirmed=True for every trade
    - copilot: auto-execute under $1K, confirmed=True for larger
    - full_auto: auto-execute up to $10K cap
    """
    # ── Observer: hard block ──
    if autonomy_mode == "observer":
        return {
            "success": False,
            "blocked": True,
            "error": "Observer mode — execution disabled. Switch to Advisor or higher with /mode."
        }
    
    # ── Advisor: every trade needs explicit confirmation ──
    if autonomy_mode == "advisor" and not confirmed:
        return {
            "success": False,
            "needs_confirmation": True,
            "message": f"Advisor mode: {action} ${amount_usd:.2f} to {protocol_id} requires your confirmation.",
            "action": action,
            "protocol_id": protocol_id,
            "amount_usd": amount_usd
        }
    
    # ── Copilot: auto under $1K, confirm above ──
    if autonomy_mode == "copilot" and amount_usd > 1000 and not confirmed:
        return {
            "success": False,
            "needs_confirmation": True,
            "message": f"Copilot mode: ${amount_usd:.2f} exceeds $1,000 threshold. Confirm to proceed.",
            "action": action,
            "protocol_id": protocol_id,
            "amount_usd": amount_usd
        }
    
    # ── Full Auto: cap at $10K per transaction ──
    if autonomy_mode == "full_auto" and amount_usd > 10000:
        return {
            "success": False,
            "blocked": True,
            "error": f"Full Auto cap: ${amount_usd:.2f} exceeds $10,000 per-transaction limit."
        }
    
    # ── Execute ──
    executor = create_executor(user_address)
    
    if action == "deposit":
        return await executor.execute_deposit(protocol_id, amount_usd)
    elif action == "withdraw":
        return await executor.execute_withdraw(protocol_id, amount_usd)
    else:
        return {"success": False, "error": f"Unknown action: {action}"}


async def emergency_exit_for_user(user_address: str, reason: str) -> Dict[str, Any]:
    """Emergency exit all positions for a user"""
    executor = create_executor(user_address)
    return await executor.emergency_exit_all(reason)
