import asyncio
from artisan.data_sources import fetch_defillama_yields

async def test():
    pools = await fetch_defillama_yields('Solana')
    print(f'Total Solana DefiLlama: {len(pools)}')
    
    # Check for each protocol
    for proto in ['kamino', 'marinade', 'orca', 'raydium']:
        matches = [p for p in pools if proto in (p.get('project', '') or '').lower()]
        print(f'\n{proto.upper()}: {len(matches)} pools')
    
    # Print all unique projects
    projects = set()
    for p in pools:
        proj = p.get('project', '')
        if proj:
            projects.add(proj.lower())
    
    print(f'\nAll unique projects ({len(projects)}):')
    for proj in sorted(projects):
        print(f'  {proj}')

asyncio.run(test())
