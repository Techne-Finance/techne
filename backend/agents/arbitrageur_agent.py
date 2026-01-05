"""
Arbitrageur Agent - "The Optimizer" of Artisan System
Cross-protocol yield comparison, opportunity detection, rebalancing suggestions

Responsibilities:
- Compare yields across protocols
- Detect yield arbitrage opportunities
- Suggest optimal allocation strategies
- Calculate gas-adjusted returns
- Monitor yield differentials
- Track arbitrage outcomes via Memory Engine
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

# Observability integration
try:
    from agents.observability_engine import observability, traced, SpanStatus
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False
    def traced(agent, op):
        def decorator(func): return func
        return decorator

# Memory integration
try:
    from agents.memory_engine import memory_engine, MemoryType
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ArbitrageurAgent")


@dataclass
class YieldOpportunity:
    from_pool: Dict
    to_pool: Dict
    yield_difference: float    # APY difference
    estimated_gain: float      # Annual gain per $1000
    gas_cost_usd: float
    break_even_days: float     # Days to break even on gas
    recommendation: str


@dataclass
class AllocationSuggestion:
    target_pools: List[Dict]
    allocations: List[float]  # Percentages
    expected_apy: float
    risk_score: float
    rationale: str


class ArbitrageurAgent:
    """
    The Arbitrageur - Yield Optimization Agent
    Always looking for the best risk-adjusted returns
    """
    
    def __init__(self):
        # Gas settings (Base chain)
        self.gas_config = {
            "average_gas_price_gwei": 0.001,  # Base is cheap
            "deposit_gas_units": 150000,
            "withdraw_gas_units": 100000,
            "swap_gas_units": 120000,
            "eth_price_usd": 2500,
        }
        
        # Minimum thresholds
        self.thresholds = {
            "min_yield_diff_percent": 5,      # Minimum APY difference to consider
            "min_tvl_for_move": 500000,       # Minimum TVL in destination
            "max_break_even_days": 30,        # Max days to break even on gas
            "min_holding_period_days": 7,     # Minimum time in position
        }
        
        # Protocol preferences (for same yield, prefer higher score)
        self.protocol_scores = {
            "aave-v3": 95,
            "compound-v3": 90,
            "uniswap-v3": 85,
            "aerodrome": 88,
            "curve-dex": 85,
            "beefy": 80,
            "moonwell": 82,
            "morpho": 85,
        }
        
        # Current suggestions cache
        self.cached_opportunities: List[YieldOpportunity] = []
        self.last_analysis: Optional[datetime] = None
        
    # ===========================================
    # YIELD COMPARISON
    # ===========================================
    
    def compare_pools(self, pool_a: Dict, pool_b: Dict) -> Dict:
        """Compare two pools"""
        apy_a = pool_a.get("apy", 0)
        apy_b = pool_b.get("apy", 0)
        tvl_a = pool_a.get("tvlUsd", 0)
        tvl_b = pool_b.get("tvlUsd", 0)
        
        return {
            "pool_a": pool_a.get("symbol"),
            "pool_b": pool_b.get("symbol"),
            "apy_difference": apy_b - apy_a,
            "tvl_comparison": "B higher" if tvl_b > tvl_a else "A higher",
            "recommendation": pool_b if apy_b > apy_a else pool_a
        }
    
    def find_better_alternatives(self, current_pool: Dict, all_pools: List[Dict]) -> List[YieldOpportunity]:
        """Find better yield opportunities for current position"""
        opportunities = []
        
        current_apy = current_pool.get("apy", 0)
        current_symbol = current_pool.get("symbol", "")
        
        # Get asset type for matching (e.g., USDC, ETH)
        current_assets = self._extract_assets(current_symbol)
        
        for pool in all_pools:
            if pool.get("pool") == current_pool.get("pool"):
                continue  # Skip same pool
            
            pool_apy = pool.get("apy", 0)
            pool_tvl = pool.get("tvlUsd", 0)
            pool_assets = self._extract_assets(pool.get("symbol", ""))
            
            # Check if assets match (same underlying)
            asset_match = bool(current_assets & pool_assets)
            
            # Calculate yield difference
            yield_diff = pool_apy - current_apy
            
            # Only consider if significant improvement
            if yield_diff < self.thresholds["min_yield_diff_percent"]:
                continue
            
            # Check TVL threshold
            if pool_tvl < self.thresholds["min_tvl_for_move"]:
                continue
            
            # Calculate gas costs and break-even
            gas_cost = self._calculate_migration_gas()
            annual_gain_per_1k = (yield_diff / 100) * 1000
            daily_gain = annual_gain_per_1k / 365
            break_even_days = gas_cost / daily_gain if daily_gain > 0 else float('inf')
            
            if break_even_days > self.thresholds["max_break_even_days"]:
                continue  # Not worth the gas
            
            # Create opportunity
            recommendation = self._generate_move_recommendation(
                yield_diff, break_even_days, asset_match
            )
            
            opportunities.append(YieldOpportunity(
                from_pool=current_pool,
                to_pool=pool,
                yield_difference=yield_diff,
                estimated_gain=annual_gain_per_1k,
                gas_cost_usd=gas_cost,
                break_even_days=break_even_days,
                recommendation=recommendation
            ))
        
        # Sort by yield difference
        opportunities.sort(key=lambda x: x.yield_difference, reverse=True)
        
        return opportunities[:5]  # Top 5 opportunities
    
    def _extract_assets(self, symbol: str) -> set:
        """Extract underlying assets from pool symbol"""
        common_assets = ["usdc", "usdt", "dai", "eth", "weth", "btc", "wbtc", 
                        "aero", "crv", "cbeth", "wsteth", "reth"]
        
        symbol_lower = symbol.lower()
        return {asset for asset in common_assets if asset in symbol_lower}
    
    def _calculate_migration_gas(self) -> float:
        """Calculate gas cost for migration (withdraw + deposit)"""
        total_gas = (
            self.gas_config["withdraw_gas_units"] + 
            self.gas_config["deposit_gas_units"]
        )
        
        gas_cost_eth = (
            total_gas * 
            self.gas_config["average_gas_price_gwei"] / 
            1e9
        )
        
        return gas_cost_eth * self.gas_config["eth_price_usd"]
    
    def _generate_move_recommendation(
        self, 
        yield_diff: float, 
        break_even_days: float,
        asset_match: bool
    ) -> str:
        """Generate recommendation text"""
        if yield_diff > 20:
            urgency = "Strong opportunity"
        elif yield_diff > 10:
            urgency = "Good opportunity"
        else:
            urgency = "Moderate opportunity"
        
        if break_even_days < 7:
            timing = "Quick break-even"
        elif break_even_days < 14:
            timing = "Reasonable break-even"
        else:
            timing = "Longer break-even period"
        
        match_text = "Same assets - direct migration" if asset_match else "Different assets - swap required"
        
        return f"{urgency}. {timing} ({break_even_days:.1f} days). {match_text}"
    
    # ===========================================
    # OPTIMAL ALLOCATION
    # ===========================================
    
    def suggest_allocation(
        self, 
        pools: List[Dict], 
        amount_usd: float,
        risk_tolerance: str = "moderate"
    ) -> AllocationSuggestion:
        """Suggest optimal allocation across pools"""
        
        # Filter pools by risk tolerance
        if risk_tolerance == "conservative":
            filtered = [p for p in pools if p.get("stablecoin") and p.get("apy", 0) < 20]
            max_pools = 3
        elif risk_tolerance == "aggressive":
            filtered = sorted(pools, key=lambda x: x.get("apy", 0), reverse=True)[:10]
            max_pools = 5
        else:  # moderate
            filtered = [p for p in pools if p.get("tvlUsd", 0) > 1000000 and p.get("apy", 0) < 50]
            max_pools = 4
        
        if not filtered:
            filtered = pools[:5]
        
        # Score pools (APY * TVL weight * protocol score)
        scored_pools = []
        for pool in filtered[:max_pools * 2]:
            tvl = pool.get("tvlUsd", 0)
            apy = pool.get("apy", 0)
            protocol = pool.get("project", "").lower()
            
            tvl_weight = min(tvl / 10000000, 1)  # Cap at $10M
            protocol_score = self.protocol_scores.get(protocol, 70) / 100
            
            score = apy * tvl_weight * protocol_score
            scored_pools.append((pool, score))
        
        # Sort and select top pools
        scored_pools.sort(key=lambda x: x[1], reverse=True)
        selected = scored_pools[:max_pools]
        
        # Calculate allocations (proportional to score)
        total_score = sum(score for _, score in selected)
        allocations = [score / total_score for _, score in selected]
        target_pools = [pool for pool, _ in selected]
        
        # Calculate expected APY
        expected_apy = sum(
            pool.get("apy", 0) * alloc 
            for pool, alloc in zip(target_pools, allocations)
        )
        
        # Calculate risk score (0-100)
        risk_score = self._calculate_portfolio_risk(target_pools, allocations)
        
        # Generate rationale
        rationale = self._generate_allocation_rationale(
            target_pools, allocations, expected_apy, risk_tolerance
        )
        
        return AllocationSuggestion(
            target_pools=target_pools,
            allocations=allocations,
            expected_apy=expected_apy,
            risk_score=risk_score,
            rationale=rationale
        )
    
    def _calculate_portfolio_risk(self, pools: List[Dict], allocations: List[float]) -> float:
        """Calculate overall portfolio risk score"""
        risk_factors = []
        
        for pool, alloc in zip(pools, allocations):
            apy = pool.get("apy", 0)
            tvl = pool.get("tvlUsd", 0)
            is_stable = pool.get("stablecoin", False)
            
            # Higher APY = higher risk
            apy_risk = min(apy / 50, 1) * 30
            
            # Lower TVL = higher risk
            tvl_risk = max(0, (1 - min(tvl / 5000000, 1))) * 25
            
            # Non-stable = higher risk
            stable_risk = 0 if is_stable else 20
            
            pool_risk = apy_risk + tvl_risk + stable_risk
            risk_factors.append(pool_risk * alloc)
        
        return sum(risk_factors)
    
    def _generate_allocation_rationale(
        self,
        pools: List[Dict],
        allocations: List[float],
        expected_apy: float,
        risk_tolerance: str
    ) -> str:
        """Generate explanation for allocation"""
        lines = [f"Optimized for {risk_tolerance} risk profile."]
        lines.append(f"Expected blended APY: {expected_apy:.1f}%")
        lines.append("")
        lines.append("Allocation breakdown:")
        
        for pool, alloc in zip(pools, allocations):
            lines.append(f"• {pool.get('symbol')}: {alloc*100:.0f}% ({pool.get('apy', 0):.1f}% APY)")
        
        return "\n".join(lines)
    
    # ===========================================
    # REBALANCING
    # ===========================================
    
    def check_rebalance_needed(
        self, 
        current_positions: List[Dict], 
        all_pools: List[Dict]
    ) -> List[Dict]:
        """Check if rebalancing is recommended"""
        recommendations = []
        
        for position in current_positions:
            pool_id = position.get("pool_id")
            current_value = position.get("value_usd", 0)
            
            # Find current pool data
            current_pool = next(
                (p for p in all_pools if p.get("pool") == pool_id), 
                None
            )
            
            if not current_pool:
                continue
            
            # Find better alternatives
            opportunities = self.find_better_alternatives(current_pool, all_pools)
            
            if opportunities:
                best = opportunities[0]
                if best.yield_difference > 10:  # Significant improvement
                    recommendations.append({
                        "action": "rebalance",
                        "from_pool": current_pool.get("symbol"),
                        "to_pool": best.to_pool.get("symbol"),
                        "yield_gain": best.yield_difference,
                        "current_value": current_value,
                        "projected_annual_gain": current_value * (best.yield_difference / 100)
                    })
        
        return recommendations
    
    # ===========================================
    # MARKET OPPORTUNITIES
    # ===========================================
    
    def find_top_opportunities(self, pools: List[Dict], limit: int = 10) -> List[Dict]:
        """Find top yield opportunities considering risk"""
        scored = []
        
        for pool in pools:
            apy = pool.get("apy", 0)
            tvl = pool.get("tvlUsd", 0)
            is_stable = pool.get("stablecoin", False)
            project = pool.get("project", "").lower()
            
            # Skip suspicious
            if apy > 200 and tvl < 100000:
                continue
            
            # Calculate risk-adjusted score
            protocol_score = self.protocol_scores.get(project, 50)
            tvl_multiplier = min(1, tvl / 1000000)
            stability_bonus = 1.2 if is_stable else 1.0
            
            score = apy * (protocol_score / 100) * tvl_multiplier * stability_bonus
            
            pool["opportunity_score"] = score
            scored.append(pool)
        
        scored.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)
        
        return scored[:limit]


# Singleton
arbitrageur = ArbitrageurAgent()
