"""Full SmartRouter flow for cbETH/WETH"""
import asyncio
import sys
sys.path.insert(0, '.')

POOL = "0x47ca96ea59c13f72745928887f84c9f52c3d7348"  # cbETH/WETH
CHAIN = "base"

async def main():
    from api.smart_router import SmartRouter
    
    router = SmartRouter()
    result = await router.smart_route_pool_check(POOL, CHAIN)
    
    if result.get('success'):
        pool = result.get('pool', {})
        print(f"Pool: {pool.get('symbol')}")
        print(f"TVL: ${pool.get('tvl', 0):,.0f}")
        print(f"APY: {pool.get('apy', 0):.2f}%")
        print(f"APY Source: {pool.get('apy_source')}")
        print(f"APY Status: {pool.get('apy_status')}")
        print(f"Pool Type: {pool.get('pool_type')}")
        print(f"Staked Ratio: {pool.get('staked_ratio', 'N/A')}")
        print(f"Yearly Emissions: ${pool.get('yearly_emissions_usd', 0):,.0f}")
    else:
        print(f"Error: {result}")

if __name__ == "__main__":
    asyncio.run(main())
