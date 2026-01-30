"""
Historical Yield Simulation
Simulates 4-day yield strategy using real DefiLlama historical data

Strategy Config:
- Protocol: Aerodrome (dual-sided LP)
- Min APY: 100%
- Min TVL: $500k
- Allocation: 10% per position
- Max positions: 10
- Max duration per pool: 1 day (then rotate)
- Total simulation: 4 days
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

# Configuration
CONFIG = {
    "initial_capital": 10000,  # $10,000 USDC
    "min_apy": 100,
    "min_tvl": 500000,
    "allocation_percent": 10,
    "max_positions": 10,
    "max_duration_days": 1,
    "simulation_days": 4,
    "protocol": "aerodrome",
    "chain": "Base",
    "pool_type": "dual"  # dual-sided LP only
}

# Gas costs on Base
GAS_COST_USD = 0.02  # ~$0.02 per swap/deposit on Base


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


async def fetch_pool_history(pool_id: str) -> List[Dict]:
    """Fetch historical APY data for a pool (last 30 days)"""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(f"https://yields.llama.fi/chart/{pool_id}")
            if resp.status_code == 200:
                return resp.json().get("data", [])
        except Exception as e:
            print(f"  [!] Could not fetch history for {pool_id}: {e}")
        return []


def filter_pools(pools: List[Dict], config: Dict) -> List[Dict]:
    """Filter pools by config criteria"""
    filtered = []
    for p in pools:
        apy = p.get("apy") or 0
        tvl = p.get("tvlUsd") or 0
        symbol = p.get("symbol", "")
        
        # Check criteria
        if apy < config["min_apy"]:
            continue
        if tvl < config["min_tvl"]:
            continue
        
        # Check dual-sided (has separator in symbol)
        is_dual = any(sep in symbol for sep in ["-", "/", " / "])
        if config["pool_type"] == "dual" and not is_dual:
            continue
        
        filtered.append(p)
    
    # Sort by APY descending
    filtered.sort(key=lambda x: x.get("apy", 0), reverse=True)
    return filtered


def calculate_daily_yield(amount: float, apy: float) -> float:
    """Calculate yield for 1 day"""
    daily_rate = apy / 365 / 100
    return amount * daily_rate


async def simulate_strategy(config: Dict) -> Dict:
    """Run the simulation"""
    print("\n" + "="*60)
    print("🚀 HISTORICAL YIELD SIMULATION")
    print("="*60)
    print(f"\n📊 Configuration:")
    print(f"   Capital: ${config['initial_capital']:,.0f}")
    print(f"   Protocol: {config['protocol'].title()}")
    print(f"   Min APY: {config['min_apy']}%")
    print(f"   Min TVL: ${config['min_tvl']:,.0f}")
    print(f"   Per Position: {config['allocation_percent']}%")
    print(f"   Max Positions: {config['max_positions']}")
    print(f"   Max Duration: {config['max_duration_days']} day(s)")
    print(f"   Simulation: {config['simulation_days']} days")
    
    # Fetch pools
    print(f"\n🔍 Fetching {config['protocol'].title()} pools on {config['chain']}...")
    all_pools = await fetch_defillama_pools(config["chain"], config["protocol"])
    print(f"   Found {len(all_pools)} total pools")
    
    # Filter pools
    eligible_pools = filter_pools(all_pools, config)
    print(f"   {len(eligible_pools)} pools meet criteria (APY>{config['min_apy']}%, TVL>${config['min_tvl']/1000:.0f}k)")
    
    if not eligible_pools:
        print("\n❌ No eligible pools found!")
        return {"error": "No eligible pools"}
    
    # Show top pools
    print(f"\n📈 Top {min(10, len(eligible_pools))} eligible pools:")
    for i, p in enumerate(eligible_pools[:10], 1):
        print(f"   {i}. {p['symbol'][:30]:30} APY: {p['apy']:>7.1f}%  TVL: ${p['tvlUsd']/1e6:.1f}M")
    
    # Fetch historical data for top pools
    print(f"\n📜 Fetching historical data...")
    pool_histories = {}
    for p in eligible_pools[:20]:  # Top 20 for history
        history = await fetch_pool_history(p["pool"])
        if history:
            pool_histories[p["pool"]] = {
                "pool": p,
                "history": history[-30:]  # Last 30 days
            }
    print(f"   Got history for {len(pool_histories)} pools")
    
    if not pool_histories:
        print("\n⚠️ No historical data available, using current APY")
        # Fallback to current APY
        for p in eligible_pools[:10]:
            pool_histories[p["pool"]] = {
                "pool": p,
                "history": [{"apy": p["apy"], "tvlUsd": p["tvlUsd"]}] * 4
            }
    
    # Simulation
    print(f"\n🎮 RUNNING SIMULATION...")
    print("-"*60)
    
    capital = config["initial_capital"]
    position_size = capital * config["allocation_percent"] / 100
    num_positions = min(config["max_positions"], len(pool_histories))
    
    total_yield = 0
    total_gas = 0
    daily_log = []
    rotations = 0
    
    # Get top N pools
    top_pools = list(pool_histories.values())[:num_positions]
    
    for day in range(config["simulation_days"]):
        day_yield = 0
        day_gas = 0
        day_positions = []
        
        print(f"\n📅 DAY {day + 1}:")
        
        # For each position, use historical APY for that day
        for i, pool_data in enumerate(top_pools):
            pool = pool_data["pool"]
            history = pool_data["history"]
            
            # Get APY for this day (from history, counting backwards)
            # Simulate as if 4 days ago -> today
            day_index = min(day, len(history) - 1)
            if history:
                # Use last N days of history
                hist_point = history[-(config["simulation_days"] - day)] if len(history) >= config["simulation_days"] else history[-1]
                apy = hist_point.get("apy", pool.get("apy", 100))
            else:
                apy = pool.get("apy", 100)
            
            # Calculate yield
            pos_yield = calculate_daily_yield(position_size, apy)
            day_yield += pos_yield
            
            # Rotation logic - if APY dropped below min, rotate
            if apy < config["min_apy"] and day > 0:
                rotations += 1
                day_gas += GAS_COST_USD * 2  # Exit + enter
                print(f"   ⚡ ROTATION: {pool['symbol'][:20]} APY dropped to {apy:.1f}%")
            
            day_positions.append({
                "pool": pool["symbol"][:25],
                "apy": apy,
                "yield": pos_yield
            })
            
            print(f"   Position {i+1}: {pool['symbol'][:25]:25} APY: {apy:>6.1f}%  Yield: ${pos_yield:.2f}")
        
        # Daily rotation cost (max 1 day duration = always rotate)
        if day > 0:
            day_gas += GAS_COST_USD * num_positions  # Rotation gas
        
        total_yield += day_yield
        total_gas += day_gas
        
        daily_log.append({
            "day": day + 1,
            "gross_yield": day_yield,
            "gas_cost": day_gas,
            "net_yield": day_yield - day_gas,
            "positions": day_positions
        })
        
        print(f"   Day {day + 1} Yield: ${day_yield:.2f} (gas: ${day_gas:.2f})")
    
    # Final summary
    net_yield = total_yield - total_gas
    roi_percent = (net_yield / capital) * 100
    annualized_apy = roi_percent * (365 / config["simulation_days"])
    
    print("\n" + "="*60)
    print("📊 SIMULATION RESULTS")
    print("="*60)
    print(f"\n💰 Capital: ${capital:,.0f}")
    print(f"📈 Positions: {num_positions} x ${position_size:,.0f}")
    print(f"⏱️  Duration: {config['simulation_days']} days")
    print(f"\n💵 GROSS YIELD: ${total_yield:.2f}")
    print(f"⛽ GAS COSTS: ${total_gas:.2f}")
    print(f"✅ NET YIELD: ${net_yield:.2f}")
    print(f"\n📊 ROI: {roi_percent:.2f}%")
    print(f"📈 Annualized APY: {annualized_apy:.1f}%")
    print(f"🔄 Rotations: {rotations}")
    print("="*60)
    
    return {
        "config": config,
        "capital": capital,
        "positions": num_positions,
        "position_size": position_size,
        "simulation_days": config["simulation_days"],
        "gross_yield": total_yield,
        "gas_costs": total_gas,
        "net_yield": net_yield,
        "roi_percent": roi_percent,
        "annualized_apy": annualized_apy,
        "rotations": rotations,
        "daily_log": daily_log,
        "eligible_pools": len(eligible_pools)
    }


if __name__ == "__main__":
    result = asyncio.run(simulate_strategy(CONFIG))
    
    # Save results
    with open("simulation_results.json", "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n💾 Results saved to simulation_results.json")
