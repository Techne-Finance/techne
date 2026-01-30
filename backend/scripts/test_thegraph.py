"""Test The Graph connectivity"""
import asyncio
import sys
sys.path.insert(0, ".")

from agents.pool_data_fetcher import pool_data_fetcher, TRACKED_POOLS, SUBGRAPHS

async def test_thegraph():
    print("=" * 60)
    print("THE GRAPH CONNECTIVITY TEST")
    print("=" * 60)
    
    # Show subgraph URLs
    print("\nConfigured subgraphs:")
    for protocol, url in SUBGRAPHS.items():
        status = "OK" if url else "MISSING URL"
        print(f"  {protocol}: {status}")
    
    print("\n" + "-" * 60)
    print("Testing pool data fetching...")
    print("-" * 60)
    
    success = 0
    failed = 0
    
    for pool_name, address in TRACKED_POOLS.items():
        protocol = pool_name.split("_")[0]
        print(f"\n{pool_name}:")
        try:
            data = await pool_data_fetcher.get_pool_data(protocol, address)
            if data and data.get("tvl", 0) > 0:
                tvl = data.get("tvl", 0)
                apy = data.get("apy", 0)
                print(f"  SUCCESS - TVL: ${tvl/1e6:.2f}M, APY: {apy:.2f}%")
                success += 1
            else:
                print(f"  FAILED - No data or empty response")
                failed += 1
        except Exception as e:
            print(f"  ERROR - {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {success} OK, {failed} FAILED")
    print("=" * 60)
    
    return success > 0

if __name__ == "__main__":
    result = asyncio.run(test_thegraph())
    print("\nThe Graph is", "WORKING" if result else "NOT WORKING")
