"""Check what apy_source is in API response"""
import httpx

POOL = "0x56c11053159a24c0731b4b12356bc1f0578fb474"
r = httpx.get(f'http://localhost:8080/api/scout/verify-rpc?pool_address={POOL}&chain=base', timeout=60)

data = r.json()
pool = data.get('pool', {})

print(f"apy_source: {pool.get('apy_source')}")
print(f"apy_status: {pool.get('apy_status')}")
print(f"source: {pool.get('source')}")
print(f"dataSource: {pool.get('dataSource')}")
