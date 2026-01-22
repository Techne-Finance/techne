"""Test getting actual staked TVL from gauge for CL pools"""
import asyncio
from web3 import Web3

POOL = "0xb30540172f1b37d1ee1d109e49f883e935e69219"  # SOL/USDC
VOTER = "0x16613524e02ad97eDfeF371bC883F2F5d6C480A5"

async def main():
    import sys
    sys.path.insert(0, '.')
    from data_sources.aerodrome import AerodromeOnChain, GAUGE_ABI, CL_GAUGE_ABI
    
    aero = AerodromeOnChain()
    pool_address = Web3.to_checksum_address(POOL)
    
    # Get gauge address from Voter
    voter = aero.w3.eth.contract(
        address=Web3.to_checksum_address(VOTER),
        abi=[{"name": "gauges", "inputs": [{"type": "address"}], "outputs": [{"type": "address"}], "type": "function"}]
    )
    gauge_address = voter.functions.gauges(pool_address).call()
    print(f"Pool: {POOL}")
    print(f"Gauge: {gauge_address}")
    
    # For CL gauges, we need to check if it has stakedLiquidity or totalSupply
    gauge = aero.w3.eth.contract(address=gauge_address, abi=GAUGE_ABI)
    
    try:
        # V2 gauge style - totalSupply of staked LP tokens
        total_supply = gauge.functions.totalSupply().call()
        print(f"\nGauge totalSupply: {total_supply} (raw)")
        print(f"Gauge totalSupply: {total_supply / 1e18:.6f} (18 decimals)")
    except Exception as e:
        print(f"totalSupply failed: {e}")
    
    # CL gauge might have different methods
    # Check what Aerodrome API returns for this pool
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://api.aerodrome.finance/v2/pools/{POOL.lower()}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"\nAerodrome API:")
            print(f"  apr: {data.get('apr', 'N/A')}")
            print(f"  stakedLiquidity: {data.get('stakedLiquidity', 'N/A')}")
            print(f"  totalSupply: {data.get('totalSupply', 'N/A')}")
        else:
            print(f"Aerodrome API error: {resp.status_code}")

if __name__ == "__main__":
    asyncio.run(main())
