import httpx
import time

print("=== VERIFY-ANY PERFORMANCE TEST (Multicall APY) ===\n")

start = time.time()
r = httpx.get('http://localhost:8080/api/scout/verify-any?pool_address=0x6cdcb1c4a4d1c3c6d054b27ac5b77e89eafb971d&chain=base', timeout=60)
elapsed = time.time() - start

print(f"Time: {elapsed:.2f}s")
print(f"Status: {r.status_code}")

if r.status_code == 200:
    data = r.json()
    print(f"\nResults:")
    print(f"  Pool: {data.get('symbol', 'N/A')}")
    print(f"  APY: {data.get('apy')}%")
    print(f"  TVL: ${data.get('tvl', data.get('tvlUsd', 0)):,.0f}")
    print(f"  Source: {data.get('source', 'N/A')}")
    print(f"  Protocol: {data.get('project', data.get('protocol', 'N/A'))}")
else:
    print(f"Error: {r.text[:500]}")
