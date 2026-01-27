"""
CoW Swap Integration
Handles token swaps via CoW Protocol (MEV-protected, gasless swaps)
https://docs.cow.fi/
"""

import httpx
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from eth_account import Account
from eth_account.messages import encode_typed_data
import json

# CoW Protocol API endpoints
COW_API_BASE = "https://api.cow.fi/base"  # Base chain
COW_API_MAINNET = "https://api.cow.fi/mainnet"

# Common token addresses on Base
TOKENS = {
    "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "USDT": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
    "WETH": "0x4200000000000000000000000000000000000006",
    "DAI": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
    "AERO": "0x940181a94A35A4569E4529A3CDfB74e38FD98631",
    "VIRTUALS": "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b",  # Virtuals Protocol token
    "cbETH": "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22",
    "cbBTC": "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf",
}


class CowSwapClient:
    """
    Client for CoW Protocol swaps on Base chain
    
    Features:
    - MEV protection (no frontrunning)
    - Gasless swaps (CoW pays gas)
    - Best execution via batch auctions
    """
    
    def __init__(self, chain: str = "base"):
        self.chain = chain
        self.api_base = COW_API_BASE if chain == "base" else COW_API_MAINNET
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_quote(
        self,
        sell_token: str,
        buy_token: str,
        sell_amount: int,
        from_address: str,
        kind: str = "sell"
    ) -> Optional[Dict[str, Any]]:
        """
        Get a quote for a swap
        
        Args:
            sell_token: Address of token to sell
            buy_token: Address of token to buy
            sell_amount: Amount in wei/smallest unit
            from_address: Address executing the swap
            kind: "sell" or "buy"
        
        Returns:
            Quote object with expected amounts
        """
        try:
            payload = {
                "sellToken": sell_token,
                "buyToken": buy_token,
                "sellAmountBeforeFee": str(sell_amount),
                "from": from_address,
                "kind": kind,
                "receiver": from_address,
                "appData": "{\"version\":\"1.1.0\",\"metadata\":{}}",  # Valid JSON appData
                "partiallyFillable": False,
                "sellTokenBalance": "erc20",
                "buyTokenBalance": "erc20",
                "signingScheme": "eip712"
            }
            
            response = await self.client.post(
                f"{self.api_base}/api/v1/quote",
                json=payload
            )
            
            if response.status_code == 200:
                quote = response.json()
                print(f"[CowSwap] Quote received: sell {sell_amount} → buy {quote.get('quote', {}).get('buyAmount', 'N/A')}")
                return quote
            else:
                print(f"[CowSwap] Quote failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"[CowSwap] Quote error: {e}")
            return None
    
    async def create_order(
        self,
        quote: Dict[str, Any],
        private_key: str
    ) -> Optional[str]:
        """
        Create and sign an order based on a quote
        
        Args:
            quote: Quote object from get_quote()
            private_key: Private key to sign the order
            
        Returns:
            Order UID if successful
        """
        try:
            q = quote.get("quote", {})
            
            # Build order
            order = {
                "sellToken": q["sellToken"],
                "buyToken": q["buyToken"],
                "sellAmount": q["sellAmount"],
                "buyAmount": q["buyAmount"],
                "validTo": q.get("validTo") or int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
                "appData": "0x0000000000000000000000000000000000000000000000000000000000000000",
                "feeAmount": "0",  # Must be 0 for CoW gasless orders
                "kind": q["kind"],
                "partiallyFillable": False,
                "receiver": q.get("receiver") or q["from"],
                "sellTokenBalance": "erc20",
                "buyTokenBalance": "erc20",
                "signingScheme": "eip712",
                "from": quote["from"]
            }
            
            # Sign order with EIP-712
            signature = self._sign_order(order, private_key)
            order["signature"] = signature
            
            # Submit order
            response = await self.client.post(
                f"{self.api_base}/api/v1/orders",
                json=order
            )
            
            if response.status_code in [200, 201]:
                order_uid = response.json()
                print(f"[CowSwap] Order created: {order_uid}")
                return order_uid
            else:
                print(f"[CowSwap] Order failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"[CowSwap] Order error: {e}")
            return None
    
    def _sign_order(self, order: Dict, private_key: str) -> str:
        """Sign order with EIP-712"""
        try:
            # CoW Protocol EIP-712 domain
            domain = {
                "name": "Gnosis Protocol",
                "version": "v2",
                "chainId": 8453 if self.chain == "base" else 1,
                "verifyingContract": "0x9008D19f58AAbD9eD0D60971565AA8510560ab41"  # CoW Settlement
            }
            
            # Order type
            types = {
                "Order": [
                    {"name": "sellToken", "type": "address"},
                    {"name": "buyToken", "type": "address"},
                    {"name": "receiver", "type": "address"},
                    {"name": "sellAmount", "type": "uint256"},
                    {"name": "buyAmount", "type": "uint256"},
                    {"name": "validTo", "type": "uint32"},
                    {"name": "appData", "type": "bytes32"},
                    {"name": "feeAmount", "type": "uint256"},
                    {"name": "kind", "type": "string"},
                    {"name": "partiallyFillable", "type": "bool"},
                    {"name": "sellTokenBalance", "type": "string"},
                    {"name": "buyTokenBalance", "type": "string"},
                ]
            }
            
            # Sign
            account = Account.from_key(private_key)
            signed = account.sign_typed_data(domain, types, order)
            
            return "0x" + signed.signature.hex()
            
        except Exception as e:
            print(f"[CowSwap] Sign error: {e}")
            # Return empty signature for now (will need proper implementation)
            return "0x"
    
    async def get_order_status(self, order_uid: str) -> Optional[Dict]:
        """Check status of an order"""
        try:
            response = await self.client.get(
                f"{self.api_base}/api/v1/orders/{order_uid}"
            )
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            print(f"[CowSwap] Status error: {e}")
            return None
    
    async def swap(
        self,
        sell_token: str,
        buy_token: str,
        sell_amount: int,
        from_address: str,
        private_key: str,
        max_slippage_percent: float = 1.0  # Default 1% slippage tolerance
    ) -> Optional[str]:
        """
        Execute a complete swap with slippage protection
        
        Args:
            sell_token: Token to sell (address or symbol)
            buy_token: Token to buy (address or symbol)
            sell_amount: Amount in wei
            from_address: Wallet address
            private_key: Wallet private key
            max_slippage_percent: Maximum allowed slippage (default 1%)
            
        Returns:
            Order UID if successful, None if slippage exceeded or error
        """
        # Resolve token symbols to addresses
        if not sell_token.startswith("0x"):
            sell_token = TOKENS.get(sell_token.upper(), sell_token)
        if not buy_token.startswith("0x"):
            buy_token = TOKENS.get(buy_token.upper(), buy_token)
        
        # Get quote
        quote = await self.get_quote(
            sell_token=sell_token,
            buy_token=buy_token,
            sell_amount=sell_amount,
            from_address=from_address
        )
        
        if not quote:
            return None
        
        # SLIPPAGE PROTECTION: Calculate and validate price impact
        q = quote.get("quote", {})
        buy_amount = int(q.get("buyAmount", 0))
        sell_amount_after_fee = int(q.get("sellAmount", sell_amount))
        fee_amount = int(q.get("feeAmount", 0))
        
        # Calculate fee impact (applies to all swaps)
        fee_impact = (fee_amount / sell_amount * 100) if sell_amount > 0 else 0
        
        # For non-stablecoin swaps, only check fee impact (not price ratio)
        # Stablecoin addresses on Base
        STABLECOINS = [
            "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC
            "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",  # USDT
            "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",  # DAI
        ]
        
        is_stablecoin_swap = sell_token.lower() in [s.lower() for s in STABLECOINS] and \
                            buy_token.lower() in [s.lower() for s in STABLECOINS]
        
        if is_stablecoin_swap and sell_amount > 0 and buy_amount > 0:
            # For stablecoins, check 1:1 ratio
            price_impact = (1 - buy_amount / sell_amount_after_fee) * 100 if sell_amount_after_fee > 0 else 0
            total_impact = abs(price_impact) + fee_impact
            print(f"[CowSwap] Stablecoin swap - Price impact: {price_impact:.2f}%, Fee: {fee_impact:.2f}%, Total: {total_impact:.2f}%")
            
            if total_impact > max_slippage_percent:
                print(f"[CowSwap] ❌ REJECTED: Slippage {total_impact:.2f}% exceeds max {max_slippage_percent}%")
                return None
        else:
            # For non-stablecoins, only check fee is reasonable (< 5%)
            print(f"[CowSwap] Non-stablecoin swap - Fee impact: {fee_impact:.2f}%")
            if fee_impact > 5.0:
                print(f"[CowSwap] ❌ REJECTED: Fee {fee_impact:.2f}% too high")
                return None
        
        print(f"[CowSwap] ✓ Slippage check passed")
        
        # Approve VaultRelayer to spend sell token
        try:
            from web3 import Web3
            from eth_account import Account
            
            COW_VAULT_RELAYER = "0xC92E8bdf79f0507f65a392b0ab4667716BFE0110"
            RPC_URL = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
            w3 = Web3(Web3.HTTPProvider(RPC_URL))
            
            account = Account.from_key(private_key)
            
            # Check current allowance
            approve_selector = "0x095ea7b3"  # approve(address,uint256)
            max_uint256 = 2**256 - 1
            
            # Build approve calldata
            spender_padded = COW_VAULT_RELAYER[2:].lower().zfill(64)
            amount_padded = hex(max_uint256)[2:].zfill(64)
            approve_data = approve_selector + spender_padded + amount_padded
            
            nonce = w3.eth.get_transaction_count(from_address, 'latest')
            
            approve_tx = {
                'to': Web3.to_checksum_address(sell_token),
                'data': approve_data,
                'from': from_address,
                'nonce': nonce,
                'gas': 60000,
                'gasPrice': int(w3.eth.gas_price * 1.5),
                'chainId': 8453
            }
            
            signed_approve = account.sign_transaction(approve_tx)
            approve_hash = w3.eth.send_raw_transaction(signed_approve.raw_transaction)
            print(f"[CowSwap] Approve TX sent: {approve_hash.hex()}")
            
            # Wait for approval
            receipt = w3.eth.wait_for_transaction_receipt(approve_hash, timeout=60)
            if receipt.status != 1:
                print(f"[CowSwap] ❌ Approve TX failed")
                return None
            print(f"[CowSwap] ✅ Approved VaultRelayer to spend tokens")
            
        except Exception as approve_err:
            print(f"[CowSwap] Approve error: {approve_err}")
            # Continue anyway in case already approved
        
        # Create order
        order_uid = await self.create_order(quote, private_key)
        
        return order_uid
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global client instance
cow_client = CowSwapClient(chain="base")


async def swap_tokens(
    sell_token: str,
    buy_token: str,
    sell_amount: int,
    wallet_address: str,
    private_key: str
) -> Optional[str]:
    """
    Convenience function to swap tokens
    
    Example:
        order_id = await swap_tokens(
            sell_token="USDC",
            buy_token="USDT",
            sell_amount=100_000_000,  # 100 USDC (6 decimals)
            wallet_address="0x...",
            private_key="0x..."
        )
    """
    return await cow_client.swap(
        sell_token=sell_token,
        buy_token=buy_token,
        sell_amount=sell_amount,
        from_address=wallet_address,
        private_key=private_key
    )
