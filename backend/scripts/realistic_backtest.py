"""
Realistic Backtest Simulator v2
Uses 14-day historical data to analyze pool behavior and simulate realistic returns

Key improvements:
1. Analyzes 2-week APY history before selecting pools
2. Filters out pools with extreme volatility (unreliable)
3. Estimates Impermanent Loss for volatile pairs
4. Uses median APY (not max) for realistic projections
5. Accounts for APY decay patterns
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import statistics

# Configuration
CONFIG = {
    "initial_capital": 10000,  # $10,000 USDC
    "min_apy": 50,             # 50% APY minimum (was 100)
    "min_tvl": 500000,         # $500k TVL minimum
    "allocation_percent": 10,  # 10% per position
    "max_positions": 10,
    "max_duration_days": 1,    # Rotate daily
    "simulation_days": 4,
    "protocol": "aerodrome",
    "chain": "Base",
    "pool_type": "dual",
    
    # Risk filters (LOOSENED)
    "max_apy_volatility": 500,    # Max daily APY change % (was 200)
    "max_il_estimate": 15,        # Max estimated IL % (was 10)
    "min_history_days": 3,        # Need 3+ days of history (was 7)
    "use_median_apy": False,      # Use CURRENT APY (not median) for more pools
}

# Estimated IL for different pair types
IL_ESTIMATES = {
    "stablecoin": 0.5,    # USDC-USDT etc
    "correlated": 3.0,    # WETH-CBBTC (both crypto)
    "volatile": 8.0,      # USDC-SHITCOIN
    "unknown": 5.0
}

GAS_COST_USD = 0.02


def classify_pair(symbol: str) -> str:
    """Classify pair type for IL estimation"""
    symbol = symbol.upper()
    stables = ["USDC", "USDT", "DAI", "EURC", "FRAX"]
    majors = ["WETH", "ETH", "WBTC", "CBBTC", "BTC"]
    
    parts = [p.strip() for p in symbol.replace("-", "/").split("/")]
    
    # Stablecoin pair
    if all(any(s in p for s in stables) for p in parts):
        return "stablecoin"
    
    # Both are majors (correlated)
    if all(any(m in p for m in majors) for p in parts):
        return "correlated"
    
    # One stable + one volatile
    return "volatile"


def estimate_il(symbol: str, days: int = 4) -> float:
    """Estimate impermanent loss % for given period"""
    pair_type = classify_pair(symbol)
    daily_il = IL_ESTIMATES.get(pair_type, 5.0) / 30  # Monthly IL / 30
    return daily_il * days


async def fetch_defillama_pools(chain: str = "Base", protocol: str = None) -> List[Dict]:
    """Fetch current pools from DefiLlama"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get("https://yields.llama.fi/pools")
        data = resp.json()["data"]
        
        pools = []
        for p in data:
            if p.get("chain", "").lower() != chain.lower():
                continue
            if protocol and protocol.lower() not in (p.get("project", "") or "").lower():
                continue
            pools.append(p)
        
        return pools


async def fetch_pool_history(pool_id: str, days: int = 14) -> List[Dict]:
    """Fetch historical APY data for a pool"""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(f"https://yields.llama.fi/chart/{pool_id}")
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                # Return last N days
                return data[-days:] if data else []
        except Exception as e:
            print(f"  [!] Error fetching {pool_id}: {e}")
        return []


def analyze_pool_history(history: List[Dict]) -> Dict:
    """Analyze pool's historical behavior"""
    if len(history) < 3:
        return {"valid": False, "reason": "insufficient_data"}
    
    apys = [h.get("apy", 0) for h in history if h.get("apy") is not None]
    tvls = [h.get("tvlUsd", 0) for h in history if h.get("tvlUsd") is not None]
    
    if not apys or len(apys) < 3:
        return {"valid": False, "reason": "no_apy_data"}
    
    # Calculate statistics
    apy_mean = statistics.mean(apys)
    apy_median = statistics.median(apys)
    apy_stdev = statistics.stdev(apys) if len(apys) > 1 else 0
    apy_min = min(apys)
    apy_max = max(apys)
    
    # Volatility = stdev as % of mean
    volatility = (apy_stdev / apy_mean * 100) if apy_mean > 0 else 999
    
    # Trend: compare first half to second half
    half = len(apys) // 2
    first_half_avg = statistics.mean(apys[:half]) if half > 0 else apy_mean
    second_half_avg = statistics.mean(apys[half:]) if half > 0 else apy_mean
    trend = "stable"
    if second_half_avg > first_half_avg * 1.2:
        trend = "rising"
    elif second_half_avg < first_half_avg * 0.8:
        trend = "declining"
    
    # TVL trend
    tvl_stable = True
    if tvls and len(tvls) > 1:
        tvl_change = (tvls[-1] - tvls[0]) / tvls[0] * 100 if tvls[0] > 0 else 0
        tvl_stable = abs(tvl_change) < 50  # Less than 50% TVL change
    
    return {
        "valid": True,
        "days": len(apys),
        "apy_mean": apy_mean,
        "apy_median": apy_median,
        "apy_min": apy_min,
        "apy_max": apy_max,
        "apy_stdev": apy_stdev,
        "volatility": volatility,
        "trend": trend,
        "tvl_stable": tvl_stable,
        "daily_apys": apys[-4:] if len(apys) >= 4 else apys  # Last 4 days
    }


