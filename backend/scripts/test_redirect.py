"""Test subgraph endpoints with redirect following"""
import httpx
import asyncio

# Test various endpoint formats
ENDPOINTS = {
    # Studio - need to follow redirects
    "aerodrome-studio": "https://api.studio.thegraph.com/query/50258/aerodrome-v2/version/latest",
    
    # Gateway without API key (may have limited access)  
    "aerodrome-gw-1": "https://gateway.thegraph.com/api/subgraphs/id/8sX1LoEbQKJXadp3h4BZ4PwmcbAWBKRXbcY9wQMdcAjH",
    
    # Try known Aave subgraph IDs
    "aave-base": "https://gateway.thegraph.com/api/subgraphs/id/GQFbb95cE6d8mV989mL5figjaGaKCQB3xqYrr1bRyXqF",
    
    # Messari aggregated subgraphs (known to work)
    "messari-lending": "https://api.thegraph.com/subgraphs/name/messari/lending-base",
}


async def test(name: str, url: str):
    query = '{ _meta { block { number } } }'
    
    # Use follow_redirects=True
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        try:
            resp = await client.post(url, json={"query": query})
            print(f"{name}:")
            print(f"  Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                if "errors" in data:
                    print(f"  Error: {data['errors'][0]['message'][:80]}")
                else:
                    block = data.get("data", {}).get("_meta", {}).get("block", {}).get("number")
                    print(f"  OK - Block: {block}")
                    print(f"  URL: {url}")
            else:
                print(f"  Body: {resp.text[:200]}")
        except Exception as e:
            print(f"  Exception: {e}")
        print()


async def main():
    print("=" * 70)
    print("SUBGRAPH ENDPOINT TEST (with redirects)")
    print("=" * 70)
    print()
    
    for name, url in ENDPOINTS.items():
        await test(name, url)


if __name__ == "__main__":
    asyncio.run(main())
