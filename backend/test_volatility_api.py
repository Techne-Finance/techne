"""Check volatility data in API response"""
import httpx

POOL = "0x56c11053159a24c0731b4b12356bc1f0578fb474"
r = httpx.get(f'http://localhost:8080/api/scout/verify-rpc?pool_address={POOL}&chain=base', timeout=60)

data = r.json()
pool = data.get('pool', {})

print("=" * 60)
print("VOLATILITY DATA IN API RESPONSE")
print("=" * 60)

# Per-token volatility
print(f"\ntoken0_volatility_24h: {pool.get('token0_volatility_24h')}")
print(f"token0_volatility_1h: {pool.get('token0_volatility_1h')}")
print(f"token1_volatility_24h: {pool.get('token1_volatility_24h')}")
print(f"token1_volatility_1h: {pool.get('token1_volatility_1h')}")

# LP/Pool volatility
print(f"\ntoken_volatility_24h: {pool.get('token_volatility_24h')}")
print(f"token_volatility_7d: {pool.get('token_volatility_7d')}")
print(f"pair_price_change_24h: {pool.get('pair_price_change_24h')}")
print(f"pair_price_change_1h: {pool.get('pair_price_change_1h')}")

# volatility_analysis object
print(f"\nvolatility_analysis: {pool.get('volatility_analysis')}")

# OHLCV data
print(f"\nohlcv_data present: {'ohlcv_data' in pool}")
