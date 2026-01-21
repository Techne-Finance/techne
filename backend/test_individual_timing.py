"""Profile EACH parallel call separately to find bottleneck"""
import asyncio
import time
import sys
sys.path.insert(0, '.')

POOL = "0x56c11053159a24c0731b4b12356bc1f0578fb474"
CHAIN = "base"

async def main():
    print("Individual Call Timing\n" + "=" * 40)
    
    # GeckoTerminal
    from data_sources.geckoterminal import gecko_client
    start = time.time()
    await gecko_client.get_pool_by_address(CHAIN, POOL)
    print(f"1. GeckoTerminal pool:  {time.time() - start:.2f}s")
    
    # GeckoTerminal OHLCV
    start = time.time()
    await gecko_client.get_pool_ohlcv(CHAIN, POOL, "day", 7)
    print(f"2. GeckoTerminal OHLCV: {time.time() - start:.2f}s")
    
    # DexScreener
    from data_sources.dexscreener import dexscreener_client
    start = time.time()
    await dexscreener_client.get_token_volatility(CHAIN, POOL)
    print(f"3. DexScreener:         {time.time() - start:.2f}s")
    
    # GoPlus Security
    from api.security_module import security_checker
    tokens = ["0xcd2f22236dd9dfe2356d7c543161d4d260fd9bcb", "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"]
    start = time.time()
    await security_checker.check_security(tokens, CHAIN)
    print(f"4. GoPlus Security:     {time.time() - start:.2f}s")
    
    # Aerodrome Multicall
    from data_sources.aerodrome import aerodrome_client
    start = time.time()
    await aerodrome_client.get_real_time_apy_multicall(POOL, "cl")
    print(f"5. Aerodrome Multicall: {time.time() - start:.2f}s")
    
    print("\n" + "=" * 40)
    print("Total verify = max of above (parallel)")

if __name__ == "__main__":
    asyncio.run(main())
