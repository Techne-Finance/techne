"""
Test Multicall APY vs Sequential APY performance.
"""
import asyncio
import time
import sys
sys.path.insert(0, '.')

from data_sources.aerodrome import aerodrome_client

# Test pool: AERO/USDC
TEST_POOL = "0x6cdcb1c4a4d1c3c6d054b27ac5b77e89eafb971d"

async def test_sequential():
    """Test original sequential method"""
    start = time.time()
    result = await aerodrome_client.get_real_time_apy(TEST_POOL)
    elapsed = time.time() - start
    print(f"\n📊 SEQUENTIAL APY:")
    print(f"   Time: {elapsed:.2f}s")
    print(f"   APY: {result.get('apy', 0):.2f}%")
    print(f"   Status: {result.get('apy_status')}")
    return elapsed

async def test_multicall():
    """Test new multicall method"""
    start = time.time()
    result = await aerodrome_client.get_real_time_apy_multicall(TEST_POOL)
    elapsed = time.time() - start
    print(f"\n🚀 MULTICALL APY:")
    print(f"   Time: {elapsed:.2f}s")
    print(f"   APY: {result.get('apy', 0):.2f}%")
    print(f"   Status: {result.get('apy_status')}")
    print(f"   Source: {result.get('source')}")
    return elapsed

async def main():
    print("=" * 60)
    print("   MULTICALL vs SEQUENTIAL APY PERFORMANCE TEST")
    print("=" * 60)
    
    # Run multicall first (it's faster)
    mc_time = await test_multicall()
    
    # Run sequential
    seq_time = await test_sequential()
    
    # Summary
    print("\n" + "=" * 60)
    print(f"   RESULTS:")
    print(f"   Sequential: {seq_time:.2f}s")
    print(f"   Multicall:  {mc_time:.2f}s")
    print(f"   Speedup:    {seq_time/mc_time:.1f}x faster!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
