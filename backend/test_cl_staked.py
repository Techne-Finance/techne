"""Debug CL pool staked liquidity vs total liquidity"""
import asyncio
from web3 import Web3

POOL = "0x47ca96ea59c13f72745928887f84c9f52c3d7348"

async def main():
    from data_sources.aerodrome import AerodromeOnChain
    
    aero = AerodromeOnChain()
    pool_address = Web3.to_checksum_address(POOL)
    
    # Get liquidity() and stakedLiquidity() directly
    CL_POOL_ABI = [
        {'name': 'liquidity', 'inputs': [], 'outputs': [{'type': 'uint128'}], 'stateMutability': 'view', 'type': 'function'},
        {'name': 'stakedLiquidity', 'inputs': [], 'outputs': [{'type': 'uint128'}], 'stateMutability': 'view', 'type': 'function'},
    ]
    
    pool = aero.w3.eth.contract(address=pool_address, abi=CL_POOL_ABI)
    
    try:
        liquidity = pool.functions.liquidity().call()
        staked = pool.functions.stakedLiquidity().call()
        
        print(f"Pool: {POOL}")
        print(f"liquidity(): {liquidity}")
        print(f"stakedLiquidity(): {staked}")
        
        if liquidity > 0:
            ratio = staked / liquidity
            print(f"\nStaked ratio: {ratio:.4f} ({ratio*100:.2f}%)")
            print(f"If we use this ratio with $4.4M yearly emissions and $37.5M TVL:")
            tvl = 37_500_000
            emissions = 4_444_936
            staked_tvl = tvl * ratio
            apy = (emissions / staked_tvl) * 100 if staked_tvl > 0 else 0
            print(f"  Staked TVL: ${staked_tvl:,.0f}")
            print(f"  APY: {apy:.2f}%")
            print(f"\nAerodrome shows: 13.89% APR")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    asyncio.run(main())
