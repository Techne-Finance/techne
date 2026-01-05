import httpx

# Test Risk Intelligence API
print("Testing /api/scout/risk endpoint...")

r = httpx.get('http://127.0.0.1:8000/api/scout/risk?chain=base&limit=5')
data = r.json()

print(f"Pools analyzed: {data.get('count', 0)}")
print()

for pool in data.get('pools', [])[:5]:
    print(f"🏊 {pool.get('project')} on {pool.get('chain')}")
    print(f"   Risk Score: {pool.get('overall_score')}/100 ({pool.get('risk_level')})")
    if pool.get('warnings'):
        for w in pool['warnings'][:2]:
            print(f"   ⚠️ {w}")
    print()
