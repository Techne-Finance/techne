"""Detailed timing of SmartRouter sections"""
import asyncio
import time
import sys
sys.path.insert(0, '.')

POOL = "0x56c11053159a24c0731b4b12356bc1f0578fb474"
CHAIN = "base"

async def main():
    from api.smart_router import SmartRouter
    
    router = SmartRouter()
    
    print("SmartRouter Detailed Timing\n" + "=" * 50)
    
    start_total = time.time()
    result = await router.smart_route_pool_check(POOL, CHAIN)
    total = time.time() - start_total
    
    print(f"\nTotal SmartRouter time: {total:.2f}s")
    
    if result.get('success'):
        pool = result.get('pool', {})
        print(f"\nVerification:")
        print(f"  APY: {pool.get('apy', 0):.2f}%")
        print(f"  Security tokens: {len(pool.get('security_result', {}).get('tokens', {}))}")
        print(f"  Volatility T0: {pool.get('token0_volatility_24h')}")
        print(f"  Whale source: {pool.get('whale_analysis', {}).get('source')}")
        print(f"  LP Lock: {pool.get('liquidity_lock', {}).get('source')}")
    else:
        print(f"Error: {result}")

if __name__ == "__main__":
    asyncio.run(main())
