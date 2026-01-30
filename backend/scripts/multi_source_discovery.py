"""
Multi-Source Pool Discovery
Compare pool data from: The Graph, GeckoTerminal, DefiLlama
"""
import asyncio
import sys
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()


async def check_defillama():
    """DefiLlama pools"""
    import httpx
    print("=" * 60)
    print("1. DEFILLAMA - Aerodrome Base")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get("https://yields.llama.fi/pools")
        data = resp.json()["data"]
        
        aero = [p for p in data if p.get("chain", "").lower() == "base" 
                and "aerodrome" in (p.get("project", "") or "").lower()]
        
        tvl_500k = [p for p in aero if (p.get("tvlUsd") or 0) >= 500000]
        apy_100 = [p for p in tvl_500k if (p.get("apy") or 0) >= 100]
        
        print(f"Total Aerodrome: {len(aero)}")
        print(f"TVL > $500k: {len(tvl_500k)}")
        print(f"APY > 100%: {len(apy_100)}")
        
        return aero


async def check_thegraph():
    """The Graph subgraph"""
    print("\n" + "=" * 60)
    print("2. THE GRAPH - Aerodrome Subgraph")
    print("=" * 60)
    
    try:
        from data_sources.thegraph import graph_client
        
        # Get pools with TVL > 500k
        pools = await graph_client.get_pools_by_tokens(min_tvl=500000, limit=50)
        print(f"Pools found: {len(pools)}")
        
        if pools:
            print("\nTop 10 by TVL:")
            for i, p in enumerate(pools[:10], 1):
                name = p.get("name", "?")[:25]
                tvl = float(p.get("totalValueLockedUSD", 0)) / 1e6
                apr = p.get("apr", 0)
                print(f"  {i}. {name:25} TVL: ${tvl:.2f}M  APR: {apr:.1f}%")
        
        return pools
    except Exception as e:
        print(f"Error: {e}")
        return []


async def check_geckoterminal():
    """GeckoTerminal pools"""
    print("\n" + "=" * 60)
    print("3. GECKOTERMINAL - Aerodrome Base")
    print("=" * 60)
    
    try:
        from data_sources.geckoterminal import gecko_client
        import httpx
        
        # GeckoTerminal has DEX-specific endpoints
        async with httpx.AsyncClient(timeout=30) as client:
            # Aerodrome pools on Base
            url = "https://api.geckoterminal.com/api/v2/networks/base/dexes/aerodrome/pools"
            resp = await client.get(url, params={"page": 1})
            
            if resp.status_code == 200:
                data = resp.json()
                pools = data.get("data", [])
                print(f"Pools from GeckoTerminal: {len(pools)}")
                
                if pools:
                    print("\nTop 10 by volume:")
                    for i, p in enumerate(pools[:10], 1):
                        attrs = p.get("attributes", {})
                        name = attrs.get("name", "?")[:30]
                        tvl = float(attrs.get("reserve_in_usd", 0) or 0) / 1e6
                        volume = float(attrs.get("volume_usd", {}).get("h24", 0) or 0) / 1e3
                        print(f"  {i}. {name:30} TVL: ${tvl:.2f}M  Vol24h: ${volume:.0f}k")
                
                return pools
            else:
                print(f"API returned {resp.status_code}")
                return []
    except Exception as e:
        print(f"Error: {e}")
        return []


async def check_thegraph_discovery():
    """The Graph Protocol Discovery (new service)"""
    print("\n" + "=" * 60)
    print("4. THE GRAPH DISCOVERY - Protocol Pooller")
    print("=" * 60)
    
    try:
        from data_sources.thegraph_discovery import discovery
        
        # Get pools from discovery service
        pools = await discovery.get_aerodrome_pools(min_tvl=500000)
        print(f"Discovery pools: {len(pools)}")
        
        return pools
    except Exception as e:
        print(f"Error: {e}")
        return []


async def main():
    print("\n🔍 MULTI-SOURCE POOL DISCOVERY")
    print("Comparing: DefiLlama, The Graph, GeckoTerminal\n")
    
    defillama = await check_defillama()
    thegraph = await check_thegraph()
    gecko = await check_geckoterminal()
    discovery = await check_thegraph_discovery()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"DefiLlama:        {len(defillama)} Aerodrome pools")
    print(f"The Graph:        {len(thegraph)} pools (min $500k TVL)")
    print(f"GeckoTerminal:    {len(gecko)} pools (page 1)")
    print(f"Graph Discovery:  {len(discovery)} pools")
    
    # Check unique pools
    defillama_ids = {p.get("pool", "").lower() for p in defillama}
    gecko_addrs = {p.get("id", "").lower() for p in gecko}
    
    print(f"\nDefiLlama pool IDs: {len(defillama_ids)}")
    print(f"GeckoTerminal pool addresses: {len(gecko_addrs)}")


if __name__ == "__main__":
    asyncio.run(main())
