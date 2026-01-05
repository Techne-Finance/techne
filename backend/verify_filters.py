import asyncio
import sys
import os

sys.path.append(os.getcwd())

from artisan.data_sources import get_aggregated_pools

async def test_filters():
    print("=" * 60)
    print("VERIFYING FILTER LOGIC")
    print("=" * 60)
    
    # Test 1: Default (All chains, stablecoins, no protocol filter)
    print("\n[TEST 1] Default: Base, Stablecoins, no protocol filter")
    result = await get_aggregated_pools(
        chain="Base",
        min_tvl=100000,
        min_apy=0,
        stablecoin_only=True,
        limit=50,
        protocol_filter=[]
    )
    print(f"  -> Found {len(result['combined'])} pools")
    if result['combined']:
        print(f"  -> Sample: {result['combined'][0]['symbol']} by {result['combined'][0]['project']}")
    
    # Test 2: Lido specifically (ETH, all pool types)
    print("\n[TEST 2] Protocol Filter: Lido on Ethereum")
    result = await get_aggregated_pools(
        chain="Ethereum",
        min_tvl=0,
        min_apy=0,
        stablecoin_only=False,
        limit=50,
        protocol_filter=["lido"]
    )
    print(f"  -> Found {len(result['combined'])} Lido pools")
    for p in result['combined'][:5]:
        print(f"     - {p['symbol']} | APY: {p['apy']:.2f}% | TVL: {p.get('tvl_formatted', 'N/A')}")
    
    # Test 3: Aave on Base
    print("\n[TEST 3] Protocol Filter: Aave on Base")
    result = await get_aggregated_pools(
        chain="Base",
        min_tvl=0,
        min_apy=0,
        stablecoin_only=False,
        limit=50,
        protocol_filter=["aave"]
    )
    print(f"  -> Found {len(result['combined'])} Aave pools")
    for p in result['combined'][:3]:
        print(f"     - {p['symbol']} | APY: {p['apy']:.2f}%")
    
    # Test 4: Low TVL threshold, all chains (simulating user setting min_tvl slider to 0)
    print("\n[TEST 4] Low TVL Filter ($10K+), ETH assets")
    result = await get_aggregated_pools(
        chain="Base",
        min_tvl=10000,
        min_apy=0,
        stablecoin_only=False,
        limit=100,
        protocol_filter=[]
    )
    print(f"  -> Found {len(result['combined'])} pools with TVL > $10K")
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_filters())
