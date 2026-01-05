import httpx

r = httpx.get('https://yields.llama.fi/pools')
pools = r.json()['data']
solana = [p for p in pools if p.get('chain','').lower() == 'solana' and p.get('stablecoin') == True]
print(f'Total Solana stablecoin pools: {len(solana)}')
for p in solana[:15]:
    print(f"{p['project']} - {p['symbol']} - APY: {p['apy']:.2f}%")