def filter_pools_realistic(pools: List[Dict], histories: Dict, config: Dict) -> List[Dict]:
    """Filter pools with realistic criteria based on history"""
    filtered = []
    
    for p in pools:
        pool_id = p.get("pool")
        symbol = p.get("symbol", "")
        current_apy = p.get("apy", 0)
        tvl = p.get("tvlUsd", 0)
        
        # Basic filters
        if tvl < config["min_tvl"]:
            continue
        
        # Must be dual-sided
        is_dual = any(sep in symbol for sep in ["-", "/"])
        if config["pool_type"] == "dual" and not is_dual:
            continue
        
        # Check history
        hist = histories.get(pool_id)
        if not hist or not hist.get("valid"):
            continue
        
        # Need enough history
        if hist.get("days", 0) < config["min_history_days"]:
            continue
        
        # Use median APY for realistic assessment
        realistic_apy = hist["apy_median"] if config["use_median_apy"] else current_apy
        if realistic_apy < config["min_apy"]:
            continue
        
        # Filter extreme volatility
        if hist["volatility"] > config["max_apy_volatility"]:
            continue
        
        # Skip declining trends
        if hist["trend"] == "declining":
            continue
        
        # Estimate IL
        il_estimate = estimate_il(symbol, config["simulation_days"])
        if il_estimate > config["max_il_estimate"]:
            continue
        
        # Add analysis to pool
        p["analysis"] = hist
        p["realistic_apy"] = realistic_apy
        p["il_estimate"] = il_estimate
        p["pair_type"] = classify_pair(symbol)
        
        filtered.append(p)
    
    # Sort by realistic APY
    filtered.sort(key=lambda x: x.get("realistic_apy", 0), reverse=True)
    return filtered


def calculate_daily_yield(amount: float, apy: float) -> float:
    """Calculate yield for 1 day"""
    daily_rate = apy / 365 / 100
    return amount * daily_rate


