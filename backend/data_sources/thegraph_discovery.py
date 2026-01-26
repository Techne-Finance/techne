"""
The Graph Pool Discovery Service
Real-time detection of new DeFi pools via subgraph subscriptions

Features:
- Poll Aerodrome subgraph for new pools
- Detect PoolCreated events
- Immediate notification to strategy executor
- Background monitoring

Subgraphs used:
- Aerodrome V2: https://thegraph.com/hosted-service/subgraph/messari/aerodrome-v2-base
"""

import os
import asyncio
import httpx
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TheGraph")

# API endpoints - using official REST APIs instead of The Graph
# Aerodrome: https://api.aerodrome.finance/
# No API key required!

POOL_APIS = {
    "aerodrome": {
        "url": "https://api.aerodrome.finance/pools",
        "name": "Aerodrome",
        "chain": "base"
    },
    "aerodrome_tokens": {
        "url": "https://api.aerodrome.finance/tokens", 
        "name": "Aerodrome Tokens",
        "chain": "base"
    }
}


class PoolDiscovery:
    """
    Pool discovery using Aerodrome REST API.
    
    Usage:
        discovery = PoolDiscovery()
        
        # One-time fetch
        pools = await discovery.fetch_aerodrome_pools(min_tvl=50000)
        
        # Continuous monitoring
        discovery.on_new_pool(callback_function)
        await discovery.start_monitoring(interval=60)
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.known_pools: set = set()
        self.callbacks: List[Callable] = []
        self.is_running = False
        
        logger.info("🔍 Pool Discovery initialized (Aerodrome REST API)")
    
    async def fetch_aerodrome_pools(self, min_tvl: float = 10000) -> List[Dict]:
        """Fetch pools from Aerodrome REST API."""
        try:
            response = await self.client.get(POOL_APIS["aerodrome"]["url"])
            
            if response.status_code != 200:
                logger.error(f"Aerodrome API error: {response.status_code}")
                return []
            
            all_pools = response.json()
            
            # Filter and transform
            result = []
            for pool in all_pools:
                tvl = float(pool.get("tvl", 0) or 0)
                
                if tvl >= min_tvl:
                    result.append({
                        "address": pool.get("lp", ""),
                        "name": pool.get("symbol", ""),
                        "symbol": pool.get("symbol", ""),
                        "tvl": tvl,
                        "apr": float(pool.get("apr", 0) or 0),
                        "tokens": [
                            pool.get("token0", {}).get("symbol", ""),
                            pool.get("token1", {}).get("symbol", "")
                        ],
                        "token0_address": pool.get("token0", {}).get("address", ""),
                        "token1_address": pool.get("token1", {}).get("address", ""),
                        "is_stable": pool.get("isStable", False),
                        "has_gauge": pool.get("gauge") is not None,
                        "gauge_address": pool.get("gauge", {}).get("address") if pool.get("gauge") else None,
                        "protocol": "Aerodrome",
                        "chain": "base"
                    })
            
            # Sort by TVL
            result.sort(key=lambda x: x["tvl"], reverse=True)
            
            logger.info(f"[Aerodrome] Fetched {len(result)} pools (TVL >= ${min_tvl:,.0f})")
            return result
            
        except Exception as e:
            logger.error(f"[Aerodrome] Fetch error: {e}")
            return []
    
    async def check_new_pools(self, min_tvl: float = 10000) -> List[Dict]:
        """Check for new pools not seen before."""
        all_pools = await self.fetch_aerodrome_pools(min_tvl=min_tvl)
        
        new_pools = []
        for pool in all_pools:
            pool_id = pool["address"]
            
            if pool_id and pool_id not in self.known_pools:
                self.known_pools.add(pool_id)
                pool["is_new"] = True
                new_pools.append(pool)
        
        if new_pools:
            logger.info(f"🆕 Found {len(new_pools)} NEW Aerodrome pools!")
            for pool in new_pools[:3]:
                logger.info(f"   → {pool['symbol']} | TVL: ${pool['tvl']:,.0f} | APR: {pool['apr']:.1f}%")
        
        return new_pools
    
    def on_new_pool(self, callback: Callable):
        """Register callback for new pool events."""
        self.callbacks.append(callback)
        logger.info(f"Registered callback: {callback.__name__}")
    
    async def _notify_callbacks(self, pools: List[Dict]):
        """Notify all registered callbacks about new pools."""
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(pools)
                else:
                    callback(pools)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    async def start_monitoring(self, interval: int = 60, min_tvl: float = 10000):
        """
        Start continuous monitoring for new pools.
        
        Args:
            interval: Check interval in seconds (default: 60)
            min_tvl: Minimum TVL filter (default: $10,000)
        """
        self.is_running = True
        logger.info(f"🚀 Started pool monitoring (interval: {interval}s, min_tvl: ${min_tvl:,.0f})")
        
        # Initial fetch to populate known pools
        pools = await self.fetch_aerodrome_pools(min_tvl=min_tvl)
        for pool in pools:
            if pool["address"]:
                self.known_pools.add(pool["address"])
        
        logger.info(f"📊 Tracking {len(self.known_pools)} existing Aerodrome pools")
        
        while self.is_running:
            try:
                new_pools = await self.check_new_pools(min_tvl=min_tvl)
                
                if new_pools:
                    await self._notify_callbacks(new_pools)
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(interval)
        
        logger.info("Pool monitoring stopped")
    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.is_running = False
    
    async def close(self):
        """Cleanup resources."""
        self.stop_monitoring()
        await self.client.aclose()


# Singleton instance
_discovery_instance = None

def get_pool_discovery() -> PoolDiscovery:
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = PoolDiscovery()
    return _discovery_instance


# ============================================
# CLI TEST
# ============================================

if __name__ == "__main__":
    async def test():
        print("=" * 60)
        print("Aerodrome Pool Discovery Test")
        print("=" * 60)
        
        discovery = PoolDiscovery()
        
        # Test fetch
        print("\n1. Fetching Aerodrome pools...")
        pools = await discovery.fetch_aerodrome_pools(min_tvl=100000)
        
        print(f"   Found {len(pools)} pools with TVL >= $100k")
        for pool in pools[:5]:
            tokens = '/'.join(pool['tokens'])
            print(f"   {tokens}: ${pool['tvl']:,.0f} TVL | {pool['apr']:.1f}% APR")
        
        # Test new pool check
        print("\n2. Checking for new pools...")
        new_pools = await discovery.check_new_pools(min_tvl=50000)
        print(f"   First run: {len(new_pools)} 'new' pools (all are new on first run)")
        
        # Second check should find 0
        new_pools2 = await discovery.check_new_pools(min_tvl=50000)
        print(f"   Second run: {len(new_pools2)} new pools")
        
        await discovery.close()
        print("\n✅ Test complete!")
    
    asyncio.run(test())

