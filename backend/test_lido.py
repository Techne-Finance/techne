import asyncio
import sys
import os

sys.path.append(os.getcwd())

from artisan.data_sources import get_aggregated_pools

async def test_lido():
    print("Testing Lido protocol filter on Ethereum...")
    result = await get_aggregated_pools(
        chain="Ethereum",
        min_tvl=0,
        min_apy=0,
        stablecoin_only=False,
        limit=50,
        protocol_filter=["lido"]
    )
    
    count = len(result.get('combined', []))
    print(f"Lido pools found: {count}")
    
    if count > 0:
        print("SUCCESS! Lido pools are being returned.")
        for p in result['combined'][:5]:
            print(f"  - {p.get('symbol')} | APY: {p.get('apy', 0):.2f}% | Project: {p.get('project')}")
    else:
        print("FAIL: No Lido pools found.")
        # Debug: show what protocols ARE in the data
        print("Checking what protocols exist in Ethereum data...")
        all_eth = await get_aggregated_pools(
            chain="Ethereum",
            min_tvl=0,
            min_apy=0,
            stablecoin_only=False,
            limit=100,
            protocol_filter=[]
        )
        projects = set(p.get('project', '').lower() for p in all_eth.get('combined', []))
        lido_like = [p for p in projects if 'lido' in p or 'steth' in p]
        print(f"Lido-like projects in data: {lido_like}")

if __name__ == "__main__":
    asyncio.run(test_lido())
