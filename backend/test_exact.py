import httpx
import asyncio
from artisan.data_sources import get_aggregated_pools

async def test():
    # Simulate exactly what /api/pools does for Solana
    chain = 'solana'
    min_tvl = 10000.0
    min_apy = 0.0
    max_apy = 100.0
    stablecoin_only = False
    asset_type = 'all'  # This is the default
    pool_type = 'all'
    limit = 50
    
    # Logic from main.py
    if chain and chain.lower() not in ["", "all"]:
        chains = [chain.capitalize()]
    else:
        chains = ["Base", "Ethereum", "Arbitrum", "Solana"]
    
    print(f'Chains to search: {chains}')
    
    all_pools = []
    sources_used = set()
    per_chain_limit = limit * 3 if len(chains) > 1 else limit * 2
    
    print(f'Per-chain limit: {per_chain_limit}')
    
    for c in chains:
        print(f'\nFetching {c}...')
        result = await get_aggregated_pools(
            chain=c,
            min_tvl=min_tvl,
            min_apy=min_apy,
            stablecoin_only=stablecoin_only or asset_type == "stablecoin",
            pool_type=pool_type,
            limit=per_chain_limit,
            blur=False
        )
        print(f'  -> Got {len(result["combined"])} pools from {c}')
        all_pools.extend(result["combined"])
        sources_used.update(result["sources_used"])
    
    print(f'\nTotal pools before filters: {len(all_pools)}')
    
    # Filter by asset type
    if asset_type == "eth":
        all_pools = [p for p in all_pools if 'ETH' in (p.get('symbol','') or '').upper()]
    elif asset_type == "sol":
        all_pools = [p for p in all_pools if 'solana' in (p.get('chain','') or '').lower()]
    elif asset_type == "stablecoin":
        all_pools = [p for p in all_pools if p.get("stablecoin", False)]
    
    print(f'After asset_type filter ({asset_type}): {len(all_pools)}')
    
    # Filter by max APY
    if max_apy and max_apy < 10000:
        all_pools = [p for p in all_pools if p.get("apy", 0) <= max_apy]
    
    print(f'After max_apy filter: {len(all_pools)}')
    
    # Show sample
    print('\nFirst 5 pools:')
    for p in all_pools[:5]:
        print(f'  {p.get("project")} | {p.get("symbol")} | APY: {p.get("apy")}')

asyncio.run(test())
