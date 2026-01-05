"""
Techne Agent Wallet - Backend Service
Manages rebalancing logic and pool selection for the Agent Wallet contract
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from web3 import Web3
from eth_account import Account

# Contract ABI (simplified - key functions only)
AGENT_WALLET_ABI = [
    {
        "inputs": [{"name": "protocols", "type": "address[]"}, {"name": "pools", "type": "address[]"}, {"name": "amounts", "type": "uint256[]"}],
        "name": "rebalance",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalValue",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getAllocationCount",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Base protocols with their deposit functions
BASE_PROTOCOLS = {
    "morpho": {
        "address": "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb",  # Morpho Blue on Base
        "type": "lending"
    },
    "aave-v3": {
        "address": "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",  # Aave V3 Pool on Base
        "type": "lending"
    },
    "moonwell": {
        "address": "0x70778cfcFC475c7eA0f24cC625Baf6EaE475D0c9",  # Moonwell on Base
        "type": "lending"
    },
    "compound-v3": {
        "address": "0x46e6b214b524310239732D51387075E0e70970bf",  # Compound V3 cUSDC on Base
        "type": "lending"
    }
}


class AgentWalletService:
    """Service to manage Agent Wallet rebalancing"""
    
    def __init__(
        self,
        wallet_address: str,
        private_key: str,
        rpc_url: str = "https://base-mainnet.g.alchemy.com/v2/Cts9SUVykfnWx2pW5qWWS"
    ):
        self.wallet_address = Web3.to_checksum_address(wallet_address)
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.account = Account.from_key(private_key)
        self.contract = self.w3.eth.contract(
            address=self.wallet_address,
            abi=AGENT_WALLET_ABI
        )
        
    async def get_best_pools(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Fetch best single-sided pools from DefiLlama
        Returns top pools sorted by APY for Base chain
        """
        from artisan.data_sources import fetch_defillama_yields
        
        try:
            pools = await fetch_defillama_yields(chain="Base")
            
            # Filter to single-sided only
            single_sided = [
                p for p in pools
                if p.get("exposure", "").lower() == "single"
                or "lending" in p.get("category", "").lower()
                or "supply" in p.get("category", "").lower()
            ]
            
            # Sort by APY
            single_sided.sort(key=lambda x: x.get("apy", 0), reverse=True)
            
            return single_sided[:limit]
            
        except Exception as e:
            print(f"[AgentWallet] Error fetching pools: {e}")
            return []
    
    def calculate_allocation(
        self,
        total_value: int,
        pools: List[Dict[str, Any]],
        max_per_pool: float = 0.25  # 25% max per pool
    ) -> List[Dict[str, Any]]:
        """
        Calculate optimal allocation across pools
        Simple strategy: equal weight with max cap
        """
        if not pools:
            return []
            
        n_pools = len(pools)
        base_allocation = total_value // n_pools
        max_allocation = int(total_value * max_per_pool)
        
        allocations = []
        for pool in pools:
            amount = min(base_allocation, max_allocation)
            
            # Map pool to protocol address
            project = pool.get("project", "").lower()
            protocol_info = BASE_PROTOCOLS.get(project)
            
            if protocol_info:
                allocations.append({
                    "protocol": protocol_info["address"],
                    "pool": pool.get("pool", protocol_info["address"]),
                    "amount": amount,
                    "apy": pool.get("apy", 0),
                    "tvl": pool.get("tvlUsd", 0)
                })
        
        return allocations
    
    async def execute_rebalance(
        self,
        allocations: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Execute rebalance transaction on-chain
        Returns transaction hash if successful
        """
        if not allocations:
            print("[AgentWallet] No allocations to execute")
            return None
            
        try:
            protocols = [a["protocol"] for a in allocations]
            pools = [a["pool"] for a in allocations]
            amounts = [a["amount"] for a in allocations]
            
            # Build transaction
            tx = self.contract.functions.rebalance(
                protocols, pools, amounts
            ).build_transaction({
                "from": self.account.address,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "gas": 500000,
                "maxFeePerGas": self.w3.eth.gas_price * 2,
                "maxPriorityFeePerGas": self.w3.to_wei(0.001, "gwei")
            })
            
            # Sign and send
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
            
            print(f"[AgentWallet] Rebalance tx sent: {tx_hash.hex()}")
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt["status"] == 1:
                print(f"[AgentWallet] Rebalance confirmed in block {receipt['blockNumber']}")
                return tx_hash.hex()
            else:
                print("[AgentWallet] Rebalance failed")
                return None
                
        except Exception as e:
            print(f"[AgentWallet] Rebalance error: {e}")
            return None
    
    async def run_rebalance_cycle(self) -> Dict[str, Any]:
        """
        Full rebalance cycle:
        1. Get current total value
        2. Fetch best pools 
        3. Calculate allocation
        4. Execute rebalance
        """
        try:
            # Get current value
            total_value = self.contract.functions.totalValue().call()
            print(f"[AgentWallet] Total value: {total_value / 1e6:.2f} USDC")
            
            if total_value < 10 * 1e6:  # Minimum 10 USDC
                return {"status": "skipped", "reason": "Below minimum value"}
            
            # Get best pools
            pools = await self.get_best_pools(limit=5)
            print(f"[AgentWallet] Found {len(pools)} pools")
            
            if not pools:
                return {"status": "skipped", "reason": "No pools found"}
            
            # Calculate allocation
            allocations = self.calculate_allocation(total_value, pools)
            print(f"[AgentWallet] Calculated {len(allocations)} allocations")
            
            # Execute rebalance
            tx_hash = await self.execute_rebalance(allocations)
            
            return {
                "status": "success" if tx_hash else "failed",
                "tx_hash": tx_hash,
                "total_value": total_value,
                "allocations": len(allocations),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}


# ============================================
# SCHEDULED REBALANCING
# ============================================

async def daily_rebalance():
    """Run daily rebalance (called by scheduler)"""
    wallet_address = os.getenv("AGENT_WALLET_ADDRESS")
    private_key = os.getenv("AGENT_PRIVATE_KEY")
    
    if not wallet_address or not private_key:
        print("[AgentWallet] Missing env vars, skipping rebalance")
        return
    
    service = AgentWalletService(wallet_address, private_key)
    result = await service.run_rebalance_cycle()
    print(f"[AgentWallet] Rebalance result: {result}")
    return result


# For manual testing
if __name__ == "__main__":
    import asyncio
    asyncio.run(daily_rebalance())
