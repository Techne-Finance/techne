import asyncio
from artisan.data_sources import get_aggregated_pools, fetch_defillama_yields

async def test():
    # First check raw data
    raw_pools = await fetch_defillama_yields('Solana')
    print(f'Raw DefiLlama Solana pools: {len(raw_pools)}')
    
    # Check TVL distribution
    tvl_above_100k = [p for p in raw_pools if (p.get('tvlUsd', 0) or 0) >= 100000]
    tvl_above_10k = [p for p in raw_pools if (p.get('tvlUsd', 0) or 0) >= 10000]
    
    print(f'With TVL >= $100K: {len(tvl_above_100k)}')
    print(f'With TVL >= $10K: {len(tvl_above_10k)}')
    
    # Now test get_aggregated_pools
    result = await get_aggregated_pools(
        chain='Solana',
        min_tvl=10000,
        min_apy=0,
        stablecoin_only=False,
        pool_type='all',
        limit=50,
        blur=False
    )
    
    print(f'\nget_aggregated_pools result:')
    print(f'  DefiLlama formatted: {len(result["defillama"])}')
    print(f'  GeckoTerminal: {len(result["geckoterminal"])}')
    print(f'  Combined: {len(result["combined"])}')
    print(f'  Sources: {result["sources_used"]}')
    
    if result["defillama"]:
        print(f'\nFirst 5 DefiLlama formatted:')
        for p in result["defillama"][:5]:
            print(f'  {p.get("project")} | {p.get("symbol")} | TVL: {p.get("tvl", 0):,.0f}')

asyncio.run(test())
