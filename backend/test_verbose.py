"""
Full flow test with verbose logging
"""
import asyncio
import time
import sys
import logging

# Enable ALL logging
logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')

sys.path.insert(0, '.')

from api.smart_router import SmartRouter

async def main():
    router = SmartRouter()
    
    pool_address = "0x6cdcb1c4a4d1c3c6d054b27ac5b77e89eafb971d"
    chain = "base"
    
    print("=" * 60)
    print("   VERBOSE SMARTROUTER TEST")
    print("=" * 60)
    
    start = time.time()
    result = await router.smart_route_pool_check(pool_address, chain)
    elapsed = time.time() - start
    
    print("\n" + "=" * 60)
    print(f"   RESULT (took {elapsed:.2f}s)")
    print("=" * 60)
    print(f"\nAPY: {result.get('apy')}")
    print(f"APY Status: {result.get('apy_status')}")
    print(f"APY Source: {result.get('apy_source')}")
    print(f"APY Reason: {result.get('apy_reason')}")
    print(f"Has Gauge: {result.get('has_gauge')}")
    print(f"Pool Type: {result.get('pool_type')}")
    print(f"Gauge: {result.get('gauge_address')}")

if __name__ == "__main__":
    asyncio.run(main())
