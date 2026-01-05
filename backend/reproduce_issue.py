import asyncio
import sys
import os

sys.path.append(os.getcwd())

from artisan.data_sources import get_aggregated_pools

async def test():
    print("Testing get_aggregated_pools with defaults (empty protocol filter)...")
    try:
        # Simulate the call from main.py when no specific protocol is selected
        result = await get_aggregated_pools(
            chain="Base",
            min_tvl=100000,
            limit=20,
            protocol_filter=[]
        )
        
        print(f"Sources used: {result.get('sources_used')}")
        print(f"DefiLlama count: {len(result.get('defillama', []))}")
        print(f"GeckoTerminal count: {len(result.get('geckoterminal', []))}")
        print(f"Combined count: {len(result.get('combined', []))}")
        
        if len(result.get('combined', [])) > 0:
            print("SUCCESS: Pools found.")
            print(f"Top 1: {result['combined'][0]['symbol']} ({result['combined'][0]['project']})")
        else:
            print("FAILURE: No pools found.")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
