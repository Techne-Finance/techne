# infrastructure/rpc.py
"""
Centralized RPC configuration for Techne Finance.
Uses Alchemy as primary RPC for Base chain.
"""
import os
from web3 import Web3
from typing import Optional


def get_rpc_url() -> str:
    """Get the primary RPC URL - Alchemy first, then fallback."""
    return os.getenv("ALCHEMY_RPC_URL") or os.getenv("BASE_RPC_URL") or "https://mainnet.base.org"


def get_web3(rpc_url: Optional[str] = None) -> Web3:
    """Get a Web3 instance connected to Base mainnet."""
    url = rpc_url or get_rpc_url()
    return Web3(Web3.HTTPProvider(url))


# Pre-configured instance for quick imports
w3 = None

def get_w3() -> Web3:
    """Get cached Web3 instance (lazy initialization)."""
    global w3
    if w3 is None:
        w3 = get_web3()
    return w3


# Base chain constants
CHAIN_ID = 8453
CHAIN_NAME = "Base"
