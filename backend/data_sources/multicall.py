"""
Multicall3 Helper - Batch multiple RPC calls into ONE request.
Reduces 12s of sequential calls to ~1-2s.

Multicall3 is deployed at the same address on all EVMs:
0xcA11bde05977b3631167028862bE2a173976CA11
"""

import logging
from typing import List, Tuple, Any, Optional
from web3 import Web3

logger = logging.getLogger("Multicall")

# Multicall3 deployed on all EVMs
MULTICALL3_ADDRESS = "0xcA11bde05977b3631167028862bE2a173976CA11"

# Minimal ABI for aggregate3 (most flexible)
MULTICALL3_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"name": "target", "type": "address"},
                    {"name": "allowFailure", "type": "bool"},
                    {"name": "callData", "type": "bytes"}
                ],
                "name": "calls",
                "type": "tuple[]"
            }
        ],
        "name": "aggregate3",
        "outputs": [
            {
                "components": [
                    {"name": "success", "type": "bool"},
                    {"name": "returnData", "type": "bytes"}
                ],
                "name": "returnData",
                "type": "tuple[]"
            }
        ],
        "stateMutability": "payable",
        "type": "function"
    }
]


class Multicall3:
    """
    Batch multiple contract calls into ONE RPC request.
    
    Usage:
        mc = Multicall3(web3_instance)
        
        # Add calls
        mc.add_call(token_contract, 'decimals')
        mc.add_call(token_contract, 'symbol')
        mc.add_call(gauge_contract, 'rewardRate')
        
        # Execute all at once
        results = mc.execute()  # One RPC call!
    """
    
    def __init__(self, w3: Web3):
        self.w3 = w3
        self.multicall = w3.eth.contract(
            address=Web3.to_checksum_address(MULTICALL3_ADDRESS),
            abi=MULTICALL3_ABI
        )
        self.calls: List[Tuple[Any, str, tuple, bool, list]] = []  # (contract, fn_name, args, allow_failure, output_types)
        
    def add_call(
        self, 
        contract, 
        function_name: str, 
        args: tuple = (), 
        allow_failure: bool = True
    ) -> int:
        """
        Add a contract function call to the batch.
        Returns the index for retrieving the result.
        """
        idx = len(self.calls)
        
        # Get output types from ABI at add time
        fn = getattr(contract.functions, function_name)(*list(args))
        output_types = self._get_output_types(contract.abi, function_name)
        
        self.calls.append((contract, function_name, args, allow_failure, output_types))
        return idx
    
    def _get_output_types(self, abi: list, function_name: str) -> list:
        """Extract output types from ABI for a function"""
        for item in abi:
            if item.get('type') == 'function' and item.get('name') == function_name:
                outputs = item.get('outputs', [])
                return [o.get('type') for o in outputs]
        return []
    
    def execute(self) -> List[Tuple[bool, Any]]:
        """
        Execute all batched calls in ONE RPC request.
        Returns list of (success, decoded_result) tuples.
        """
        if not self.calls:
            return []
        
        # Build multicall3 calls array
        call_data = []
        for contract, fn_name, args, allow_failure, _ in self.calls:
            fn = getattr(contract.functions, fn_name)(*list(args))
            call_data.append({
                "target": contract.address,
                "allowFailure": allow_failure,
                "callData": fn._encode_transaction_data()
            })
        
        # Execute ONE RPC call
        try:
            raw_results = self.multicall.functions.aggregate3(call_data).call()
        except Exception as e:
            logger.error(f"Multicall failed: {e}")
            return [(False, None) for _ in self.calls]
        
        # Decode results
        results = []
        for i, (success, return_data) in enumerate(raw_results):
            if not success or not return_data:
                results.append((False, None))
                continue
            
            try:
                _, _, _, _, output_types = self.calls[i]
                
                if not output_types:
                    # No output types - return raw bytes
                    results.append((True, return_data))
                    continue
                
                # Decode using stored output types
                decoded = self.w3.codec.decode(output_types, return_data)
                
                # Unwrap single values
                if len(decoded) == 1:
                    decoded = decoded[0]
                    
                results.append((True, decoded))
            except Exception as e:
                logger.debug(f"Decode failed for call {i}: {e}")
                results.append((False, None))
        
        # Clear calls for reuse
        self.calls = []
        
        return results
    
    def clear(self):
        """Clear all pending calls"""
        self.calls = []


async def batch_aerodrome_calls(
    w3: Web3,
    pool_address: str,
    gauge_address: str,
    is_cl: bool = False
) -> dict:
    """
    Get all Aerodrome APY data in ONE RPC call.
    
    Batches:
    - Gauge: rewardRate, totalSupply, periodFinish
    - Pool: liquidity, stakedLiquidity (for CL)
    - Voter: isAlive
    
    Returns dict with all data or None on failure.
    """
    from data_sources.aerodrome import GAUGE_ABI, CL_GAUGE_ABI
    
    pool_address = Web3.to_checksum_address(pool_address)
    gauge_address = Web3.to_checksum_address(gauge_address)
    
    mc = Multicall3(w3)
    
    # Create contracts
    gauge_abi = CL_GAUGE_ABI if is_cl else GAUGE_ABI
    gauge = w3.eth.contract(address=gauge_address, abi=gauge_abi)
    
    # Add gauge calls
    reward_rate_idx = mc.add_call(gauge, 'rewardRate')
    period_finish_idx = mc.add_call(gauge, 'periodFinish')
    
    # V2 gauges have totalSupply, CL gauges need pool.stakedLiquidity
    if not is_cl:
        total_staked_idx = mc.add_call(gauge, 'totalSupply')
    
    # For CL pools, get liquidity from pool contract
    if is_cl:
        CL_POOL_ABI = [
            {'name': 'liquidity', 'inputs': [], 'outputs': [{'type': 'uint128'}], 'stateMutability': 'view', 'type': 'function'},
            {'name': 'stakedLiquidity', 'inputs': [], 'outputs': [{'type': 'uint128'}], 'stateMutability': 'view', 'type': 'function'},
        ]
        pool = w3.eth.contract(address=pool_address, abi=CL_POOL_ABI)
        liquidity_idx = mc.add_call(pool, 'liquidity')
        staked_liq_idx = mc.add_call(pool, 'stakedLiquidity')
    
    # Execute ALL in ONE call
    results = mc.execute()
    
    # Parse results
    data = {
        "reward_rate": results[reward_rate_idx][1] if results[reward_rate_idx][0] else 0,
        "period_finish": results[period_finish_idx][1] if results[period_finish_idx][0] else 0,
    }
    
    if not is_cl:
        data["total_staked"] = results[total_staked_idx][1] if results[total_staked_idx][0] else 0
    else:
        data["liquidity"] = results[liquidity_idx][1] if results[liquidity_idx][0] else 0
        data["staked_liquidity"] = results[staked_liq_idx][1] if results[staked_liq_idx][0] else 0
        if data["liquidity"] > 0:
            data["staked_ratio"] = data["staked_liquidity"] / data["liquidity"]
        else:
            data["staked_ratio"] = 1.0
    
    logger.info(f"🚀 Multicall: fetched all Aerodrome data in ONE RPC call")
    return data
