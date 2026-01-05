import httpx

r = httpx.get('https://yields.llama.fi/pools')
pools = r.json()['data']

# Count pools per chain
chain_counts = {}
for p in pools:
    c = p.get('chain', 'unknown')
    chain_counts[c] = chain_counts.get(c, 0) + 1

# Sort and show top chains
sorted_chains = sorted(chain_counts.items(), key=lambda x: x[1], reverse=True)
print(f'Total pools: {len(pools)}')
print(f'\nTop 15 chains:')
for c, count in sorted_chains[:15]:
    print(f'  {c}: {count} pools')

# Specifically check Solana
solana_pools = [p for p in pools if 'solana' in p.get('chain', '').lower()]
print(f'\nSolana pools: {len(solana_pools)}')

# Check chain value for first Solana pool
if solana_pools:
    print(f'Example chain value: "{solana_pools[0]["chain"]}"')
