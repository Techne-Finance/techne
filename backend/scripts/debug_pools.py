"""Debug: Check available Aerodrome pools from multiple sources"""
import asyncio
import httpx

async def check_defillama():
    """Check DefiLlama pools"""
    print("=" * 60)
    print("DEFILLAMA AERODROME POOLS")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get("https://yields.llama.fi/pools")
        data = resp.json()["data"]
        
        # All Aerodrome on Base
        aero = [p for p in data if p.get("chain", "").lower() == "base" 
                and "aerodrome" in (p.get("project", "") or "").lower()]
        print(f"Total Aerodrome Base: {len(aero)}")
        
        # With TVL > 500k
        tvl_ok = [p for p in aero if (p.get("tvlUsd") or 0) >= 500000]
        print(f"TVL > $500k: {len(tvl_ok)}")
        
        # Dual-sided
        dual = [p for p in tvl_ok if any(s in p.get("symbol", "") for s in ["-", "/"])]
        print(f"Dual-sided LP: {len(dual)}")
        
        # APY buckets
        apy_50 = [p for p in dual if (p.get("apy") or 0) >= 50]
        apy_100 = [p for p in dual if (p.get("apy") or 0) >= 100]
        apy_200 = [p for p in dual if (p.get("apy") or 0) >= 200]
        print(f"APY > 50%:  {len(apy_50)}")
        print(f"APY > 100%: {len(apy_100)}")
        print(f"APY > 200%: {len(apy_200)}")
        
        print("\nTop 20 dual-sided by APY:")
        dual.sort(key=lambda x: x.get("apy", 0), reverse=True)
        for i, p in enumerate(dual[:20], 1):
            symbol = p["symbol"][:28]
            apy = p.get("apy", 0)
            tvl = p.get("tvlUsd", 0) / 1e6
            print(f"  {i:2}. {symbol:28} APY: {apy:>10.1f}%  TVL: ${tvl:.1f}M")
        
        return dual


async def check_aerodrome_api():
    """Check Aerodrome's own API"""
    print("\n" + "=" * 60)
    print("AERODROME NATIVE API (api.aerodrome.finance)")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            # Aerodrome has their own API
            resp = await client.get("https://api.aerodrome.finance/api/v1/pools")
            if resp.status_code == 200:
                pools = resp.json()
                print(f"Total pools from Aerodrome API: {len(pools)}")
                
                # Filter by TVL
                if pools and isinstance(pools, list):
                    tvl_ok = [p for p in pools if float(p.get("tvl", 0) or 0) >= 500000]
                    print(f"TVL > $500k: {len(tvl_ok)}")
                    
                    print("\nTop 10 by APR:")
                    pools.sort(key=lambda x: float(x.get("apr", 0) or 0), reverse=True)
                    for i, p in enumerate(pools[:10], 1):
                        symbol = p.get("symbol", "?")[:25]
                        apr = float(p.get("apr", 0) or 0)
                        tvl = float(p.get("tvl", 0) or 0) / 1e6
                        print(f"  {i:2}. {symbol:25} APR: {apr:>8.1f}%  TVL: ${tvl:.1f}M")
            else:
                print(f"API returned status: {resp.status_code}")
        except Exception as e:
            print(f"Aerodrome API error: {e}")


async def main():
    await check_defillama()
    await check_aerodrome_api()
    print("\n✅ Done")

if __name__ == "__main__":
    asyncio.run(main())
