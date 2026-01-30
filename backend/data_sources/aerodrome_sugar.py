"""
Aerodrome Sugar v3 Contract Integration
Direct on-chain data fetching for Aerodrome pools on Base.

Sugar v3 Contract: 0x68c19e13618C41158fE4bAba1B8fb3A9c74bDb0A
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from web3 import Web3

# Sugar v3 contract address on Base
SUGAR_ADDRESS = "0x68c19e13618C41158fE4bAba1B8fb3A9c74bDb0A"

# LP Sugar v3 ABI - `all` function takes 2 params (no account), returns 26 fields
SUGAR_ABI = [
    {
        "name": "all",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "_limit", "type": "uint256"},
            {"name": "_offset", "type": "uint256"}
        ],
        "outputs": [
            {
                "name": "",
                "type": "tuple[]",
                "components": [
                    {"name": "lp", "type": "address"},
                    {"name": "symbol", "type": "string"},
                    {"name": "decimals", "type": "uint8"},
                    {"name": "liquidity", "type": "uint256"},
                    {"name": "type", "type": "int24"},
                    {"name": "tick", "type": "int24"},
                    {"name": "sqrt_ratio", "type": "uint160"},
                    {"name": "token0", "type": "address"},
                    {"name": "reserve0", "type": "uint256"},
                    {"name": "staked0", "type": "uint256"},
                    {"name": "token1", "type": "address"},
                    {"name": "reserve1", "type": "uint256"},
                    {"name": "staked1", "type": "uint256"},
                    {"name": "gauge", "type": "address"},
                    {"name": "gauge_liquidity", "type": "uint256"},
                    {"name": "gauge_alive", "type": "bool"},
                    {"name": "fee", "type": "address"},
                    {"name": "bribe", "type": "address"},
                    {"name": "factory", "type": "address"},
                    {"name": "emissions", "type": "uint256"},
                    {"name": "emissions_token", "type": "address"},
                    {"name": "pool_fee", "type": "uint256"},
                    {"name": "unstaked_fee", "type": "uint256"},
                    {"name": "token0_fees", "type": "uint256"},
                    {"name": "token1_fees", "type": "uint256"},
                    {"name": "nfpm", "type": "address"}
                ]
            }
        ]
    }
]

# AERO token price (simplified - in production use oracle)
AERO_PRICE_USD = 1.50


class AerodromeSugar:
    """
    Fetches Aerodrome pool data directly from Sugar v3 contracts on Base.
    
    Benefits over The Graph:
    - Zero API cost (only RPC calls)
    - Live on-chain data (block-level accuracy)
    - No rate limits beyond RPC
    """
    
    def __init__(self, rpc_url: str = None):
        self.rpc_url = rpc_url or os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.sugar = self.w3.eth.contract(
            address=Web3.to_checksum_address(SUGAR_ADDRESS),
            abi=SUGAR_ABI
        )
        
        # Cache with 5 min TTL
        self.cache: Dict[str, Any] = {}
        self.cache_time: Dict[str, datetime] = {}
        self.cache_ttl = 300  # 5 minutes
        
    def _is_cache_valid(self, key: str) -> bool:
        if key not in self.cache_time:
            return False
        return datetime.now() - self.cache_time[key] < timedelta(seconds=self.cache_ttl)
    
    def _parse_pool(self, raw_pool: tuple) -> Dict:
        """Parse raw tuple from Sugar v3 contract into dict (26 fields)"""
        return {
            "lp": raw_pool[0],
            "symbol": raw_pool[1],
            "decimals": raw_pool[2],
            "liquidity": raw_pool[3],
            "type": raw_pool[4],           # Pool type (CL tick spacing or 0 for stable/volatile)
            "tick": raw_pool[5],
            "sqrt_ratio": raw_pool[6],
            "token0": raw_pool[7],
            "reserve0": raw_pool[8],
            "staked0": raw_pool[9],
            "token1": raw_pool[10],
            "reserve1": raw_pool[11],
            "staked1": raw_pool[12],
            "gauge": raw_pool[13],
            "gauge_liquidity": raw_pool[14],
            "gauge_alive": raw_pool[15],
            "fee": raw_pool[16],
            "bribe": raw_pool[17],
            "factory": raw_pool[18],
            "emissions": raw_pool[19],
            "emissions_token": raw_pool[20],
            "pool_fee": raw_pool[21],
            "unstaked_fee": raw_pool[22],
            "token0_fees": raw_pool[23],
            "token1_fees": raw_pool[24],
            "nfpm": raw_pool[25],
        }
    
    def _calculate_tvl(self, pool: Dict) -> float:
        """Estimate TVL in USD (simplified - use oracle in production)"""
        reserve0 = pool["reserve0"] / 1e18
        reserve1 = pool["reserve1"] / 1e18
        
        symbol = pool["symbol"].upper()
        
        # Simple heuristic for stablecoin pools
        if "USDC" in symbol or "USDT" in symbol or "DAI" in symbol:
            return (reserve0 + reserve1) * 1.0  # Assume ~$1
        
        # For other pools, rough estimate
        return (reserve0 + reserve1) * 0.5
    
    def _calculate_apr(self, pool: Dict) -> float:
        """Calculate APR from emissions"""
        emissions_per_sec = pool["emissions"] / 1e18
        emissions_per_year = emissions_per_sec * 365 * 24 * 60 * 60
        
        tvl = self._calculate_tvl(pool)
        if tvl <= 0:
            return 0
        
        apr = (emissions_per_year * AERO_PRICE_USD) / tvl * 100
        return min(apr, 10000)  # Cap at 10000%
    
    async def get_all_pools(self, limit: int = 300, offset: int = 0) -> List[Dict]:
        """Fetch all Aerodrome pools from Sugar v3 contract."""
        cache_key = f"all_pools_{limit}_{offset}"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        try:
            # Sugar v3: all(limit, offset) - NO account parameter
            raw_pools = self.sugar.functions.all(limit, offset).call()
            
            pools = []
            for raw in raw_pools:
                pool = self._parse_pool(raw)
                pool["tvlUsd"] = self._calculate_tvl(pool)
                pool["apy"] = self._calculate_apr(pool)
                pool["project"] = "aerodrome"
                pool["chain"] = "Base"
                pool["source"] = "sugar_v3"
                pools.append(pool)
            
            self.cache[cache_key] = pools
            self.cache_time[cache_key] = datetime.now()
            
            return pools
            
        except Exception as e:
            print(f"[AerodromeSugar] Error fetching pools: {e}")
            return self.cache.get(cache_key, [])
    
    async def get_pool_by_address(self, pool_address: str) -> Optional[Dict]:
        """Get specific pool data by address."""
        all_pools = await self.get_all_pools()
        
        pool_address = pool_address.lower()
        for pool in all_pools:
            if pool["lp"].lower() == pool_address:
                return pool
        
        return None
    
    async def get_pools_for_tracking(self, min_tvl: float = 100000, min_apr: float = 5) -> List[Dict]:
        """Get pools suitable for tracking/investment."""
        all_pools = await self.get_all_pools()
        
        return [
            p for p in all_pools 
            if p["tvlUsd"] >= min_tvl 
            and p["apy"] >= min_apr
            and p["gauge_alive"]
        ]


# Singleton instance
aerodrome_sugar = AerodromeSugar()


async def get_aerodrome_pools_from_sugar(min_tvl: float = 100000) -> List[Dict]:
    """Convenience function for fetching Aerodrome pools via Sugar"""
    pools = await aerodrome_sugar.get_all_pools()
    return [p for p in pools if p["tvlUsd"] >= min_tvl]


if __name__ == "__main__":
    async def test():
        print("Testing Aerodrome Sugar v3...")
        sugar = AerodromeSugar()
        print(f"RPC: {sugar.rpc_url[:40]}...")
        print(f"Sugar: {sugar.sugar.address}")
        
        pools = await sugar.get_all_pools(limit=20)
        print(f"\n✅ Fetched {len(pools)} pools")
        
        if pools:
            print("\nTop 5 by emissions:")
            sorted_pools = sorted(pools, key=lambda p: p.get("emissions", 0), reverse=True)
            for p in sorted_pools[:5]:
                print(f"  {p['symbol'][:35]:<35} APR: {p['apy']:.1f}%  Emissions: {p['emissions']/1e18:.2f}/s")
    
    asyncio.run(test())
