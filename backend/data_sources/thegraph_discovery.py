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

# Subgraph endpoints (Updated to decentralized network)
# API Key from: https://thegraph.com/studio/apikeys/
GRAPH_API_KEY = os.getenv("GRAPH_API_KEY", "")

SUBGRAPHS = {
    "aerodrome_v2": {
        # Aerodrome official subgraph
        "url": "https://api.studio.thegraph.com/query/50806/aerodrome/version/latest",
        "name": "Aerodrome V2",
        "factory": "0x420DD381b31aEf6683db6B902084cB0FFECe40Da"
    },
    "uniswap_v3": {
        # Uniswap V3 on Base
        "url": "https://api.studio.thegraph.com/query/48211/uniswap-v3-base/version/latest",
        "name": "Uniswap V3",
        "factory": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"
    }
}

# Aerodrome-specific query (their schema is different)
AERODROME_POOLS_QUERY = """
query GetPools($first: Int!, $skip: Int!) {
    pools(
        first: $first
        skip: $skip
        orderBy: totalValueLockedUSD
        orderDirection: desc
        where: { totalValueLockedUSD_gt: "10000" }
    ) {
        id
        symbol
        name
        totalValueLockedUSD
        volumeUSD
        feesUSD
        txCount
        token0 {
            id
            symbol
            name
        }
        token1 {
            id
            symbol
            name
        }
        isStable
        gauge {
            id
        }
    }
}
"""

# Generic Messari schema query
POOLS_QUERY = """
query GetRecentPools($first: Int!, $skip: Int!, $minTVL: BigDecimal!) {
    liquidityPools(
        first: $first
        skip: $skip
        orderBy: totalValueLockedUSD
        orderDirection: desc
        where: { totalValueLockedUSD_gte: $minTVL }
    ) {
        id
        name
        symbol
        createdTimestamp
        totalValueLockedUSD
        inputTokens {
            id
            symbol
        }
    }
}
"""


