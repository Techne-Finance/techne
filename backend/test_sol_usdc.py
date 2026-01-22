"""Debug SOL/USDC APY discrepancy - 8.50% vs 880%"""
import asyncio
import sys
sys.path.insert(0, '.')

POOL = "0xb30540172f1b37d1ee1d109e49f883e935e69219"
CHAIN = "base"

async def main():
    print(f"=== Debug Pool: {POOL} ===\n")
    
    # 1. Check GeckoTerminal data
    from data_sources.geckoterminal import gecko_client
    gecko = await gecko_client.get_pool_by_address(CHAIN, POOL)
    print(f"1. GeckoTerminal:")
    print(f"   Name: {gecko.get('name')}")
    print(f"   TVL: ${gecko.get('tvl', 0):,.0f}")
    print(f"   Volume 24h: {gecko.get('volume_24h_formatted')}")
    
    # 2. Check Aerodrome on-chain
    from data_sources.aerodrome import aerodrome_client
    apy_data = await aerodrome_client.get_real_time_apy_multicall(POOL, "cl")
    print(f"\n2. Aerodrome Multicall:")
    print(f"   Status: {apy_data.get('apy_status')}")
    print(f"   Pool Type: {apy_data.get('pool_type')}")
    print(f"   Reward Rate: {apy_data.get('reward_rate')}")
    print(f"   Yearly Rewards USD: ${apy_data.get('yearly_rewards_usd', 0):,.0f}")
    print(f"   Staked Ratio: {apy_data.get('staked_ratio', 0):.4f}")
    print(f"   AERO Price: ${apy_data.get('aero_price', 0):.4f}")
    
    # 3. Calculate what APY should be
    tvl = gecko.get('tvl', 0)
    yearly = apy_data.get('yearly_rewards_usd', 0)
    staked_ratio = apy_data.get('staked_ratio', 1.0)
    
    if tvl > 0 and staked_ratio > 0:
        staked_tvl = tvl * staked_ratio
        our_apy = (yearly / staked_tvl) * 100 if staked_tvl > 0 else 0
        print(f"\n3. Calculation:")
        print(f"   TVL: ${tvl:,.0f}")
        print(f"   Staked Ratio: {staked_ratio:.4f} ({staked_ratio*100:.2f}%)")
        print(f"   Staked TVL: ${staked_tvl:,.0f}")
        print(f"   Yearly Rewards: ${yearly:,.0f}")
        print(f"   Our APY: {our_apy:.2f}%")
        
        # What staked_ratio would give 880% APY?
        target_apy = 880
        required_staked_tvl = yearly / (target_apy / 100) if target_apy > 0 else 0
        required_ratio = required_staked_tvl / tvl if tvl > 0 else 0
        print(f"\n4. To match Aerodrome 880% APR:")
        print(f"   Required Staked TVL: ${required_staked_tvl:,.0f}")
        print(f"   Required Staked Ratio: {required_ratio:.6f} ({required_ratio*100:.4f}%)")
    
    # 4. Full SmartRouter check
    from api.smart_router import SmartRouter
    router = SmartRouter()
    result = await router.smart_route_pool_check(POOL, CHAIN)
    
    if result.get('success'):
        pool = result.get('pool', {})
        print(f"\n5. SmartRouter Result:")
        print(f"   APY: {pool.get('apy', 0):.2f}%")
        print(f"   APY Source: {pool.get('apy_source')}")
        print(f"   Staked Ratio: {pool.get('staked_ratio', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(main())
