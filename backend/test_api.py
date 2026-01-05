import httpx
import json

# Test the actual API endpoint
r = httpx.get('http://localhost:8000/api/pools?chain=solana&min_tvl=10000&limit=50')
data = r.json()

print(f"Success: {data.get('success')}")
print(f"Count: {data.get('count')}")
print(f"Chains: {data.get('chains')}")
print(f"Asset type: {data.get('asset_type')}")
print(f"Sources: {data.get('sources')}")

pools = data.get('combined', [])
print(f"\nPools returned: {len(pools)}")

# Show first 10 pools
for p in pools[:10]:
    print(f"  {p.get('project', '???')} | {p.get('symbol', '???')} | TVL: {p.get('tvl', 0):,.0f}")

# Check for kamino specifically
kamino_pools = [p for p in pools if 'kamino' in (p.get('project', '') or '').lower()]
print(f"\nKamino pools in response: {len(kamino_pools)}")
