"""
x402 Payment Verification for Techne.finance
Real blockchain verification via Alchemy RPC
"""

import os
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

# Configuration (same as sniper)
CONFIG = {
    "api_url": "https://api.mrdn.finance/v1",
    "network": "base",
    "chain_id": 8453,
    "usdc_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "rpc_url": os.getenv("ALCHEMY_RPC_URL", "https://base-mainnet.g.alchemy.com/v2/AqxI9okL6ZYv38MBFDHhb"),
}

# Get keys from environment
API_KEY = os.getenv("MERIDIAN_PUBLIC_KEY")
WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")
ROUTER_ADDRESS = os.getenv("FACILITATOR_CONTRACT_ADDRESS")
RECIPIENT_ADDRESS = os.getenv("RECIPIENT_ADDRESS")

# Web3 connection
w3 = Web3(Web3.HTTPProvider(CONFIG["rpc_url"]))

# USDC Transfer event signature (Transfer(address,address,uint256))
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


@dataclass
class PaymentSession:
    """Track payment sessions for x402"""
    session_id: str
    amount_usd: float
    pool_id: str
    created_at: datetime
    paid: bool = False
    tx_hash: Optional[str] = None


# In-memory payment sessions (use Redis in production)
_sessions: Dict[str, PaymentSession] = {}


def create_payment_session(pool_id: str, amount_usd: float = 0.50) -> PaymentSession:
    """
    Create a new payment session for unlocking pool details
    """
    import secrets
    session_id = secrets.token_urlsafe(16)
    
    session = PaymentSession(
        session_id=session_id,
        amount_usd=amount_usd,
        pool_id=pool_id,
        created_at=datetime.now(),
    )
    
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Optional[PaymentSession]:
    """Get a payment session by ID"""
    return _sessions.get(session_id)


def mark_session_paid(session_id: str, tx_hash: str) -> bool:
    """Mark a session as paid"""
    session = _sessions.get(session_id)
    if session:
        session.paid = True
        session.tx_hash = tx_hash
        return True
    return False


async def verify_usdc_transfer(
    tx_hash: str,
    expected_recipient: str,
    min_amount_usdc: float
) -> Dict[str, Any]:
    """
    Verify a USDC transfer on Base via Alchemy RPC
    """
    try:
        print(f"[x402] Verifying tx: {tx_hash}")
        print(f"[x402] Expected recipient: {expected_recipient}")
        print(f"[x402] Min amount: ${min_amount_usdc}")
        
        # Get transaction receipt
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        
        if not receipt:
            print("[x402] Transaction receipt not found")
            return {"valid": False, "error": "Transaction not found. It may still be pending."}
        
        print(f"[x402] Receipt status: {receipt['status']}")
        print(f"[x402] Logs count: {len(receipt['logs'])}")
        
        if receipt['status'] != 1:
            return {"valid": False, "error": "Transaction failed on blockchain"}
        
        # Look for USDC Transfer event
        usdc_address = CONFIG["usdc_address"].lower()
        expected_recipient_lower = expected_recipient.lower()
        
        # Transfer topic without 0x prefix for comparison
        transfer_topic_clean = TRANSFER_TOPIC.lower().replace("0x", "")
        
        for i, log in enumerate(receipt['logs']):
            log_address = log['address'].lower()
            print(f"[x402] Log {i}: address={log_address}, topics={len(log['topics'])}")
            
            # Check if this is from USDC contract
            if log_address != usdc_address:
                continue
            
            if len(log['topics']) < 3:
                print(f"[x402] Log {i}: Not enough topics")
                continue
            
            # Get topic hex - web3.py returns bytes, need to convert
            topic0 = log['topics'][0]
            if hasattr(topic0, 'hex'):
                topic0_hex = topic0.hex().lower()
            else:
                topic0_hex = topic0.lower().replace("0x", "")
            
            print(f"[x402] Log {i}: topic0={topic0_hex[:20]}...")
            
            # Compare without 0x prefix
            if topic0_hex.replace("0x", "") != transfer_topic_clean:
                print(f"[x402] Log {i}: Not a Transfer event")
                continue
            
            # Decode from/to addresses
            topic1 = log['topics'][1]
            topic2 = log['topics'][2]
            
            if hasattr(topic1, 'hex'):
                from_addr = "0x" + topic1.hex()[-40:]
                to_addr = "0x" + topic2.hex()[-40:]
            else:
                from_addr = "0x" + str(topic1)[-40:]
                to_addr = "0x" + str(topic2)[-40:]
            
            from_addr = from_addr.lower()
            to_addr = to_addr.lower()
            
            print(f"[x402] Transfer: from={from_addr[:10]}... to={to_addr[:10]}...")
            
            # Check recipient matches
            if to_addr != expected_recipient_lower:
                print(f"[x402] Recipient mismatch: expected {expected_recipient_lower[:10]}...")
                continue
            
            # Decode amount (USDC has 6 decimals)
            data = log['data']
            if hasattr(data, 'hex'):
                data_hex = data.hex()
            else:
                data_hex = str(data).replace("0x", "")
            
            amount_wei = int(data_hex, 16)
            amount_usdc = amount_wei / 1_000_000
            
            print(f"[x402] Amount: ${amount_usdc:.2f} USDC")
            
            # Check minimum amount
            if amount_usdc >= min_amount_usdc:
                print(f"[x402] ✅ Payment verified!")
                return {
                    "valid": True,
                    "amount_usdc": amount_usdc,
                    "from": from_addr,
                    "to": to_addr,
                    "tx_hash": tx_hash
                }
            else:
                print(f"[x402] Amount too low: ${amount_usdc} < ${min_amount_usdc}")
        
        return {"valid": False, "error": "No valid USDC transfer to recipient found in transaction"}
        
    except Exception as e:
        print(f"[x402] Error: {e}")
        import traceback
        traceback.print_exc()
        return {"valid": False, "error": f"Verification error: {str(e)}"}


