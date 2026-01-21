"""
Profile verify-rpc endpoint to find bottlenecks
"""
import httpx
import time

POOL = "0x85f1aa3a70fedd1c52705c15baed143e675cd626"  # NOCK/USDC

print("=" * 60)
print("   VERIFY-RPC TIMING TEST")
print("=" * 60)

start = time.time()
r = httpx.get(f'http://localhost:8080/api/scout/verify-rpc?pool_address={POOL}&chain=base', timeout=60)
elapsed = time.time() - start

print(f"\n⏱️  Total time: {elapsed:.2f}s")
print(f"Status: {r.status_code}")

if r.status_code == 200:
    data = r.json()
    pool = data.get('pool', data)
    print(f"\nPool: {pool.get('symbol')}")
    print(f"APY: {pool.get('apy', 'N/A')}%")
    
    # Check timings if available
    timings = data.get('timings', {})
    if timings:
        print("\nTimings:")
        for k, v in timings.items():
            print(f"  {k}: {v:.2f}s")
