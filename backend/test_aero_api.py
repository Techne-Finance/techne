import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get('https://api.aerodrome.finance/pools')
        print(f"Status: {r.status_code}")
        data = r.json()
        print(f"Pools: {len(data)}")
        if data:
            print(f"Sample: {data[0].get('symbol', 'N/A')}")

asyncio.run(test())
