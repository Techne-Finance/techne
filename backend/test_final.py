"""
Final test - checking correct path: result['pool']['apy']
"""
import asyncio
import time
import sys
import logging

logging.basicConfig(level=logging.WARNING)  # Quiet logs

sys.path.insert(0, '.')

from api.smart_router import SmartRouter

async def main():
    router = SmartRouter()
    
    pool_address = "0x6cdcb1c4a4d1c3c6d054b27ac5b77e89eafb971d"
    chain = "base"
    
    print("=" * 60)
    print("   MULTICALL APY - FINAL PERFORMANCE TEST")
    print("=" * 60)
    
    start = time.time()
    result = await router.smart_route_pool_check(pool_address, chain)
    elapsed = time.time() - start
    
    print(f"\n⏱️  Total time: {elapsed:.2f}s")
    
    # APY is inside the 'pool' object
    pool = result.get('pool', {})
    
    print(f"\n📊 Results:")
    print(f"   Success: {result.get('success')}")
    print(f"   APY: {pool.get('apy', 'N/A')}%")
    print(f"   APY Status: {pool.get('apy_status')}")
    print(f"   APY Source: {pool.get('apy_source')}")
    print(f"   Has Gauge: {pool.get('has_gauge')}")
    print(f"   Pool Type: {pool.get('pool_type')}")
    print(f"   TVL: ${pool.get('tvl', 0):,.0f}")
    print(f"   Symbol: {pool.get('symbol')}")
    print(f"   Source: {result.get('source')}")
    print(f"   Quality: {result.get('data_quality')}")

if __name__ == "__main__":
    asyncio.run(main())
