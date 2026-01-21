"""
Raw test GoPlus API directly 
"""
import httpx
import asyncio

async def main():
    tokens = [
        "0xcd2f22236dd9dfe2356d7c543161d4d260fd9bcb",  # GHST
        "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"   # USDC
    ]
    
    addresses_param = ",".join(tokens)
    url = f"https://api.gopluslabs.io/api/v1/token_security/8453?contract_addresses={addresses_param}"
    
    print(f"Calling: {url}")
    
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        print(f"Status: {response.status_code}")
        
        data = response.json()
        result = data.get("result", {})
        
        print(f"\nResult keys from GoPlus: {list(result.keys())}")
        
        for addr in result.keys():
            info = result[addr]
            print(f"\n{addr}:")
            print(f"  token_name: {info.get('token_name')}")

if __name__ == "__main__":
    asyncio.run(main())
