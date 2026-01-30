"""Test The Graph Decentralized Network with API key"""
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GRAPH_API_KEY")

# Known working subgraph IDs for Base chain (Decentralized Network)
SUBGRAPHS = {
    # Aerodrome Finance - Base
    "aerodrome": "GwVkDp97M4gPhz8ovUTLQwzRZT1YFXMeCo66AHpWojak",
    
    # Aave V3 - Base  
    "aave-v3": "GQFbb95cE6d8mV989mL5figjaGaKCQB3xqYrr1bRyXqF",
    
    # Uniswap V3 - Base
    "uniswap-v3": "43Hwfi3dJSoGpyas9VwNoDAv55yjgGrPCNzh76hKHKxd",
}


async def test_subgraph(name: str, subgraph_id: str):
    """Test a subgraph on Decentralized Network"""
    url = f"https://gateway.thegraph.com/api/{API_KEY}/subgraphs/id/{subgraph_id}"
    query = """
    {
        _meta {
            block { number timestamp }
            deployment
            hasIndexingErrors
        }
    }
    """
    
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(url, json={"query": query})
            print(f"\n{name}:")
            print(f"  Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                if "errors" in data:
                    error = data["errors"][0]["message"]
                    print(f"  ERROR: {error[:100]}")
                    return False
                else:
                    meta = data.get("data", {}).get("_meta", {})
                    block = meta.get("block", {})
                    print(f"  Block: {block.get('number')}")
                    print(f"  Timestamp: {block.get('timestamp')}")
                    print(f"  Deployment: {meta.get('deployment', 'N/A')[:30]}...")
                    print(f"  Indexing Errors: {meta.get('hasIndexingErrors')}")
                    return True
            else:
                print(f"  Response: {resp.text[:200]}")
                return False
        except Exception as e:
            print(f"  Exception: {e}")
            return False


async def main():
    print("=" * 70)
    print("THE GRAPH DECENTRALIZED NETWORK TEST")
    print("=" * 70)
    print(f"API Key: {API_KEY[:8]}..." if API_KEY else "API Key: NOT SET!")
    
    if not API_KEY:
        print("\nERROR: GRAPH_API_KEY not found in environment!")
        return
    
    working = 0
    for name, subgraph_id in SUBGRAPHS.items():
        if await test_subgraph(name, subgraph_id):
            working += 1
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {working}/{len(SUBGRAPHS)} working")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
