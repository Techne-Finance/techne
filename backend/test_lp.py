import asyncio
from artisan.scout_agent import get_scout_pools
from agents.strategy_executor import strategy_executor
from api.agent_config_router import DEPLOYED_AGENTS

async def test():
    a = DEPLOYED_AGENTS.get('0xba9d6947c0ad6ea2aaa99507355cf83b4d098058'.lower(), [])[0]
    r = await get_scout_pools(chain='base', min_apy=50, min_tvl=500000)
    all_p = r.get('pools', [])
    pools = [p for p in all_p if isinstance(p, dict) and 'aerodrome' in (p.get('project') or '').lower()]
    print(f'Aero pools: {len(pools)}')
    if pools:
        print(f'Pool: {pools[0]}')
    a['recommended_pools'] = pools
    a['user_address'] = '0xba9d6947c0ad6ea2aaa99507355cf83b4d098058'
    result = await strategy_executor.execute_allocation(a, 40)
    print(f'Result: {result}')

asyncio.run(test())
