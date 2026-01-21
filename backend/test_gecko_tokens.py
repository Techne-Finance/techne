"""Quick check what GeckoTerminal returns"""
import asyncio
import sys
sys.path.insert(0, '.')

from data_sources.geckoterminal import gecko_client

async def main():
    data = await gecko_client.get_pool_by_address("base", "0x56c11053159a24c0731b4b12356bc1f0578fb474")
    
    print("GeckoTerminal pool data keys:", list(data.keys()) if data else "None")
    print(f"\ntoken0: {data.get('token0', 'NOT PRESENT')}")
    print(f"token1: {data.get('token1', 'NOT PRESENT')}")

if __name__ == "__main__":
    asyncio.run(main())
