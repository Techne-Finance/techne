import httpx

# Test new protocols
r = httpx.get('http://localhost:8000/api/pools?protocols=marinade,meme-dollar,merkl&limit=20')
d = r.json()

print(f"Count: {d['count']}")
print(f"Protocols found:")
for p in d.get('combined', [])[:15]:
    print(f"  {p['project']} | {p['chain']} | APY: {p['apy']:.2f}%")
