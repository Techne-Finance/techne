"""
Production-Accurate Backtest
Uses SAME filters as strategy_executor.py - NO extra volatility/history filters

This is what REAL production would use.
"""
import asyncio
import httpx
from datetime import datetime
from typing import Dict, List
import json

# Production-like config (matches strategy_executor.py)
CONFIG = {
    "initial_capital": 10000,  # $10,000 USDC
    "min_apy": 100,            # 100% APY minimum (original request)
    "min_tvl": 500000,         # $500k TVL minimum
    "allocation_percent": 10,  # 10% per position
    "max_positions": 10,
    "simulation_days": 4,
    "protocol": "aerodrome",
    "chain": "Base",
    "pool_type": "dual",       # Dual-sided LP only
    
    # ASSET FILTER - only pools with these tokens on at least one side
    # This matches what strategy_executor.py uses with preferred_assets
    "preferred_assets": ["USDC", "WETH"],
    
    # NO EXTRA FILTERS - just like production
    # No volatility filter
    # No history filter  
    # No trend filter
}

# Estimated IL for different pair types
IL_ESTIMATES = {
    "stablecoin": 0.5,    # USDC-USDT etc
    "correlated": 3.0,    # WETH-CBBTC (both crypto)
    "volatile": 8.0,      # USDC-random
}

GAS_COST_USD = 0.02


def classify_pair(symbol: str) -> str:
    """Classify pair type for IL estimation"""
    symbol = symbol.upper()
    stables = ["USDC", "USDT", "DAI", "EURC", "FRAX"]
    majors = ["WETH", "ETH", "WBTC", "CBBTC", "BTC"]
    
    parts = [p.strip() for p in symbol.replace("-", "/").split("/")]
    
    if all(any(s in p for s in stables) for p in parts):
        return "stablecoin"
    if all(any(m in p for m in majors) for p in parts):
        return "correlated"
    return "volatile"


def estimate_il(symbol: str, days: int = 4) -> float:
    """Estimate impermanent loss % for given period"""
    pair_type = classify_pair(symbol)
    daily_il = IL_ESTIMATES.get(pair_type, 5.0) / 30
    return daily_il * days