async def verify_x402_payment(
    tx_hash: str,
    expected_amount_usd: float,
    session_id: str
) -> Dict[str, Any]:
    """
    Verify an x402 payment transaction on Base via Alchemy
    """
    session = get_session(session_id)
    
    if not session:
        return {
            "valid": False,
            "error": "Session not found"
        }
    
    if session.paid:
        return {
            "valid": True,
            "already_paid": True,
            "pool_id": session.pool_id
        }
    
    # Validate tx_hash format
    if not tx_hash.startswith("0x") or len(tx_hash) != 66:
        return {
            "valid": False,
            "error": "Invalid transaction hash format"
        }
    
    # Verify on blockchain
    recipient = RECIPIENT_ADDRESS
    if not recipient:
        return {"valid": False, "error": "Recipient address not configured"}
    
    verification = await verify_usdc_transfer(
        tx_hash=tx_hash,
        expected_recipient=recipient,
        min_amount_usdc=expected_amount_usd * 0.95  # 5% tolerance
    )
    
    if verification["valid"]:
        mark_session_paid(session_id, tx_hash)
        return {
            "valid": True,
            "pool_id": session.pool_id,
            "tx_hash": tx_hash,
            "amount_received": verification["amount_usdc"],
            "from_address": verification["from"]
        }
    
    return verification


def get_payment_requirements(pool_id: str, amount_usd: float = 0.50) -> Dict[str, Any]:
    """
    Generate x402 payment requirements for a pool unlock
    """
    session = create_payment_session(pool_id, amount_usd)
    
    # Convert amount to USDC (6 decimals)
    amount_wei = int(amount_usd * 1_000_000)
    
    return {
        "session_id": session.session_id,
        "x402Version": 1,
        "scheme": "exact",
        "network": CONFIG["network"],
        "chain_id": CONFIG["chain_id"],
        "asset": CONFIG["usdc_address"],
        "asset_symbol": "USDC",
        "amount": str(amount_wei),
        "amount_usd": amount_usd,
        "recipient": RECIPIENT_ADDRESS,
        "description": f"Unlock yield details for pool {pool_id[:8]}...",
        "expires_in_seconds": 3600,
        "instructions": f"Send {amount_usd} USDC to {RECIPIENT_ADDRESS} on Base network"
    }


# Test
if __name__ == "__main__":
    import asyncio
    
    print("Testing x402 verifier with Alchemy...")
    print(f"RPC URL: {CONFIG['rpc_url'][:50]}...")
    print(f"Recipient: {RECIPIENT_ADDRESS}")
    
    # Test connection
    try:
        block = w3.eth.block_number
        print(f"✅ Connected! Current block: {block}")
    except Exception as e:
        print(f"❌ RPC Error: {e}")
    
    # Create test session
    requirements = get_payment_requirements("test-pool-123")
    print(f"\nPayment Requirements:")
    print(f"  Amount: ${requirements['amount_usd']} USDC")
    print(f"  Send to: {requirements['recipient']}")
    print(f"  Network: Base (Chain ID: {requirements['chain_id']})")
