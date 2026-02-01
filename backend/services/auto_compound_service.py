"""
Auto-Compound Service for Aerodrome LP Rewards
Claims AERO emissions and reinvests them into LP position.

Workflow:
1. Monitor pending AERO rewards
2. Claim from Gauge contract (getReward)
3. Swap AERO → pool tokens via CoW
4. Add to LP position

Features:
- Automatic compounding on schedule
- MEV-protected swaps via CoW
- Configurable min compound threshold
- Supports any Aerodrome pool
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from web3 import Web3
from eth_account import Account
from datetime import datetime, timedelta

from integrations.cow_swap import cow_client, TOKENS
from services.aerodrome_lp import get_aerodrome_lp, LPResult
from services.dual_lp_service import get_dual_lp_service


# Aerodrome contract addresses
AERO_TOKEN = "0x940181a94A35A4569E4529A3CDfB74e38FD98631"

# Gauge ABI (minimal for reward claiming)
GAUGE_ABI = [
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "earned",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "getReward",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "rewardToken",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "stakingToken",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Pool ABI for token info
POOL_ABI = [
    {
        "inputs": [],
        "name": "token0",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token1",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "stable",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]


@dataclass
class CompoundResult:
    """Result of auto-compound operation"""
    success: bool
    aero_claimed: int = 0
    aero_value_usd: float = 0.0
    lp_added: int = 0
    tx_hash_claim: Optional[str] = None
    tx_hash_lp: Optional[str] = None
    error: Optional[str] = None


@dataclass
class PoolPosition:
    """LP position info"""
    gauge_address: str
    pool_address: str
    token0: str
    token1: str
    stable: bool
    staked_lp: int
    pending_aero: int


class AutoCompoundService:
    """
    Automatically compounds AERO rewards into LP positions.
    
    Usage:
        service = AutoCompoundService()
        
        # Check pending rewards
        pending = await service.get_pending_rewards(gauge_address, agent_address)
        
        # Compound if above threshold
        if pending > MIN_COMPOUND:
            result = await service.compound(
                gauge_address=gauge_address,
                agent_address=agent_address,
                private_key=private_key
            )
    """
    
    # Minimum AERO to compound (avoid dust, ~$5 worth)
    MIN_COMPOUND_AERO = 5 * 10**18  # 5 AERO
    
    def __init__(self, rpc_url: str = None):
        self.rpc_url = rpc_url or os.environ.get("ALCHEMY_RPC_URL", "https://mainnet.base.org")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.cow = cow_client
        self.dual_lp = get_dual_lp_service()
        self.aerodrome_lp = get_aerodrome_lp()
        
    def _get_gauge_contract(self, gauge_address: str):
        """Get Gauge contract instance"""
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(gauge_address),
            abi=GAUGE_ABI
        )
    
    def _get_pool_contract(self, pool_address: str):
        """Get Pool contract instance"""
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=POOL_ABI
        )
    
    async def get_pending_rewards(
        self,
        gauge_address: str,
        account: str
    ) -> int:
        """
        Get pending AERO rewards for an account.
        
        Returns:
            Amount of AERO in wei (18 decimals)
        """
        try:
            gauge = self._get_gauge_contract(gauge_address)
            earned = gauge.functions.earned(
                Web3.to_checksum_address(account)
            ).call()
            return earned
        except Exception as e:
            print(f"[AutoCompound] Error getting pending: {e}")
            return 0
    
    async def get_position_info(
        self,
        gauge_address: str,
        account: str
    ) -> Optional[PoolPosition]:
        """
        Get full position info for an LP stake.
        """
        try:
            gauge = self._get_gauge_contract(gauge_address)
            
            # Get staked LP balance
            staked = gauge.functions.balanceOf(
                Web3.to_checksum_address(account)
            ).call()
            
            # Get pool address (staking token)
            pool_address = gauge.functions.stakingToken().call()
            
            # Get pending rewards
            pending = await self.get_pending_rewards(gauge_address, account)
            
            # Get pool tokens
            pool = self._get_pool_contract(pool_address)
            token0 = pool.functions.token0().call()
            token1 = pool.functions.token1().call()
            stable = pool.functions.stable().call()
            
            return PoolPosition(
                gauge_address=gauge_address,
                pool_address=pool_address,
                token0=token0,
                token1=token1,
                stable=stable,
                staked_lp=staked,
                pending_aero=pending
            )
            
        except Exception as e:
            print(f"[AutoCompound] Error getting position: {e}")
            return None
    
    async def claim_rewards(
        self,
        gauge_address: str,
        agent_address: str,
        private_key: str
    ) -> Optional[str]:
        """
        Claim AERO rewards from gauge.
        
        Returns:
            Transaction hash if successful
        """
        try:
            gauge = self._get_gauge_contract(gauge_address)
            account = Account.from_key(private_key)
            
            # Build getReward transaction
            nonce = self.w3.eth.get_transaction_count(agent_address, 'latest')
            
            claim_tx = gauge.functions.getReward(
                Web3.to_checksum_address(agent_address)
            ).build_transaction({
                'from': Web3.to_checksum_address(agent_address),
                'nonce': nonce,
                'gas': 200000,
                'gasPrice': int(self.w3.eth.gas_price * 1.2),
                'chainId': 8453
            })
            
            signed = account.sign_transaction(claim_tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            
            print(f"[AutoCompound] Claim TX: {tx_hash.hex()}")
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            if receipt.status == 1:
                print(f"[AutoCompound] ✅ Rewards claimed!")
                return tx_hash.hex()
            else:
                print(f"[AutoCompound] ❌ Claim failed")
                return None
                
        except Exception as e:
            print(f"[AutoCompound] Claim error: {e}")
            return None
    
    async def compound(
        self,
        gauge_address: str,
        agent_address: str,
        private_key: str,
        min_aero: int = None
    ) -> CompoundResult:
        """
        Full auto-compound workflow:
        1. Check pending rewards
        2. Claim AERO
        3. Swap AERO → pool token (via CoW)
        4. Add to LP
        
        Args:
            gauge_address: Aerodrome gauge contract
            agent_address: Agent smart account
            private_key: Signing key
            min_aero: Minimum AERO to compound (default 5 AERO)
            
        Returns:
            CompoundResult with operation details
        """
        min_aero = min_aero or self.MIN_COMPOUND_AERO
        
        print(f"[AutoCompound] ========================================")
        print(f"[AutoCompound] Starting compound for {agent_address[:10]}...")
        print(f"[AutoCompound] ========================================")
        
        # 1. Get position info
        position = await self.get_position_info(gauge_address, agent_address)
        
        if not position:
            return CompoundResult(success=False, error="Failed to get position info")
        
        pending = position.pending_aero
        print(f"[AutoCompound] Pending AERO: {pending / 10**18:.4f}")
        
        # Check minimum threshold
        if pending < min_aero:
            print(f"[AutoCompound] Below minimum ({min_aero / 10**18:.2f} AERO), skipping")
            return CompoundResult(
                success=True,
                aero_claimed=0,
                error="Below minimum threshold"
            )
        
        # 2. Claim rewards
        claim_hash = await self.claim_rewards(gauge_address, agent_address, private_key)
        
        if not claim_hash:
            return CompoundResult(success=False, error="Failed to claim rewards")
        
        # 3. Determine which token to swap to
        # Strategy: Swap to the token with better liquidity (usually USDC or WETH)
        token0 = position.token0
        token1 = position.token1
        
        # Prefer stablecoins or WETH as target
        STABLES = ["0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"]  # USDC
        WETH = "0x4200000000000000000000000000000000000006"
        
        if token0.lower() in [s.lower() for s in STABLES]:
            target_token = token0
            target_name = "USDC"
        elif token1.lower() in [s.lower() for s in STABLES]:
            target_token = token1
            target_name = "USDC"
        elif token0.lower() == WETH.lower():
            target_token = token0
            target_name = "WETH"
        elif token1.lower() == WETH.lower():
            target_token = token1
            target_name = "WETH"
        else:
            target_token = token0
            target_name = "token0"
        
        print(f"[AutoCompound] Swapping AERO → {target_name}")
        
        # 4. Deposit via DualSidedLP (handles swap + LP add)
        # First swap AERO → target token via CoW
        order_uid = await self.cow.swap(
            sell_token=AERO_TOKEN,
            buy_token=target_token,
            sell_amount=pending,
            from_address=agent_address,
            private_key=private_key,
            max_slippage_percent=2.0
        )
        
        if not order_uid:
            return CompoundResult(
                success=False,
                aero_claimed=pending,
                tx_hash_claim=claim_hash,
                error="Failed to create swap order"
            )
        
        # Wait for swap to fill
        fill_result = await self.cow.wait_for_fill(order_uid, timeout=300)
        
        if not fill_result:
            return CompoundResult(
                success=False,
                aero_claimed=pending,
                tx_hash_claim=claim_hash,
                error="Swap not filled"
            )
        
        received_amount = int(fill_result.get("executedBuyAmount", 0))
        print(f"[AutoCompound] Received {received_amount} {target_name}")
        
        # 5. Add to LP via dual_lp_service
        lp_result = await self.dual_lp.deposit_single_token_lp(
            pool_token_a=position.token0,
            pool_token_b=position.token1,
            token_in=target_token,
            amount_in=received_amount,
            stable=position.stable,
            agent_address=agent_address,
            private_key=private_key
        )
        
        if not lp_result.success:
            return CompoundResult(
                success=False,
                aero_claimed=pending,
                tx_hash_claim=claim_hash,
                error=f"LP add failed: {lp_result.error}"
            )
        
        print(f"[AutoCompound] ✅ Compound complete!")
        print(f"  Claimed: {pending / 10**18:.4f} AERO")
        print(f"  LP TX: {lp_result.lp_tx_hash}")
        
        return CompoundResult(
            success=True,
            aero_claimed=pending,
            lp_added=lp_result.lp_tokens_received,
            tx_hash_claim=claim_hash,
            tx_hash_lp=lp_result.lp_tx_hash
        )
    
    async def compound_all_positions(
        self,
        gauge_addresses: List[str],
        agent_address: str,
        private_key: str
    ) -> List[CompoundResult]:
        """
        Compound rewards from multiple gauge positions.
        """
        results = []
        
        for gauge in gauge_addresses:
            print(f"\n[AutoCompound] Processing gauge {gauge[:10]}...")
            result = await self.compound(gauge, agent_address, private_key)
            results.append(result)
            
            # Small delay between compounds
            await asyncio.sleep(2)
        
        return results


# Global instance
_auto_compound: Optional[AutoCompoundService] = None


def get_auto_compound_service() -> AutoCompoundService:
    """Get or create global AutoCompoundService instance"""
    global _auto_compound
    if _auto_compound is None:
        _auto_compound = AutoCompoundService()
    return _auto_compound


# ============================================
# Scheduler for periodic compounding
# ============================================

class CompoundScheduler:
    """
    Runs auto-compound on a schedule for registered agents.
    
    Usage:
        scheduler = CompoundScheduler()
        scheduler.register(agent_address, [gauge1, gauge2], private_key)
        await scheduler.start()
    """
    
    def __init__(self, interval_hours: int = 24):
        self.interval = timedelta(hours=interval_hours)
        self.agents: Dict[str, Dict] = {}  # address -> {gauges, key, last_compound}
        self.running = False
        self.service = get_auto_compound_service()
    
    def register(
        self,
        agent_address: str,
        gauge_addresses: List[str],
        private_key: str
    ):
        """Register an agent for auto-compounding"""
        self.agents[agent_address] = {
            "gauges": gauge_addresses,
            "key": private_key,
            "last_compound": None
        }
        print(f"[Scheduler] Registered {agent_address[:10]}... for auto-compound")
    
    def unregister(self, agent_address: str):
        """Unregister an agent"""
        if agent_address in self.agents:
            del self.agents[agent_address]
            print(f"[Scheduler] Unregistered {agent_address[:10]}...")
    
    async def run_once(self):
        """Run one round of compounding for all agents"""
        now = datetime.utcnow()
        
        for address, info in self.agents.items():
            last = info.get("last_compound")
            
            # Check if due for compound
            if last is None or (now - last) >= self.interval:
                print(f"[Scheduler] Compounding for {address[:10]}...")
                
                results = await self.service.compound_all_positions(
                    gauge_addresses=info["gauges"],
                    agent_address=address,
                    private_key=info["key"]
                )
                
                info["last_compound"] = now
                
                # Log results
                successful = sum(1 for r in results if r.success)
                print(f"[Scheduler] Completed {successful}/{len(results)} compounds")
    
    async def start(self):
        """Start the scheduler loop"""
        self.running = True
        print(f"[Scheduler] Started with {len(self.agents)} agents, interval {self.interval}")
        
        while self.running:
            try:
                await self.run_once()
            except Exception as e:
                print(f"[Scheduler] Error: {e}")
            
            # Sleep for 1 hour between checks
            await asyncio.sleep(3600)
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        print("[Scheduler] Stopped")


# ============================================
# CLI TEST
# ============================================

if __name__ == "__main__":
    async def test():
        print("=== AutoCompoundService Test ===\n")
        
        service = AutoCompoundService()
        
        # Example gauge (would need real gauge address)
        test_gauge = "0xA4e46b4f701c62e14DF11B48dCe76A7d793CD6d7"
        test_account = "0x0000000000000000000000000000000000000001"
        
        print(f"Testing with gauge: {test_gauge[:20]}...")
        
        # This would fail with real data but tests the structure
        pending = await service.get_pending_rewards(test_gauge, test_account)
        print(f"Pending AERO: {pending / 10**18:.4f}")
        
    asyncio.run(test())
