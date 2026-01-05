import httpx
from collections import Counter

# Test with MORE pools - single sided (lending)
print("Testing single-sided lending pools...")
r = httpx.get('http://127.0.0.1:8000/api/pools?chain=all&asset_type=stablecoin&pool_type=single&limit=100', timeout=120)
data = r.json()

pools = data.get('combined', [])
print(f"Total single-sided pools: {len(pools)}")

# Count by risk level
levels = Counter(p.get('risk_level', 'Unknown') for p in pools)
print("\nRisk Level Distribution:")
for level in ['Low', 'Medium', 'High', 'Critical']:
    count = levels.get(level, 0)
    pct = count / len(pools) * 100 if pools else 0
    print(f"  {level:8s}: {count:3d} ({pct:.1f}%)")

# Show scores distribution
scores = [p.get('risk_score', 0) for p in pools]
if scores:
    print(f"\nScore stats: min={min(scores):.1f}, max={max(scores):.1f}, avg={sum(scores)/len(scores):.1f}")

# Show Low risk pools
print("\n=== LOW RISK POOLS (first 10) ===")
low_pools = [p for p in pools if p.get('risk_level') == 'Low']
for p in low_pools[:10]:
    print(f"  {p.get('project'):20s} Score:{p.get('risk_score'):5.1f} APY:{p.get('apy', 0):6.1f}% TVL:${p.get('tvl', 0)/1e6:.1f}M")
