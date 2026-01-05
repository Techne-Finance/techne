# AGENTS.md - Techne Finance Agent Documentation

> **"Forms are dead."** - Use natural language to interact with agents.

## Overview

Techne Finance uses **19 autonomous AI agents** to power yield optimization. This document provides instructions for agents and developers on how to work within the system.

---

## Agent Roster

| Agent | Role | Primary Tools |
|-------|------|---------------|
| **Scout** | Discover yield opportunities | DefiLlama, GeckoTerminal |
| **Guardian** | Monitor & protect portfolio | Price feeds, TVL alerts |
| **Engineer** | Execute transactions | Web3, wallet APIs |
| **Appraiser** | Value pools & strategies | Historical data, ML |
| **Arbitrageur** | Find arbitrage opportunities | DEX aggregators |
| **Merchant** | Execute trades | 1inch, Jupiter |
| **Concierge** | User onboarding | Chat, tutorials |
| **Historian** | Track performance | Time-series DB |
| **Sentinel** | Security monitoring | Contract analysis |
| **Memory** | Learn from outcomes | SQLite, patterns |
| **Observability** | Trace agent actions | Metrics, spans |

---

## Natural Language Commands

### Finding Yields
```
"Find safe stablecoin yields above 10%"
→ Scout filters: asset_type=stablecoin, min_apy=10, risk_level=low

"Show me Aave pools on Ethereum"
→ Scout filters: project=aave, chain=ethereum

"What's the best yield for USDC right now?"
→ Scout: searches USDC pools, sorts by APY, returns top 5
```

### Risk Assessment
```
"Is this pool safe?"
→ Guardian: runs risk_intelligence analysis

"What's the risk of [protocol]?"
→ Guardian: checks audits, TVL stability, protocol age
```

### Executing Strategies
```
"Deposit 100 USDC into the best Aave pool"
→ Engineer: finds pool, prepares tx, requests approval

"Withdraw everything from risky pools"
→ Engineer: identifies high-risk positions, prepares exits
```

---

## Code Conventions

### API Responses
Always return structured JSON:
```python
{
    "success": True,
    "data": {...},
    "error": None
}
```

### Error Handling
```python
try:
    result = await agent.execute()
    return {"success": True, "data": result}
except Exception as e:
    observability.log_error(trace_id, str(e))
    return {"success": False, "error": str(e)}
```

### Tracing
Use decorators for automatic tracing:
```python
from agents.observability_engine import traced

@traced("scout", "find_pools")
async def find_pools(filters):
    # Agent logic here
    pass
```

### Memory Integration
Record outcomes for learning:
```python
from agents.memory_engine import memory_engine

# After successful operation
await memory_engine.store_pool_outcome(
    pool_id=pool.id,
    project=pool.project,
    predicted_apy=predicted,
    actual_apy=actual,
    profit_loss=profit
)
```

---

## Prompt Templates

### Pool Search
```
You are Scout Agent for Techne Finance.
User request: {user_input}

Extract the following filters:
- chain: (ethereum, solana, base, all)
- asset_type: (stablecoin, eth, sol, all)
- min_apy: (number or null)
- max_risk: (low, medium, high, critical, all)
- protocol: (specific protocol name or null)

Respond with JSON only.
```

### Risk Assessment
```
You are Guardian Agent analyzing pool risk.
Pool data: {pool_data}

Evaluate:
1. Protocol reputation (audits, age, TVL)
2. APY sustainability (is it too high?)
3. Smart contract risk
4. Liquidity depth

Provide risk_score (0-100) and risk_level (Low/Medium/High/Critical).
```

---

## Rules for Agents

1. **Never hallucinate data** - Only use real API responses
2. **Always trace operations** - Use observability decorators
3. **Record outcomes** - Feed the memory engine
4. **Fail gracefully** - Return structured errors
5. **Be conservative** - When in doubt, recommend lower risk
6. **Explain decisions** - Users should understand recommendations

---

## Adding New Agents

1. Create `backend/agents/new_agent.py`
2. Implement async methods with tracing
3. Add router in `backend/api/`
4. Register in `main.py`
5. Update this AGENTS.md

---

## Quick Reference

```bash
# API Endpoints
GET  /api/scout/chat          # Natural language interface
GET  /api/pools               # Pool discovery
GET  /api/scout/risk/{id}     # Risk analysis
GET  /api/memory/preferences  # User preferences
GET  /api/observability/dashboard  # Agent metrics
```

---

*Last updated: 2026-01-01*
