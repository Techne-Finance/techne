"""Test Sugar client speed"""
import asyncio
import time

async def test_sugar():
    from data_sources.aerodrome_sugar import sugar_client
    
    print("Testing Aerodrome Sugar client...")
    print("=" * 50)
    
    pool = "0x6cdcb1c4a4d1c3c6d054b27ac5b77e89eafb971d"
    
    # Test 1: Raw Sugar call
    start = time.time()
    result = await sugar_client.get_pool_data_fast(pool, "base")
    sugar_time = time.time() - start
    print(f"1. Sugar call: {sugar_time:.2f}s")
    
    if result:
        print(f"   Symbol: {result.get('symbol')}")
        print(f"   Emissions: {result.get('emissions')}/s")
        print(f"   Has gauge: {result.get('has_gauge')}")
        print(f"   Pool type: {result.get('pool_type_name')}")
    
    # Test 2: Full APY calculation with TVL
    start = time.time()
    apy_result = await sugar_client.calculate_apy_from_sugar(pool, "base", tvl_usd=32000000)
    apy_time = time.time() - start
    print(f"\n2. APY calculation (with TVL): {apy_time:.2f}s")
    
    if apy_result:
        print(f"   Status: {apy_result.get('apy_status')}")
        print(f"   APY: {apy_result.get('apy', 0):.2f}%")
        print(f"   Yearly rewards: ${apy_result.get('yearly_rewards_usd', 0):,.0f}")
    
    # Compare with old method
    print(f"\n3. Comparison:")
    print(f"   Sugar: {sugar_time + apy_time:.2f}s total")
    print(f"   Old RPC method: ~12.7s")
    print(f"   Speedup: {12.7 / (sugar_time + apy_time):.1f}x faster!")

if __name__ == "__main__":
    asyncio.run(test_sugar())
