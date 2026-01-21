"""Compare Multicall vs Sequential RPC speed"""
import asyncio
import time
from web3 import Web3

RPC = "https://mainnet.base.org"
POOL = "0x6cdcb1c4a4d1c3c6d054b27ac5b77e89eafb971d"
VOTER = "0x16613524e02ad97eDfeF371bC883F2F5d6C480A5"

VOTER_ABI = [
    {"inputs": [{"name": "pool", "type": "address"}], "name": "gauges", 
     "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
]

GAUGE_ABI = [
    {"inputs": [], "name": "rewardRate", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "periodFinish", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
]

async def test_sequential():
    """Old way: sequential RPC calls"""
    w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={'timeout': 10}))
    
    start = time.time()
    
    # Call 1
    voter = w3.eth.contract(address=Web3.to_checksum_address(VOTER), abi=VOTER_ABI)
    gauge_addr = voter.functions.gauges(Web3.to_checksum_address(POOL)).call()
    
    # Calls 2-4
    gauge = w3.eth.contract(address=gauge_addr, abi=GAUGE_ABI)
    reward_rate = gauge.functions.rewardRate().call()
    total_supply = gauge.functions.totalSupply().call()
    period_finish = gauge.functions.periodFinish().call()
    
    elapsed = time.time() - start
    print(f"Sequential: {elapsed:.2f}s")
    print(f"  Gauge: {gauge_addr[:10]}...")
    print(f"  RewardRate: {reward_rate}")
    print(f"  TotalSupply: {total_supply}")
    return elapsed


async def test_multicall():
    """New way: Multicall3 batched"""
    w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={'timeout': 10}))
    
    # First get gauge address (need this for multicall)
    voter = w3.eth.contract(address=Web3.to_checksum_address(VOTER), abi=VOTER_ABI)
    gauge_addr = voter.functions.gauges(Web3.to_checksum_address(POOL)).call()
    
    start = time.time()
    
    # Import multicall
    from data_sources.multicall import Multicall3
    
    mc = Multicall3(w3)
    gauge = w3.eth.contract(address=gauge_addr, abi=GAUGE_ABI)
    
    # Add all calls
    rr_idx = mc.add_call(gauge, 'rewardRate')
    ts_idx = mc.add_call(gauge, 'totalSupply')
    pf_idx = mc.add_call(gauge, 'periodFinish')
    
    # Execute ONE call
    results = mc.execute()
    
    elapsed = time.time() - start
    print(f"\nMulticall: {elapsed:.2f}s")
    print(f"  RewardRate: {results[rr_idx]}")
    print(f"  TotalSupply: {results[ts_idx]}")
    return elapsed


async def main():
    print("Testing RPC performance...\n")
    
    seq_time = await test_sequential()
    mc_time = await test_multicall()
    
    print(f"\n=== RESULTS ===")
    print(f"Sequential: {seq_time:.2f}s")
    print(f"Multicall:  {mc_time:.2f}s")
    print(f"Speedup:    {seq_time/mc_time:.1f}x faster!")

if __name__ == "__main__":
    asyncio.run(main())
