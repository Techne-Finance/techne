"""
Test raw multicall without wrapper to identify issue.
"""
import asyncio
import sys
sys.path.insert(0, '.')

from web3 import Web3
from data_sources.aerodrome import aerodrome_client, VOTER_ADDRESS, VOTER_ABI

TEST_POOL = "0x6cdcb1c4a4d1c3c6d054b27ac5b77e89eafb971d"

# Multicall3 ABI
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

MULTICALL3_ADDRESS = "0xcA11bde05977b3631167028862bE2a173976CA11"

async def main():
    w3 = aerodrome_client.w3
    
    print("=" * 60)
    print("   RAW MULTICALL TEST")
    print("=" * 60)
    
    # Create voter contract
    voter = w3.eth.contract(
        address=Web3.to_checksum_address(VOTER_ADDRESS),
        abi=VOTER_ABI
    )
    
    # Create multicall contract
    multicall = w3.eth.contract(
        address=Web3.to_checksum_address(MULTICALL3_ADDRESS),
        abi=MULTICALL3_ABI
    )
    
    pool_address = Web3.to_checksum_address(TEST_POOL)
    
    # Encode the call data
    fn = voter.functions.gauges(pool_address)
    call_data = fn._encode_transaction_data()
    
    print(f"\n[1] Encoded call data: {call_data[:50]}...")
    
    # Build calls array
    calls = [{
        "target": voter.address,
        "allowFailure": True,
        "callData": call_data
    }]
    
    print(f"[2] Calling aggregate3...")
    
    try:
        raw_results = multicall.functions.aggregate3(calls).call()
        print(f"[3] Raw results: {raw_results}")
        
        success, return_data = raw_results[0]
        print(f"[4] Success: {success}")
        print(f"[5] Return data: {return_data}")
        print(f"[6] Return data hex: {return_data.hex() if return_data else 'None'}")
        
        if success and return_data:
            # Manual decode
            decoded = w3.codec.decode(['address'], return_data)
            print(f"[7] Decoded address: {decoded}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Also test direct call for comparison
    print("\n[DIRECT CALL]")
    gauge = voter.functions.gauges(pool_address).call()
    print(f"Direct gauge result: {gauge}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
