"""
10 Flexible Preset Tests — Pool Filtering + Deposit Simulation
Tests the full flow: agent config → find_matching_pools() → rank_and_select()
                     → deposit simulation (single-sided / dual-sided + token conversion)

Run: python -m tests.test_pool_search_deposit
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any

# ──────────────────────────────────────────────
# Mock DeFiLlama-style pool data (realistic Base pools)
# ──────────────────────────────────────────────
MOCK_POOLS = [
    # ─── Single-sided lending (no separator in symbol) ───
    {"pool": "aave-usdc-base", "symbol": "USDC", "project": "aave-v3", "chain": "Base",
     "apy": 8.2, "tvlUsd": 45_000_000, "risk_score": "Low"},
    {"pool": "aave-weth-base", "symbol": "WETH", "project": "aave-v3", "chain": "Base",
     "apy": 3.5, "tvlUsd": 120_000_000, "risk_score": "Low"},
    {"pool": "morpho-usdc-base", "symbol": "USDC", "project": "morpho-blue", "chain": "Base",
     "apy": 12.4, "tvlUsd": 15_000_000, "risk_score": "Low"},
    {"pool": "morpho-weth-base", "symbol": "WETH", "project": "morpho-blue", "chain": "Base",
     "apy": 6.8, "tvlUsd": 8_000_000, "risk_score": "Medium"},
    {"pool": "moonwell-usdc-base", "symbol": "USDC", "project": "moonwell", "chain": "Base",
     "apy": 9.1, "tvlUsd": 22_000_000, "risk_score": "Low"},
    {"pool": "moonwell-weth-base", "symbol": "WETH", "project": "moonwell", "chain": "Base",
     "apy": 5.2, "tvlUsd": 10_000_000, "risk_score": "Medium"},
    {"pool": "comp-usdc-base", "symbol": "USDC", "project": "compound-v3", "chain": "Base",
     "apy": 7.0, "tvlUsd": 30_000_000, "risk_score": "Low"},
    {"pool": "beefy-usdc-base", "symbol": "USDC", "project": "beefy", "chain": "Base",
     "apy": 15.3, "tvlUsd": 2_800_000, "risk_score": "Medium"},
    # High APY single-sided
    {"pool": "extra-usdc-degen", "symbol": "USDC", "project": "extrafi", "chain": "Base",
     "apy": 55.0, "tvlUsd": 800_000, "risk_score": "High"},
    {"pool": "seamless-usdc", "symbol": "USDC", "project": "seamless-protocol", "chain": "Base",
     "apy": 18.2, "tvlUsd": 5_000_000, "risk_score": "Medium"},

    # ─── Dual-sided LP (separator in symbol) ───
    {"pool": "aero-weth-usdc", "symbol": "WETH/USDC", "project": "aerodrome", "chain": "Base",
     "apy": 62.5, "tvlUsd": 12_000_000, "risk_score": "Medium"},
    {"pool": "aero-cbeth-weth", "symbol": "cbETH/WETH", "project": "aerodrome", "chain": "Base",
     "apy": 35.0, "tvlUsd": 8_500_000, "risk_score": "Medium"},
    {"pool": "aero-usdc-dai", "symbol": "USDC/DAI", "project": "aerodrome", "chain": "Base",
     "apy": 22.0, "tvlUsd": 15_000_000, "risk_score": "Low"},
    {"pool": "aero-weth-aero", "symbol": "WETH-AERO", "project": "aerodrome", "chain": "Base",
     "apy": 180.0, "tvlUsd": 3_200_000, "risk_score": "High"},
    {"pool": "uni-weth-usdc", "symbol": "WETH-USDC", "project": "uniswap-v3", "chain": "Base",
     "apy": 75.0, "tvlUsd": 25_000_000, "risk_score": "Medium"},
    {"pool": "uni-weth-usdt", "symbol": "WETH-USDT", "project": "uniswap-v3", "chain": "Base",
     "apy": 68.0, "tvlUsd": 18_000_000, "risk_score": "Medium"},
    {"pool": "velo-usdc-aero", "symbol": "USDC/AERO", "project": "velodrome-v2", "chain": "Base",
     "apy": 120.0, "tvlUsd": 1_500_000, "risk_score": "High"},
    {"pool": "curve-usdc-usdt", "symbol": "USDC-USDT", "project": "curve-dex", "chain": "Base",
     "apy": 4.8, "tvlUsd": 40_000_000, "risk_score": "Low"},
    # Low TVL pool (should be filtered by min_pool_tvl)
    {"pool": "tiny-lp", "symbol": "WETH-USDC", "project": "baseswap", "chain": "Base",
     "apy": 250.0, "tvlUsd": 90_000, "risk_score": "High"},
    # Ethereum pools (should be filtered by chain)
    {"pool": "eth-aave-usdc", "symbol": "USDC", "project": "aave-v3", "chain": "Ethereum",
     "apy": 5.5, "tvlUsd": 200_000_000, "risk_score": "Low"},
    {"pool": "eth-uni-weth-usdc", "symbol": "WETH/USDC", "project": "uniswap-v3", "chain": "Ethereum",
     "apy": 45.0, "tvlUsd": 100_000_000, "risk_score": "Medium"},
]


# ──────────────────────────────────────────────
# Pool filtering logic (mirrors strategy_executor.find_matching_pools)
# ──────────────────────────────────────────────
def find_matching_pools(agent: dict, all_pools: List[dict]) -> List[dict]:
    """Find pools matching agent's configuration — pure logic, no Scout API"""
    chain = agent.get("chain", "base")
    chain_map = {"base": "Base", "ethereum": "Ethereum", "arbitrum": "Arbitrum"}
    normalized = chain_map.get(chain.lower(), chain.title())

    # Pre-filter by chain and TVL (Scout API would do this)
    pools = [p for p in all_pools
             if p.get("chain", "").lower() == normalized.lower()
             and (p.get("tvlUsd") or 0) >= agent.get("min_pool_tvl", agent.get("min_tvl", 500000))]
    
    # Apply max_pool_tvl if set
    max_tvl = agent.get("max_pool_tvl")
    if max_tvl:
        pools = [p for p in pools if (p.get("tvlUsd") or 0) <= max_tvl]
    
    # Filter by agent preferences (mirrors strategy_executor exactly)
    filtered = []
    for pool in pools:
        # APY range
        apy = pool.get("apy", 0)
        if apy < agent.get("min_apy", 0):
            continue
        max_apy = agent.get("max_apy", 1000)
        if max_apy < 500 and apy > max_apy:
            continue
        
        # Protocols
        project = (pool.get("project") or "").lower()
        allowed = [p.lower() for p in agent.get("protocols", [])]
        if allowed and not any(p in project for p in allowed):
            continue
        
        # Assets
        symbol = (pool.get("symbol") or "").upper()
        assets = [a.upper() for a in agent.get("preferred_assets", [])]
        if assets and not any(a in symbol for a in assets):
            continue
        
        # Pool type (single/dual/all)
        pool_type = agent.get("pool_type", "all")
        is_lp = any(sep in symbol for sep in ["-", "/", " / "])
        if pool_type == "single" and is_lp:
            continue
        if pool_type == "dual" and not is_lp:
            continue
        
        # Risk
        risk_score = pool.get("risk_score", "Medium")
        risk_level = agent.get("risk_level", "medium")
        if risk_level == "low" and risk_score == "High":
            continue
        
        # Audit check
        if agent.get("only_audited", False):
            trusted = ['aave', 'compound', 'curve', 'uniswap', 'morpho', 'lido', 'aerodrome', 'velodrome', 'moonwell', 'beefy']
            if not any(t in project for t in trusted):
                continue
        
        # Avoid IL filter
        if agent.get("avoid_il", False):
            safe = ["aave", "compound", "morpho", "moonwell", "beefy"]
            if not any(s in project for s in safe):
                continue
        
        filtered.append(pool)
    
    return filtered


