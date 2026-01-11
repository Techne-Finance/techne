"""
Moonwell Finance API Client
Fetches lending market data, supply/borrow APY from Moonwell on Base.
"""
import httpx
import logging
from typing import Optional, Dict, List, Any
import time

logger = logging.getLogger("Moonwell")

class MoonwellClient:
    """
    Client for Moonwell Finance API.
    Provides market data, supply APY, borrow rates.
    """
    # Moonwell yield-backend API
    API_URL = "https://yield-api.moonwell.fi"
    CACHE_TTL = 300  # 5 minutes
    
    def __init__(self):
        self._markets_cache: Optional[Dict] = None
        self._cache_time: float = 0
    
    async def _fetch_json(self, endpoint: str = "", timeout: float = 10.0) -> Any:
        """Fetch JSON from Moonwell API."""
        url = f"{self.API_URL}{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Moonwell API error: {e}")
            return None
    
    async def get_all_markets(self, chain: str = "base") -> List[Dict]:
        """
        Get all Moonwell markets (cached).
        Returns list of market objects with supply/borrow APY.
        """
        now = time.time()
        cache_key = f"markets_{chain}"
        
        if self._markets_cache and (now - self._cache_time) < self.CACHE_TTL:
            return self._markets_cache.get(chain, [])
        
        data = await self._fetch_json()
        if data:
            self._markets_cache = data
            self._cache_time = now
            
            # Extract markets for chain
            chain_key = self._normalize_chain(chain)
            markets = data.get(chain_key, {}).get("markets", [])
            logger.info(f"Cached {len(markets)} Moonwell markets for {chain}")
            return markets
        
        return []
    
    def _normalize_chain(self, chain: str) -> str:
        """Normalize chain name to Moonwell format."""
        chain_map = {
            "base": "base",
            "optimism": "optimism",
            "moonbeam": "moonbeam",
            "moonriver": "moonriver",
        }
        return chain_map.get(chain.lower(), chain.lower())
    
    async def get_market_by_token(self, token_symbol: str, chain: str = "base") -> Optional[Dict]:
        """
        Get market by token symbol (e.g., 'USDC', 'ETH', 'cbETH').
        """
        markets = await self.get_all_markets(chain)
        token_upper = token_symbol.upper()
        
        for market in markets:
            symbol = market.get("underlyingSymbol", "").upper()
            if symbol == token_upper or token_upper in symbol:
                return market
        
        return None
    
    async def get_market_by_address(self, address: str, chain: str = "base") -> Optional[Dict]:
        """
        Get market by mToken contract address.
        """
        markets = await self.get_all_markets(chain)
        address_lower = address.lower()
        
        for market in markets:
            market_address = market.get("marketAddress", "").lower()
            underlying_address = market.get("underlyingAddress", "").lower()
            
            if market_address == address_lower or underlying_address == address_lower:
                return market
        
        return None
    
    async def get_market_full_data(self, token_or_address: str, chain: str = "base") -> Optional[Dict]:
        """
        Get complete market data normalized for SmartRouter.
        """
        # Try by address first, then by token symbol
        if token_or_address.startswith("0x"):
            market = await self.get_market_by_address(token_or_address, chain)
        else:
            market = await self.get_market_by_token(token_or_address, chain)
        
        if not market:
            return None
        
        # Extract APY data
        supply_apy = market.get("supplyApy", 0) * 100  # Convert to percentage
        borrow_apy = market.get("borrowApy", 0) * 100
        
        # WELL rewards APY
        supply_rewards_apy = market.get("supplyRewardsApy", 0) * 100
        borrow_rewards_apy = market.get("borrowRewardsApy", 0) * 100
        
        total_supply_apy = supply_apy + supply_rewards_apy
        
        # TVL = total supply in USD
        tvl = market.get("totalSupplyUsd", 0)
        
        # Utilization rate
        total_supply = market.get("totalSupplyUsd", 1)
        total_borrow = market.get("totalBorrowUsd", 0)
        utilization = (total_borrow / total_supply * 100) if total_supply > 0 else 0
        
        return {
            "pool_address": market.get("marketAddress", ""),
            "chain": chain,
            "project": "Moonwell",
            "symbol": market.get("underlyingSymbol", ""),
            "pool_type": "lending",
            "tokens": [market.get("underlyingSymbol", "")],
            "token_symbols": [market.get("underlyingSymbol", "")],
            "tvl": tvl,
            
            # APY breakdown
            "apy": round(total_supply_apy, 2),
            "apy_base": round(supply_apy, 2),
            "apy_reward": round(supply_rewards_apy, 2),
            "apy_source": "moonwell_api",
            
            # Lending-specific
            "lending_type": "supply",
            "borrow_apy": round(borrow_apy, 2),
            "borrow_rewards_apy": round(borrow_rewards_apy, 2),
            "utilization_rate": round(utilization, 2),
            "collateral_factor": market.get("collateralFactor", 0) * 100,
            "reserve_factor": market.get("reserveFactor", 0) * 100,
            
            # Market stats
            "total_supply_usd": total_supply,
            "total_borrow_usd": total_borrow,
            "underlying_price": market.get("underlyingPrice", 0),
            
            # Links
            "pool_link": f"https://moonwell.fi/markets/{chain}/{market.get('underlyingSymbol', '').lower()}",
            "explorer_link": f"https://basescan.org/address/{market.get('marketAddress', '')}",
        }
    
    async def search_markets(self, query: str, chain: str = "base") -> List[Dict]:
        """
        Search markets by token name.
        """
        markets = await self.get_all_markets(chain)
        query_lower = query.lower()
        
        results = []
        for market in markets:
            symbol = market.get("underlyingSymbol", "").lower()
            name = market.get("underlyingName", "").lower()
            
            if query_lower in symbol or query_lower in name:
                results.append(market)
        
        return results


# Singleton instance
moonwell_client = MoonwellClient()
