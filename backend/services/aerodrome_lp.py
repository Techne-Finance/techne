"""
Aerodrome LP Service
Direct integration with Aerodrome Router for liquidity operations on Base.

Features:
- Add liquidity (dual-sided)
- Remove liquidity
- Get pool info and reserves
- Calculate optimal amounts

Addresses:
- Router: 0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43
- Factory: 0x420DD381b31aEf6683db6B902084cB0FFECe40Da
"""

import os
import asyncio
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from web3 import Web3
from eth_account import Account

# Aerodrome contract addresses on Base
AERODROME_ROUTER = "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"
AERODROME_FACTORY = "0x420DD381b31aEf6683db6B902084cB0FFECe40Da"

# Common tokens
TOKENS = {
    "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "WETH": "0x4200000000000000000000000000000000000006",
    "AERO": "0x940181a94A35A4569E4529A3CDfB74e38FD98631",
    "cbETH": "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22",
    "cbBTC": "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf",
}

# Router ABI (minimal for liquidity operations)
ROUTER_ABI = [
    {
        "inputs": [
            {"name": "tokenA", "type": "address"},
            {"name": "tokenB", "type": "address"},
            {"name": "stable", "type": "bool"},
            {"name": "amountADesired", "type": "uint256"},
            {"name": "amountBDesired", "type": "uint256"},
            {"name": "amountAMin", "type": "uint256"},
            {"name": "amountBMin", "type": "uint256"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"}
        ],
        "name": "addLiquidity",
        "outputs": [
            {"name": "amountA", "type": "uint256"},
            {"name": "amountB", "type": "uint256"},
            {"name": "liquidity", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "token", "type": "address"},
            {"name": "stable", "type": "bool"},
            {"name": "amountTokenDesired", "type": "uint256"},
            {"name": "amountTokenMin", "type": "uint256"},
            {"name": "amountETHMin", "type": "uint256"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"}
        ],
        "name": "addLiquidityETH",
        "outputs": [
            {"name": "amountToken", "type": "uint256"},
            {"name": "amountETH", "type": "uint256"},
            {"name": "liquidity", "type": "uint256"}
        ],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "tokenA", "type": "address"},
            {"name": "tokenB", "type": "address"},
            {"name": "stable", "type": "bool"},
            {"name": "liquidity", "type": "uint256"},
            {"name": "amountAMin", "type": "uint256"},
            {"name": "amountBMin", "type": "uint256"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"}
        ],
        "name": "removeLiquidity",
        "outputs": [
            {"name": "amountA", "type": "uint256"},
            {"name": "amountB", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "tokenIn", "type": "address"},
            {"name": "tokenOut", "type": "address"},
            {"name": "stable", "type": "bool"}
        ],
        "name": "getAmountOut",
        "outputs": [
            {"name": "amount", "type": "uint256"},
            {"name": "stable", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "tokenA", "type": "address"},
            {"name": "tokenB", "type": "address"},
            {"name": "stable", "type": "bool"}
        ],
        "name": "getReserves",
        "outputs": [
            {"name": "reserveA", "type": "uint256"},
            {"name": "reserveB", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# ERC20 ABI for approvals
ERC20_ABI = [
    {
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]


@dataclass
class LPResult:
    """Result of LP operation"""
    success: bool
    tx_hash: Optional[str] = None
    amount_a: int = 0
    amount_b: int = 0
    liquidity: int = 0
    error: Optional[str] = None


class AerodromeLPService:
    """
    Aerodrome Router integration for LP operations.
    
    Usage:
        service = AerodromeLPService()
        result = await service.add_liquidity(
            token_a="USDC",
            token_b="WETH",
            amount_a=500_000_000,  # 500 USDC
            amount_b=200_000_000_000_000_000,  # 0.2 ETH
            stable=False,
            agent_address="0x...",
            private_key="0x..."
        )
    """
    
    def __init__(self, rpc_url: str = None):
        self.rpc_url = rpc_url or os.environ.get("ALCHEMY_RPC_URL", "https://mainnet.base.org")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.router = self.w3.eth.contract(
            address=Web3.to_checksum_address(AERODROME_ROUTER),
            abi=ROUTER_ABI
        )
        
    def _resolve_token(self, token: str) -> str:
        """Resolve token symbol to address"""
        if token.startswith("0x"):
            return Web3.to_checksum_address(token)
        return Web3.to_checksum_address(TOKENS.get(token.upper(), token))
    
    async def get_reserves(
        self,
        token_a: str,
        token_b: str,
        stable: bool = False
    ) -> Tuple[int, int]:
        """
        Get pool reserves for a token pair.
        
        Returns:
            (reserve_a, reserve_b) in wei
        """
        token_a = self._resolve_token(token_a)
        token_b = self._resolve_token(token_b)
        
        try:
            reserves = self.router.functions.getReserves(
                token_a, token_b, stable
            ).call()
            return (reserves[0], reserves[1])
        except Exception as e:
            print(f"[AerodromeLP] Get reserves error: {e}")
            return (0, 0)
    
    async def calculate_optimal_amounts(
        self,
        token_a: str,
        token_b: str,
        amount_a: int,
        stable: bool = False
    ) -> Tuple[int, int]:
        """
        Calculate optimal amount_b for given amount_a based on reserves.
        
        Returns:
            (optimal_amount_a, optimal_amount_b)
        """
        reserve_a, reserve_b = await self.get_reserves(token_a, token_b, stable)
        
        if reserve_a == 0 or reserve_b == 0:
            # New pool, any ratio works
            return (amount_a, amount_a)
        
        # Calculate proportional amount
        optimal_b = (amount_a * reserve_b) // reserve_a
        return (amount_a, optimal_b)
    
    async def approve_token(
        self,
        token: str,
        amount: int,
        owner_address: str,
        private_key: str
    ) -> bool:
        """Approve Router to spend tokens"""
        token_address = self._resolve_token(token)
        
        try:
            token_contract = self.w3.eth.contract(
                address=token_address,
                abi=ERC20_ABI
            )
            
            # Check current allowance
            current_allowance = token_contract.functions.allowance(
                Web3.to_checksum_address(owner_address),
                Web3.to_checksum_address(AERODROME_ROUTER)
            ).call()
            
            if current_allowance >= amount:
                print(f"[AerodromeLP] Already approved: {current_allowance}")
                return True
            
            # Build approve tx
            account = Account.from_key(private_key)
            nonce = self.w3.eth.get_transaction_count(owner_address, 'latest')
            
            approve_tx = token_contract.functions.approve(
                Web3.to_checksum_address(AERODROME_ROUTER),
                2**256 - 1  # Max approval
            ).build_transaction({
                'from': Web3.to_checksum_address(owner_address),
                'nonce': nonce,
                'gas': 60000,
                'gasPrice': int(self.w3.eth.gas_price * 1.2),
                'chainId': 8453
            })
            
            signed = account.sign_transaction(approve_tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"[AerodromeLP] Approve TX: {tx_hash.hex()}")
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            return receipt.status == 1
            
        except Exception as e:
            print(f"[AerodromeLP] Approve error: {e}")
            return False
    
    async def add_liquidity(
        self,
        token_a: str,
        token_b: str,
        amount_a: int,
        amount_b: int,
        stable: bool,
        agent_address: str,
        private_key: str,
        slippage_percent: float = 1.0
    ) -> LPResult:
        """
        Add liquidity to Aerodrome pool.
        
        Args:
            token_a: First token (symbol or address)
            token_b: Second token (symbol or address)  
            amount_a: Amount of token_a in wei
            amount_b: Amount of token_b in wei
            stable: True for stable pools (e.g., USDC/USDT)
            agent_address: Wallet address
            private_key: Wallet private key
            slippage_percent: Allowed slippage (default 1%)
            
        Returns:
            LPResult with success status and LP token amount
        """
        token_a_addr = self._resolve_token(token_a)
        token_b_addr = self._resolve_token(token_b)
        
        try:
            # 1. Approve both tokens
            print(f"[AerodromeLP] Approving {token_a}...")
            if not await self.approve_token(token_a, amount_a, agent_address, private_key):
                return LPResult(success=False, error="Failed to approve token A")
            
            print(f"[AerodromeLP] Approving {token_b}...")
            if not await self.approve_token(token_b, amount_b, agent_address, private_key):
                return LPResult(success=False, error="Failed to approve token B")
            
            # 2. Calculate min amounts with slippage
            slippage_factor = 1 - (slippage_percent / 100)
            amount_a_min = int(amount_a * slippage_factor)
            amount_b_min = int(amount_b * slippage_factor)
            
            # 3. Build addLiquidity transaction
            account = Account.from_key(private_key)
            nonce = self.w3.eth.get_transaction_count(agent_address, 'latest')
            deadline = self.w3.eth.get_block('latest')['timestamp'] + 1200  # 20 min
            
            add_liq_tx = self.router.functions.addLiquidity(
                token_a_addr,
                token_b_addr,
                stable,
                amount_a,
                amount_b,
                amount_a_min,
                amount_b_min,
                Web3.to_checksum_address(agent_address),
                deadline
            ).build_transaction({
                'from': Web3.to_checksum_address(agent_address),
                'nonce': nonce,
                'gas': 300000,
                'gasPrice': int(self.w3.eth.gas_price * 1.2),
                'chainId': 8453
            })
            
            # 4. Sign and send
            signed = account.sign_transaction(add_liq_tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"[AerodromeLP] Add liquidity TX: {tx_hash.hex()}")
            
            # 5. Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt.status == 1:
                print(f"[AerodromeLP] ✅ Liquidity added successfully!")
                # TODO: Parse logs to get actual amounts
                return LPResult(
                    success=True,
                    tx_hash=tx_hash.hex(),
                    amount_a=amount_a,
                    amount_b=amount_b,
                    liquidity=0  # Would parse from logs
                )
            else:
                return LPResult(success=False, error="Transaction reverted", tx_hash=tx_hash.hex())
                
        except Exception as e:
            print(f"[AerodromeLP] Add liquidity error: {e}")
            return LPResult(success=False, error=str(e))
    
    async def remove_liquidity(
        self,
        token_a: str,
        token_b: str,
        lp_amount: int,
        stable: bool,
        agent_address: str,
        private_key: str,
        slippage_percent: float = 1.0
    ) -> LPResult:
        """
        Remove liquidity from Aerodrome pool.
        
        Returns:
            LPResult with amounts received
        """
        token_a_addr = self._resolve_token(token_a)
        token_b_addr = self._resolve_token(token_b)
        
        try:
            account = Account.from_key(private_key)
            nonce = self.w3.eth.get_transaction_count(agent_address, 'latest')
            deadline = self.w3.eth.get_block('latest')['timestamp'] + 1200
            
            # With slippage, accept 0 minimum (for simplicity)
            # In production, should calculate based on reserves
            
            remove_tx = self.router.functions.removeLiquidity(
                token_a_addr,
                token_b_addr,
                stable,
                lp_amount,
                0,  # amountAMin
                0,  # amountBMin  
                Web3.to_checksum_address(agent_address),
                deadline
            ).build_transaction({
                'from': Web3.to_checksum_address(agent_address),
                'nonce': nonce,
                'gas': 250000,
                'gasPrice': int(self.w3.eth.gas_price * 1.2),
                'chainId': 8453
            })
            
            signed = account.sign_transaction(remove_tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"[AerodromeLP] Remove liquidity TX: {tx_hash.hex()}")
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt.status == 1:
                print(f"[AerodromeLP] ✅ Liquidity removed successfully!")
                return LPResult(success=True, tx_hash=tx_hash.hex())
            else:
                return LPResult(success=False, error="Transaction reverted", tx_hash=tx_hash.hex())
                
        except Exception as e:
            print(f"[AerodromeLP] Remove liquidity error: {e}")
            return LPResult(success=False, error=str(e))


# Global instance
_aerodrome_lp: Optional[AerodromeLPService] = None


def get_aerodrome_lp() -> AerodromeLPService:
    """Get or create global AerodromeLPService instance"""
    global _aerodrome_lp
    if _aerodrome_lp is None:
        _aerodrome_lp = AerodromeLPService()
    return _aerodrome_lp


# ============================================
# CLI TEST
# ============================================

if __name__ == "__main__":
    async def test():
        print("=== AerodromeLPService Test ===")
        
        service = AerodromeLPService()
        
        # Test get reserves
        reserves = await service.get_reserves("USDC", "WETH", stable=False)
        print(f"USDC/WETH reserves: {reserves}")
        
        # Test calculate optimal
        optimal = await service.calculate_optimal_amounts(
            "USDC", "WETH",
            amount_a=100_000_000,  # 100 USDC
            stable=False
        )
        print(f"For 100 USDC, need {optimal[1] / 10**18:.6f} WETH")
        
    asyncio.run(test())
