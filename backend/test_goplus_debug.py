"""
Debug GoPlus token security for GHST and USDC on Base
"""
import asyncio
import httpx

# GHST and USDC on Base
GHST_TOKEN = "0xd68a2ef151667e1e9ce09c42c2ebf5b5d7c19795"  # Need actual address
USDC_TOKEN = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

async def check_goplus(token_address: str, chain_id: str = "8453"):
    """Test GoPlus API directly"""
    url = f"https://api.gopluslabs.io/api/v1/token_security/{chain_id}?contract_addresses={token_address}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30)
        print(f"\nGoPlus response for {token_address[:10]}...")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Result: {data.get('result', {})}")
        
        # Check if token has data
        result = data.get('result', {})
        if token_address.lower() in result:
            token_info = result[token_address.lower()]
            print(f"Token name: {token_info.get('token_name')}")
            print(f"Is honeypot: {token_info.get('is_honeypot')}")
        else:
            print("❌ Token not found in GoPlus!")
            print(f"Available keys: {list(result.keys())}")

async def main():
    print("=" * 60)
    print("   GOPLUS TOKEN SECURITY DEBUG")
    print("=" * 60)
    
    # Test USDC
    print("\n[1] Testing USDC (known good token):")
    await check_goplus(USDC_TOKEN)
    
    # Test GHST - need to find the actual address first
    print("\n[2] Testing GHST:")
    # Get GHST address from pool
    import sys
    sys.path.insert(0, '.')
    from web3 import Web3
    from data_sources.aerodrome import aerodrome_client
    
    pool_address = Web3.to_checksum_address("0x56c11053159a24c0731b4b12356bc1f0578fb474")
    pool_abi = [
        {'name': 'token0', 'inputs': [], 'outputs': [{'type': 'address'}], 'stateMutability': 'view', 'type': 'function'},
        {'name': 'token1', 'inputs': [], 'outputs': [{'type': 'address'}], 'stateMutability': 'view', 'type': 'function'},
    ]
    pool = aerodrome_client.w3.eth.contract(address=pool_address, abi=pool_abi)
    
    token0 = pool.functions.token0().call()
    token1 = pool.functions.token1().call()
    print(f"Token0: {token0}")
    print(f"Token1: {token1}")
    
    await check_goplus(token0)
    await check_goplus(token1)

if __name__ == "__main__":
    asyncio.run(main())
