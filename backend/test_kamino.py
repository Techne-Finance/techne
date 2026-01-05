import asyncio
from artisan.data_sources import fetch_defillama_yields

async def test():
    pools = await fetch_defillama_yields('Solana')
    print(f'Total Solana pools from DefiLlama: {len(pools)}')
    
    # Find Kamino pools with any TVL
    kamino_all = [p for p in pools if 'kamino' in (p.get('project', '') or '').lower()]
    print(f'\nKamino pools (all TVL): {len(kamino_all)}')
    
    for p in kamino_all[:10]:
        tvl = p.get('tvlUsd', 0) or 0
        apy = p.get('apy', 0) or 0
        print(f'  {p["project"]} | {p["symbol"]} | TVL: ${tvl:,.0f} | APY: {apy:.2f}%')
    
    # Also check Marinade
    marinade_all = [p for p in pools if 'marinade' in (p.get('project', '') or '').lower()]
    print(f'\nMarinade pools: {len(marinade_all)}')
    for p in marinade_all[:5]:
        tvl = p.get('tvlUsd', 0) or 0
        apy = p.get('apy', 0) or 0
        print(f'  {p["project"]} | {p["symbol"]} | TVL: ${tvl:,.0f} | APY: {apy:.2f}%')

asyncio.run(test())