class TheGraphPoolDiscovery:
    """
    Real-time pool discovery using The Graph subgraphs.
    
    Usage:
        discovery = TheGraphPoolDiscovery()
        
        # One-time fetch
        pools = await discovery.fetch_recent_pools("aerodrome_v2", limit=100)
        
        # Continuous monitoring
        discovery.on_new_pool(callback_function)
        await discovery.start_monitoring(interval=60)
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.last_check: Dict[str, int] = {}  # subgraph -> last timestamp
        self.known_pools: set = set()
        self.callbacks: List[Callable] = []
        self.is_running = False
        
        logger.info("🔍 TheGraph Pool Discovery initialized")
    
    async def fetch_recent_pools(
        self, 
        subgraph: str = "aerodrome_v2",
        limit: int = 100,
        min_tvl: float = 10000
    ) -> List[Dict]:
        """Fetch recent pools from subgraph."""
        if subgraph not in SUBGRAPHS:
            logger.error(f"Unknown subgraph: {subgraph}")
            return []
        
        endpoint = SUBGRAPHS[subgraph]["url"]
        
        # Use Aerodrome-specific query for aerodrome subgraphs
        if "aerodrome" in subgraph:
            query = AERODROME_POOLS_QUERY
            variables = {"first": limit, "skip": 0}
        else:
            query = POOLS_QUERY
            variables = {"first": limit, "skip": 0, "minTVL": str(min_tvl)}
        
        try:
            response = await self.client.post(
                endpoint,
                json={"query": query, "variables": variables}
            )
            
            data = response.json()
            
            if "errors" in data:
                logger.error(f"GraphQL error: {data['errors']}")
                return []
            
            # Handle different response schemas
            if "aerodrome" in subgraph:
                pools = data.get("data", {}).get("pools", [])
            else:
                pools = data.get("data", {}).get("liquidityPools", [])
            
            # Transform to standard format
            result = []
            for pool in pools:
                if "aerodrome" in subgraph:
                    # Aerodrome schema
                    tokens = []
                    if pool.get("token0"):
                        tokens.append(pool["token0"]["symbol"])
                    if pool.get("token1"):
                        tokens.append(pool["token1"]["symbol"])
                    
                    result.append({
                        "address": pool["id"],
                        "name": pool.get("name", ""),
                        "symbol": pool.get("symbol", ""),
                        "tvl": float(pool.get("totalValueLockedUSD", 0)),
                        "volume_24h": float(pool.get("volumeUSD", 0)),
                        "tokens": tokens,
                        "is_stable": pool.get("isStable", False),
                        "has_gauge": pool.get("gauge") is not None,
                        "source": subgraph,
                        "protocol": SUBGRAPHS[subgraph]["name"]
                    })
                else:
                    # Messari schema
                    result.append({
                        "address": pool["id"],
                        "name": pool.get("name", ""),
                        "symbol": pool.get("symbol", ""),
                        "tvl": float(pool.get("totalValueLockedUSD", 0)),
                        "tokens": [t["symbol"] for t in pool.get("inputTokens", [])],
                        "source": subgraph,
                        "protocol": SUBGRAPHS[subgraph]["name"]
                    })
            
            logger.info(f"[{subgraph}] Fetched {len(result)} pools (TVL >= ${min_tvl:,.0f})")
            return result
            
        except Exception as e:
            logger.error(f"[{subgraph}] Fetch error: {e}")
            return []
    
    async def check_new_pools(
        self,
        subgraph: str = "aerodrome_v2",
        lookback_hours: int = 1,
        min_tvl: float = 10000
    ) -> List[Dict]:
        """Check for new pools not seen before."""
        # Fetch current pools
        all_pools = await self.fetch_recent_pools(subgraph, limit=200, min_tvl=min_tvl)
        
        new_pools = []
        for pool in all_pools:
            pool_id = pool["address"]
            
            if pool_id not in self.known_pools:
                self.known_pools.add(pool_id)
                pool["is_new"] = True
                new_pools.append(pool)
        
        # Update last check time
        self.last_check[subgraph] = int(datetime.utcnow().timestamp())
        
        if new_pools:
            logger.info(f"🆕 [{subgraph}] Found {len(new_pools)} NEW pools!")
            for pool in new_pools[:3]:  # Log first 3
                logger.info(f"   → {pool.get('symbol', 'N/A')} | TVL: ${pool['tvl']:,.0f}")
        
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
        
        # Initial pool fetch to populate known pools
        for subgraph in SUBGRAPHS:
            pools = await self.fetch_recent_pools(subgraph, limit=200, min_tvl=min_tvl)
            for pool in pools:
                self.known_pools.add(pool["address"])
        
        logger.info(f"📊 Tracking {len(self.known_pools)} existing pools")
        
        while self.is_running:
            try:
                all_new_pools = []
                
                for subgraph in SUBGRAPHS:
                    new_pools = await self.check_new_pools(
                        subgraph=subgraph,
                        lookback_hours=1,
                        min_tvl=min_tvl
                    )
                    all_new_pools.extend(new_pools)
                
                if all_new_pools:
                    await self._notify_callbacks(all_new_pools)
                
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

def get_pool_discovery() -> TheGraphPoolDiscovery:
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = TheGraphPoolDiscovery()
    return _discovery_instance


# ============================================
# Integration with Strategy Executor
# ============================================

async def on_new_pool_detected(pools: List[Dict]):
    """
    Callback when new pools are detected.
    Notifies strategy executor to consider these pools.
    """
    from datetime import datetime
    
    for pool in pools:
        print(f"[TheGraph] 🆕 NEW POOL: {pool['symbol']}")
        print(f"   TVL: ${pool['tvl']:,.0f}")
        print(f"   Protocol: {pool['protocol']}")
        print(f"   Tokens: {', '.join(pool.get('tokens', []))}")
        
        # Could trigger immediate analysis
        # from services.scam_detector import get_detector
        # detector = get_detector()
        # result = await detector.analyze_contract(pool['address'])


# ============================================
# CLI TEST
# ============================================

if __name__ == "__main__":
    async def test():
        print("=" * 60)
        print("The Graph Pool Discovery Test")
        print("=" * 60)
        
        discovery = TheGraphPoolDiscovery()
        
        # Test fetch
        print("\n1. Fetching recent Aerodrome pools...")
        pools = await discovery.fetch_recent_pools("aerodrome_v2", limit=10, min_tvl=50000)
        
        for pool in pools[:5]:
            print(f"   {pool['symbol']}: ${pool['tvl']:,.0f} TVL")
        
        # Test new pool check
        print("\n2. Checking for new pools (last 24h)...")
        new_pools = await discovery.check_new_pools("aerodrome_v2", lookback_hours=24, min_tvl=10000)
        print(f"   Found {len(new_pools)} new pools")
        
        await discovery.close()
        print("\n✅ Test complete!")
    
    asyncio.run(test())
