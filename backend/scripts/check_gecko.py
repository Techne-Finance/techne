"""Check GeckoTerminal pools with pagination"""
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient(timeout=30) as c:
        all_pools = []
        for page in range(1, 11):  # 10 pages
            url = "https://api.geckoterminal.com/api/v2/networks/base/dexes/aerodrome-slipstream-2/pools"
            r = await c.get(url, params={"page": page})
            if r.status_code == 200:
                pools = r.json().get("data", [])
                all_pools.extend(pools)
                print(f"Page {page}: {len(pools)} pools")
                if len(pools) < 20:
                    break
            await asyncio.sleep(0.3)  # Rate limit
        
        print(f"\nTotal GeckoTerminal Aerodrome: {len(all_pools)}")
        
        # Filter by TVL
        big = [p for p in all_pools 
               if float(p.get("attributes", {}).get("reserve_in_usd", 0) or 0) >= 500000]
        print(f"TVL >= $500k: {len(big)}")
        
        print("\nTop 20 by TVL:")
        big.sort(key=lambda x: float(x.get("attributes", {}).get("reserve_in_usd", 0) or 0), reverse=True)
        for i, p in enumerate(big[:20], 1):
            a = p.get("attributes", {})
            name = a.get("name", "?")[:35]
            tvl = float(a.get("reserve_in_usd", 0) or 0) / 1e6
            vol = float(a.get("volume_usd", {}).get("h24", 0) or 0) / 1e3
            print(f"{i:2}. {name:35} TVL: ${tvl:.2f}M  Vol24h: ${vol:.0f}k")

asyncio.run(main())
