"""
Debug: Check if protocol is being detected correctly
"""
import asyncio
import sys
sys.path.insert(0, '.')

from api.smart_router import SmartRouter

async def main():
    router = SmartRouter()
    
    pool_address = "0x6cdcb1c4a4d1c3c6d054b27ac5b77e89eafb971d"
    chain = "base"
    
    print(f"Testing SmartRouter protocol detection...")
    print(f"Pool: {pool_address}")
    print(f"Chain: {chain}")
    
    # Detect protocol
    protocol = await router.detect_protocol(pool_address, chain)
    print(f"\nDetected Protocol: {protocol}")
    
    # Get adapter type
    from api.smart_router import PROTOCOL_ADAPTERS
    adapter_type = PROTOCOL_ADAPTERS.get(protocol, "universal")
    print(f"Adapter Type: {adapter_type}")
    
if __name__ == "__main__":
    asyncio.run(main())