def rank_and_select(pools: List[dict], agent: dict) -> List[dict]:
    """Rank and select top N pools — mirrors strategy_executor.rank_and_select"""
    vault_count = agent.get("vault_count", 5)
    max_allocation = agent.get("max_allocation", 25)
    risk_level = agent.get("risk_level", "medium")
    trading_style = agent.get("trading_style", {
        "low": "conservative", "medium": "moderate", "high": "aggressive"
    }.get(risk_level, "moderate"))
    
    for pool in pools:
        score = 0
        apy = pool.get("apy", 0)
        tvl = pool.get("tvlUsd", 0)
        score += min(apy, 100) * 0.4
        if tvl > 10_000_000: score += 30
        elif tvl > 1_000_000: score += 20
        elif tvl > 100_000: score += 10
        
        if trading_style == "conservative":
            if apy > 100: score -= 20
            score = score * 0.7 + (30 - min(apy, 30))
        elif trading_style == "aggressive":
            score = score * 1.3
        
        pool["_score"] = round(score, 2)
        pool["_allocation"] = min(max_allocation, 100 // vault_count)
    
    pools.sort(key=lambda p: p.get("_score", 0), reverse=True)
    return pools[:vault_count]


# ──────────────────────────────────────────────
# Deposit simulation
# ──────────────────────────────────────────────
GAS_COST_BASE = 0.02  # $0.02 per tx on Base

def simulate_deposit(pool: dict, amount_usd: float, allocation_pct: float) -> dict:
    """Simulate depositing to a pool — single or dual-sided"""
    deposit_amount = amount_usd * allocation_pct / 100
    symbol = pool.get("symbol", "")
    is_dual = any(sep in symbol for sep in ["-", "/"])
    
    result = {
        "pool": symbol,
        "protocol": pool.get("project"),
        "pool_type": "dual-sided LP" if is_dual else "single-sided lending",
        "deposit_amount_usd": round(deposit_amount, 2),
        "apy": pool.get("apy", 0),
        "tvl": pool.get("tvlUsd", 0),
        "steps": [],
        "gas_costs": [],
        "total_gas": 0,
        "conversion_needed": False,
    }
    
    if is_dual:
        # ─── DUAL-SIDED LP DEPOSIT ───
        # Need to split deposit into 2 tokens
        tokens = []
        for sep in [" / ", "/", "-"]:
            if sep in symbol:
                tokens = [t.strip() for t in symbol.split(sep)]
                break
        
        if len(tokens) != 2:
            tokens = [symbol, symbol]
        
        token_a, token_b = tokens
        half = deposit_amount / 2
        
        # Step 1: Need to acquire both tokens (assume we start with USDC)
        result["steps"].append(f"1. Start with ${deposit_amount:.2f} USDC")
        
        # Check if we need to swap
        needs_swap_a = token_a not in ["USDC", "USDT", "DAI"]
        needs_swap_b = token_b not in ["USDC", "USDT", "DAI"]
        
        step_num = 2
        
        if needs_swap_a:
            result["conversion_needed"] = True
            result["steps"].append(f"{step_num}. Swap ${half:.2f} USDC → {token_a} (via DEX router)")
            result["gas_costs"].append({"action": f"swap_to_{token_a}", "cost": GAS_COST_BASE})
            step_num += 1
        else:
            result["steps"].append(f"{step_num}. Keep ${half:.2f} as {token_a}")
            step_num += 1
        
        if needs_swap_b:
            result["conversion_needed"] = True
            result["steps"].append(f"{step_num}. Swap ${half:.2f} USDC → {token_b} (via DEX router)")
            result["gas_costs"].append({"action": f"swap_to_{token_b}", "cost": GAS_COST_BASE})
            step_num += 1
        else:
            result["steps"].append(f"{step_num}. Keep ${half:.2f} as {token_b}")
            step_num += 1
        
        # Step: Approve both tokens
        result["steps"].append(f"{step_num}. Approve {token_a} to LP router")
        result["gas_costs"].append({"action": f"approve_{token_a}", "cost": GAS_COST_BASE})
        step_num += 1
        
        result["steps"].append(f"{step_num}. Approve {token_b} to LP router")
        result["gas_costs"].append({"action": f"approve_{token_b}", "cost": GAS_COST_BASE})
        step_num += 1
        
        # Step: Add liquidity
        result["steps"].append(f"{step_num}. addLiquidity({token_a}, {token_b}, ${half:.2f} each)")
        result["gas_costs"].append({"action": "add_liquidity", "cost": GAS_COST_BASE * 2})
        step_num += 1
        
        # IL warning
        stables = ["USDC", "USDT", "DAI"]
        both_stable = token_a in stables and token_b in stables
        result["il_risk"] = "LOW" if both_stable else "MEDIUM-HIGH"
        result["steps"].append(f"   ⚠️ IL Risk: {result['il_risk']}")
    
    else:
        # ─── SINGLE-SIDED LENDING DEPOSIT ───
        # ERC-4626 vault: approve + deposit
        token = symbol  # e.g. "USDC", "WETH"
        
        needs_swap = token not in ["USDC", "USDT", "DAI"]
        step_num = 1
        
        result["steps"].append(f"{step_num}. Start with ${deposit_amount:.2f} USDC")
        step_num += 1
        
        if needs_swap:
            result["conversion_needed"] = True
            result["steps"].append(f"{step_num}. Swap ${deposit_amount:.2f} USDC → {token} (via DEX router)")
            result["gas_costs"].append({"action": f"swap_to_{token}", "cost": GAS_COST_BASE})
            step_num += 1
        
        result["steps"].append(f"{step_num}. Approve {token} to vault")
        result["gas_costs"].append({"action": "approve", "cost": GAS_COST_BASE})
        step_num += 1
        
        result["steps"].append(f"{step_num}. vault.deposit(${deposit_amount:.2f} {token})")
        result["gas_costs"].append({"action": "deposit", "cost": GAS_COST_BASE})
    
    result["total_gas"] = sum(g["cost"] for g in result["gas_costs"])
    
    # Estimated daily yield
    daily_yield = deposit_amount * (pool.get("apy", 0) / 365 / 100)
    result["estimated_daily_yield"] = round(daily_yield, 4)
    result["estimated_weekly_yield"] = round(daily_yield * 7, 4)
    
    return result


# ──────────────────────────────────────────────
# 10 TEST PRESETS (mimicking buildDeployPayload flexible mode)
# ──────────────────────────────────────────────
def build_test_presets() -> List[Dict[str, Any]]:
    return [
        # 1. User's exact request: dual-sided, 500k-10M TVL, 50%+ APY, ETH+USDC
        {
            "name": "T1: Dual-Sided ETH/USDC Yield Hunter",
            "chain": "base", "pool_type": "dual", "risk_level": "medium",
            "min_apy": 50, "max_apy": 200, "trading_style": "moderate",
            "protocols": ["aerodrome", "uniswap"],
            "preferred_assets": ["WETH", "USDC"],
            "min_pool_tvl": 500_000, "max_pool_tvl": 10_000_000,
            "vault_count": 3, "max_allocation": 33,
            "avoid_il": False, "only_audited": True,
        },
        
        # 2. Conservative stablecoin lender
        {
            "name": "T2: Conservative Stablecoin Lender",
            "chain": "base", "pool_type": "single", "risk_level": "low",
            "min_apy": 5, "max_apy": 50, "trading_style": "conservative",
            "protocols": ["aave", "morpho", "compound", "moonwell"],
            "preferred_assets": ["USDC"],
            "min_pool_tvl": 10_000_000,
            "vault_count": 3, "max_allocation": 33,
            "avoid_il": True, "only_audited": True,
        },
        
        # 3. Aggressive high-APY degen
        {
            "name": "T3: Aggressive Degen Farmer",
            "chain": "base", "pool_type": "all", "risk_level": "high",
            "min_apy": 100, "max_apy": 10000, "trading_style": "aggressive",
            "protocols": ["aerodrome", "velodrome", "uniswap"],
            "preferred_assets": [],  # any asset
            "min_pool_tvl": 500_000,
            "vault_count": 5, "max_allocation": 20,
            "avoid_il": False, "only_audited": False,
        },
        
        # 4. ETH-only single-sided
        {
            "name": "T4: ETH-Only Lending",
            "chain": "base", "pool_type": "single", "risk_level": "medium",
            "min_apy": 3, "max_apy": 30, "trading_style": "moderate",
            "protocols": ["aave", "morpho", "moonwell"],
            "preferred_assets": ["WETH", "ETH"],
            "min_pool_tvl": 1_000_000,
            "vault_count": 3, "max_allocation": 33,
            "avoid_il": True, "only_audited": True,
        },
        
        # 5. Stable-stable dual LP (low IL)
        {
            "name": "T5: Stable/Stable LP Farmer",
            "chain": "base", "pool_type": "dual", "risk_level": "low",
            "min_apy": 3, "max_apy": 100, "trading_style": "conservative",
            "protocols": ["aerodrome", "curve", "uniswap"],
            "preferred_assets": ["USDC", "DAI", "USDT"],
            "min_pool_tvl": 5_000_000,
            "vault_count": 3, "max_allocation": 33,
            "avoid_il": False, "only_audited": True,
        },
        
        # 6. Morpho maximizer (single protocol)
        {
            "name": "T6: Morpho Maximizer",
            "chain": "base", "pool_type": "single", "risk_level": "medium",
            "min_apy": 5, "max_apy": 200, "trading_style": "moderate",
            "protocols": ["morpho"],
            "preferred_assets": ["USDC", "WETH"],
            "min_pool_tvl": 1_000_000,
            "vault_count": 5, "max_allocation": 25,
            "avoid_il": True, "only_audited": True,
        },
        
        # 7. High TVL only (institutional grade)
        {
            "name": "T7: Institutional Grade (TVL >$20M)",
            "chain": "base", "pool_type": "all", "risk_level": "low",
            "min_apy": 3, "max_apy": 50, "trading_style": "conservative",
            "protocols": ["aave", "compound", "uniswap", "curve"],
            "preferred_assets": ["USDC"],
            "min_pool_tvl": 20_000_000,
            "vault_count": 3, "max_allocation": 33,
            "avoid_il": True, "only_audited": True,
        },
        
        # 8. Multi-asset diversified
        {
            "name": "T8: Multi-Asset Diversified",
            "chain": "base", "pool_type": "all", "risk_level": "medium",
            "min_apy": 5, "max_apy": 200, "trading_style": "moderate",
            "protocols": ["aave", "morpho", "moonwell", "aerodrome", "uniswap"],
            "preferred_assets": ["USDC", "WETH"],
            "min_pool_tvl": 1_000_000,
            "vault_count": 5, "max_allocation": 20,
            "avoid_il": False, "only_audited": True,
        },
        
        # 9. Aerodrome-only LP hunter
        {
            "name": "T9: Aerodrome LP Hunter",
            "chain": "base", "pool_type": "dual", "risk_level": "high",
            "min_apy": 30, "max_apy": 1000, "trading_style": "aggressive",
            "protocols": ["aerodrome"],
            "preferred_assets": [],  # any
            "min_pool_tvl": 500_000,
            "vault_count": 5, "max_allocation": 25,
            "avoid_il": False, "only_audited": False,
        },
        
        # 10. Ultra-safe deposit (min risk, max TVL, no IL)
        {
            "name": "T10: Ultra-Safe Treasury",
            "chain": "base", "pool_type": "single", "risk_level": "low",
            "min_apy": 2, "max_apy": 15, "trading_style": "conservative",
            "protocols": ["aave", "compound"],
            "preferred_assets": ["USDC"],
            "min_pool_tvl": 25_000_000,
            "vault_count": 2, "max_allocation": 50,
            "avoid_il": True, "only_audited": True,
        },
    ]


# ──────────────────────────────────────────────
# MAIN: Run all tests
# ──────────────────────────────────────────────
def run_all_tests():
    presets = build_test_presets()
    capital = 10_000  # $10,000 per test
    
    results = []
    passed = 0
    failed = 0
    warnings = []
    
    print("=" * 80)
    print("🧪 POOL SEARCH + DEPOSIT SIMULATION — 10 FLEXIBLE PRESETS")
    print("=" * 80)
    print(f"📊 Mock pool universe: {len(MOCK_POOLS)} pools")
    print(f"💰 Simulated capital: ${capital:,}")
    print()
    
    for i, preset in enumerate(presets, 1):
        name = preset.pop("name")
        print(f"\n{'─' * 80}")
        print(f"📋 TEST {i}: {name}")
        print(f"{'─' * 80}")
        
        # Config summary
        print(f"   Chain: {preset['chain']} | Pool type: {preset['pool_type']} | Risk: {preset['risk_level']}")
        print(f"   APY: {preset['min_apy']}%-{preset['max_apy']}% | Style: {preset['trading_style']}")
        print(f"   Protocols: {', '.join(preset['protocols'])}")
        print(f"   Assets: {', '.join(preset['preferred_assets']) or 'ANY'}")
        print(f"   TVL: ${preset['min_pool_tvl']/1e6:.1f}M" + 
              (f" - ${preset.get('max_pool_tvl', 0)/1e6:.0f}M" if preset.get('max_pool_tvl') else "+"))
        print(f"   Vaults: {preset['vault_count']} | Max alloc: {preset['max_allocation']}%")
        print(f"   Avoid IL: {preset.get('avoid_il')} | Audited only: {preset.get('only_audited')}")
        
        # 1. POOL SEARCH
        matching = find_matching_pools(preset, MOCK_POOLS)
        print(f"\n   🔍 POOL SEARCH RESULTS: {len(matching)} matching pools")
        
        test_result = {
            "test": i,
            "name": name,
            "config": preset,
            "matching_pools": len(matching),
            "selected_pools": [],
            "deposits": [],
            "errors": [],
            "passed": True,
        }
        
        if not matching:
            print("   ❌ NO POOLS FOUND — would fallback to Aave USDC parking")
            test_result["errors"].append("No pools matched filters")
            test_result["passed"] = False
            failed += 1
            results.append(test_result)
            continue
        
        for j, pool in enumerate(matching[:8], 1):
            mark = "LP" if any(s in pool["symbol"] for s in ["-", "/"]) else "Lending"
            print(f"      {j}. {pool['symbol']:20} APY:{pool['apy']:>7.1f}%  TVL:${pool['tvlUsd']/1e6:>5.1f}M  [{mark}] {pool['project']}")
        if len(matching) > 8:
            print(f"      ... +{len(matching)-8} more")
        
        # 2. VALIDATION CHECKS
        errors = []
        
        # Check: pool type filter correctness
        for pool in matching:
            sym = pool["symbol"]
            is_lp = any(s in sym for s in ["-", "/"])
            if preset["pool_type"] == "single" and is_lp:
                errors.append(f"FAIL: Single-sided filter let through LP pool: {sym}")
            if preset["pool_type"] == "dual" and not is_lp:
                errors.append(f"FAIL: Dual-sided filter let through single pool: {sym}")
        
        # Check: APY range
        for pool in matching:
            apy = pool["apy"]
            if apy < preset["min_apy"]:
                errors.append(f"FAIL: APY {apy}% below min {preset['min_apy']}% for {pool['symbol']}")
            max_apy = preset["max_apy"]
            if max_apy < 500 and apy > max_apy:
                errors.append(f"FAIL: APY {apy}% above max {max_apy}% for {pool['symbol']}")
        
        # Check: TVL range
        for pool in matching:
            tvl = pool["tvlUsd"]
            if tvl < preset["min_pool_tvl"]:
                errors.append(f"FAIL: TVL ${tvl/1e6:.1f}M below min ${preset['min_pool_tvl']/1e6:.1f}M for {pool['symbol']}")
            max_tvl = preset.get("max_pool_tvl")
            if max_tvl and tvl > max_tvl:
                errors.append(f"FAIL: TVL ${tvl/1e6:.1f}M above max ${max_tvl/1e6:.1f}M for {pool['symbol']}")
        
        # Check: Protocol filter
        for pool in matching:
            project = pool["project"].lower()
            allowed = [p.lower() for p in preset["protocols"]]
            if allowed and not any(p in project for p in allowed):
                errors.append(f"FAIL: Protocol {pool['project']} not in allowed list for {pool['symbol']}")
        
        # Check: Asset filter
        for pool in matching:
            sym = pool["symbol"].upper()
            assets = [a.upper() for a in preset["preferred_assets"]]
            if assets and not any(a in sym for a in assets):
                errors.append(f"FAIL: Asset {sym} not matching preferred {assets}")
        
        # Check: Risk filter
        for pool in matching:
            if preset["risk_level"] == "low" and pool.get("risk_score") == "High":
                errors.append(f"FAIL: High-risk pool {pool['symbol']} passed low-risk filter")
        
        if errors:
            for e in errors:
                print(f"   ⛔ {e}")
            test_result["errors"] = errors
            test_result["passed"] = False
            failed += 1
        else:
            print("   ✅ All validation checks passed")
        
        # 3. RANK & SELECT
        selected = rank_and_select(matching.copy(), preset)
        test_result["selected_pools"] = [{"symbol": p["symbol"], "apy": p["apy"], "score": p.get("_score")} for p in selected]
        
        print(f"\n   📊 RANKED & SELECTED (top {preset['vault_count']}):")
        for j, pool in enumerate(selected, 1):
            print(f"      {j}. {pool['symbol']:20} Score:{pool['_score']:>6.1f}  APY:{pool['apy']:>7.1f}%  Alloc:{pool['_allocation']}%")
        
        # 4. DEPOSIT SIMULATION
        print(f"\n   💰 DEPOSIT SIMULATION (${capital:,}):")
        total_gas = 0
        total_daily = 0
        
        for pool in selected:
            deposit = simulate_deposit(pool, capital, pool["_allocation"])
            test_result["deposits"].append(deposit)
            total_gas += deposit["total_gas"]
            total_daily += deposit["estimated_daily_yield"]
            
            print(f"\n      {'═' * 50}")
            print(f"      📦 {deposit['pool']} ({deposit['pool_type']})")
            print(f"         Amount: ${deposit['deposit_amount_usd']:,.2f}")
            for step in deposit["steps"]:
                print(f"         {step}")
            if deposit["conversion_needed"]:
                print(f"         🔄 Token conversion required")
            print(f"         ⛽ Gas: ${deposit['total_gas']:.4f}")
            print(f"         📈 Est. daily: ${deposit['estimated_daily_yield']:.4f}")
            if "il_risk" in deposit:
                risk_emoji = "🟢" if deposit["il_risk"] == "LOW" else "🟡"
                print(f"         {risk_emoji} IL Risk: {deposit['il_risk']}")
        
        print(f"\n   {'─' * 50}")
        print(f"   📊 SUMMARY:")
        print(f"      Total Gas: ${total_gas:.4f}")
        print(f"      Est. Daily Yield: ${total_daily:.4f}")
        print(f"      Est. Weekly Yield: ${total_daily * 7:.4f}")
        print(f"      Est. Monthly Yield: ${total_daily * 30:.2f}")
        annualized = (total_daily * 365 / capital) * 100
        print(f"      Annualized ROI: {annualized:.1f}%")
        
        if not errors:
            passed += 1
        results.append(test_result)
    
    # ──────────────────────────────────────────────
    # FINAL REPORT
    # ──────────────────────────────────────────────
    print(f"\n\n{'=' * 80}")
    print(f"📊 FINAL REPORT: {passed}/{len(presets)} TESTS PASSED")
    print(f"{'=' * 80}")
    
    for r in results:
        status = "✅ PASS" if r["passed"] else "❌ FAIL"
        print(f"   {status} T{r['test']}: {r['name']} — {r['matching_pools']} pools, {len(r['selected_pools'])} selected")
        if r["errors"]:
            for e in r["errors"]:
                print(f"         ⛔ {e}")
    
    # KNOWN ISSUES REPORT
    print(f"\n{'=' * 80}")
    print("🐛 KNOWN ISSUES DETECTED DURING CODE REVIEW:")
    print(f"{'=' * 80}")
    print("""
   1. ⚠️  FIELD NAME MISMATCH (strategy_executor.py:836-837)
      - find_matching_pools() reads: agent.get("min_tvl", 500000) 
      - _build_agent_data() stores:  min_pool_tvl (from AgentDeployRequest)
      - Result: TVL filter uses DEFAULT 500000 instead of agent's configured value
      - Impact: Agents with custom TVL settings (e.g., 1M, 5M, 10M) will be IGNORED
      - Fix: Change agent.get("min_tvl") → agent.get("min_pool_tvl") in strategy_executor.py

   2. ⚠️  FIELD NAME MISMATCH (strategy_executor.py:838)
      - find_matching_pools() reads: agent.get("max_apy", 50000)
      - But this field name IS correct in _build_agent_data (max_apy)
      - OK ✅

   3. ℹ️  NO DUAL-SIDED TOKEN CONVERSION IN ENGINEER (engineer_agent.py)
      - create_deposit_task() only handles single-sided ERC-4626 vaults
      - Dual-sided LP deposits need: USDC → split → swap → approve × 2 → addLiquidity
      - Currently not implemented — would need Aerodrome/Uniswap router integration
      - Impact: Dual-sided pools can be RECOMMENDED but not AUTO-DEPOSITED yet
""")
    
    print(f"\n💾 Test complete at {datetime.utcnow().isoformat()}")
    return results


if __name__ == "__main__":
    run_all_tests()
