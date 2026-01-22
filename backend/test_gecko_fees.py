"""Check if GeckoTerminal gives us fee_24h for cbETH/WETH"""
import asyncio
import sys
sys.path.insert(0, '.')

POOL = "0x47ca96ea59c13f72745928887f84c9f52c3d7348"
CHAIN = "base"

async def main():
    from data_sources.geckoterminal import gecko_client
    
    data = await gecko_client.get_pool_by_address(CHAIN, POOL)
    
    print(f"Pool: {data.get('name')}")
    print(f"TVL: ${data.get('tvl', 0):,.0f}")
    print(f"Volume 24h: {data.get('volume_24h_formatted')}")
    print(f"Fee 24h USD: ${data.get('fee_24h_usd', 0) or 0:,.2f}")
    print(f"Trading Fee Rate: {data.get('trading_fee')}%")
    print(f"APY Base (from fees): {data.get('apy_base', 0):.2f}%")

if __name__ == "__main__":
    asyncio.run(main())
