import httpx
import json

BASE = "http://127.0.0.1:8000"

print("=" * 60)
print("🧪 Testing Scout Agent v2.0 - All Phases")
print("=" * 60)

# Phase 1: Risk Intelligence
print("\n📊 PHASE 1: Risk Intelligence")
print("-" * 40)
r = httpx.get(f"{BASE}/api/scout/risk?chain=base&limit=3")
if r.status_code == 200:
    data = r.json()
    print(f"✅ Risk endpoint working - {data.get('count', 0)} pools analyzed")
    for pool in data.get('pools', [])[:2]:
        print(f"   • {pool.get('project')}: {pool.get('overall_score')}/100 ({pool.get('risk_level')})")
else:
    print(f"❌ Risk endpoint failed: {r.status_code}")

# Phase 2: Yield Prediction
print("\n🔮 PHASE 2: Yield Prediction")
print("-" * 40)
r = httpx.get(f"{BASE}/api/scout/predict?chain=base&limit=3&days=7")
if r.status_code == 200:
    data = r.json()
    print(f"✅ Predict endpoint working - {data.get('count', 0)} predictions")
    for pred in data.get('predictions', [])[:2]:
        trend = pred.get('trend', {})
        print(f"   • {pred.get('project')}: {pred.get('current_apy')}% → {trend.get('icon', '')} {trend.get('direction', '')}")
else:
    print(f"❌ Predict endpoint failed: {r.status_code}")

# Phase 3: Conversational AI
print("\n💬 PHASE 3: Conversational AI")
print("-" * 40)
queries = [
    "Find USDC pools on Solana",
    "Is Aave safe?",
    "What is APY?"
]
for query in queries:
    r = httpx.post(f"{BASE}/api/scout/chat?query={query}")
    if r.status_code == 200:
        data = r.json()
        text = data.get('text', '')[:80] + "..." if len(data.get('text', '')) > 80 else data.get('text', '')
        print(f"✅ '{query}' → {data.get('intent')}")
        print(f"   {text}")
    else:
        print(f"❌ Chat failed for '{query}': {r.status_code}")

print("\n" + "=" * 60)
print("🎉 Scout Agent v2.0 Test Complete!")
print("=" * 60)
