import httpx

# Test all Solana protocols
r = httpx.get('http://localhost:8000/api/pools?chain=solana&min_tvl=10000&protocols=kamino,marinade,raydium,orca&limit=20')
d = r.json()

print(f"Count: {d['count']}")
print(f"Protocols found:")
for p in d['combined'][:15]:
    print(f"  {p['project']} | {p['symbol']} | APY: {p['apy']:.2f}%")
