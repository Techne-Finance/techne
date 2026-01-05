"""
Rate Limiter with Async Queue - Control API request rate

WHY: External APIs (DefiLlama) have rate limits (e.g., 300 req/5min).
Exceeding limits causes 429 errors and potential bans.

DESIGN:
- Token bucket algorithm for smooth rate limiting
- Async queue for excess requests (don't drop, queue)
- Per-endpoint limits (different endpoints, different limits)
- Non-blocking - callers await their turn
"""

import asyncio
import time
import logging
from typing import Dict, Any, Callable, Awaitable, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RateLimitTier(Enum):
    """
    Different endpoints have different rate limits.
    WHY tiered: Price endpoints are called more often, need higher limits.
    """
    HIGH = "high"       # 1 request per 5 seconds (12/min)
    MEDIUM = "medium"   # 1 request per 15 seconds (4/min)
    LOW = "low"         # 1 request per 60 seconds (1/min)


# Rate limit configuration
# WHY these values: Based on typical DeFi API limits (~300 req/5min)
RATE_LIMITS = {
    RateLimitTier.HIGH: {"tokens_per_sec": 0.2, "max_tokens": 3},     # Max 3 burst, refill 1/5s
    RateLimitTier.MEDIUM: {"tokens_per_sec": 0.067, "max_tokens": 2}, # Max 2 burst, refill 1/15s
    RateLimitTier.LOW: {"tokens_per_sec": 0.017, "max_tokens": 1},    # Max 1, refill 1/60s
}


