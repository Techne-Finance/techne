import asyncio
from data_sources.geckoterminal import gecko_client

async def test():
    pool_addr = '0x4a79b0168296c0ef7b8f314973b82ad406a29f1b'
    data = await gecko_client.get_pool_by_address('base', pool_addr)
    if data:
        print(f"Pool: {data.get('name', '?')}")
        print(f"TVL: ${data.get('tvl', 0):,.2f}")
        print(f"Volume 24h: ${data.get('volume_24h', 0):,.2f}")
        print(f"APY: {data.get('apy', 0):.2f}%")
    else:
        print('Pool not found in GeckoTerminal')
    
asyncio.run(test())
