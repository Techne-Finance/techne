import asyncio
from data_sources.aerodrome import AerodromeOnChain

async def test():
    client = AerodromeOnChain()
    pool = await client.get_pool_by_address('0x6cdcb1c4a4d1c3c6d054b27ac5b77e89eafb971d')
    if pool:
        print(f"APY: {pool.get('apy', 0)}")
        print(f"APY Source: {pool.get('apy_source', 'n/a')}")
        print(f"Has Gauge: {pool.get('has_gauge', False)}")
        print(f"Gauge Address: {pool.get('gauge_address', 'n/a')}")
        print(f"TVL: ${pool.get('tvl', 0):,.0f}")
    else:
        print("Pool returned None")

asyncio.run(test())
