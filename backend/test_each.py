import httpx

# Test each protocol separately
protocols = ['marinade', 'meme-dollar', 'merkl']

for proto in protocols:
    r = httpx.get(f'http://localhost:8000/api/pools?protocols={proto}&min_tvl=10000&limit=10')
    d = r.json()
    print(f"\n{proto.upper()}: {d['count']} pools")
    for p in d.get('combined', [])[:3]:
        print(f"  {p['project']} | {p['chain']} | TVL: ${p['tvl']:,.0f}")
