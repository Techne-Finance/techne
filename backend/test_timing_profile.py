"""Profile verify-rpc timing breakdown"""
import httpx
import time

POOL = "0x56c11053159a24c0731b4b12356bc1f0578fb474"

print("Verify-RPC Timing Profile\n" + "=" * 40)

start = time.time()
r = httpx.get(f'http://localhost:8080/api/scout/verify-rpc?pool_address={POOL}&chain=base', timeout=60)
total = time.time() - start

print(f"\nTotal time: {total:.2f}s")

if r.status_code == 200:
    data = r.json()
    pool = data.get('pool', {})
    
    # Check what data we got
    has_apy = pool.get('apy', 0) > 0
    has_security = bool(pool.get('security_result', {}).get('tokens'))
    has_volatility = pool.get('token0_volatility_24h') is not None
    has_ohlcv = pool.get('tvl_change_24h') is not None
    
    print(f"\nData received:")
    print(f"  APY: {pool.get('apy', 0):.2f}% ({'✓' if has_apy else '✗'})")
    print(f"  Security: {'✓' if has_security else '✗'}")  
    print(f"  Token Volatility: {'✓' if has_volatility else '✗'}")
    print(f"  OHLCV: {'✓' if has_ohlcv else '✗'}")
else:
    print(f"Error: {r.status_code}")
