"""Quick debug for enricher"""
import asyncio
import httpx
import os
from dotenv import load_dotenv
load_dotenv()

POOL = "0xcDAC0d6c6C59727a65F871236188350531885C43"

async def test():
    print("=" * 50)
    print("1. MORALIS HOLDER COUNT")
    print("=" * 50)
    moralis = os.getenv("MORALIS_API_KEY", "")
    print(f"Key exists: {bool(moralis)}")
    
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"https://deep-index.moralis.io/api/v2.2/erc20/{POOL}/stats",
            params={"chain": "base"},
            headers={"X-API-Key": moralis}
        )
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text[:400]}")
    
    print("\n" + "=" * 50)
    print("2. ALCHEMY RPC - POOL AGE")
    print("=" * 50)
    alchemy = os.getenv("ALCHEMY_RPC_URL", "")
    print(f"RPC exists: {bool(alchemy)}")
    
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            alchemy,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_getLogs",
                "params": [{
                    "address": POOL,
                    "topics": ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"],
                    "fromBlock": "0x0",
                    "toBlock": "0x200000"
                }]
            }
        )
        print(f"Status: {resp.status_code}")
        data = resp.json()
        logs = data.get("result", [])
        print(f"Logs found: {len(logs) if isinstance(logs, list) else 'error'}")
        if logs and isinstance(logs, list) and len(logs) > 0:
            print(f"First block: {logs[0].get('blockNumber')}")

asyncio.run(test())
