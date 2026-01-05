"""
Aerodrome Finance LP Integration
Deposit and withdraw liquidity from Aerodrome pools on Base
"""

import os
from web3 import Web3
from eth_account import Account
from typing import Dict, Any, Optional, Tuple

# Aerodrome V2 addresses on Base
AERODROME_ROUTER = "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"
USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
WETH_ADDRESS = "0x4200000000000000000000000000000000000006"

# ABIs
ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
]

# Aerodrome Router ABI (partial - only what we need)
AERODROME_ROUTER_ABI = [
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
    }
]


class AerodromeLP:
    """Aerodrome Liquidity Provider helper"""
    
    def __init__(self, rpc_url: str, private_key: Optional[str] = None):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.private_key = private_key
        self.account = Account.from_key(private_key) if private_key else None
        
        self.router = self.w3.eth.contract(
            address=self.w3.to_checksum_address(AERODROME_ROUTER),
            abi=AERODROME_ROUTER_ABI
        )
    
    def get_token_contract(self, address: str):
        return self.w3.eth.contract(
            address=self.w3.to_checksum_address(address),
            abi=ERC20_ABI
        )
    
    def approve_token(self, token_address: str, amount: int) -> str:
        """Approve router to spend tokens"""
        if not self.account:
            raise ValueError("No private key configured")
        
        token = self.get_token_contract(token_address)
        
        # Check current allowance
        allowance = token.functions.allowance(
            self.account.address, 
            AERODROME_ROUTER
        ).call()
        
        if allowance >= amount:
            print(f"Already approved: {allowance}")
            return None
        
        # Build approval tx
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        tx = token.functions.approve(
            self.w3.to_checksum_address(AERODROME_ROUTER),
            amount
        ).build_transaction({
            'from': self.account.address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': self.w3.eth.gas_price,
            'chainId': 8453
        })
        
        signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        print(f"Approved: {tx_hash.hex()}")
        return tx_hash.hex()
    
    def add_liquidity(
        self,
        token_a: str,
        token_b: str,
        amount_a: int,
        amount_b: int,
        stable: bool = True,
        slippage: float = 0.01  # 1%
    ) -> Dict[str, Any]:
        """
        Add liquidity to an Aerodrome pool
        Returns tx hash and amounts
        """
        if not self.account:
            raise ValueError("No private key configured")
        
        # Calculate min amounts with slippage
        min_a = int(amount_a * (1 - slippage))
        min_b = int(amount_b * (1 - slippage))
        
        # Deadline: 20 minutes from now
        deadline = self.w3.eth.get_block('latest')['timestamp'] + 1200
        
        # First approve both tokens
        print(f"Approving token A...")
        self.approve_token(token_a, amount_a)
        
        print(f"Approving token B...")
        self.approve_token(token_b, amount_b)
        
        # Build addLiquidity tx
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        tx = self.router.functions.addLiquidity(
            self.w3.to_checksum_address(token_a),
            self.w3.to_checksum_address(token_b),
            stable,
            amount_a,
            amount_b,
            min_a,
            min_b,
            self.account.address,
            deadline
        ).build_transaction({
            'from': self.account.address,
            'nonce': nonce,
            'gas': 350000,
            'gasPrice': self.w3.eth.gas_price,
            'chainId': 8453
        })
        
        signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return {
            "success": receipt['status'] == 1,
            "tx_hash": tx_hash.hex(),
            "block": receipt['blockNumber'],
            "gas_used": receipt['gasUsed'],
            "basescan": f"https://basescan.org/tx/{tx_hash.hex()}"
        }
    
    def remove_liquidity(
        self,
        token_a: str,
        token_b: str,
        lp_token: str,
        lp_amount: int,
        stable: bool = True,
        slippage: float = 0.01
    ) -> Dict[str, Any]:
        """
        Remove liquidity from an Aerodrome pool
        """
        if not self.account:
            raise ValueError("No private key configured")
        
        # Approve LP token
        print(f"Approving LP token...")
        self.approve_token(lp_token, lp_amount)
        
        # Calculate min amounts (0 for simplicity - use quote in production)
        min_a = 0
        min_b = 0
        
        deadline = self.w3.eth.get_block('latest')['timestamp'] + 1200
        
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        tx = self.router.functions.removeLiquidity(
            self.w3.to_checksum_address(token_a),
            self.w3.to_checksum_address(token_b),
            stable,
            lp_amount,
            min_a,
            min_b,
            self.account.address,
            deadline
        ).build_transaction({
            'from': self.account.address,
            'nonce': nonce,
            'gas': 250000,
            'gasPrice': self.w3.eth.gas_price,
            'chainId': 8453
        })
        
        signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return {
            "success": receipt['status'] == 1,
            "tx_hash": tx_hash.hex(),
            "basescan": f"https://basescan.org/tx/{tx_hash.hex()}"
        }


# Test function
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    RPC_URL = os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")
    PRIVATE_KEY = os.getenv("PRIVATE_KEY")
    
    if not PRIVATE_KEY:
        print("Set PRIVATE_KEY in .env to test")
        exit(1)
    
    lp = AerodromeLP(RPC_URL, PRIVATE_KEY)
    
    print(f"Wallet: {lp.account.address}")
    
    # Example: Add $1 USDC + equivalent WETH to stable pool
    # amount_usdc = 1_000_000  # $1 USDC
    # amount_weth = ?  # Would need price oracle
    
    # result = lp.add_liquidity(
    #     USDC_ADDRESS,
    #     WETH_ADDRESS,
    #     amount_usdc,
    #     amount_weth,
    #     stable=False  # USDC/WETH is volatile pair
    # )
    # print(result)
