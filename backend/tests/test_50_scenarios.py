"""
50 Agent Simulation Scenarios — Full Real-World Testing
Covers: duration, APY rotation, vault_count, compound, emergency exit,
        stop-loss, take-profit, volatility guard, park, rebalance, gas limits
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from copy import deepcopy

# ═══════════════════════════════════════════════
# MOCK POOLS (21 realistic Base pools)
# ═══════════════════════════════════════════════
POOLS = [
    {"pool":"aave-usdc","symbol":"USDC","project":"aave-v3","chain":"Base","apy":8.2,"tvlUsd":45e6,"risk_score":"Low"},
    {"pool":"aave-weth","symbol":"WETH","project":"aave-v3","chain":"Base","apy":3.5,"tvlUsd":120e6,"risk_score":"Low"},
    {"pool":"morpho-usdc","symbol":"USDC","project":"morpho-blue","chain":"Base","apy":12.4,"tvlUsd":15e6,"risk_score":"Low"},
    {"pool":"morpho-weth","symbol":"WETH","project":"morpho-blue","chain":"Base","apy":6.8,"tvlUsd":8e6,"risk_score":"Medium"},
    {"pool":"moonwell-usdc","symbol":"USDC","project":"moonwell","chain":"Base","apy":9.1,"tvlUsd":22e6,"risk_score":"Low"},
    {"pool":"moonwell-weth","symbol":"WETH","project":"moonwell","chain":"Base","apy":5.2,"tvlUsd":10e6,"risk_score":"Medium"},
    {"pool":"comp-usdc","symbol":"USDC","project":"compound-v3","chain":"Base","apy":7.0,"tvlUsd":30e6,"risk_score":"Low"},
    {"pool":"beefy-usdc","symbol":"USDC","project":"beefy","chain":"Base","apy":15.3,"tvlUsd":2.8e6,"risk_score":"Medium"},
    {"pool":"extra-usdc","symbol":"USDC","project":"extrafi","chain":"Base","apy":55.0,"tvlUsd":800e3,"risk_score":"High"},
    {"pool":"seamless-usdc","symbol":"USDC","project":"seamless","chain":"Base","apy":18.2,"tvlUsd":5e6,"risk_score":"Medium"},
    {"pool":"aero-weth-usdc","symbol":"WETH/USDC","project":"aerodrome","chain":"Base","apy":62.5,"tvlUsd":12e6,"risk_score":"Medium"},
    {"pool":"aero-cbeth-weth","symbol":"cbETH/WETH","project":"aerodrome","chain":"Base","apy":35.0,"tvlUsd":8.5e6,"risk_score":"Medium"},
    {"pool":"aero-usdc-dai","symbol":"USDC/DAI","project":"aerodrome","chain":"Base","apy":22.0,"tvlUsd":15e6,"risk_score":"Low"},
    {"pool":"aero-weth-aero","symbol":"WETH-AERO","project":"aerodrome","chain":"Base","apy":180.0,"tvlUsd":3.2e6,"risk_score":"High"},
    {"pool":"uni-weth-usdc","symbol":"WETH-USDC","project":"uniswap-v3","chain":"Base","apy":75.0,"tvlUsd":25e6,"risk_score":"Medium"},
    {"pool":"uni-weth-usdt","symbol":"WETH-USDT","project":"uniswap-v3","chain":"Base","apy":68.0,"tvlUsd":18e6,"risk_score":"Medium"},
    {"pool":"velo-usdc-aero","symbol":"USDC/AERO","project":"velodrome-v2","chain":"Base","apy":120.0,"tvlUsd":1.5e6,"risk_score":"High"},
    {"pool":"curve-usdc-usdt","symbol":"USDC-USDT","project":"curve-dex","chain":"Base","apy":4.8,"tvlUsd":40e6,"risk_score":"Low"},
    {"pool":"tiny-lp","symbol":"WETH-USDC","project":"baseswap","chain":"Base","apy":250.0,"tvlUsd":90e3,"risk_score":"High"},
    {"pool":"eth-aave-usdc","symbol":"USDC","project":"aave-v3","chain":"Ethereum","apy":5.5,"tvlUsd":200e6,"risk_score":"Low"},
    {"pool":"arb-aave-usdc","symbol":"USDC","project":"aave-v3","chain":"Arbitrum","apy":6.0,"tvlUsd":80e6,"risk_score":"Low"},
]

# ═══════════════════════════════════════════════
# CORE SIMULATION ENGINE (mirrors strategy_executor.py exactly)
# ═══════════════════════════════════════════════

def find_matching_pools(agent, pools=POOLS):
    chain_map = {"base":"Base","ethereum":"Ethereum","arbitrum":"Arbitrum"}
    chain = chain_map.get(agent.get("chain","base").lower(), agent.get("chain","Base").title())
    filtered = []
    for p in pools:
        if p["chain"].lower() != chain.lower(): continue
        if (p.get("tvlUsd",0)) < agent.get("min_pool_tvl", agent.get("min_tvl",500000)): continue
        max_tvl = agent.get("max_pool_tvl")
        if max_tvl and p["tvlUsd"] > max_tvl: continue
        apy = p.get("apy",0)
        if apy < agent.get("min_apy",0): continue
        max_apy = agent.get("max_apy",1000)
        if max_apy < 500 and apy > max_apy: continue
        proj = (p.get("project") or "").lower()
        allowed = [x.lower() for x in agent.get("protocols",[])]
        if allowed and not any(x in proj for x in allowed): continue
        sym = (p.get("symbol") or "").upper()
        assets = [a.upper() for a in agent.get("preferred_assets",[])]
        if assets and not any(a in sym for a in assets): continue
        pt = agent.get("pool_type","all")
        is_lp = any(s in sym for s in ["-","/"])
        if pt == "single" and is_lp: continue
        if pt == "dual" and not is_lp: continue
        rs = p.get("risk_score","Medium")
        rl = agent.get("risk_level","medium")
        if rl == "low" and rs == "High": continue
        if agent.get("only_audited"):
            trusted = ['aave','compound','curve','uniswap','morpho','lido','aerodrome','velodrome','moonwell','beefy']
            if not any(t in proj for t in trusted): continue
        if agent.get("avoid_il"):
            safe = ["aave","compound","morpho","moonwell","beefy"]
            if not any(s in proj for s in safe): continue
        filtered.append(deepcopy(p))
    return filtered

def rank_and_select(pools, agent):
    vc = agent.get("vault_count",5)
    ma = agent.get("max_allocation",25)
    rl = agent.get("risk_level","medium")
    ts = agent.get("trading_style",{"low":"conservative","medium":"moderate","high":"aggressive"}.get(rl,"moderate"))
    for p in pools:
        s = min(p.get("apy",0),100)*0.4
        tvl = p.get("tvlUsd",0)
        if tvl > 10e6: s += 30
        elif tvl > 1e6: s += 20
        elif tvl > 100e3: s += 10
        if ts == "conservative":
            if p["apy"] > 100: s -= 20
            s = s*0.7 + (30 - min(p["apy"],30))
        elif ts == "aggressive": s *= 1.3
        p["_score"] = round(s,2)
        p["_allocation"] = min(ma, 100 // vc)
    pools.sort(key=lambda x: x.get("_score",0), reverse=True)
    return pools[:vc]

def check_duration_expired(agent, now=None):
    dur = agent.get("duration",30)
    if not dur or dur <= 0: return False
    dep = agent.get("deployed_at")
    if not dep: return False
    now = now or datetime.utcnow()
    if isinstance(dep, str): dep = datetime.fromisoformat(dep.replace('Z',''))
    return now >= dep + timedelta(days=dur)

def check_should_compound(agent, now=None):
    freq = agent.get("compound_frequency",7)
    last = agent.get("last_compound_time")
    if not last: return True
    now = now or datetime.utcnow()
    if isinstance(last, str): last = datetime.fromisoformat(last)
    return now >= last + timedelta(days=freq)

def check_emergency_exit(agent, current_value, initial_value):
    if not agent.get("emergency_exit",True): return False
    md = agent.get("max_drawdown",30)
    if initial_value <= 0: return False
    dd = ((initial_value - current_value) / initial_value) * 100
    return dd >= md

def check_gas_ok(agent, current_gwei):
    return current_gwei <= agent.get("max_gas_price",50)

def check_stop_loss(agent, position):
    sl = agent.get("stop_loss_percent", agent.get("pro_config",{}).get("stopLossPercent",15))
    invested = position.get("amount",0)
    current = position.get("current_value", invested)
    if invested <= 0: return False
    loss_pct = ((invested - current) / invested) * 100
    return loss_pct >= sl

def check_take_profit(agent, position):
    tp = agent.get("take_profit_amount", agent.get("pro_config",{}).get("takeProfitAmount"))
    if not tp: return False
    invested = position.get("amount",0)
    current = position.get("current_value", invested)
    profit = current - invested
    return profit >= tp

def check_volatility_guard(agent, volatility_index):
    if not agent.get("volatility_guard", agent.get("pro_config",{}).get("volatilityGuard",True)):
        return False
    return volatility_index > 80  # High volatility threshold

def check_apy_below_min_rotation(agent, pool_id, pool_avg_apy, hours_below):
    min_apy = agent.get("min_apy",5)
    check_hours = agent.get("apy_check_hours",24)
    if pool_avg_apy < min_apy and hours_below >= check_hours:
        return {"should_rotate": True, "reason": f"APY {pool_avg_apy:.1f}% < min {min_apy}% for {hours_below}h"}
    return {"should_rotate": False}

def check_rebalance_apy_drift(agent, old_apy, new_apy):
    threshold = agent.get("rebalance_threshold",5) / 100
    if old_apy > 0 and abs(new_apy - old_apy) / old_apy > threshold:
        return True
    return False

def check_park_conditions(pools_found, idle_balance, hours_no_pools=0, minutes_idle=0, has_allocations=False, is_locked=False):
    if is_locked: return {"should_park": False, "reason": "locked"}
    if idle_balance < 100: return {"should_park": False, "reason": "below_min"}
    if not has_allocations and not pools_found and hours_no_pools >= 1:
        return {"should_park": True, "trigger": "no_pools_timeout", "amount": idle_balance}
    if has_allocations and minutes_idle >= 15:
        return {"should_park": True, "trigger": "partial_idle_timeout", "amount": idle_balance}
    return {"should_park": False, "reason": "conditions_not_met"}


# ═══════════════════════════════════════════════
# 50 TEST SCENARIOS
# ═══════════════════════════════════════════════

def build_50_scenarios():
    S = []
    
    # ──── DURATION (1-8) ────
    for i, (dur, label) in enumerate([
        (0.04,"1H"), (1,"1D"), (7,"1W"), (30,"1M"),
        (90,"3M"), (180,"6M"), (365,"1Y"), (0,"Infinite")
    ], 1):
        expired_offset = dur + 0.1 if dur > 0 else 999
        S.append({
            "id": i, "category": "DURATION",
            "name": f"Duration {label} — {'expires' if dur > 0 else 'never expires'}",
            "agent": {
                "chain":"base","pool_type":"single","risk_level":"low","min_apy":5,"max_apy":50,
                "protocols":["aave","compound"],"preferred_assets":["USDC"],"min_pool_tvl":10e6,
                "vault_count":2,"max_allocation":50,"avoid_il":True,"only_audited":True,
                "duration": dur,
                "deployed_at": (datetime.utcnow() - timedelta(days=expired_offset)).isoformat(),
            },
            "test": "duration_expired",
            "expect_expired": dur > 0,
        })
    
    # ──── APY ROTATION (9-14) ────
    for i, (avg_apy, hours, min_apy, check_h, should) in enumerate([
        (3.0, 12, 5, 12, True),    # 9: APY 3% < min 5% for 12h (check=12h) → ROTATE
        (3.0, 11, 5, 12, False),   # 10: APY 3% < min 5% for 11h < check 12h → NO
        (6.0, 24, 5, 12, False),   # 11: APY 6% > min 5% → NO (above min)
        (2.0, 25, 5, 24, True),    # 12: APY 2% < 5% for 25h (check=24h) → ROTATE
        (4.9, 13, 5, 12, True),    # 13: APY 4.9% < 5% for 13h → ROTATE (edge case)
        (5.0, 100, 5, 12, False),  # 14: APY exactly 5% = min → NO (not below)
    ], 9):
        S.append({
            "id": i, "category": "APY_ROTATION",
            "name": f"APY {avg_apy}% for {hours}h (min={min_apy}%, check={check_h}h) → {'ROTATE' if should else 'KEEP'}",
            "agent": {"min_apy": min_apy, "apy_check_hours": check_h,
                      "chain":"base","pool_type":"single","risk_level":"medium",
                      "protocols":["aave","morpho"],"preferred_assets":["USDC"],"min_pool_tvl":1e6,
                      "vault_count":3,"max_allocation":33},
            "test": "apy_rotation",
            "pool_avg_apy": avg_apy, "hours_below": hours,
            "expect_rotate": should,
        })
    
    # ──── VAULT COUNT / POSITIONS (15-20) ────
    for i, vc in enumerate([1, 2, 3, 5, 8, 10], 15):
        S.append({
            "id": i, "category": "VAULT_COUNT",
            "name": f"vault_count={vc} — select exactly {vc} positions",
            "agent": {"chain":"base","pool_type":"all","risk_level":"medium","min_apy":3,"max_apy":500,
                      "protocols":["aave","morpho","moonwell","aerodrome","uniswap","compound","curve"],
                      "preferred_assets":["USDC","WETH"],"min_pool_tvl":1e6,
                      "vault_count": vc, "max_allocation": max(10, 100//vc),
                      "avoid_il":False,"only_audited":True},
            "test": "vault_count",
            "expect_count": vc,
        })
    
    # ──── COMPOUND FREQUENCY (21-25) ────
    for i, (freq, last_days_ago, should) in enumerate([
        (1, 2, True),     # 21: daily compound, last 2 days ago → YES
        (7, 3, False),    # 22: weekly compound, last 3 days ago → NO
        (7, 8, True),     # 23: weekly compound, last 8 days ago → YES
        (30, 15, False),  # 24: monthly compound, 15 days ago → NO
        (1, 0.5, False),  # 25: daily compound, 12h ago → NO
    ], 21):
        S.append({
            "id": i, "category": "COMPOUND",
            "name": f"Compound every {freq}d, last {last_days_ago}d ago → {'COMPOUND' if should else 'SKIP'}",
            "agent": {"compound_frequency": freq,
                      "last_compound_time": (datetime.utcnow() - timedelta(days=last_days_ago)).isoformat(),
                      "chain":"base","pool_type":"single","risk_level":"low","min_apy":5,
                      "protocols":["aave"],"preferred_assets":["USDC"],"min_pool_tvl":10e6,
                      "vault_count":2,"max_allocation":50},
            "test": "compound",
            "expect_compound": should,
        })
    
    # ──── EMERGENCY EXIT / MAX DRAWDOWN (26-30) ────
    for i, (invested, current, max_dd, exit_on, should) in enumerate([
        (10000, 6500, 30, True, True),   # 26: 35% loss > 30% max → EXIT
        (10000, 7500, 30, True, False),  # 27: 25% loss < 30% max → HOLD
        (10000, 5000, 50, True, True),   # 28: 50% loss = 50% max → EXIT (boundary)
        (10000, 8000, 10, True, True),   # 29: 20% loss > 10% strict → EXIT
        (10000, 6000, 30, False, False), # 30: exit disabled → HOLD despite 40% loss
    ], 26):
        S.append({
            "id": i, "category": "EMERGENCY_EXIT",
            "name": f"${invested}→${current} (dd={round((invested-current)/invested*100)}%) max_dd={max_dd}% exit={'ON' if exit_on else 'OFF'} → {'EXIT' if should else 'HOLD'}",
            "agent": {"max_drawdown": max_dd, "emergency_exit": exit_on,
                      "chain":"base","pool_type":"single","risk_level":"medium","min_apy":5,
                      "protocols":["aave"],"preferred_assets":["USDC"],"min_pool_tvl":10e6,
                      "vault_count":2,"max_allocation":50},
            "test": "emergency_exit",
            "invested": invested, "current": current,
            "expect_exit": should,
        })
    
    # ──── STOP-LOSS / TAKE-PROFIT (31-36) ────
    for i, (amt, cur, sl, tp, expect_sl, expect_tp) in enumerate([
        (1000, 800, 15, None, True, False),   # 31: 20% loss > 15% SL → STOP
        (1000, 900, 15, None, False, False),   # 32: 10% loss < 15% SL → HOLD
        (1000, 1500, 15, 400, False, True),    # 33: $500 profit > $400 TP → TAKE
        (1000, 1300, 15, 400, False, False),   # 34: $300 profit < $400 TP → HOLD
        (1000, 850, 15, 500, True, False),     # 35: SL triggers before TP
        (1000, 1000, 15, None, False, False),  # 36: Break-even, no triggers
    ], 31):
        S.append({
            "id": i, "category": "STOP_LOSS_TAKE_PROFIT",
            "name": f"${amt}→${cur} SL={sl}% TP={'$'+str(tp) if tp else 'OFF'} → {'SL' if expect_sl else ''}{'TP' if expect_tp else ''}{'HOLD' if not expect_sl and not expect_tp else ''}",
            "agent": {"stop_loss_percent": sl,
                      "take_profit_amount": tp,
                      "chain":"base","pool_type":"single","risk_level":"medium","min_apy":5,
                      "protocols":["aave"],"preferred_assets":["USDC"],"min_pool_tvl":10e6,
                      "vault_count":2,"max_allocation":50},
            "test": "sl_tp",
            "position": {"amount": amt, "current_value": cur},
            "expect_sl": expect_sl, "expect_tp": expect_tp,
        })
    
    # ──── VOLATILITY GUARD (37-39) ────
    for i, (vi, guard_on, should_pause) in enumerate([
        (90, True, True),    # 37: High vol + guard ON → PAUSE
        (50, True, False),   # 38: Normal vol + guard ON → OK
        (95, False, False),  # 39: High vol + guard OFF → OK (disabled)
    ], 37):
        S.append({
            "id": i, "category": "VOLATILITY_GUARD",
            "name": f"Vol={vi} guard={'ON' if guard_on else 'OFF'} → {'PAUSE' if should_pause else 'CONTINUE'}",
            "agent": {"volatility_guard": guard_on,
                      "chain":"base","pool_type":"single","risk_level":"medium","min_apy":5,
                      "protocols":["aave"],"preferred_assets":["USDC"],"min_pool_tvl":10e6,
                      "vault_count":2,"max_allocation":50},
            "test": "volatility",
            "volatility_index": vi,
            "expect_pause": should_pause,
        })
    
    # ──── PARK CONDITIONS (40-43) ────
    for i, (pools_found, idle, hrs_no_pools, mins_idle, has_alloc, locked, should) in enumerate([
        (False, 5000, 1.5, 0, False, False, True),   # 40: No pools for 1.5h → PARK
        (False, 5000, 0.5, 0, False, False, False),   # 41: No pools only 0.5h → WAIT
        (True, 3000, 0, 20, True, False, True),        # 42: Partial idle 20min → PARK
        (False, 5000, 2, 0, False, True, False),       # 43: Locked → NO PARK
    ], 40):
        S.append({
            "id": i, "category": "PARK",
            "name": f"pools={'Y' if pools_found else 'N'} idle=${idle} no_pool={hrs_no_pools}h idle_min={mins_idle} alloc={'Y' if has_alloc else 'N'} lock={'Y' if locked else 'N'} → {'PARK' if should else 'WAIT'}",
            "agent": {"chain":"base","pool_type":"single","risk_level":"low","min_apy":5,
                      "protocols":["aave"],"preferred_assets":["USDC"],"min_pool_tvl":10e6,
                      "vault_count":2,"max_allocation":50},
            "test": "park",
            "pools_found": pools_found, "idle_balance": idle,
            "hours_no_pools": hrs_no_pools, "minutes_idle": mins_idle,
            "has_allocations": has_alloc, "is_locked": locked,
            "expect_park": should,
        })
    
    # ──── REBALANCE / APY DRIFT (44-46) ────
    for i, (old_apy, new_apy, thresh, should) in enumerate([
        (50.0, 35.0, 5, True),    # 44: 30% drift > 5% threshold → REBALANCE
        (50.0, 48.0, 5, False),   # 45: 4% drift < 5% threshold → HOLD
        (10.0, 8.5, 10, True),    # 46: 15% drift > 10% threshold → REBALANCE
    ], 44):
        S.append({
            "id": i, "category": "REBALANCE",
            "name": f"APY {old_apy}%→{new_apy}% (drift={abs(new_apy-old_apy)/old_apy*100:.0f}%) thresh={thresh}% → {'REBAL' if should else 'HOLD'}",
            "agent": {"rebalance_threshold": thresh,
                      "chain":"base","pool_type":"single","risk_level":"medium","min_apy":5,
                      "protocols":["aave"],"preferred_assets":["USDC"],"min_pool_tvl":10e6,
                      "vault_count":2,"max_allocation":50},
            "test": "rebalance",
            "old_apy": old_apy, "new_apy": new_apy,
            "expect_rebalance": should,
        })
    
    # ──── GAS PRICE LIMITS (47-48) ────
    for i, (gas_gwei, max_gas, ok) in enumerate([
        (2.0, 50, True),    # 47: Base 2 gwei < 50 max → OK
        (55.0, 50, False),  # 48: 55 gwei > 50 max → SKIP
    ], 47):
        S.append({
            "id": i, "category": "GAS",
            "name": f"Gas {gas_gwei} gwei, max={max_gas} → {'OK' if ok else 'SKIP'}",
            "agent": {"max_gas_price": max_gas,
                      "chain":"base","pool_type":"single","risk_level":"low","min_apy":5,
                      "protocols":["aave"],"preferred_assets":["USDC"],"min_pool_tvl":10e6,
                      "vault_count":2,"max_allocation":50},
            "test": "gas",
            "current_gwei": gas_gwei,
            "expect_ok": ok,
        })
    
    # ──── EDGE CASES (49-50) ────
    S.append({
        "id": 49, "category": "EDGE",
        "name": "Ethereum chain — should find Ethereum pools only",
        "agent": {"chain":"ethereum","pool_type":"single","risk_level":"low","min_apy":3,"max_apy":100,
                  "protocols":["aave"],"preferred_assets":["USDC"],"min_pool_tvl":50e6,
                  "vault_count":2,"max_allocation":50,"avoid_il":True,"only_audited":True},
        "test": "chain_filter",
        "expect_chain": "Ethereum",
    })
    S.append({
        "id": 50, "category": "EDGE",
        "name": "Empty protocols list — should match ALL protocols",
        "agent": {"chain":"base","pool_type":"single","risk_level":"medium","min_apy":5,"max_apy":100,
                  "protocols":[],"preferred_assets":["USDC"],"min_pool_tvl":1e6,
                  "vault_count":5,"max_allocation":20,"avoid_il":False,"only_audited":False},
        "test": "empty_protocol_filter",
    })
    
    return S


# ═══════════════════════════════════════════════
# TEST RUNNER
# ═══════════════════════════════════════════════

def run_test(scenario):
    t = scenario["test"]
    a = scenario["agent"]
    result = {"passed": False, "detail": ""}
    
    if t == "duration_expired":
        expired = check_duration_expired(a)
        result["passed"] = expired == scenario["expect_expired"]
        result["detail"] = f"expired={expired} (expected {scenario['expect_expired']})"
    
    elif t == "apy_rotation":
        r = check_apy_below_min_rotation(a, "test-pool", scenario["pool_avg_apy"], scenario["hours_below"])
        result["passed"] = r["should_rotate"] == scenario["expect_rotate"]
        result["detail"] = f"rotate={r['should_rotate']} (expected {scenario['expect_rotate']})"
        if r.get("reason"): result["detail"] += f" | {r['reason']}"
    
    elif t == "vault_count":
        pools = find_matching_pools(a)
        selected = rank_and_select(pools, a)
        actual = len(selected)
        expected = min(scenario["expect_count"], len(pools))
        result["passed"] = actual == expected
        result["detail"] = f"selected={actual} (expected={expected}, available={len(pools)})"
        if selected:
            syms = [p["symbol"] for p in selected]
            result["detail"] += f" | pools: {', '.join(syms[:5])}"
    
    elif t == "compound":
        should = check_should_compound(a)
        result["passed"] = should == scenario["expect_compound"]
        result["detail"] = f"compound={should} (expected {scenario['expect_compound']})"
    
    elif t == "emergency_exit":
        should = check_emergency_exit(a, scenario["current"], scenario["invested"])
        result["passed"] = should == scenario["expect_exit"]
        dd = (scenario["invested"]-scenario["current"])/scenario["invested"]*100
        result["detail"] = f"exit={should} dd={dd:.0f}% (expected {scenario['expect_exit']})"
    
    elif t == "sl_tp":
        pos = scenario["position"]
        sl_hit = check_stop_loss(a, pos)
        tp_hit = check_take_profit(a, pos)
        result["passed"] = sl_hit == scenario["expect_sl"] and tp_hit == scenario["expect_tp"]
        result["detail"] = f"SL={sl_hit}(exp={scenario['expect_sl']}) TP={tp_hit}(exp={scenario['expect_tp']})"
    
    elif t == "volatility":
        paused = check_volatility_guard(a, scenario["volatility_index"])
        result["passed"] = paused == scenario["expect_pause"]
        result["detail"] = f"pause={paused} (expected {scenario['expect_pause']})"
    
    elif t == "park":
        r = check_park_conditions(
            scenario["pools_found"], scenario["idle_balance"],
            scenario["hours_no_pools"], scenario["minutes_idle"],
            scenario["has_allocations"], scenario["is_locked"])
        result["passed"] = r.get("should_park", False) == scenario["expect_park"]
        result["detail"] = f"park={r.get('should_park')} (expected {scenario['expect_park']}) trigger={r.get('trigger','none')}"
    
    elif t == "rebalance":
        should = check_rebalance_apy_drift(a, scenario["old_apy"], scenario["new_apy"])
        result["passed"] = should == scenario["expect_rebalance"]
        drift = abs(scenario["new_apy"]-scenario["old_apy"])/scenario["old_apy"]*100
        result["detail"] = f"rebal={should} drift={drift:.0f}% (expected {scenario['expect_rebalance']})"
    
    elif t == "gas":
        ok = check_gas_ok(a, scenario["current_gwei"])
        result["passed"] = ok == scenario["expect_ok"]
        result["detail"] = f"gas_ok={ok} (expected {scenario['expect_ok']})"
    
    elif t == "chain_filter":
        pools = find_matching_pools(a)
        all_correct = all(p["chain"] == scenario["expect_chain"] for p in pools)
        result["passed"] = len(pools) > 0 and all_correct
        result["detail"] = f"found={len(pools)} all_correct_chain={all_correct}"
    
    elif t == "empty_protocol_filter":
        pools = find_matching_pools(a)
        projs = set(p["project"] for p in pools)
        result["passed"] = len(projs) > 1  # Should match multiple protocols
        result["detail"] = f"found={len(pools)} protocols={projs}"
    
    return result


def main():
    scenarios = build_50_scenarios()
    
    print("=" * 90)
    print("  50 AGENT SIMULATION SCENARIOS - FULL REAL-WORLD TESTING")
    print("=" * 90)
    
    categories = {}
    passed = 0
    failed = 0
    
    for s in scenarios:
        cat = s["category"]
        if cat not in categories:
            categories[cat] = {"passed": 0, "failed": 0, "tests": []}
            print(f"\n{'=' * 90}")
            print(f"  CATEGORY: {cat}")
            print(f"{'=' * 90}")
        
        result = run_test(s)
        status = "PASS" if result["passed"] else "FAIL"
        icon = "[OK]" if result["passed"] else "[XX]"
        
        if result["passed"]:
            passed += 1
            categories[cat]["passed"] += 1
        else:
            failed += 1
            categories[cat]["failed"] += 1
        
        categories[cat]["tests"].append({"id": s["id"], "status": status})
        
        print(f"  {icon} #{s['id']:02d} {s['name']}")
        print(f"       -> {result['detail']}")
    
    # ── FINAL REPORT ──
    print(f"\n\n{'=' * 90}")
    print(f"  FINAL REPORT: {passed}/{len(scenarios)} PASSED | {failed} FAILED")
    print(f"{'=' * 90}")
    
    for cat, data in categories.items():
        cat_status = "[OK]" if data["failed"] == 0 else "[XX]"
        print(f"  {cat_status} {cat:30s} {data['passed']}/{data['passed']+data['failed']}")
    
    print(f"\n  {'[OK] ALL TESTS PASSED' if failed == 0 else f'[XX] {failed} TESTS FAILED'}")
    print(f"\n  Completed at {datetime.utcnow().isoformat()}")
    
    return passed, failed


if __name__ == "__main__":
    main()
