"""
Full flow test: SmartRouter -> verify endpoint with timing details
"""
import asyncio
import time
import sys
sys.path.insert(0, '.')

from api.smart_router import SmartRouter

async def main():
    router = SmartRouter()
    
    pool_address = "0x6cdcb1c4a4d1c3c6d054b27ac5b77e89eafb971d"
    chain = "base"
    
    print("=" * 60)
    print("   SMARTROUTER FULL FLOW TEST")
    print("=" * 60)
    
    start = time.time()
    result = await router.smart_route_pool_check(pool_address, chain)
    elapsed = time.time() - start
    
    print(f"\nTotal time: {elapsed:.2f}s")
    print(f"\nResult keys: {list(result.keys())}")
    print(f"\nKey values:")
    print(f"  APY: {result.get('apy')}%")
    print(f"  APY Status: {result.get('apy_status')}")
    print(f"  APY Source: {result.get('apy_source')}")
    print(f"  Pool Type: {result.get('pool_type')}")
    print(f"  Has Gauge: {result.get('has_gauge')}")
    print(f"  Symbol: {result.get('symbol')}")
    print(f"  TVL: ${result.get('tvl', result.get('tvlUsd', 0)):,.0f}")
    print(f"  Source: {result.get('source')}")

if __name__ == "__main__":
    asyncio.run(main())
