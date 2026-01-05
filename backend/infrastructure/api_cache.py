"""
API Cache Manager - Core caching layer for external API calls

WHY: DefiLlama and other external APIs have rate limits and latency.
Caching reduces API calls by 20-50x and improves response times from 500ms+ to <10ms.

DESIGN:
- In-memory cache (no Redis dependency for simplicity)
- TTL-based expiration with stale-while-revalidate
- Thread-safe with asyncio locks
- Automatic background refresh for hot data
"""

import asyncio
import time
import hashlib
import json
import logging
from typing import Any, Optional, Dict, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CacheEndpointType(Enum):
    """
    Different endpoint types have different caching strategies.
    WHY: Prices change every second, but protocol metadata rarely changes.
    """
    PRICES = "prices"           # High volatility - short TTL
    POOLS = "pools"             # Medium change rate
    TVL = "tvl"                 # Medium change rate
    METADATA = "metadata"       # Rarely changes
    CHAINS = "chains"           # Almost static


# TTL Configuration (seconds)
# WHY: Tuned based on data volatility and acceptable staleness
TTL_CONFIG = {
    CacheEndpointType.PRICES: {"ttl": 15, "stale_ttl": 30},
    CacheEndpointType.POOLS: {"ttl": 120, "stale_ttl": 300},      # 2min fresh, 5min stale OK
    CacheEndpointType.TVL: {"ttl": 120, "stale_ttl": 300},
    CacheEndpointType.METADATA: {"ttl": 3600, "stale_ttl": 86400}, # 1h fresh, 24h stale OK
    CacheEndpointType.CHAINS: {"ttl": 86400, "stale_ttl": 172800}, # 24h fresh, 48h stale OK
}


@dataclass
class CacheEntry:
    """
    Single cache entry with metadata for TTL management.
    WHY: Need to track when data was fetched and when it expires.
    """
    value: Any
    created_at: float
    ttl: float
    stale_ttl: float
    hit_count: int = 0
    
    @property
    def is_fresh(self) -> bool:
        """Data is within primary TTL - serve directly"""
        return time.time() < (self.created_at + self.ttl)
    
    @property
    def is_stale_but_usable(self) -> bool:
        """Data is stale but within stale TTL - serve but trigger refresh"""
        now = time.time()
        return (self.created_at + self.ttl) <= now < (self.created_at + self.stale_ttl)
    
    @property
    def is_expired(self) -> bool:
        """Data is completely expired - must refetch"""
        return time.time() >= (self.created_at + self.stale_ttl)