@dataclass
class TokenBucket:
    """
    Token bucket for rate limiting.
    WHY token bucket: Allows bursting while maintaining average rate.
    """
    tokens: float
    max_tokens: float
    tokens_per_sec: float
    last_refill: float
    
    def refill(self):
        """Add tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.tokens_per_sec)
        self.last_refill = now
    
    def try_consume(self) -> bool:
        """Try to consume a token. Returns True if successful."""
        self.refill()
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False
    
    def time_until_available(self) -> float:
        """Calculate seconds until a token is available."""
        self.refill()
        if self.tokens >= 1:
            return 0
        needed = 1 - self.tokens
        return needed / self.tokens_per_sec


class RateLimiter:
    """
    Rate limiter with async queue.
    
    BEHAVIOR:
    - If under rate limit: execute immediately
    - If over rate limit: queue the request, wait for turn
    - Multiple endpoints can have different rate limits
    
    WHY queue instead of reject:
    - Better UX - requests eventually complete
    - Works well with coalescing (fewer unique requests)
    - Prevents retry storms from rejected requests
    """
    
    def __init__(self):
        self._buckets: Dict[str, TokenBucket] = {}
        self._queues: Dict[str, asyncio.Queue] = {}
        self._workers: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        
        # Statistics
        self._stats = {
            "immediate": 0,   # Requests executed immediately
            "queued": 0,      # Requests that had to wait
            "total_wait_ms": 0,  # Total wait time
        }
    
    def _get_bucket(self, endpoint: str, tier: RateLimitTier) -> TokenBucket:
        """Get or create token bucket for endpoint."""
        if endpoint not in self._buckets:
            config = RATE_LIMITS[tier]
            self._buckets[endpoint] = TokenBucket(
                tokens=config["max_tokens"],  # Start full
                max_tokens=config["max_tokens"],
                tokens_per_sec=config["tokens_per_sec"],
                last_refill=time.time()
            )
        return self._buckets[endpoint]
    
    async def execute(
        self,
        endpoint: str,
        fetcher: Callable[[], Awaitable[Any]],
        tier: RateLimitTier = RateLimitTier.MEDIUM
    ) -> Any:
        """
        Execute request with rate limiting.
        
        Args:
            endpoint: Identifier for this endpoint (for per-endpoint limits)
            fetcher: Async function to execute
            tier: Rate limit tier
            
        Returns:
            Result from fetcher
        """
        bucket = self._get_bucket(endpoint, tier)
        
        # Try to execute immediately
        if bucket.try_consume():
            self._stats["immediate"] += 1
            return await fetcher()
        
        # Must wait - calculate wait time
        wait_time = bucket.time_until_available()
        self._stats["queued"] += 1
        self._stats["total_wait_ms"] += int(wait_time * 1000)
        
        logger.debug(f"Rate limited: {endpoint}, waiting {wait_time:.2f}s")
        
        # Wait and then execute
        await asyncio.sleep(wait_time)
        bucket.try_consume()  # Consume the token we waited for
        
        return await fetcher()
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        total = self._stats["immediate"] + self._stats["queued"]
        avg_wait = self._stats["total_wait_ms"] / max(1, self._stats["queued"])
        
        return {
            **self._stats,
            "total_requests": total,
            "queue_rate": f"{self._stats['queued'] / max(1, total):.1%}",
            "avg_wait_ms": f"{avg_wait:.0f}",
        }


class RequestBatcher:
    """
    Batches multiple requests into one.
    
    WHY BATCHING:
    - DefiLlama supports batch endpoints (e.g., /prices for multiple coins)
    - Even without API batch support, we can batch on our side:
      - Collect requests for 100ms
      - Deduplicate and combine
      - Execute single request
      - Distribute results
    
    DESIGN:
    - Configurable batch window (default 100ms)
    - Maximum batch size
    - Works with request coalescer for maximum efficiency
    """
    
    def __init__(
        self,
        batch_window_ms: int = 100,
        max_batch_size: int = 50
    ):
        self._batch_window = batch_window_ms / 1000
        self._max_batch_size = max_batch_size
        self._pending: Dict[str, list] = {}  # endpoint -> list of (params, future)
        self._locks: Dict[str, asyncio.Lock] = {}
        self._batch_tasks: Dict[str, asyncio.Task] = {}
        
        self._stats = {
            "batched_requests": 0,
            "actual_fetches": 0,
            "items_per_batch": [],
        }
    
    async def add_to_batch(
        self,
        endpoint: str,
        params: Dict,
        batch_fetcher: Callable[[list], Awaitable[Dict]],
        extract_result: Callable[[Dict, Dict], Any]
    ) -> Any:
        """
        Add request to batch.
        
        Args:
            endpoint: Endpoint identifier
            params: Request parameters
            batch_fetcher: Function that fetches batch (receives list of params)
            extract_result: Function to extract individual result from batch response
            
        Returns:
            Individual result for this request's params
        """
        if endpoint not in self._locks:
            self._locks[endpoint] = asyncio.Lock()
            self._pending[endpoint] = []
        
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        
        async with self._locks[endpoint]:
            self._pending[endpoint].append((params, future))
            self._stats["batched_requests"] += 1
            
            # Start batch timer if this is first in batch
            if len(self._pending[endpoint]) == 1:
                self._batch_tasks[endpoint] = asyncio.create_task(
                    self._execute_batch_after_delay(endpoint, batch_fetcher, extract_result)
                )
            
            # Execute immediately if batch is full
            elif len(self._pending[endpoint]) >= self._max_batch_size:
                if endpoint in self._batch_tasks:
                    self._batch_tasks[endpoint].cancel()
                asyncio.create_task(
                    self._execute_batch(endpoint, batch_fetcher, extract_result)
                )
        
        return await future
    
    async def _execute_batch_after_delay(
        self,
        endpoint: str,
        batch_fetcher: Callable[[list], Awaitable[Dict]],
        extract_result: Callable[[Dict, Dict], Any]
    ):
        """Wait for batch window then execute."""
        await asyncio.sleep(self._batch_window)
        await self._execute_batch(endpoint, batch_fetcher, extract_result)
    
    async def _execute_batch(
        self,
        endpoint: str,
        batch_fetcher: Callable[[list], Awaitable[Dict]],
        extract_result: Callable[[Dict, Dict], Any]
    ):
        """Execute the batched request."""
        async with self._locks[endpoint]:
            pending = self._pending[endpoint]
            self._pending[endpoint] = []
        
        if not pending:
            return
        
        batch_size = len(pending)
        self._stats["actual_fetches"] += 1
        self._stats["items_per_batch"].append(batch_size)
        
        logger.debug(f"Executing batch: {endpoint} with {batch_size} items")
        
        try:
            # Collect all params for batch fetch
            all_params = [p[0] for p in pending]
            
            # Execute batch fetch
            batch_result = await batch_fetcher(all_params)
            
            # Distribute results
            for params, future in pending:
                try:
                    result = extract_result(batch_result, params)
                    if not future.done():
                        future.set_result(result)
                except Exception as e:
                    if not future.done():
                        future.set_exception(e)
                        
        except Exception as e:
            # Batch failed - fail all pending
            for _, future in pending:
                if not future.done():
                    future.set_exception(e)
    
    def get_stats(self) -> Dict:
        """Get batcher statistics."""
        avg_batch = sum(self._stats["items_per_batch"]) / max(1, len(self._stats["items_per_batch"]))
        
        return {
            "batched_requests": self._stats["batched_requests"],
            "actual_fetches": self._stats["actual_fetches"],
            "avg_batch_size": f"{avg_batch:.1f}",
            "savings_factor": f"{self._stats['batched_requests'] / max(1, self._stats['actual_fetches']):.1f}x",
        }


# Global instances
rate_limiter = RateLimiter()
request_batcher = RequestBatcher()
