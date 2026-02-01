"""
Dual-Sided LP Service
Orchestrates CoW Swap pre-swap + Aerodrome LP deposit for dual-sided pools.

Workflow:
1. User provides single token (e.g., USDC)
2. Calculate 50/50 split for LP
3. Swap half via CoW Swap (MEV-protected)
4. Wait for CoW order to fill
5. Add both tokens to Aerodrome LP

Features:
- MEV-protected swaps via CoW Protocol
- Automatic token balancing for LP
- Slippage protection
- Async polling for swap completion
"""

import os
import asyncio
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from decimal import Decimal

from services.aerodrome_lp import AerodromeLPService, LPResult, get_aerodrome_lp
from integrations.cow_swap import CowSwapClient, cow_client, TOKENS


@dataclass
class DualLPResult:
    """Result of dual-sided LP operation"""
    success: bool
    swap_order_uid: Optional[str] = None
    swap_filled: bool = False
    lp_tx_hash: Optional[str] = None
    amount_a_deposited: int = 0
    amount_b_deposited: int = 0
    lp_tokens_received: int = 0
    error: Optional[str] = None


class DualSidedLPService:
    """
    Manages dual-sided LP deposits with CoW Swap pre-swap.
    
    Usage:
        service = DualSidedLPService()
        result = await service.deposit_single_token_lp(
            pool_token_a="USDC",
            pool_token_b="WETH",
            token_in="USDC",
            amount_in=1000_000_000,  # 1000 USDC
            stable=False,
            agent_address="0x...",
            private_key="0x..."
        )
    """
    
    def __init__(self):
        self.cow = cow_client
        self.aerodrome = get_aerodrome_lp()
        
        # Token decimals
        self.decimals = {
            "USDC": 6,
            "USDT": 6,
            "WETH": 18,
            "ETH": 18,
            "AERO": 18,
            "cbETH": 18,
            "cbBTC": 8,
        }
    
    def _get_decimals(self, token: str) -> int:
        """Get decimals for a token"""
        if token.startswith("0x"):
            # Try to find by address
            for symbol, addr in TOKENS.items():
                if addr.lower() == token.lower():
                    return self.decimals.get(symbol, 18)
            return 18
        return self.decimals.get(token.upper(), 18)
    
    def _resolve_token(self, token: str) -> str:
        """Resolve token symbol to address"""
        if token.startswith("0x"):
            return token
        return TOKENS.get(token.upper(), token)
    
    async def calculate_split(
        self,
        pool_token_a: str,
        pool_token_b: str,
        token_in: str,
        amount_in: int,
        stable: bool = False
    ) -> Tuple[str, int, str, int]:
        """
        Calculate optimal split for dual-sided LP.
        
        Args:
            pool_token_a: First pool token
            pool_token_b: Second pool token
            token_in: Token user is depositing
            amount_in: Amount in wei
            stable: Is stable pool
            
        Returns:
            (token_keep, amount_keep, token_swap, amount_swap)
        """
        token_in_addr = self._resolve_token(token_in)
        token_a_addr = self._resolve_token(pool_token_a)
        token_b_addr = self._resolve_token(pool_token_b)
        
        # Determine which token to swap to
        is_token_a = token_in_addr.lower() == token_a_addr.lower()
        
        if is_token_a:
            token_keep = pool_token_a
            token_swap_to = pool_token_b
        else:
            token_keep = pool_token_b
            token_swap_to = pool_token_a
        
        # Get pool reserves to calculate optimal ratio
        reserves = await self.aerodrome.get_reserves(pool_token_a, pool_token_b, stable)
        reserve_a, reserve_b = reserves
        
        if reserve_a == 0 or reserve_b == 0:
            # New pool or error - use 50/50 split
            amount_to_swap = amount_in // 2
            amount_to_keep = amount_in - amount_to_swap
            print(f"[DualLP] Using 50/50 split: keep {amount_to_keep}, swap {amount_to_swap}")
        else:
            # Calculate based on reserves
            # For optimal LP, we need A/B ratio matching reserves
            # Since we're swapping half, we use 50/50 as approximation
            # A more sophisticated calculation would use: 
            # swap_amount = amount_in * (1 - sqrt(1 / (1 + fee_impact)))
            amount_to_swap = amount_in // 2
            amount_to_keep = amount_in - amount_to_swap
            
            print(f"[DualLP] Pool reserves: {reserve_a} / {reserve_b}")
            print(f"[DualLP] Split: keep {amount_to_keep} {token_in}, swap {amount_to_swap} → {token_swap_to}")
        
        return (token_keep, amount_to_keep, token_swap_to, amount_to_swap)
    
    async def execute_pre_swap(
        self,
        from_token: str,
        to_token: str,
        amount: int,
        agent_address: str,
        private_key: str,
        max_slippage: float = 2.0
    ) -> Optional[str]:
        """
        Execute swap via CoW Swap.
        
        Returns:
            Order UID if successful
        """
        print(f"[DualLP] Swapping {amount} {from_token} → {to_token} via CoW...")
        
        order_uid = await self.cow.swap(
            sell_token=from_token,
            buy_token=to_token,
            sell_amount=amount,
            from_address=agent_address,
            private_key=private_key,
            max_slippage_percent=max_slippage
        )
        
        return order_uid
    
    async def wait_for_swap(
        self,
        order_uid: str,
        timeout: int = 300
    ) -> Optional[Dict]:
        """
        Wait for CoW swap to fill.
        
        Returns:
            Order details if filled, None otherwise
        """
        return await self.cow.wait_for_fill(order_uid, timeout=timeout)
    
    async def deposit_single_token_lp(
        self,
        pool_token_a: str,
        pool_token_b: str,
        token_in: str,
        amount_in: int,
        stable: bool,
        agent_address: str,
        private_key: str,
        max_slippage: float = 2.0,
        swap_timeout: int = 300
    ) -> DualLPResult:
        """
        Deposit single token into dual-sided LP.
        
        Flow:
        1. Calculate 50/50 split
        2. Swap half via CoW Swap
        3. Wait for fill
        4. Add liquidity to Aerodrome
        
        Args:
            pool_token_a: First token in pool (e.g., "USDC")
            pool_token_b: Second token in pool (e.g., "WETH")
            token_in: Token user is depositing (must be one of pool tokens)
            amount_in: Amount in smallest unit (wei/etc)
            stable: True for stable pools
            agent_address: Smart account address
            private_key: Signing key
            max_slippage: Max slippage for swap (default 2%)
            swap_timeout: Max wait for CoW fill (default 5 min)
            
        Returns:
            DualLPResult with operation details
        """
        print(f"[DualLP] ========================================")
        print(f"[DualLP] Depositing {amount_in} {token_in} into {pool_token_a}/{pool_token_b} LP")
        print(f"[DualLP] ========================================")
        
        # 1. Calculate split
        token_keep, amount_keep, token_swap_to, amount_swap = await self.calculate_split(
            pool_token_a, pool_token_b, token_in, amount_in, stable
        )
        
        # 2. Execute swap via CoW
        order_uid = await self.execute_pre_swap(
            from_token=token_in,
            to_token=token_swap_to,
            amount=amount_swap,
            agent_address=agent_address,
            private_key=private_key,
            max_slippage=max_slippage
        )
        
        if not order_uid:
            return DualLPResult(
                success=False,
                error="Failed to create CoW swap order"
            )
        
        print(f"[DualLP] CoW order created: {order_uid[:40]}...")
        
        # 3. Wait for swap to fill
        fill_result = await self.wait_for_swap(order_uid, timeout=swap_timeout)
        
        if not fill_result:
            return DualLPResult(
                success=False,
                swap_order_uid=order_uid,
                swap_filled=False,
                error="CoW swap not filled (timeout/cancelled)"
            )
        
        print(f"[DualLP] ✅ Swap filled!")
        
        # Get actual received amount
        amount_received = int(fill_result.get("executedBuyAmount", 0))
        if amount_received == 0:
            amount_received = int(fill_result.get("buyAmount", 0))
        
        print(f"[DualLP] Received {amount_received} {token_swap_to}")
        
        # 4. Determine final amounts for LP
        # token_in is what we kept, token_swap_to is what we received
        token_in_addr = self._resolve_token(token_in)
        token_a_addr = self._resolve_token(pool_token_a)
        
        if token_in_addr.lower() == token_a_addr.lower():
            # token_in is token_a
            final_amount_a = amount_keep
            final_amount_b = amount_received
        else:
            # token_in is token_b
            final_amount_a = amount_received
            final_amount_b = amount_keep
        
        print(f"[DualLP] Adding LP: {final_amount_a} {pool_token_a} + {final_amount_b} {pool_token_b}")
        
        # 5. Add liquidity
        lp_result = await self.aerodrome.add_liquidity(
            token_a=pool_token_a,
            token_b=pool_token_b,
            amount_a=final_amount_a,
            amount_b=final_amount_b,
            stable=stable,
            agent_address=agent_address,
            private_key=private_key,
            slippage_percent=max_slippage
        )
        
        if not lp_result.success:
            return DualLPResult(
                success=False,
                swap_order_uid=order_uid,
                swap_filled=True,
                error=f"LP deposit failed: {lp_result.error}"
            )
        
        print(f"[DualLP] ✅ LP added! TX: {lp_result.tx_hash}")
        
        return DualLPResult(
            success=True,
            swap_order_uid=order_uid,
            swap_filled=True,
            lp_tx_hash=lp_result.tx_hash,
            amount_a_deposited=final_amount_a,
            amount_b_deposited=final_amount_b,
            lp_tokens_received=lp_result.liquidity
        )
    
    async def get_quote_for_lp(
        self,
        pool_token_a: str,
        pool_token_b: str,
        token_in: str,
        amount_in: int,
        stable: bool = False
    ) -> Dict[str, Any]:
        """
        Get quote for LP deposit without executing.
        
        Returns estimated amounts and fees.
        """
        # Calculate split
        token_keep, amount_keep, token_swap_to, amount_swap = await self.calculate_split(
            pool_token_a, pool_token_b, token_in, amount_in, stable
        )
        
        # Get CoW quote
        quote = await self.cow.get_quote(
            sell_token=self._resolve_token(token_in),
            buy_token=self._resolve_token(token_swap_to),
            sell_amount=amount_swap,
            from_address="0x0000000000000000000000000000000000000001"  # Dummy for quote
        )
        
        if not quote:
            return {
                "success": False,
                "error": "Failed to get swap quote"
            }
        
        q = quote.get("quote", {})
        expected_receive = int(q.get("buyAmount", 0))
        fee = int(q.get("feeAmount", 0))
        
        return {
            "success": True,
            "token_kept": token_keep,
            "amount_kept": amount_keep,
            "token_swapped_to": token_swap_to,
            "amount_to_swap": amount_swap,
            "expected_swap_receive": expected_receive,
            "cow_fee": fee,
            "estimated_lp_amounts": {
                pool_token_a: amount_keep if token_in == pool_token_a else expected_receive,
                pool_token_b: expected_receive if token_in == pool_token_a else amount_keep
            }
        }


# Global instance
_dual_lp_service: Optional[DualSidedLPService] = None


def get_dual_lp_service() -> DualSidedLPService:
    """Get or create global DualSidedLPService instance"""
    global _dual_lp_service
    if _dual_lp_service is None:
        _dual_lp_service = DualSidedLPService()
    return _dual_lp_service


# ============================================
# CLI TEST
# ============================================

if __name__ == "__main__":
    async def test():
        print("=== DualSidedLPService Test ===\n")
        
        service = DualSidedLPService()
        
        # Test quote
        print("Getting quote for 100 USDC → USDC/WETH LP...")
        quote = await service.get_quote_for_lp(
            pool_token_a="USDC",
            pool_token_b="WETH",
            token_in="USDC",
            amount_in=100_000_000,  # 100 USDC
            stable=False
        )
        
        if quote.get("success"):
            print(f"  Keep: {quote['amount_kept']} USDC")
            print(f"  Swap: {quote['amount_to_swap']} USDC → WETH")
            print(f"  Expected WETH: {quote['expected_swap_receive']}")
            print(f"  CoW fee: {quote['cow_fee']}")
        else:
            print(f"  Error: {quote.get('error')}")
        
    asyncio.run(test())
