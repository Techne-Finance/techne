"""Direct Sugar contract test"""
from web3 import Web3

# Connect to Base
w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
print(f"Connected: {w3.is_connected()}")
print(f"Block: {w3.eth.block_number}")

# Sugar contract
SUGAR_ADDRESS = "0x2073D8035bB2b0F2e85aAF5a8732C6f397F9ff9b"

# Minimal ABI for just the `all` function
ABI = [
    {
        "name": "all",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "_limit", "type": "uint256"},
            {"name": "_offset", "type": "uint256"},
            {"name": "_account", "type": "address"}
        ],
        "outputs": [
            {
                "name": "",
                "type": "tuple[]",
                "components": [
                    {"name": "lp", "type": "address"},
                    {"name": "symbol", "type": "string"},
                    {"name": "decimals", "type": "uint8"},
                    {"name": "stable", "type": "bool"},
                    {"name": "total_supply", "type": "uint256"},
                    {"name": "token0", "type": "address"},
                    {"name": "reserve0", "type": "uint256"},
                    {"name": "claimable0", "type": "uint256"},
                    {"name": "token1", "type": "address"},
                    {"name": "reserve1", "type": "uint256"},
                    {"name": "claimable1", "type": "uint256"},
                    {"name": "gauge", "type": "address"},
                    {"name": "gauge_total_supply", "type": "uint256"},
                    {"name": "gauge_alive", "type": "bool"},
                    {"name": "fee", "type": "address"},
                    {"name": "bribe", "type": "address"},
                    {"name": "factory", "type": "address"},
                    {"name": "emissions", "type": "uint256"},
                    {"name": "emissions_token", "type": "address"},
                    {"name": "account_balance", "type": "uint256"},
                    {"name": "account_earned", "type": "uint256"},
                    {"name": "account_staked", "type": "uint256"},
                    {"name": "pool_fee", "type": "uint256"},
                    {"name": "token0_fees", "type": "uint256"},
                    {"name": "token1_fees", "type": "uint256"}
                ]
            }
        ]
    }
]

sugar = w3.eth.contract(
    address=Web3.to_checksum_address(SUGAR_ADDRESS),
    abi=ABI
)

print(f"\nSugar contract: {sugar.address}")
print(f"Calling all(10, 0, 0x0)...")

try:
    zero = "0x0000000000000000000000000000000000000000"
    result = sugar.functions.all(10, 0, zero).call()
    print(f"Result type: {type(result)}")
    print(f"Result length: {len(result)}")
    
    if result:
        print(f"\nFirst pool:")
        pool = result[0]
        print(f"  LP: {pool[0]}")
        print(f"  Symbol: {pool[1]}")
        print(f"  Stable: {pool[3]}")
        print(f"  Total Supply: {pool[4] / 1e18:.2f}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