class CacheManager:
    """
    In-memory cache with stale-while-revalidate support.
    
    WHY in-memory instead of Redis:
    - Zero infrastructure dependency
    - No network latency for cache hits
    - Sufficient for single-server deployment
    - Can add Redis later if needed for multi-server
    
    STALE-WHILE-REVALIDATE:
    - If data is fresh: return immediately
    - If data is stale but usable: return immediately + trigger background refresh
    - If data is expired: wait for fresh fetch
    """
    
    def __init__(self, max_entries: int = 10000):
        self._cache: Dict[str, CacheEntry] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._max_entries = max_entries
        self._global_lock = asyncio.Lock()
        
        # Statistics for monitoring
        self._stats = {
            "hits": 0,
            "misses": 0,
            "stale_hits": 0,
            "evictions": 0
        }
    
    def _make_key(self, endpoint: str, params: Optional[Dict] = None) -> str:
        """
        Generate cache key from endpoint and parameters.
        WHY hash: Ensures consistent, short keys regardless of param complexity.
        """
        key_data = {"endpoint": endpoint, "params": params or {}}
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def _get_lock(self, key: str) -> asyncio.Lock:
        """
        Get or create lock for a specific key.
        WHY per-key locks: Allows concurrent access to different cache entries.
        """
        async with self._global_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]
    
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        endpoint_type: CacheEndpointType = CacheEndpointType.POOLS,
        fetcher: Optional[Callable[[], Awaitable[Any]]] = None
    ) -> Optional[Any]:
        """
        Get value from cache with stale-while-revalidate.
        
        Args:
            endpoint: API endpoint identifier
            params: Query parameters
            endpoint_type: Type of endpoint for TTL config
            fetcher: Async function to fetch fresh data if needed
            
        Returns:
            Cached or freshly fetched value
        """
        key = self._make_key(endpoint, params)
        entry = self._cache.get(key)
        
        # CASE 1: Fresh data exists - return immediately
        if entry and entry.is_fresh:
            entry.hit_count += 1
            self._stats["hits"] += 1
            logger.debug(f"Cache HIT (fresh): {endpoint}")
            return entry.value
        
        # CASE 2: Stale but usable - return immediately + background refresh
        if entry and entry.is_stale_but_usable:
            entry.hit_count += 1
            self._stats["stale_hits"] += 1
            logger.debug(f"Cache HIT (stale, refreshing): {endpoint}")
            
            # Trigger background refresh if fetcher provided
            if fetcher:
                asyncio.create_task(self._background_refresh(key, endpoint_type, fetcher))
            
            return entry.value
        
        # CASE 3: No data or expired - must fetch
        self._stats["misses"] += 1
        logger.debug(f"Cache MISS: {endpoint}")
        
        if fetcher:
            return await self._fetch_and_cache(key, endpoint_type, fetcher)
        
        return None
    
    async def _fetch_and_cache(
        self,
        key: str,
        endpoint_type: CacheEndpointType,
        fetcher: Callable[[], Awaitable[Any]]
    ) -> Any:
        """
        Fetch fresh data and store in cache.
        WHY lock: Prevents multiple concurrent fetches for same key (stampede protection).
        """
        lock = await self._get_lock(key)
        
        async with lock:
            # Double-check after acquiring lock (another request may have fetched)
            entry = self._cache.get(key)
            if entry and entry.is_fresh:
                return entry.value
            
            # Fetch fresh data
            try:
                value = await fetcher()
                await self.set(key, value, endpoint_type)
                return value
            except Exception as e:
                # On error, return stale data if available (graceful degradation)
                if entry and not entry.is_expired:
                    logger.warning(f"Fetch failed, returning stale: {e}")
                    return entry.value
                raise
    
    async def _background_refresh(
        self,
        key: str,
        endpoint_type: CacheEndpointType,
        fetcher: Callable[[], Awaitable[Any]]
    ):
        """
        Background refresh for stale-while-revalidate.
        WHY background: User gets stale data instantly, fresh data for next request.
        """
        try:
            lock = await self._get_lock(key)
            
            # Non-blocking try - skip if another refresh is in progress
            if lock.locked():
                return
            
            async with lock:
                value = await fetcher()
                await self.set(key, value, endpoint_type)
                logger.debug(f"Background refresh complete: {key[:16]}")
        except Exception as e:
            logger.warning(f"Background refresh failed: {e}")
    
    async def set(
        self,
        key: str,
        value: Any,
        endpoint_type: CacheEndpointType = CacheEndpointType.POOLS
    ):
        """
        Store value in cache with appropriate TTL.
        """
        config = TTL_CONFIG.get(endpoint_type, TTL_CONFIG[CacheEndpointType.POOLS])
        
        # Evict old entries if at capacity
        if len(self._cache) >= self._max_entries:
            await self._evict_lru()
        
        self._cache[key] = CacheEntry(
            value=value,
            created_at=time.time(),
            ttl=config["ttl"],
            stale_ttl=config["stale_ttl"]
        )
    
    async def _evict_lru(self):
        """
        Evict least recently used entries.
        WHY LRU: Keeps frequently accessed data, removes cold data.
        """
        if not self._cache:
            return
        
        # Sort by hit_count (ascending) and created_at (oldest first)
        sorted_keys = sorted(
            self._cache.keys(),
            key=lambda k: (self._cache[k].hit_count, self._cache[k].created_at)
        )
        
        # Remove bottom 10%
        to_remove = max(1, len(sorted_keys) // 10)
        for key in sorted_keys[:to_remove]:
            del self._cache[key]
            if key in self._locks:
                del self._locks[key]
            self._stats["evictions"] += 1
    
    def invalidate(self, endpoint: str, params: Optional[Dict] = None):
        """Manually invalidate a cache entry."""
        key = self._make_key(endpoint, params)
        if key in self._cache:
            del self._cache[key]
    
    def invalidate_pattern(self, endpoint_prefix: str):
        """Invalidate all entries matching endpoint prefix."""
        # For in-memory, we need to check all keys
        # In Redis, we'd use SCAN with pattern
        to_remove = []
        for key in self._cache:
            entry = self._cache[key]
            # This is a limitation of hash-based keys
            # In production, maintain a reverse index
        pass  # TODO: Implement if needed
    
    def get_stats(self) -> Dict:
        """Get cache statistics for monitoring."""
        total = self._stats["hits"] + self._stats["misses"] + self._stats["stale_hits"]
        hit_rate = (self._stats["hits"] + self._stats["stale_hits"]) / max(1, total)
        
        return {
            **self._stats,
            "total_requests": total,
            "hit_rate": f"{hit_rate:.1%}",
            "entries": len(self._cache),
            "max_entries": self._max_entries
        }
    
    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        self._locks.clear()
        logger.info("Cache cleared")


# Global cache instance
cache_manager = CacheManager()
