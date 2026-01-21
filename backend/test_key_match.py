"""
Exact key comparison for security tokens
"""
import httpx

POOL = "0x56c11053159a24c0731b4b12356bc1f0578fb474"
r = httpx.get(f'http://localhost:8080/api/scout/verify-rpc?pool_address={POOL}&chain=base', timeout=60)

data = r.json()
pool = data.get('pool', {})

token0 = pool.get('token0', '')
token1 = pool.get('token1', '')
tokens = pool.get('security_result', {}).get('tokens', {})

print(f"pool.token0: '{token0}'")
print(f"pool.token1: '{token1}'")
print(f"\nsecurity_result.tokens keys:")
for k in tokens.keys():
    print(f"  '{k}'")

print(f"\nExact match token0: {token0 in tokens}")
print(f"Exact match token0.lower(): {token0.lower() in tokens}")
print(f"Exact match token1: {token1 in tokens}")
print(f"Exact match token1.lower(): {token1.lower() in tokens}")
