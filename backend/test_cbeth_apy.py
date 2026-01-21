"""Debug cbETH/WETH APY discrepancy"""
import asyncio
import sys
sys.path.insert(0, '.')

POOL = "0x47ca96ea59c13f72745928887f84c9f52c3d7348"  # cbETH/WETH 0.01%
CHAIN = "base"

async def main():
    print(f"Pool: {POOL}")
    print("=" * 60)
    
    # Get GeckoTerminal data
    from data_sources.geckoterminal import gecko_client
    gecko = await gecko_client.get_pool_by_address(CHAIN, POOL)
    print(f"\n1. GeckoTerminal:")
    print(f"   TVL: ${gecko.get('tvl', 0):,.0f}")
    print(f"   APY (from Gecko): {gecko.get('apy', 0):.2f}%")
    print(f"   Pool Type: {gecko.get('pool_type')}")
    
    # Get Aerodrome on-chain APY
    from data_sources.aerodrome import aerodrome_client
    
    # Check if it's CL or sAMM
    print(f"\n2. Detecting pool type...")
    pool_type = "cl"  # Assuming CL based on "Concentrated Stable"
    
    apy_data = await aerodrome_client.get_real_time_apy_multicall(POOL, pool_type)
    print(f"\n3. Aerodrome Multicall APY:")
    print(f"   Status: {apy_data.get('apy_status')}")
    print(f"   APY: {apy_data.get('apy', 0):.2f}%")
    print(f"   Emissions/year: ${apy_data.get('emissions_usd_yearly', 0):,.0f}")
    print(f"   Staked ratio: {apy_data.get('staked_ratio', 0):.2%}")
    print(f"   Source: {apy_data.get('apy_source')}")
    print(f"   Reason: {apy_data.get('reason', 'N/A')}")
    
    # Calculate what APY SHOULD be based on Aerodrome's 13.89%
    aerodrome_apr = 13.89
    print(f"\n4. Comparison:")
    print(f"   Aerodrome shows: {aerodrome_apr}% APR")
    print(f"   Our calculation: {apy_data.get('apy', 0):.2f}%")
    print(f"   Ratio: {apy_data.get('apy', 0) / aerodrome_apr:.1f}x off")

if __name__ == "__main__":
    asyncio.run(main())
