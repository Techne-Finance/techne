"""
Check if SmartRouter returns security data for GHST/USDC pool
"""
import asyncio
import sys
sys.path.insert(0, '.')

import logging
logging.basicConfig(level=logging.WARNING)

from api.smart_router import SmartRouter

GHST_USDC_POOL = "0x56c11053159a24c0731b4b12356bc1f0578fb474"

async def main():
    router = SmartRouter()
    
    print("=" * 60)
    print("   SMARTROUTER SECURITY DATA CHECK")
    print("=" * 60)
    
    result = await router.smart_route_pool_check(GHST_USDC_POOL, "base")
    
    pool = result.get("pool", {})
    
    print(f"\nPool: {pool.get('symbol')}")
    print(f"\n📊 Security Fields:")
    print(f"  security_status: {pool.get('security_status')}")
    print(f"  security_penalty: {pool.get('security_penalty')}")
    print(f"  security_risks: {pool.get('security_risks')}")
    print(f"  security_result: {pool.get('security_result', {}).get('status')}")
    
    # Check token details
    security_result = pool.get('security_result', {})
    if security_result:
        tokens = security_result.get('tokens', {})
        print(f"\n🔐 Token Security Details:")
        for addr, data in tokens.items():
            print(f"\n  Token {addr[:10]}...:")
            if data:
                print(f"    name: {data.get('token_name')}")
                print(f"    is_honeypot: {data.get('is_honeypot')}")
                print(f"    risks: {data.get('risks', [])}")
            else:
                print(f"    No data!")

if __name__ == "__main__":
    asyncio.run(main())
