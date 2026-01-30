"""Test discovered subgraph endpoints"""
import asyncio
import httpx
import os

API_KEY = os.getenv("GRAPH_API_KEY", "98c42a618f916532f0d34bb07c084f28")

# Discovered from web search
ENDPOINTS_TO_TEST = {
    # Aerodrome - from search results
    "aerodrome-v2": "https://api.studio.thegraph.com/query/50258/aerodrome-v2/version/latest",
    "aerodrome-v1": "https://api.studio.thegraph.com/query/50258/aerodrome-v1/version/latest",  
    "messari-aerodrome": "https://api.thegraph.com/subgraphs/name/messari/aerodrome-base",
    
    # Moonwell
    "moonwell-base": "https://api.studio.thegraph.com/query/74584/moonwell-base/version/latest",
    "messari-moonwell": "https://api.thegraph.com/subgraphs/name/messari/moonwell-base",
    
    # Compound
    "compound-v3-base": "https://api.studio.thegraph.com/query/50419/compound-v3-base/version/latest",
    "messari-compound": "https://api.thegraph.com/subgraphs/name/messari/compound-v3-base",
}


async def test(name: str, url: str):
    query = '{ _meta { block { number } hasIndexingErrors deployment } }'
    
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        try:
            resp = await client.post(url, json={"query": query})
            if resp.status_code == 200:
                data = resp.json()
                if "errors" not in data:
                    meta = data.get("data", {}).get("_meta", {})
                    block = meta.get("block", {}).get("number")
                    deployment = meta.get("deployment", "")[:20]
                    return {"name": name, "url": url, "block": block, "deployment": deployment, "ok": True}
                else:
                    return {"name": name, "error": data["errors"][0]["message"][:60], "ok": False}
            return {"name": name, "error": f"HTTP {resp.status_code}", "ok": False}
        except Exception as e:
            return {"name": name, "error": str(e)[:40], "ok": False}


async def main():
    print("=" * 70)
    print("TESTING DISCOVERED SUBGRAPH ENDPOINTS")
    print("=" * 70)
    
    tasks = [test(name, url) for name, url in ENDPOINTS_TO_TEST.items()]
    results = await asyncio.gather(*tasks)
    
    working = [r for r in results if r.get("ok")]
    failed = [r for r in results if not r.get("ok")]
    
    print("\n✅ WORKING:")
    for r in working:
        print(f"  {r['name']:20} block={r['block']}")
        print(f"    URL: {r['url']}")
    
    print("\n❌ FAILED:")
    for r in failed:
        print(f"  {r['name']:20} {r.get('error', '')[:50]}")
    
    print("\n" + "=" * 70)
    print(f"WORKING: {len(working)}/{len(results)}")


if __name__ == "__main__":
    asyncio.run(main())
