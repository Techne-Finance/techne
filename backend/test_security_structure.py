"""
Check full API response structure for security data
"""
import httpx
import json

POOL = "0x56c11053159a24c0731b4b12356bc1f0578fb474"

r = httpx.get(f'http://localhost:8080/api/scout/verify-rpc?pool_address={POOL}&chain=base', timeout=60)

data = r.json()
pool = data.get('pool', {})

print("=" * 60)
print("API SECURITY RESPONSE STRUCTURE")
print("=" * 60)

# Check all security-related fields
print("\n1. pool.security:", pool.get('security', 'NOT PRESENT'))
print("2. pool.security_result:", pool.get('security_result', {}).get('status', 'NOT PRESENT'))

sec_result = pool.get('security_result', {})
if sec_result:
    tokens = sec_result.get('tokens', {})
    print(f"\n3. security_result.tokens keys: {list(tokens.keys())}")
    
    for addr, info in tokens.items():
        print(f"\n   Token {addr}:")
        print(f"     token_name: {info.get('token_name') if info else 'NO DATA'}")
        print(f"     is_honeypot: {info.get('is_honeypot') if info else 'N/A'}")

# Check token addresses
print(f"\n4. pool.token0: {pool.get('token0', 'NOT PRESENT')}")
print(f"5. pool.token1: {pool.get('token1', 'NOT PRESENT')}")

# Compare keys
token0 = pool.get('token0', '').lower()
token1 = pool.get('token1', '').lower()
tokens = sec_result.get('tokens', {})
token_keys = [k.lower() for k in tokens.keys()]

print(f"\n6. Token address match:")
print(f"   token0 in security_result: {token0 in token_keys}")
print(f"   token1 in security_result: {token1 in token_keys}")
