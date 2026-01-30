"""Find working The Graph subgraph endpoints for Base chain"""
import httpx
import asyncio

# Known subgraph endpoints to test (hosted service names)
HOSTED_SUBGRAPHS = {
    # Aerodrome variations
    "aerodrome/aerodrome-base": "aerodrome-finance/aerodrome-base",
    "aerodrome/slipstream": "aerodrome-finance/slipstream",
    "aerodrome/cl": "aerodrome-finance/cl",
    
    # Aave variations  
    "aave/v3-base": "aave/protocol-v3-base",
    "messari/aave-base": "messari/aave-v3-base",
    
    # Compound
    "compound/v3-base": "compound-finance/compound-v3-base",
    "messari/compound": "messari/compound-v3-base",
    
    # Uniswap
    "uniswap/v3-base": "uniswap/uniswap-v3-base",
    
    # Moonwell
    "moonwell/base": "moonwell-fi/moonwell-base",
}

# Decentralized network subgraph IDs (need API key)
DECENTRALIZED_IDS = {
    "aerodrome": "8jKhSdT2FXcN5VxZJXpHnVhtXdJqNWNHpXGtJgEaM8cW",
    "aave-v3": "GQFbb95cE6d8mV989mL5figjaGaKCQB3xqYrr1bRyXqF",
    "uniswap-v3": "43Hwfi3dJSoGpyas9VwNoDAv55yjgGrPCNzh76hKHKxd",
}


async def test_hosted_subgraph(name: str, path: str) -> dict:
    """Test a hosted service subgraph"""
    url = f"https://api.thegraph.com/subgraphs/name/{path}"
    query = """
    {
        _meta {
            block { number }
            deployment
            hasIndexingErrors
        }
    }
    """
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(url, json={"query": query})
            if resp.status_code == 200:
                data = resp.json()
                if "errors" in data:
                    return {"name": name, "status": "ERROR", "error": data["errors"][0]["message"][:80]}
                
                meta = data.get("data", {}).get("_meta", {})
                return {
                    "name": name,
                    "status": "OK",
                    "url": url,
                    "block": meta.get("block", {}).get("number"),
                    "deployment": meta.get("deployment"),
                    "errors": meta.get("hasIndexingErrors")
                }
            else:
                return {"name": name, "status": "HTTP_ERROR", "code": resp.status_code}
        except Exception as e:
            return {"name": name, "status": "FAIL", "error": str(e)[:50]}


async def test_decentralized(name: str, subgraph_id: str, api_key: str = None) -> dict:
    """Test decentralized network subgraph"""
    if not api_key:
        return {"name": name, "status": "NO_API_KEY"}
    
    url = f"https://gateway.thegraph.com/api/{api_key}/subgraphs/id/{subgraph_id}"
    query = '{ _meta { block { number } } }'
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(url, json={"query": query})
            if resp.status_code == 200:
                data = resp.json()
                if "errors" not in data:
                    block = data.get("data", {}).get("_meta", {}).get("block", {}).get("number")
                    return {"name": name, "status": "OK", "block": block, "url": url}
            return {"name": name, "status": "ERROR"}
        except Exception as e:
            return {"name": name, "status": "FAIL", "error": str(e)[:50]}


async def main():
    import os
    api_key = os.getenv("GRAPH_API_KEY")
    
    print("=" * 70)
    print("THE GRAPH SUBGRAPH DISCOVERY")
    print("=" * 70)
    
    print("\n1. HOSTED SERVICE (api.thegraph.com):")
    print("-" * 70)
    
    working = []
    
    for name, path in HOSTED_SUBGRAPHS.items():
        result = await test_hosted_subgraph(name, path)
        status = result["status"]
        
        if status == "OK":
            print(f"  {name:30} OK  block={result.get('block')}")
            working.append(result)
        else:
            error = str(result.get("error", result.get("code", "")))[:40]
            print(f"  {name:30} {status}  {error}")
    
    print("\n2. DECENTRALIZED NETWORK (gateway.thegraph.com):")
    print("-" * 70)
    
    if api_key:
        for name, subgraph_id in DECENTRALIZED_IDS.items():
            result = await test_decentralized(name, subgraph_id, api_key)
            status = result["status"]
            if status == "OK":
                print(f"  {name:30} OK  block={result.get('block')}")
                working.append(result)
            else:
                print(f"  {name:30} {status}")
    else:
        print("  GRAPH_API_KEY not set - skipping decentralized tests")
        print("  Get free API key at: https://thegraph.com/studio/apikeys/")
    
    print("\n" + "=" * 70)
    print(f"WORKING SUBGRAPHS: {len(working)}")
    print("=" * 70)
    
    for w in working:
        print(f"  {w['name']}: {w.get('url', 'decentralized')}")
    
    return working


if __name__ == "__main__":
    asyncio.run(main())
