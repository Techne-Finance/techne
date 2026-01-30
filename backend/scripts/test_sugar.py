"""Test Aerodrome Sugar Contract Integration"""
import asyncio
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from data_sources.aerodrome_sugar import AerodromeSugar, aerodrome_sugar


async def test_sugar_connection():
    """Test that we can connect to Sugar contract and fetch data"""
    print("=" * 70)
    print("AERODROME SUGAR CONTRACT TEST")
    print("=" * 70)
    
    sugar = AerodromeSugar()
    
    print(f"\nRPC URL: {sugar.rpc_url[:50]}...")
    print(f"Sugar Address: {sugar.sugar.address}")
    print(f"Connected: {sugar.w3.is_connected()}")
    
    print("\n1. Fetching all pools (limit=20)...")
    try:
        pools = await sugar.get_all_pools(limit=20)
        print(f"   ✅ Fetched {len(pools)} pools")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    if not pools:
        print("   ⚠️ No pools returned!")
        return False
    
    print("\n2. Top 10 pools by TVL:")
    print("-" * 70)
    sorted_pools = sorted(pools, key=lambda p: p.get("tvlUsd", 0), reverse=True)
    
    print(f"{'Symbol':<35} {'TVL':>12} {'APR':>8} {'Gauge'}")
    print("-" * 70)
    for p in sorted_pools[:10]:
        gauge_status = "✅" if p.get("gauge_alive") else "❌"
        print(f"{p['symbol'][:35]:<35} ${p.get('tvlUsd', 0):>10,.0f} {p.get('apy', 0):>7.1f}% {gauge_status}")
    
    print("\n3. Pool structure sample:")
    sample = pools[0]
    print(f"   Keys: {list(sample.keys())[:10]}...")
    print(f"   LP: {sample['lp']}")
    print(f"   Token0: {sample['token0']}")
    print(f"   Token1: {sample['token1']}")
    print(f"   Emissions: {sample['emissions'] / 1e18:.4f} AERO/sec")
    
    print("\n4. Testing cache...")
    pools2 = await sugar.get_all_pools(limit=20)
    cache_hit = sugar._is_cache_valid("all_pools_20_0")
    print(f"   Cache valid: {'✅ Yes' if cache_hit else '❌ No'}")
    
    print("\n" + "=" * 70)
    print("✅ SUGAR CONTRACT INTEGRATION WORKING!")
    print("=" * 70)
    
    return True


async def compare_with_defillama():
    """Compare Sugar data with DefiLlama for validation"""
    import httpx
    
    print("\n\n5. Comparing with DefiLlama...")
    
    # Get Sugar data
    sugar = AerodromeSugar()
    sugar_pools = await sugar.get_all_pools(limit=50)
    
    # Get DefiLlama data
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://yields.llama.fi/pools")
        if resp.status_code != 200:
            print("   ⚠️ Could not fetch DefiLlama data")
            return
        
        llama_data = resp.json().get("data", [])
        llama_aero = [
            p for p in llama_data 
            if p.get("project") == "aerodrome" and p.get("chain") == "Base"
        ]
    
    print(f"   Sugar pools: {len(sugar_pools)}")
    print(f"   DefiLlama pools: {len(llama_aero)}")
    
    # Compare TVL for matching pools
    print("\n   TVL Comparison (matched pools):")
    matched = 0
    for sugar_pool in sugar_pools[:10]:
        symbol = sugar_pool.get("symbol", "").upper()
        for llama_pool in llama_aero:
            if llama_pool.get("symbol", "").upper() == symbol:
                sugar_tvl = sugar_pool.get("tvlUsd", 0)
                llama_tvl = llama_pool.get("tvlUsd", 0)
                diff_pct = abs(sugar_tvl - llama_tvl) / max(llama_tvl, 1) * 100
                print(f"   {symbol[:30]:<30} Sugar: ${sugar_tvl:>12,.0f}  Llama: ${llama_tvl:>12,.0f}  Diff: {diff_pct:.1f}%")
                matched += 1
                break
    
    print(f"\n   Matched {matched} pools")


if __name__ == "__main__":
    success = asyncio.run(test_sugar_connection())
    if success:
        asyncio.run(compare_with_defillama())
