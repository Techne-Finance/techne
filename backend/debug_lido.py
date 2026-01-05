import asyncio
import sys
import os

# Ensure backend directory is in path
sys.path.append(os.getcwd())

from artisan.data_sources import get_aggregated_pools

async def test():
    print('Testing Lido on Ethereum...')
    # Fetching 'Ethereum' explicitly
    result = await get_aggregated_pools(chain='Ethereum', min_tvl=0, limit=50, pool_type='all', stablecoin_only=False)
    
    found_lido = False
    print(f'Total Pools Fetched: {len(result["combined"])}')
    for p in result['combined']:
        project = p.get('project', '').lower()
        symbol = p.get('symbol', '').lower()
        if 'lido' in project or 'steth' in symbol:
            print(f'FOUND: {p.get("project")} - {p.get("symbol")} | APY: {p.get("apy")}%')
            found_lido = True
    
    if not found_lido:
        print("NO LIDO POOLS FOUND. Dumping top 5 pools to see what we got:")
        for p in result['combined'][:5]:
            print(f"{p.get('project')} - {p.get('symbol')}")

if __name__ == '__main__':
    asyncio.run(test())
