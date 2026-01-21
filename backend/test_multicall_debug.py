"""
Debug Multicall issue - check each call separately.
"""
import asyncio
import sys
sys.path.insert(0, '.')

from web3 import Web3
from data_sources.multicall import Multicall3
from data_sources.aerodrome import (
    aerodrome_client, VOTER_ADDRESS, GAUGE_ABI, POOL_ABI, 
    AERO_USDC_POOL, ZERO_ADDRESS, AERO_TOKEN
)

TEST_POOL = "0x6cdcb1c4a4d1c3c6d054b27ac5b77e89eafb971d"

async def main():
    w3 = aerodrome_client.w3
    voter = aerodrome_client.voter
    pool_address = Web3.to_checksum_address(TEST_POOL)
    
    print("=" * 60)
    print("   MULTICALL DEBUG")
    print("=" * 60)
    
    # BATCH 1: Get gauge
    print("\n[BATCH 1] Get gauge address...")
    mc = Multicall3(w3)
    voter_idx = mc.add_call(voter, 'gauges', (pool_address,))
    results1 = mc.execute()
    
    print(f"   Result: {results1}")
    
    if not results1[voter_idx][0]:
        print("   ERROR: Voter call failed!")
        return
    
    gauge_address = results1[voter_idx][1]
    print(f"   Gauge: {gauge_address}")
    
    if gauge_address == ZERO_ADDRESS:
        print("   ERROR: No gauge")
        return
    
    # BATCH 2: Get all data
    print("\n[BATCH 2] Get gauge + pool + price data...")
    mc2 = Multicall3(w3)
    gauge_checksum = Web3.to_checksum_address(gauge_address)
    
    # Create contracts
    v2_gauge = w3.eth.contract(address=gauge_checksum, abi=GAUGE_ABI)
    
    # Add calls
    v2_reward_rate_idx = mc2.add_call(v2_gauge, 'rewardRate')
    v2_total_supply_idx = mc2.add_call(v2_gauge, 'totalSupply')
    
    # AERO price
    aero_usdc_pool = w3.eth.contract(
        address=Web3.to_checksum_address(AERO_USDC_POOL), 
        abi=POOL_ABI
    )
    aero_reserves_idx = mc2.add_call(aero_usdc_pool, 'getReserves')
    aero_token0_idx = mc2.add_call(aero_usdc_pool, 'token0')
    
    # Execute
    results2 = mc2.execute()
    
    print(f"\n   Results:")
    for i, (success, data) in enumerate(results2):
        print(f"   [{i}] success={success}, data={data}")
    
    # Parse
    v2_reward_rate = results2[v2_reward_rate_idx][1] if results2[v2_reward_rate_idx][0] else 0
    v2_total_supply = results2[v2_total_supply_idx][1] if results2[v2_total_supply_idx][0] else 0
    
    print(f"\n   Reward Rate: {v2_reward_rate}")
    print(f"   Total Supply: {v2_total_supply}")
    
    # AERO price
    if results2[aero_reserves_idx][0] and results2[aero_token0_idx][0]:
        reserves = results2[aero_reserves_idx][1]
        token0 = results2[aero_token0_idx][1]
        print(f"\n   AERO reserves: {reserves}")
        print(f"   Token0: {token0}")
        
        if token0.lower() == AERO_TOKEN.lower():
            aero_reserve = reserves[0] / 1e18
            usdc_reserve = reserves[1] / 1e6
        else:
            usdc_reserve = reserves[0] / 1e6
            aero_reserve = reserves[1] / 1e18
        
        aero_price = usdc_reserve / aero_reserve if aero_reserve > 0 else 0
        print(f"   AERO Price: ${aero_price:.4f}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
