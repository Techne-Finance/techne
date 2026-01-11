"""
Merkl API Client - Fetch APY data from Merkl (Angle Protocol)
https://merkl.angle.money

Merkl provides an API with pre-calculated APR for LP incentives.
Updates approximately every 2 hours.
"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger("Merkl")

# Chain ID mapping
CHAIN_IDS = {
    "base": 8453,
    "ethereum": 1,
    "arbitrum": 42161,
    "optimism": 10,
    "polygon": 137,
}


class MerklClient:
    """Client for Merkl API to fetch APR data for incentivized pools."""
    
    BASE_URL = "https://api.merkl.xyz/v4"
    CACHE_TTL = 7200  # 2 hours - matches Merkl update frequency
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, datetime] = {}
        logger.info("🎯 Merkl client initialized")
    
    def _get_chain_id(self, chain: str) -> int:
        """Convert chain name to chain ID."""
        return CHAIN_IDS.get(chain.lower(), 8453)
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        if key not in self._cache_time:
            return False
        age = (datetime.now() - self._cache_time[key]).total_seconds()
        return age < self.CACHE_TTL
    
    async def get_opportunities(self, chain: str = "base") -> List[Dict[str, Any]]:
        """
        Fetch all Merkl opportunities (incentivized pools) for a chain.
        
        Returns list of opportunities with APR, TVL, and token info.
        """
        chain_id = self._get_chain_id(chain)
        cache_key = f"opportunities_{chain_id}"
        
        # Check cache
        if self._is_cache_valid(cache_key):
            logger.debug(f"Using cached Merkl data for chain {chain}")
            return self._cache[cache_key]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.BASE_URL}/opportunities?chainId={chain_id}"
                response = await client.get(url)
                response.raise_for_status()
                
                data = response.json()
                
                # Cache the result
                self._cache[cache_key] = data
                self._cache_time[cache_key] = datetime.now()
                
                logger.info(f"Fetched {len(data) if isinstance(data, list) else 'unknown'} Merkl opportunities for {chain}")
                return data
                
        except httpx.HTTPError as e:
            logger.error(f"Merkl API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Merkl client error: {e}")
            return []
    
    async def get_pool_apr(self, pool_address: str, chain: str = "base") -> Optional[Dict[str, Any]]:
        """
        Get APR data for a specific pool address.
        
        Returns dict with:
        - apr: Total APR percentage
        - tvl: Total Value Locked in USD
        - rewards: List of reward tokens and their APRs
        - source: "merkl"
        """
        pool_address = pool_address.lower()
        opportunities = await self.get_opportunities(chain)
        
        if not opportunities:
            return None
        
        # Search for pool in opportunities
        for opportunity in opportunities:
            try:
                # Check if this opportunity matches our pool
                opp_identifier = opportunity.get("identifier", "").lower()
                opp_tokens = opportunity.get("tokens", [])
                
                # Check identifier match
                if pool_address in opp_identifier:
                    return self._parse_opportunity(opportunity)
                
                # Check AMM info if available
                amm_info = opportunity.get("amm", {})
                if amm_info:
                    amm_pool = amm_info.get("address", "").lower()
                    if pool_address == amm_pool:
                        return self._parse_opportunity(opportunity)
                
                # Check action data
                action = opportunity.get("action", {})
                if action:
                    action_pool = action.get("poolAddress", "").lower()
                    if pool_address == action_pool:
                        return self._parse_opportunity(opportunity)
                        
            except Exception as e:
                logger.debug(f"Error parsing opportunity: {e}")
                continue
        
        logger.info(f"Pool {pool_address[:10]}... not found in Merkl opportunities")
        return None
    
    def _parse_opportunity(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Merkl opportunity into standard APR response."""
        try:
            # Extract APR from different possible structures
            apr = 0.0
            
            # Check for direct apr field
            if "apr" in opportunity:
                apr = float(opportunity.get("apr", 0))
            
            # Check breakdown for APR values
            breakdowns = opportunity.get("breakdowns", [])
            if breakdowns:
                for breakdown in breakdowns:
                    if isinstance(breakdown, dict):
                        apr += float(breakdown.get("value", 0))
            
            # Extract TVL
            tvl = float(opportunity.get("tvl", 0))
            
            # Extract tokens
            tokens = []
            for token in opportunity.get("tokens", []):
                if isinstance(token, dict):
                    tokens.append({
                        "symbol": token.get("symbol", "TOKEN"),
                        "address": token.get("address", ""),
                    })
            
            # Extract reward info
            rewards = []
            reward_data = opportunity.get("rewards", {})
            if isinstance(reward_data, dict):
                for key, value in reward_data.items():
                    if isinstance(value, dict):
                        rewards.append({
                            "token": value.get("symbol", key),
                            "apr": float(value.get("apr", 0)),
                        })
            
            result = {
                "apr": apr,
                "tvl": tvl,
                "tokens": tokens,
                "rewards": rewards,
                "source": "merkl",
                "name": opportunity.get("name", "Merkl Opportunity"),
                "identifier": opportunity.get("identifier", ""),
            }
            
            logger.info(f"Merkl APR for {result['name']}: {apr:.2f}%")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing Merkl opportunity: {e}")
            return {
                "apr": 0,
                "tvl": 0,
                "source": "merkl",
                "error": str(e)
            }


# Singleton instance
merkl_client = MerklClient()
