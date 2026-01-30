"""Find working subgraph IDs for Base chain"""
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GRAPH_API_KEY", "98c42a618f916532f0d34bb07c084f28")

# Try multiple possible subgraph IDs
SUBGRAPHS_TO_TEST = {
    # Aerodrome variations
    "aerodrome-1": "GwVkDp97M4gPhz8ovUTLQwzRZT1YFXMeCo66AHpWojak",
    "aerodrome-2": "8sX1LoEbQKJXadp3h4BZ4PwmcbAWBKRXbcY9wQMdcAjH",
    "aerodrome-slipstream": "DiZ1q46EKV1VbKVCGqWLLvNHnCYu5RpXKD5zMUU2YXgD",
    
    # Aave V3 Base variations
    "aave-v3-1": "GQFbb95cE6d8mV989mL5figjaGaKCQB3xqYrr1bRyXqF",
    "aave-v3-2": "8JLqrMvRpfaqb39a7N6qWvhZsJdZEAMULzjnrNBBLLSR",
    "aave-v3-base": "5JtLNnLPD5FLhAyH7BKMD6DWq8dq8nNNkGzYBMYXXSQw",
    
    # Uniswap V3 Base (this one works)
    "uniswap-v3": "43Hwfi3dJSoGpyas9VwNoDAv55yjgGrPCNzh76hKHKxd",
    
    # Moonwell
    "moonwell-1": "ExCF5jPbKxQ6Fzng8qXPrhCuZNxZ9v7wLZFSR9qmq",
    
    # Compound V3
    "compound-v3": "5nwMCHGwBgLb9F8dG1FdWg9D7YkXHv9hKxQJ7qHxcDXk",
}


async def test(name: str, subgraph_id: str):
    url = f"https://gateway.thegraph.com/api/{API_KEY}/subgraphs/id/{subgraph_id}"
    query = '{ _meta { block { number } } }'
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(url, json={"query": query})
            if resp.status_code == 200:
                data = resp.json()
                if "errors" not in data:
                    block = data.get("data", {}).get("_meta", {}).get("block", {}).get("number")
                    return {"name": name, "id": subgraph_id, "block": block, "ok": True}
                else:
                    return {"name": name, "error": data["errors"][0]["message"][:50], "ok": False}
            return {"name": name, "error": f"HTTP {resp.status_code}", "ok": False}
        except Exception as e:
            return {"name": name, "error": str(e)[:30], "ok": False}


async def main():
    print("=" * 70)
    print("SEARCHING FOR WORKING SUBGRAPH IDS")
    print("=" * 70)
    
    tasks = [test(name, sid) for name, sid in SUBGRAPHS_TO_TEST.items()]
    results = await asyncio.gather(*tasks)
    
    working = [r for r in results if r.get("ok")]
    failed = [r for r in results if not r.get("ok")]
    
    print("\n WORKING:")
    for r in working:
        print(f"  {r['name']:20} ID: {r['id']}")
        print(f"                      Block: {r['block']}")
    
    print("\n FAILED:")
    for r in failed:
        print(f"  {r['name']:20} {r.get('error', 'unknown')[:40]}")
    
    print("\n" + "=" * 70)
    print(f"WORKING: {len(working)}/{len(results)}")
    print("=" * 70)
    
    # Output for copy-paste
    if working:
        print("\nCopy these to pool_data_fetcher.py:")
        print("SUBGRAPH_IDS = {")
        for r in working:
            print(f'    "{r["name"].split("-")[0]}": "{r["id"]}",')
        print("}")


if __name__ == "__main__":
    asyncio.run(main())
