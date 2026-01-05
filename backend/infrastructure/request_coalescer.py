"""
Request Coalescer - Deduplicate concurrent identical requests

WHY: When 10 users load the explore page simultaneously, we don't want 10 API calls.
SOLUTION: First request fetches, others wait for the same result.

DESIGN:
- Track "in-flight" requests by cache key
- If request is in-flight, return the same Future
- When fetch completes, all waiters get the result
- Prevents "thundering herd" / cache stampede
"""

import asyncio
import logging
from typing import Any, Dict, Callable, Awaitable, Optional
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)


@dataclass
class InFlightRequest:
    """
    Represents a request that is currently being processed.
    WHY dataclass: Clean, immutable structure for tracking request state.
    """
    future: asyncio.Future
    started_at: float
    waiter_count: int = 1


class RequestCoalescer:
    """
    Coalesces multiple identical concurrent requests into one.
    
    PROBLEM SOLVED:
    - 100 users request /api/pools?chain=Base simultaneously
    - Without coalescing: 100 API calls to DefiLlama
    - With coalescing: 1 API call, 100 users get the result
    
    HOW IT WORKS:
    1. Request comes in, check if same request is in-flight
    2. If yes: return the same Future (caller awaits it)
    3. If no: start new request, create Future, track it
    4. When request completes: resolve Future for all waiters
    """
    
    def __init__(self, timeout: float = 30.0):
        self._in_flight: Dict[str, InFlightRequest] = {}
        self._lock = asyncio.Lock()
        self._timeout = timeout
        
        # Statistics
        self._stats = {
            "coalesced": 0,      # Requests that piggybacked on existing
            "initiated": 0,      # Requests that started a new fetch
            "total_waiters": 0,  # Total waiters saved
        }
    
    async def execute(
        self,
        key: str,
        fetcher: Callable[[], Awaitable[Any]]
    ) -> Any:
        """
        Execute request with coalescing.
        
        Args:
            key: Unique identifier for this request (from cache key)
            fetcher: Async function that fetches the data
            
        Returns:
            Result from the fetch (shared if coalesced)
        """
        async with self._lock:
            # Check if this request is already in-flight
            if key in self._in_flight:
                in_flight = self._in_flight[key]
                in_flight.waiter_count += 1
                self._stats["coalesced"] += 1
                self._stats["total_waiters"] += 1
                
                logger.debug(f"Coalescing request {key[:16]}... ({in_flight.waiter_count} waiters)")
                
                # Return the same future - caller will await it
                future = in_flight.future
            else:
                # Start new request
                loop = asyncio.get_event_loop()
                future = loop.create_future()
                
                self._in_flight[key] = InFlightRequest(
                    future=future,
                    started_at=time.time()
                )
                self._stats["initiated"] += 1
                
                logger.debug(f"Initiating new request {key[:16]}...")
                
                # Start the fetch in background
                asyncio.create_task(self._do_fetch(key, fetcher, future))
        
        # Await the result (whether we initiated or coalesced)
        try:
            return await asyncio.wait_for(future, timeout=self._timeout)
        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {key[:16]}")
            raise
    
    async def _do_fetch(
        self,
        key: str,
        fetcher: Callable[[], Awaitable[Any]],
        future: asyncio.Future
    ):
        """
        Perform the actual fetch and resolve the future.
        WHY separate task: Allows non-blocking execution while waiters queue up.
        """
        try:
            result = await fetcher()
            
            if not future.done():
                future.set_result(result)
                
        except Exception as e:
            if not future.done():
                future.set_exception(e)
                
        finally:
            # Clean up in-flight tracking
            async with self._lock:
                if key in self._in_flight:
                    waiter_count = self._in_flight[key].waiter_count
                    del self._in_flight[key]
                    
                    if waiter_count > 1:
                        logger.info(f"Coalesced {waiter_count} requests for {key[:16]}")
    
    def get_stats(self) -> Dict:
        """Get coalescing statistics."""
        total = self._stats["initiated"] + self._stats["coalesced"]
        savings_rate = self._stats["coalesced"] / max(1, total)
        
        return {
            **self._stats,
            "in_flight": len(self._in_flight),
            "savings_rate": f"{savings_rate:.1%}",
        }
    
    async def cleanup_stale(self):
        """
        Clean up stale in-flight requests (safety net).
        WHY: In case a fetch hangs, we don't want to block forever.
        """
        async with self._lock:
            now = time.time()
            stale_keys = [
                key for key, req in self._in_flight.items()
                if now - req.started_at > self._timeout * 2
            ]
            
            for key in stale_keys:
                req = self._in_flight[key]
                if not req.future.done():
                    req.future.set_exception(TimeoutError("Request stale"))
                del self._in_flight[key]
                
            if stale_keys:
                logger.warning(f"Cleaned up {len(stale_keys)} stale requests")


# Global coalescer instance
request_coalescer = RequestCoalescer()
