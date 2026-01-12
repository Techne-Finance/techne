"""
RugCheck.xyz API Client for Solana Token Security
Provides token safety analysis (rug pull risk, mutable metadata, etc.)
"""
import httpx
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger("RugCheck")

RUGCHECK_API_BASE = "https://api.rugcheck.xyz/v1"


class RugCheckClient:
    """Client for RugCheck.xyz API (Solana tokens)"""
    
    def __init__(self):
        self.timeout = 15.0
        logger.info("🔍 RugCheck client initialized (Solana)")
    
    async def check_token(self, mint_address: str) -> Optional[Dict[str, Any]]:
        """
        Check Solana token security via RugCheck API.
        
        Args:
            mint_address: Solana token mint address (base58)
            
        Returns:
            Security analysis dict or None if not found
        """
        url = f"{RUGCHECK_API_BASE}/tokens/{mint_address}/report"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                
                if response.status_code == 404:
                    logger.debug(f"Token not found on RugCheck: {mint_address[:8]}...")
                    return None
                    
                if response.status_code != 200:
                    logger.warning(f"RugCheck API error: {response.status_code}")
                    return None
                
                data = response.json()
                return self._normalize_response(data, mint_address)
                
        except Exception as e:
            logger.error(f"RugCheck request failed: {e}")
            return None
    
    async def check_tokens(self, mint_addresses: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Check multiple Solana tokens.
        
        Args:
            mint_addresses: List of Solana token mint addresses
            
        Returns:
            Dict mapping mint address to security analysis
        """
        results = {}
        
        for mint in mint_addresses:
            if mint and len(mint) > 30:  # Basic Solana address validation
                result = await self.check_token(mint)
                if result:
                    results[mint] = result
        
        return results
    
    def _normalize_response(self, data: Dict[str, Any], mint: str) -> Dict[str, Any]:
        """
        Normalize RugCheck response to match GoPlus format for consistency.
        """
        # RugCheck returns various risk indicators
        risks = data.get("risks") or []  # Handle None
        score = data.get("score", 0)  # 0-100, higher is safer
        
        # Map RugCheck risks to our format
        risk_list = []
        is_critical = False
        score_penalty = 0
        
        for risk in risks:
            risk_name = risk.get("name", "")
            risk_level = risk.get("level", "")
            risk_description = risk.get("description", risk_name)
            
            if risk_level == "critical" or risk_level == "danger":
                is_critical = True
                score_penalty += 50
                risk_list.append({
                    "type": "CRITICAL",
                    "reason": f"🚨 {risk_description}"
                })
            elif risk_level == "warn" or risk_level == "warning":
                score_penalty += 20
                risk_list.append({
                    "type": "HIGH",
                    "reason": f"⚠️ {risk_description}"
                })
            elif risk_level == "info":
                score_penalty += 5
                risk_list.append({
                    "type": "MEDIUM",
                    "reason": risk_description
                })
        
        # Check for specific risk flags
        is_mutable = any("mutable" in r.get("name", "").lower() for r in risks)
        has_freeze_authority = any("freeze" in r.get("name", "").lower() for r in risks)
        low_liquidity = any("liquidity" in r.get("name", "").lower() for r in risks)
        
        return {
            "mint_address": mint,
            "source": "rugcheck",
            "score": score,
            "score_normalized": max(0, 100 - score_penalty),  # Convert to our 0-100 scale
            "is_critical": is_critical,
            "is_honeypot": False,  # RugCheck doesn't have direct honeypot flag
            "is_verified": True,  # Solana tokens are always "verified" on-chain
            "is_mutable": is_mutable,
            "has_freeze_authority": has_freeze_authority,
            "low_liquidity": low_liquidity,
            "risks": risk_list,
            "score_penalty": min(score_penalty, 100),
            "raw_data": {
                "score": score,
                "risk_count": len(risks),
                "market": data.get("market", {}),
                "token_meta": data.get("tokenMeta", {})
            }
        }


# Singleton instance
rugcheck_client = RugCheckClient()
