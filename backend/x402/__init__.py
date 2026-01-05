# x402 Payment Module
from .verifier import (
    create_payment_session,
    get_session,
    verify_x402_payment,
    get_payment_requirements
)

def create_x402_payment_session(user_wallet: str, amount_usd: float, duration_days: int = 30, tier: str = "pro"):
    """Create a payment session for x402 subscription"""
    import uuid
    import time
    
    session_id = str(uuid.uuid4())
    
    return {
        "session_id": session_id,
        "user_wallet": user_wallet,
        "amount_usd": amount_usd,
        "duration_days": duration_days,
        "tier": tier,
        "created_at": int(time.time()),
        "payment_details": {
            "recipient": "0x1234567890123456789012345678901234567890",  # Your wallet
            "amount": str(int(amount_usd * 1e6)),  # USDC has 6 decimals
            "token": "USDC",
            "chain": "base",
            "chain_id": 8453
        }
    }
