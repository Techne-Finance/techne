"""
Direct test of multicall APY + SmartRouter fetch_apy
"""
import asyncio
import time
import sys
sys.path.insert(0, '.')

# Enable logging
import logging
logging.basicConfig(level=logging.INFO)

from data_sources.aerodrome import aerodrome_client

async def main():
    pool_address = "0x6cdcb1c4a4d1c3c6d054b27ac5b77e89eafb971d"
    pool_type_hint = "v2"
    
    print("=" * 60)
    print("   MULTICALL APY DIRECT TEST")
    print("=" * 60)
    
    start = time.time()
    result = await aerodrome_client.get_real_time_apy_multicall(pool_address, pool_type_hint)
    elapsed = time.time() - start
    
    print(f"\nTime: {elapsed:.2f}s")
    print(f"\nResult:")
    for k, v in result.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    asyncio.run(main())
