import httpx

r = httpx.get('https://yields.llama.fi/pools')
pools = r.json()['data']

# Find protocols
marinade = [p for p in pools if 'marinade' in p.get('project','').lower()]
meme = [p for p in pools if 'meme' in p.get('project','').lower()]
merkl = [p for p in pools if 'merkl' in p.get('project','').lower()]

print(f'Marinade: {len(marinade)} pools')
for p in marinade[:3]:
    print(f"  {p['project']} | {p['chain']} | TVL: ${p.get('tvlUsd', 0):,.0f}")

print(f'\nMemeDollar/Meme: {len(meme)} pools')
for p in meme[:5]:
    print(f"  {p['project']} | {p['chain']} | TVL: ${p.get('tvlUsd', 0):,.0f}")

print(f'\nMerkl: {len(merkl)} pools')
for p in merkl[:5]:
    print(f"  {p['project']} | {p['chain']} | TVL: ${p.get('tvlUsd', 0):,.0f}")
