import asyncio
from artisan.data_sources import get_aggregated_pools

async def test():
    result = await get_aggregated_pools(chain='Solana', min_tvl=50000, min_apy=0, limit=200, blur=False)
    print(f'Total Solana pools: {len(result["combined"])}')
    
    # Check for specific protocols
    for proto in ['kamino', 'marinade', 'orca', 'raydium']:
        pools = [p for p in result['combined'] if proto in p.get('project', '').lower()]
        print(f'{proto}: {len(pools)} pools')
        for p in pools[:3]:
            print(f'  - {p["project"]} | {p["symbol"]} | APY: {p["apy"]}')

asyncio.run(test())