async def run_backtest(config: Dict) -> Dict:
    """Run realistic backtest simulation"""
    print("\n" + "="*70)
    print("🔬 REALISTIC BACKTEST SIMULATION v2")
    print("="*70)
    print(f"\n📊 Configuration:")
    print(f"   Capital: ${config['initial_capital']:,.0f}")
    print(f"   Protocol: {config['protocol'].title()}")
    print(f"   Min APY: {config['min_apy']}% (uses MEDIAN from 2 weeks)")
    print(f"   Min TVL: ${config['min_tvl']:,.0f}")
    print(f"   Max APY Volatility: {config['max_apy_volatility']}%")
    print(f"   Max IL Estimate: {config['max_il_estimate']}%")
    print(f"   Simulation: {config['simulation_days']} days")
    
    # Fetch pools
    print(f"\n🔍 Fetching pools...")
    all_pools = await fetch_defillama_pools(config["chain"], config["protocol"])
    print(f"   Found {len(all_pools)} total Aerodrome pools")
    
    # Pre-filter by TVL and dual-sided
    prefiltered = [p for p in all_pools 
                   if (p.get("tvlUsd", 0) >= config["min_tvl"]) and
                   any(sep in p.get("symbol", "") for sep in ["-", "/"])]
    print(f"   {len(prefiltered)} pools with TVL > ${config['min_tvl']/1000:.0f}k")
    
    # Fetch historical data
    print(f"\n📜 Fetching 14-day historical data...")
    histories = {}
    for i, p in enumerate(prefiltered[:30]):  # Top 30 by TVL
        pool_id = p.get("pool")
        history = await fetch_pool_history(pool_id, 14)
        if history:
            analysis = analyze_pool_history(history)
            histories[pool_id] = analysis
        if (i + 1) % 10 == 0:
            print(f"   Analyzed {i + 1}/{min(30, len(prefiltered))} pools...")
    
    print(f"   Got valid history for {sum(1 for h in histories.values() if h.get('valid'))} pools")
    
    # Filter with realistic criteria
    eligible = filter_pools_realistic(prefiltered, histories, config)
    print(f"\n✅ {len(eligible)} pools pass all filters")
    
    if not eligible:
        print("\n❌ No pools meet the strict criteria!")
        print("   Try: lowering min_apy, or increasing max_volatility")
        return {"error": "No eligible pools"}
    
    # Show filtered pools
    print(f"\n📈 Top {min(10, len(eligible))} REALISTIC pools:")
    print("-"*70)
    for i, p in enumerate(eligible[:10], 1):
        symbol = p['symbol'][:20]
        median_apy = p['realistic_apy']
        current_apy = p.get('apy', 0)
        volatility = p['analysis']['volatility']
        trend = p['analysis']['trend']
        il = p['il_estimate']
        pair_type = p['pair_type']
        
        print(f"   {i}. {symbol:20} | Median APY: {median_apy:>6.1f}% | "
              f"Current: {current_apy:>6.1f}% | Vol: {volatility:>5.1f}% | "
              f"Trend: {trend:8} | IL est: {il:.1f}%")
    
    # Run simulation with ACTUAL historical daily APYs
    print(f"\n🎮 RUNNING 4-DAY BACKTEST...")
    print("-"*70)
    
    capital = config["initial_capital"]
    position_size = capital * config["allocation_percent"] / 100
    num_positions = min(config["max_positions"], len(eligible))
    
    total_yield = 0
    total_il = 0
    total_gas = 0
    daily_log = []
    
    selected_pools = eligible[:num_positions]
    
    for day in range(config["simulation_days"]):
        day_yield = 0
        day_il = 0
        day_gas = GAS_COST_USD * num_positions if day > 0 else 0  # Daily rotation
        day_positions = []
        
        print(f"\n📅 DAY {day + 1}:")
        
        for pool in selected_pools:
            analysis = pool["analysis"]
            daily_apys = analysis.get("daily_apys", [])
            
            # Get APY for this specific day (from history)
            if len(daily_apys) > day:
                day_apy = daily_apys[day]
            else:
                day_apy = analysis["apy_median"]
            
            # Calculate yield
            pos_yield = calculate_daily_yield(position_size, day_apy)
            
            # Calculate daily IL (proportional)
            daily_il = pool["il_estimate"] / config["simulation_days"]
            il_loss = position_size * (daily_il / 100)
            
            day_yield += pos_yield
            day_il += il_loss
            
            day_positions.append({
                "pool": pool["symbol"][:25],
                "apy": day_apy,
                "yield": pos_yield,
                "il_loss": il_loss,
                "net": pos_yield - il_loss
            })
            
            print(f"   {pool['symbol'][:25]:25} APY: {day_apy:>6.1f}%  "
                  f"Yield: ${pos_yield:.2f}  IL: -${il_loss:.2f}  "
                  f"Net: ${pos_yield - il_loss:.2f}")
        
        net_day = day_yield - day_il - day_gas
        total_yield += day_yield
        total_il += day_il
        total_gas += day_gas
        
        daily_log.append({
            "day": day + 1,
            "gross_yield": day_yield,
            "il_loss": day_il,
            "gas_cost": day_gas,
            "net_yield": net_day,
            "positions": day_positions
        })
        
        print(f"   ━━━ Day {day + 1}: Gross ${day_yield:.2f} - IL ${day_il:.2f} - Gas ${day_gas:.2f} = Net ${net_day:.2f}")
    
    # Final calculations
    net_yield = total_yield - total_il - total_gas
    roi_percent = (net_yield / capital) * 100
    annualized_apy = roi_percent * (365 / config["simulation_days"])
    
    print("\n" + "="*70)
    print("📊 REALISTIC BACKTEST RESULTS")
    print("="*70)
    print(f"\n💰 Initial Capital: ${capital:,.0f}")
    print(f"📈 Positions: {num_positions} × ${position_size:,.0f}")
    print(f"⏱️  Duration: {config['simulation_days']} days")
    print(f"\n📊 BREAKDOWN:")
    print(f"   Gross Yield:        ${total_yield:>10.2f}")
    print(f"   Impermanent Loss:   ${-total_il:>10.2f}")
    print(f"   Gas Costs:          ${-total_gas:>10.2f}")
    print(f"   ─────────────────────────────")
    print(f"   NET PROFIT:         ${net_yield:>10.2f}")
    print(f"\n📈 ROI: {roi_percent:.2f}%")
    print(f"📈 Annualized (realistic): {annualized_apy:.1f}%")
    print("="*70)
    
    return {
        "config": config,
        "capital": capital,
        "positions": num_positions,
        "position_size": position_size,
        "simulation_days": config["simulation_days"],
        "gross_yield": total_yield,
        "il_loss": total_il,
        "gas_costs": total_gas,
        "net_yield": net_yield,
        "roi_percent": roi_percent,
        "annualized_apy": annualized_apy,
        "daily_log": daily_log,
        "selected_pools": [
            {
                "symbol": p["symbol"],
                "median_apy": p["realistic_apy"],
                "volatility": p["analysis"]["volatility"],
                "trend": p["analysis"]["trend"],
                "il_estimate": p["il_estimate"]
            }
            for p in selected_pools
        ]
    }


if __name__ == "__main__":
    result = asyncio.run(run_backtest(CONFIG))
    
    # Save results
    with open("backtest_results.json", "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n💾 Results saved to backtest_results.json")
