"""
Meridian x402 Payment Router
Handles x402 payment verification and settlement for Filter Credits purchases.
"""

import os
import logging
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

logger = logging.getLogger("Meridian")
router = APIRouter(prefix="/api/meridian", tags=["meridian"])

# Configuration
MERIDIAN_API_URL = "https://api.mrdn.finance/v1"
MERIDIAN_PK = os.getenv("MERIDIAN_PUBLIC_KEY", "pk_9e408b7d2b5068cc1b5e2d9c01c62660ac3705d6f3173bbeea729b647450e16f")
MERIDIAN_SK = os.getenv("MERIDIAN_SECRET_KEY", "sk_46deb55781b5df700713ecfe5fd56b58654f989e901a1b7a6e54a7553d3ed328")
MERIDIAN_RECIPIENT = os.getenv("MERIDIAN_RECIPIENT", "0xa30A689ec0F9D717C5bA1098455B031b868B720f")

# Meridian contract address for Base mainnet (per docs)
# authorization.to and payTo must point to this address
MERIDIAN_CONTRACT = "0x8E7769D440b3460b92159Dd9C6D17302b036e2d6"

# USDC on Base
USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
NETWORK = "base"

# Credit package pricing
CREDITS_PACKAGE = {
    "credits": 100,
    "price_usdc": "100000",  # 0.10 USDC (6 decimals)
    "price_display": "0.10"
}

# Premium subscription pricing ($99/mo)
PREMIUM_PACKAGE = {
    "price_usdc": "99000000",  # 99 USDC (6 decimals)
    "price_display": "99.00",
    "duration_days": 30,
    "product": "Artisan Bot"
}


class PaymentRequest(BaseModel):
    """Request with signed payment payload from frontend"""
    paymentPayload: Dict[str, Any]


class PaymentResponse(BaseModel):
    """Response after successful payment"""
    success: bool
    credits: int = 0
    transaction: Optional[str] = None
    error: Optional[str] = None


@router.get("/payment-requirements")
async def get_payment_requirements():
    """
    Get payment requirements for Filter Credits purchase.
    Frontend uses this to construct the EIP-712 signature request.
    """
    import time
    
    return {
        "amount": CREDITS_PACKAGE["price_usdc"],
        "recipient": MERIDIAN_CONTRACT,  # Meridian contract, not our wallet
        "network": NETWORK,
        "asset": USDC_ADDRESS,
        "scheme": "exact",
        "maxAmountRequired": CREDITS_PACKAGE["price_usdc"],
        "maxTimeoutSeconds": 3600,
        "resource": "https://techne.finance/credits",
        "description": f"{CREDITS_PACKAGE['credits']} Filter Credits",
        "mimeType": "application/json",
        "id": f"credits-{int(time.time() * 1000)}",
        # Extra info for frontend
        "credits": CREDITS_PACKAGE["credits"],
        "priceDisplay": CREDITS_PACKAGE["price_display"],
        "usdcAddress": USDC_ADDRESS,
        "recipientAddress": MERIDIAN_CONTRACT  # Must match authorization.to
    }


@router.get("/premium-requirements")
async def get_premium_requirements():
    """
    Get payment requirements for $99 Artisan Bot subscription.
    Uses same x402 flow as credits but different amount.
    """
    import time
    
    return {
        "amount": PREMIUM_PACKAGE["price_usdc"],
        "recipient": MERIDIAN_CONTRACT,
        "network": NETWORK,
        "asset": USDC_ADDRESS,
        "scheme": "exact",
        "maxAmountRequired": PREMIUM_PACKAGE["price_usdc"],
        "maxTimeoutSeconds": 3600,
        "resource": "https://techne.finance/premium",
        "description": "Artisan Bot - 30 day subscription",
        "mimeType": "application/json",
        "id": f"premium-{int(time.time() * 1000)}",
        # Extra info for frontend
        "priceDisplay": PREMIUM_PACKAGE["price_display"],
        "usdcAddress": USDC_ADDRESS,
        "recipientAddress": MERIDIAN_CONTRACT,
        "product": PREMIUM_PACKAGE["product"],
        "durationDays": PREMIUM_PACKAGE["duration_days"]
    }


@router.post("/settle", response_model=PaymentResponse)
async def settle_payment(request: PaymentRequest):
    """
    Verify and settle x402 payment.
    1. Verify signature with Meridian API (using pk)
    2. Settle payment (using sk)
    3. Return success with credits
    """
    try:
        payment_payload = request.paymentPayload
        
        # Construct payment requirements (must match Meridian API format)
        # Format based on working cashback-sniper.js
        payment_requirements = {
            "recipient": MERIDIAN_RECIPIENT,  # Final recipient of funds
            "network": NETWORK,
            "asset": USDC_ADDRESS,
            "scheme": "exact",
            "payTo": MERIDIAN_CONTRACT,  # Meridian contract address
            "maxTimeoutSeconds": 3600,
            "resource": "https://techne.finance/credits",
            "description": f"{CREDITS_PACKAGE['credits']} Filter Credits",
            "mimeType": "application/json",
            "amount": CREDITS_PACKAGE["price_usdc"],
            "maxAmountRequired": CREDITS_PACKAGE["price_usdc"]
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            # Step 1: Verify payment
            logger.info("Verifying payment with Meridian...")
            verify_response = await client.post(
                f"{MERIDIAN_API_URL}/verify",
                headers={
                    "Authorization": f"Bearer {MERIDIAN_PK}",
                    "Content-Type": "application/json"
                },
                json={
                    "paymentPayload": payment_payload,
                    "paymentRequirements": payment_requirements
                }
            )
            
            verify_data = verify_response.json()
            logger.info(f"Verify response: {verify_data}")
            
            if not verify_data.get("isValid"):
                return PaymentResponse(
                    success=False,
                    error=f"Payment invalid: {verify_data.get('invalidReason', 'Unknown reason')}"
                )
            
            # Step 2: Settle payment
            logger.info("Settling payment with Meridian...")
            settle_response = await client.post(
                f"{MERIDIAN_API_URL}/settle",
                headers={
                    # Using PK like cashback-sniper - both verify and settle use public key
                    "Authorization": f"Bearer {MERIDIAN_PK}",
                    "Content-Type": "application/json"
                },
                json={
                    "paymentPayload": payment_payload,
                    "paymentRequirements": payment_requirements
                }
            )
            
            settle_data = settle_response.json()
            logger.info(f"Settle response status: {settle_response.status_code}")
            logger.info(f"Settle response: {settle_data}")
            
            if settle_data.get("success"):
                logger.info(f"✅ Payment successful! Transaction: {settle_data.get('transaction')}")
                return PaymentResponse(
                    success=True,
                    credits=CREDITS_PACKAGE["credits"],
                    transaction=settle_data.get("transaction")
                )
            else:
                # Check for error in multiple places (API can return error or errorReason)
                error_msg = settle_data.get('errorReason') or settle_data.get('error') or 'Unknown error'
                logger.error(f"Settlement failed: {error_msg}")
                logger.error(f"Full settle response: {settle_data}")
                return PaymentResponse(
                    success=False,
                    error=f"Settlement failed: {error_msg}"
                )
                
    except httpx.TimeoutException:
        logger.error("Meridian API timeout")
        return PaymentResponse(success=False, error="Payment service timeout")
    except Exception as e:
        logger.error(f"Payment error: {e}")
        return PaymentResponse(success=False, error=str(e))
