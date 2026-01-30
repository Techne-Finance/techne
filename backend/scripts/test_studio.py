"""Test alternative The Graph endpoints"""
import httpx
import asyncio

# The Graph Studio endpoints (some work without API key)
STUDIO_ENDPOINTS = {
    # Aerodrome - try different variations
    "aerodrome-sugar": "https://api.studio.thegraph.com/query/50258/aerodrome-sugar/version/latest",
    "aerodrome-v2": "https://api.studio.thegraph.com/query/50258/aerodrome/version/latest", 
    
    # Aave V3 Base (official)
    "aave-v3-base": "https://api.studio.thegraph.com/query/50419/aave-v3-base/version/latest",
    
    # Uniswap V3 Base
    "uniswap-v3-base": "https://api.studio.thegraph.com/query/48211/uniswap-v3-base/version/latest",
}

# Alternative: use proxy endpoints that aggregate subgraphs
PROXY_ENDPOINTS = {
    "messari-aave": "https://api.thegraph.com/subgraphs/name/messari/aave-v3-ethereum",  # try ethereum first
}


async def test_endpoint(name: str, url: str) -> dict:
    """Test a subgraph endpoint"""
    query = """
    {
        _meta {
            block { number }
        }
    }
    """
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(url, json={"query": query})
            if resp.status_code == 200:
                data = resp.json()
                if "errors" in data:
                    return {"name": name, "status": "ERROR", "msg": data["errors"][0]["message"][:60]}
                
                block = data.get("data", {}).get("_meta", {}).get("block", {}).get("number")
                return {"name": name, "status": "OK", "block": block, "url": url}
            else:
                return {"name": name, "status": f"HTTP_{resp.status_code}"}
        except Exception as e:
            return {"name": name, "status": "FAIL", "msg": str(e)[:50]}


async def main():
    print("=" * 70)
    print("THE GRAPH STUDIO ENDPOINTS TEST")
    print("=" * 70)
    
    working = []
    
    print("\n1. STUDIO ENDPOINTS:")
    print("-" * 70)
    for name, url in STUDIO_ENDPOINTS.items():
        result = await test_endpoint(name, url)
        if result["status"] == "OK":
            print(f"  {name:25} OK  block={result.get('block')}")
            working.append(result)
        else:
            print(f"  {name:25} {result['status']}  {result.get('msg', '')[:40]}")
    
    print("\n2. PROXY ENDPOINTS:")
    print("-" * 70)
    for name, url in PROXY_ENDPOINTS.items():
        result = await test_endpoint(name, url)
        if result["status"] == "OK":
            print(f"  {name:25} OK  block={result.get('block')}")
            working.append(result)
        else:
            print(f"  {name:25} {result['status']}  {result.get('msg', '')[:40]}")
    
    print("\n" + "=" * 70)
    print(f"WORKING: {len(working)}")
    print("=" * 70)
    
    for w in working:
        print(f"  {w['name']}")
        print(f"    URL: {w['url']}")


if __name__ == "__main__":
    asyncio.run(main())
