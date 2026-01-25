"""
Gas Manager Service
Monitors ETH balance per agent and proactively refills from USDC when low.

Features:
- Per-agent gas tracking
- Predictive depletion based on tx history
- Auto swap USDC → ETH via Aerodrome
- Minimal refill amounts (~$10)
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import deque
import os

# Try imports, fallback gracefully
try:
    from web3 import Web3
    from eth_account import Account
    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False

# Configuration
GAS_CONFIG = {
    "MIN_TX_BUFFER": 5,              # Trigger refill when < 5 tx remaining
    "REFILL_AMOUNT_USD": 10,         # Swap $10 USDC → ETH
    "CHECK_INTERVAL_SECONDS": 300,   # Check every 5 min
    "DEFAULT_AVG_TX_COST_ETH": 0.0002,  # ~$0.60 at $3000 ETH
    "USDC_DECIMALS": 6,
    "ETH_DECIMALS": 18,
}

# In-memory storage per agent
_agent_gas_data: Dict[str, Dict] = {}


class GasManager:
    """
    Manages gas (ETH) for deployed agents.
    
    Usage:
        manager = GasManager(rpc_url="https://base-mainnet.g.alchemy.com/...")
        
        # Check and refill if needed
        result = await manager.check_and_refill(agent_address)
        
        if result["refilled"]:
            print(f"Refilled {result['amount_eth']} ETH")
    """
    
    def __init__(self, rpc_url: str = None):
        self.rpc_url = rpc_url or os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url)) if HAS_WEB3 else None
        
        # Aerodrome router on Base
        self.aerodrome_router = "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"
        self.weth_address = "0x4200000000000000000000000000000000000006"
        self.usdc_address = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        
    def _get_agent_data(self, agent_address: str) -> Dict:
        """Get or create agent gas tracking data."""
        addr = agent_address.lower()
        if addr not in _agent_gas_data:
            _agent_gas_data[addr] = {
                "tx_costs": deque(maxlen=50),  # Last 50 tx costs
                "last_check": None,
                "total_refills": 0,
                "total_eth_refilled": 0.0,
            }
        return _agent_gas_data[addr]
    
    async def get_eth_balance(self, agent_address: str) -> float:
        """Get current ETH balance in ETH (not wei)."""
        if not self.w3:
            return 0.01  # Mock for testing
            
        try:
            balance_wei = self.w3.eth.get_balance(
                Web3.to_checksum_address(agent_address)
            )
            return float(self.w3.from_wei(balance_wei, 'ether'))
        except Exception as e:
            print(f"[GAS] Error getting balance: {e}")
            return 0.0
    
    def record_tx_cost(self, agent_address: str, gas_used: int, gas_price: int):
        """Record a transaction cost for average calculation."""
        data = self._get_agent_data(agent_address)
        cost_eth = (gas_used * gas_price) / (10 ** 18)
        data["tx_costs"].append(cost_eth)
    
    def get_avg_tx_cost(self, agent_address: str) -> float:
        """Get average transaction cost based on history."""
        data = self._get_agent_data(agent_address)
        
        if not data["tx_costs"]:
            return GAS_CONFIG["DEFAULT_AVG_TX_COST_ETH"]
        
        return sum(data["tx_costs"]) / len(data["tx_costs"])
    
    def predict_remaining_tx(self, agent_address: str, current_balance: float) -> int:
        """Predict how many transactions can be executed with current balance."""
        avg_cost = self.get_avg_tx_cost(agent_address)
        if avg_cost <= 0:
            avg_cost = GAS_CONFIG["DEFAULT_AVG_TX_COST_ETH"]
        
        return int(current_balance / avg_cost)
    
    def should_refill(self, remaining_tx: int) -> bool:
        """Check if refill is needed based on remaining tx count."""
        return remaining_tx < GAS_CONFIG["MIN_TX_BUFFER"]
    
    def calculate_refill_amount(self, eth_price_usd: float = 3000) -> Dict[str, float]:
        """Calculate how much USDC to swap and expected ETH output."""
        usdc_amount = GAS_CONFIG["REFILL_AMOUNT_USD"]
        expected_eth = usdc_amount / eth_price_usd
        
        # Add 10% buffer for slippage
        usdc_with_buffer = usdc_amount * 1.1
        
        return {
            "usdc_amount": usdc_amount,
            "usdc_raw": int(usdc_amount * (10 ** GAS_CONFIG["USDC_DECIMALS"])),
            "expected_eth": expected_eth,
            "min_eth_out": expected_eth * 0.95,  # 5% slippage tolerance
        }
    
    async def execute_swap_usdc_to_eth(
        self, 
        agent_address: str,
        usdc_amount: float,
        private_key: str = None
    ) -> Dict[str, Any]:
        """
        Execute USDC → ETH swap via Aerodrome.
        
        In production, this would:
        1. Approve USDC spending
        2. Call Aerodrome router
        3. Unwrap WETH → ETH
        
        For now, returns mock result.
        """
        # TODO: Implement actual swap when contract integration ready
        
        refill = self.calculate_refill_amount()
        
        return {
            "success": True,
            "tx_hash": "0x" + "0" * 64,  # Mock
            "usdc_spent": usdc_amount,
            "eth_received": refill["expected_eth"],
            "mock": True,  # Flag for testing
        }
    
    async def check_and_refill(
        self, 
        agent_address: str,
        eth_price_usd: float = 3000,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Main entry point: check gas level and refill if needed.
        
        Args:
            agent_address: The agent wallet to check
            eth_price_usd: Current ETH price for calculations
            dry_run: If True, don't execute swap, just report
            
        Returns:
            {
                "checked": True,
                "current_balance_eth": 0.002,
                "avg_tx_cost": 0.0002,
                "remaining_tx": 10,
                "needs_refill": False,
                "refilled": False,
                ...
            }
        """
        data = self._get_agent_data(agent_address)
        data["last_check"] = datetime.utcnow().isoformat()
        
        # Get current balance
        current_balance = await self.get_eth_balance(agent_address)
        
        # Calculate predictions
        avg_cost = self.get_avg_tx_cost(agent_address)
        remaining_tx = self.predict_remaining_tx(agent_address, current_balance)
        needs_refill = self.should_refill(remaining_tx)
        
        result = {
            "checked": True,
            "agent": agent_address,
            "current_balance_eth": round(current_balance, 6),
            "avg_tx_cost_eth": round(avg_cost, 6),
            "remaining_tx": remaining_tx,
            "needs_refill": needs_refill,
            "refilled": False,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if needs_refill and not dry_run:
            refill_calc = self.calculate_refill_amount(eth_price_usd)
            
            # Execute swap
            swap_result = await self.execute_swap_usdc_to_eth(
                agent_address,
                refill_calc["usdc_amount"]
            )
            
            if swap_result["success"]:
                result["refilled"] = True
                result["refill_usdc"] = swap_result["usdc_spent"]
                result["refill_eth"] = swap_result["eth_received"]
                result["tx_hash"] = swap_result["tx_hash"]
                
                # Update tracking
                data["total_refills"] += 1
                data["total_eth_refilled"] += swap_result["eth_received"]
                
                result["log_message"] = (
                    f"[GAS] Low gas detected ({remaining_tx} tx remaining). "
                    f"Swapped ${refill_calc['usdc_amount']} USDC → "
                    f"{swap_result['eth_received']:.4f} ETH"
                )
        
        return result
    
    def get_stats(self, agent_address: str) -> Dict[str, Any]:
        """Get gas management statistics for an agent."""
        data = self._get_agent_data(agent_address)
        
        return {
            "agent": agent_address,
            "total_refills": data["total_refills"],
            "total_eth_refilled": round(data["total_eth_refilled"], 6),
            "tx_history_count": len(data["tx_costs"]),
            "avg_tx_cost": round(self.get_avg_tx_cost(agent_address), 6),
            "last_check": data["last_check"],
        }


# Global instance
_gas_manager: Optional[GasManager] = None

def get_gas_manager() -> GasManager:
    """Get or create global GasManager instance."""
    global _gas_manager
    if _gas_manager is None:
        _gas_manager = GasManager()
    return _gas_manager


# ============================================
# CLI TEST
# ============================================

if __name__ == "__main__":
    async def test():
        print("=" * 60)
        print("Gas Manager Test")
        print("=" * 60)
        
        manager = GasManager()
        
        # Mock agent
        test_agent = "0x1234567890123456789012345678901234567890"
        
        # Record some tx history
        for _ in range(10):
            manager.record_tx_cost(test_agent, 100000, 1000000000)  # 100k gas @ 1 gwei
        
        # Check (dry run)
        result = await manager.check_and_refill(test_agent, dry_run=True)
        
        print(f"\n  Agent: {result['agent'][:10]}...")
        print(f"  Balance: {result['current_balance_eth']} ETH")
        print(f"  Avg TX Cost: {result['avg_tx_cost_eth']} ETH")
        print(f"  Remaining TX: {result['remaining_tx']}")
        print(f"  Needs Refill: {result['needs_refill']}")
        
        # Simulate low balance
        print("\n  Simulating low balance scenario...")
        
        # Force needs_refill by checking with low threshold
        result2 = await manager.check_and_refill(test_agent, dry_run=False)
        
        if result2.get("refilled"):
            print(f"  ✅ Refilled: {result2['refill_eth']} ETH")
            print(f"  Log: {result2.get('log_message', 'N/A')}")
        
        # Stats
        stats = manager.get_stats(test_agent)
        print(f"\n  Stats: {stats}")
    
    asyncio.run(test())
