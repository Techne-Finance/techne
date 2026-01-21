"""Check what DexScreener actually returns"""
import asyncio
import sys
sys.path.insert(0, '.')

from data_sources.dexscreener import dexscreener_client

async def main():
    pool = "0x56c11053159a24c0731b4b12356bc1f0578fb474"
    result = await dexscreener_client.get_token_volatility("base", pool)
    
    print("DexScreener raw response:")
    print(f"  token0: {result.get('token0')}")
    print(f"  token1: {result.get('token1')}")
    print(f"  pair_price_change_1h: {result.get('pair_price_change_1h')}")
    print(f"  pair_price_change_24h: {result.get('pair_price_change_24h')}")

if __name__ == "__main__":
    asyncio.run(main())
