import httpx
import json

BASE = "http://127.0.0.1:8000"

print("=" * 60)
print("🧠 Testing Outcome-Based Memory Engine")
print("=" * 60)

# Test 1: Get initial stats
print("\n1️⃣ Memory Stats (initial):")
r = httpx.get(f"{BASE}/api/memory/stats", timeout=30)
if r.status_code == 200:
    stats = r.json()
    print(f"   Total memories: {stats['stats'].get('total', 0)}")
else:
    print(f"   ❌ Error: {r.status_code}")

# Test 2: Store a pool outcome (profitable)
print("\n2️⃣ Storing pool outcome (PROFITABLE):")
r = httpx.post(f"{BASE}/api/memory/pool-outcome", params={
    "pool_id": "test-aave-usdc",
    "project": "aave-v3",
    "chain": "ethereum",
    "predicted_apy": 5.0,
    "actual_apy": 5.2,
    "profit_loss": 150.0
}, timeout=30)
if r.status_code == 200:
    result = r.json()
    memory_id_1 = result.get("memory_id")
    print(f"   ✅ Stored! Memory ID: {memory_id_1[:12]}...")
    print(f"   Profitable: {result.get('profitable')}, Score: {result.get('score')}")
else:
    print(f"   ❌ Error: {r.status_code} - {r.text}")

# Test 3: Store another pool outcome (loss)
print("\n3️⃣ Storing pool outcome (LOSS):")
r = httpx.post(f"{BASE}/api/memory/pool-outcome", params={
    "pool_id": "test-risky-pool",
    "project": "unknown-dex",
    "chain": "base",
    "predicted_apy": 100.0,
    "actual_apy": 5.0,
    "profit_loss": -200.0
}, timeout=30)
if r.status_code == 200:
    result = r.json()
    memory_id_2 = result.get("memory_id")
    print(f"   ✅ Stored! Memory ID: {memory_id_2[:12]}...")
    print(f"   Profitable: {result.get('profitable')}, Score: {result.get('score')}")
else:
    print(f"   ❌ Error: {r.status_code}")

# Test 4: Set user preference
print("\n4️⃣ Setting user preference:")
r = httpx.post(f"{BASE}/api/memory/preferences", params={
    "key": "favorite_chain",
    "value": "ethereum"
}, timeout=30)
if r.status_code == 200:
    print(f"   ✅ Preference set: favorite_chain = ethereum")
else:
    print(f"   ❌ Error: {r.status_code}")

# Test 5: Get user preferences
print("\n5️⃣ Getting user preferences:")
r = httpx.get(f"{BASE}/api/memory/preferences", timeout=30)
if r.status_code == 200:
    prefs = r.json()
    print(f"   Preferences: {prefs.get('preferences', {})}")
else:
    print(f"   ❌ Error: {r.status_code}")

# Test 6: Get best protocols
print("\n6️⃣ Best protocols from memory:")
r = httpx.get(f"{BASE}/api/memory/protocols/best", timeout=30)
if r.status_code == 200:
    data = r.json()
    for p in data.get("protocols", []):
        print(f"   🏆 {p['protocol']}: score {p['average_score']}")
else:
    print(f"   ❌ Error: {r.status_code}")

# Test 7: Final stats
print("\n7️⃣ Memory Stats (after operations):")
r = httpx.get(f"{BASE}/api/memory/stats", timeout=30)
if r.status_code == 200:
    stats = r.json()
    print(f"   Total memories: {stats['stats'].get('total', 0)}")
    for tier, data in stats['stats'].get('tiers', {}).items():
        print(f"   - {tier}: {data['count']} (avg score: {data['avg_score']})")
else:
    print(f"   ❌ Error: {r.status_code}")

print("\n" + "=" * 60)
print("🎉 Memory Engine Test Complete!")
print("=" * 60)
