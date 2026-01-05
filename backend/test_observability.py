# -*- coding: utf-8 -*-
import httpx
import time

BASE = "http://127.0.0.1:8000"

print("=" * 60)
print("Testing Agent Observability System")
print("=" * 60)

# Test 1: Health check
print("\n1. Health Check:")
r = httpx.get(f"{BASE}/api/observability/health", timeout=30)
if r.status_code == 200:
    data = r.json()
    print(f"   Status: {data.get('status')}")
else:
    print(f"   Error: {r.status_code}")

# Test 2: Start a trace
print("\n2. Starting Trace (Scout Agent):")
r = httpx.post(f"{BASE}/api/observability/traces/start", params={
    "agent": "scout",
    "operation": "find_pools"
}, timeout=30)
if r.status_code == 200:
    trace_id = r.json().get("trace_id")
    print(f"   OK Trace started: {trace_id}")
else:
    print(f"   Error: {r.status_code}")
    trace_id = None

# Test 3: Log an event
print("\n3. Logging Event:")
r = httpx.post(f"{BASE}/api/observability/events", params={
    "agent": "scout",
    "event_type": "pool_discovered",
    "message": "Found 50 stablecoin pools on Ethereum",
    "trace_id": trace_id
}, timeout=30)
if r.status_code == 200:
    print(f"   OK Event logged")
else:
    print(f"   Error: {r.status_code}")

# Test 4: Start and end a span
print("\n4. Span lifecycle:")
r = httpx.post(f"{BASE}/api/observability/spans/start", params={
    "trace_id": trace_id,
    "agent": "scout",
    "operation": "fetch_defillama"
}, timeout=30)
if r.status_code == 200:
    span_id = r.json().get("span_id")
    print(f"   OK Span started: {span_id}")
    time.sleep(0.1)
    r = httpx.post(f"{BASE}/api/observability/spans/{span_id}/end", params={"success": True}, timeout=30)
    if r.status_code == 200:
        print(f"   OK Span ended")
else:
    print(f"   Error: {r.status_code}")

# Test 5: End the trace
print("\n5. Ending Trace:")
if trace_id:
    r = httpx.post(f"{BASE}/api/observability/traces/{trace_id}/end", params={"success": True}, timeout=30)
    print(f"   OK Trace ended" if r.status_code == 200 else f"   Error: {r.status_code}")

# Test 6: Get dashboard
print("\n6. Dashboard Data:")
r = httpx.get(f"{BASE}/api/observability/dashboard", timeout=30)
if r.status_code == 200:
    data = r.json()
    print(f"   Agents: {len(data.get('agents', []))}")
    print(f"   Recent traces: {len(data.get('recent_traces', []))}")
    for agent in data.get('agents', []):
        print(f"   - {agent['agent']}: {agent['success']} success, {agent['errors']} errors ({agent['success_rate']}%)")
else:
    print(f"   Error: {r.status_code}")

# Test 7: Agent metrics
print("\n7. Scout Agent Metrics:")
r = httpx.get(f"{BASE}/api/observability/agents/scout/metrics", timeout=30)
if r.status_code == 200:
    data = r.json()
    print(f"   Total ops: {data.get('total_operations')}")
    print(f"   Success rate: {data.get('success_rate')}%")
    print(f"   Avg latency: {data.get('avg_latency_ms'):.1f}ms")
else:
    print(f"   Error: {r.status_code}")

print("\n" + "=" * 60)
print("Observability System Test Complete!")
print("=" * 60)