async def fetch_pools() -> List[Dict]:
    """Fetch pools from DefiLlama - SAME as production Scout"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get("https://yields.llama.fi/pools")
        return resp.json()["data"]


async def fetch_pool_history(pool_id: str) -> List[Dict]:
    """Fetch historical APY data"""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(f"https://yields.llama.fi/chart/{pool_id}")
            if resp.status_code == 200:
                return resp.json().get("data", [])[-4:]  # Last 4 days
        except:
            pass
        return []


def filter_pools_production(pools: List[Dict], config: Dict) -> List[Dict]:
    """Filter pools EXACTLY like strategy_executor.py does"""
    filtered = []
    
    for p in pools:
        # Chain filter
        if p.get("chain", "").lower() != config["chain"].lower():
            continue
        
        # Protocol filter
        if config["protocol"] and config["protocol"].lower() not in (p.get("project", "") or "").lower():
            continue
        
        # TVL filter
        if (p.get("tvlUsd") or 0) < config["min_tvl"]:
            continue
        
        # APY filter
        if (p.get("apy") or 0) < config["min_apy"]:
            continue
        
        # Pool type filter (dual = LP pairs)
        symbol = p.get("symbol", "")
        is_dual = any(sep in symbol for sep in ["-", "/"])
        if config["pool_type"] == "dual" and not is_dual:
            continue
        
        # ASSET FILTER - pool must have at least one preferred asset
        # This matches strategy_executor.py preferred_assets logic
        preferred_assets = config.get("preferred_assets", [])
        if preferred_assets:
            symbol_upper = symbol.upper()
            if not any(asset.upper() in symbol_upper for asset in preferred_assets):
                continue
        
        # That's it! No volatility/history filters in production
        filtered.append(p)
    
    # Sort by APY
    filtered.sort(key=lambda x: x.get("apy", 0), reverse=True)
    return filtered


async def run_production_backtest(config: Dict) -> Dict:
    """Run backtest with production-like filtering"""
    print("\n" + "="*70)
    print("🏭 PRODUCTION-ACCURATE BACKTEST")
    print("   (Uses SAME filters as strategy_executor.py)")
    print("="*70)
    print(f"\n📊 Configuration:")
    print(f"   Capital: ${config['initial_capital']:,}")
    print(f"   Protocol: {config['protocol'].title()}")
    print(f"   Min APY: {config['min_apy']}%")
    print(f"   Min TVL: ${config['min_tvl']:,}")
    print(f"   Pool type: {config['pool_type']}")
    print(f"   Simulation: {config['simulation_days']} days")
    print(f"\n   ⚠️  NO volatility filter")
    print(f"   ⚠️  NO history filter")
    print(f"   ⚠️  NO trend filter")
    
    # Fetch pools
    print(f"\n🔍 Fetching pools from DefiLlama...")
    all_pools = await fetch_pools()
    
    # Filter like production
    eligible = filter_pools_production(all_pools, config)
    print(f"✅ {len(eligible)} pools pass PRODUCTION filters")
    
    if not eligible:
        print("\n❌ No eligible pools!")
        return {"error": "No pools"}
    
    # Show eligible pools
    print(f"\n📈 All {len(eligible)} eligible pools:")
    print("-"*70)
    for i, p in enumerate(eligible, 1):
        symbol = p["symbol"][:30]
        apy = p.get("apy", 0)
        tvl = p.get("tvlUsd", 0) / 1e6
        print(f"  {i:2}. {symbol:30} APY: {apy:>10.1f}%  TVL: ${tvl:.2f}M")
    
    # Select top N
    num_positions = min(config["max_positions"], len(eligible))
    selected = eligible[:num_positions]
    position_size = config["initial_capital"] * config["allocation_percent"] / 100
    
    print(f"\n🎯 Selected top {num_positions} pools")
    
    # Fetch historical data for simulation
    print(f"\n📜 Fetching 4-day historical APY data...")
    for pool in selected:
        history = await fetch_pool_history(pool["pool"])
        pool["daily_apys"] = [h.get("apy", pool["apy"]) for h in history] if history else [pool["apy"]] * 4
        pool["il_estimate"] = estimate_il(pool["symbol"], config["simulation_days"])
    
    # Run simulation
    print(f"\n🎮 RUNNING 4-DAY SIMULATION...")
    print("-"*70)
    
    total_yield = 0
    total_il = 0
    total_gas = 0
    daily_log = []
    
    for day in range(config["simulation_days"]):
        day_yield = 0
        day_il = 0
        day_gas = GAS_COST_USD * num_positions if day > 0 else 0
        day_positions = []
        
        print(f"\n📅 DAY {day + 1}:")
        
        for pool in selected:
            # Get APY for this day
            apys = pool.get("daily_apys", [pool["apy"]])
            day_apy = apys[min(day, len(apys)-1)]
            
            # Calculate yield
            daily_rate = day_apy / 365 / 100
            pos_yield = position_size * daily_rate
            
            # IL loss
            daily_il = pool["il_estimate"] / config["simulation_days"]
            il_loss = position_size * (daily_il / 100)
            
            day_yield += pos_yield
            day_il += il_loss
            
            net = pos_yield - il_loss
            day_positions.append({
                "pool": pool["symbol"][:25],
                "apy": day_apy,
                "yield": pos_yield,
                "il": il_loss,
                "net": net
            })
            
            print(f"   {pool['symbol'][:25]:25} APY: {day_apy:>8.1f}%  "
                  f"Yield: ${pos_yield:>7.2f}  IL: -${il_loss:.2f}  Net: ${net:.2f}")
        
        net_day = day_yield - day_il - day_gas
        total_yield += day_yield
        total_il += day_il
        total_gas += day_gas
        
        daily_log.append({
            "day": day + 1,
            "gross_yield": day_yield,
            "il_loss": day_il,
            "gas": day_gas,
            "net": net_day
        })
        
        print(f"   ━━━ Day {day+1}: Gross ${day_yield:.2f} - IL ${day_il:.2f} - Gas ${day_gas:.2f} = Net ${net_day:.2f}")
    
    # Final results
    net_yield = total_yield - total_il - total_gas
    invested = position_size * num_positions
    roi = (net_yield / invested) * 100
    annualized = roi * (365 / config["simulation_days"])
    
    print("\n" + "="*70)
    print("📊 PRODUCTION-ACCURATE RESULTS")
    print("="*70)
    print(f"\n💰 Invested: ${invested:,.0f} ({num_positions} pools × ${position_size:,.0f})")
    print(f"⏱️  Duration: {config['simulation_days']} days")
    print(f"\n📊 BREAKDOWN:")
    print(f"   Gross Yield:        ${total_yield:>12,.2f}")
    print(f"   Impermanent Loss:   ${-total_il:>12,.2f}")
    print(f"   Gas Costs:          ${-total_gas:>12,.2f}")
    print(f"   ─────────────────────────────────")
    print(f"   NET PROFIT:         ${net_yield:>12,.2f}")
    print(f"\n📈 ROI ({config['simulation_days']} days): {roi:.2f}%")
    print(f"📈 Annualized: {annualized:.1f}%")
    print("="*70)
    
    return {
        "config": config,
        "invested": invested,
        "positions": num_positions,
        "eligible_pools": len(eligible),
        "gross_yield": total_yield,
        "il_loss": total_il,
        "gas_costs": total_gas,
        "net_yield": net_yield,
        "roi_percent": roi,
        "annualized_apy": annualized,
        "daily_log": daily_log,
        "selected_pools": [
            {"symbol": p["symbol"], "apy": p["apy"], "il_est": p["il_estimate"]}
            for p in selected
        ]
    }


if __name__ == "__main__":
    result = asyncio.run(run_production_backtest(CONFIG))
    
    with open("production_backtest.json", "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n💾 Saved to production_backtest.json")
