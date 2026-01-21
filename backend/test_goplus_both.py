"""
Test GoPlus directly with both tokens
"""
import asyncio
import sys
sys.path.insert(0, '.')

from api.security_module import security_checker

async def main():
    tokens = [
        "0xcd2f22236dd9dfe2356d7c543161d4d260fd9bcb",  # GHST
        "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"   # USDC
    ]
    
    print(f"Calling check_security with {len(tokens)} tokens...")
    
    result = await security_checker.check_security(tokens, "base")
    
    print(f"\nResult status: {result.get('status')}")
    print(f"Tokens in result: {list(result.get('tokens', {}).keys())}")
    
    for addr, info in result.get('tokens', {}).items():
        print(f"\nToken {addr[:15]}...:")
        if info:
            print(f"  token_name: {info.get('token_name')}")
        else:
            print(f"  NO DATA!")

if __name__ == "__main__":
    asyncio.run(main())
