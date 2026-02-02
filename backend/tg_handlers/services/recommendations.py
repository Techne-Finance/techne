"""
Techne Telegram Bot - Smart Recommendations Service
AI-Powered personalized yield recommendations
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from ..models.user_config import UserConfig


@dataclass
class Recommendation:
    """A personalized yield recommendation"""
    pool_id: str
    symbol: str
    protocol: str
    chain: str
    apy: float
    tvl: float
    risk_level: str
    reason: str
    score: float  # 0-100 match score
    action: str  # "enter", "exit", "increase", "decrease"


class SmartRecommendations:
    """
    AI-powered recommendation engine that analyzes user preferences,
    market conditions, and pool metrics to suggest optimal strategies.
    """
    
    def __init__(self):
        self.strategies = {
            "conservative": {
                "max_risk": "Low",
                "min_tvl": 10_000_000,
                "max_apy": 15,
                "preferred_protocols": ["aave", "compound", "lido", "spark"],
                "stablecoin_bias": 0.8
            },
            "balanced": {
                "max_risk": "Medium",
                "min_tvl": 1_000_000,
                "max_apy": 50,
                "preferred_protocols": ["aave", "compound", "morpho", "curve", "aerodrome"],
                "stablecoin_bias": 0.5
            },
            "growth": {
                "max_risk": "High",
                "min_tvl": 500_000,
                "max_apy": 200,
                "preferred_protocols": ["aerodrome", "pendle", "gmx", "balancer"],
                "stablecoin_bias": 0.3
            },
            "aggressive": {
                "max_risk": "High",
                "min_tvl": 100_000,
                "max_apy": 1000,
                "preferred_protocols": [],  # Any
                "stablecoin_bias": 0.1
            }
        }
    
    def analyze_pool(self, pool: Dict, config: UserConfig) -> Optional[Recommendation]:
        """
        Analyze a pool and determine if it's a good match for the user
        """
        symbol = pool.get("symbol", "")
        protocol = pool.get("project", "").lower()
        chain = pool.get("chain", "")
        apy = pool.get("apy", 0)
        tvl = pool.get("tvl", 0)
        risk = pool.get("risk_level", "Unknown")
        
        # Base score
        score = 50
        reasons = []
        
        # TVL score (higher = safer = better)
        if tvl >= 10_000_000:
            score += 15
            reasons.append("High TVL ($10M+)")
        elif tvl >= 1_000_000:
            score += 10
            reasons.append("Good TVL ($1M+)")
        elif tvl < 100_000:
            score -= 20
            reasons.append("Low TVL (risky)")
        
        # APY score (reasonable APY is good, too high is suspicious)
        if 5 <= apy <= 20:
            score += 10
            reasons.append("Sustainable APY")
        elif 20 < apy <= 50:
            score += 5
            reasons.append("Attractive APY")
        elif apy > 100:
            score -= 10
            reasons.append("High APY (may be unsustainable)")
        
        # Risk matching
        risk_map = {"Low": 1, "Medium": 2, "High": 3}
        user_risk = {"low": 1, "medium": 2, "high": 3, "all": 3}.get(config.risk_level, 3)
        pool_risk = risk_map.get(risk, 2)
        
        if pool_risk <= user_risk:
            score += 10
            reasons.append(f"Within your risk tolerance ({risk})")
        else:
            score -= 15
            reasons.append(f"Above your risk preference ({risk})")
        
        # Protocol trust
        blue_chip = ["aave", "compound", "lido", "uniswap", "curve"]
        if any(bc in protocol for bc in blue_chip):
            score += 10
            reasons.append("Blue-chip protocol")
        
        # Chain preference
        if config.chain != "all" and chain.lower() == config.chain.lower():
            score += 5
            reasons.append(f"On your preferred chain ({chain})")
        
        # Filter out poor matches
        if score < 40:
            return None
        
        # Determine action
        if score >= 70:
            action = "enter"
        elif score >= 55:
            action = "consider"
        else:
            action = "monitor"
        
        return Recommendation(
            pool_id=pool.get("pool", pool.get("id", "")),
            symbol=symbol,
            protocol=protocol,
            chain=chain,
            apy=apy,
            tvl=tvl,
            risk_level=risk,
            reason="; ".join(reasons[:3]),
            score=min(score, 100),
            action=action
        )
    
    def get_recommendations(self, pools: List[Dict], config: UserConfig, limit: int = 5) -> List[Recommendation]:
        """
        Get personalized recommendations from a list of pools
        """
        recommendations = []
        
        for pool in pools:
            rec = self.analyze_pool(pool, config)
            if rec:
                recommendations.append(rec)
        
        # Sort by score descending
        recommendations.sort(key=lambda r: r.score, reverse=True)
        
        return recommendations[:limit]
    
    def format_recommendations(self, recommendations: List[Recommendation]) -> str:
        """
        Format recommendations for Telegram message
        """
        if not recommendations:
            return "🤖 No strong recommendations at this time.\n\nTry adjusting your filters or check back later."
        
        lines = ["🎯 *AI Recommendations*\n"]
        lines.append("_Personalized for your risk profile_\n")
        
        for i, rec in enumerate(recommendations, 1):
            action_emoji = {
                "enter": "🟢 ENTER",
                "consider": "🟡 CONSIDER",
                "monitor": "⚪ MONITOR"
            }.get(rec.action, "⚪")
            
            tvl_str = f"${rec.tvl/1_000_000:.1f}M" if rec.tvl >= 1_000_000 else f"${rec.tvl/1_000:.0f}K"
            
            lines.append(
                f"*{i}. {rec.symbol}* ({rec.protocol})\n"
                f"   {action_emoji} | Score: {rec.score:.0f}/100\n"
                f"   📈 {rec.apy:.1f}% APY • {tvl_str}\n"
                f"   💡 _{rec.reason}_\n"
            )
        
        lines.append("\n_Recommendations update every 15 minutes_")
        lines.append("Use /pool [number] for details")
        
        return "\n".join(lines)
    
    def format_strategy_analysis(self, config: UserConfig) -> str:
        """
        Analyze user's current strategy settings
        """
        # Determine strategy type based on settings
        if config.risk_level == "low" and config.stablecoin_only:
            strategy = "Conservative"
            emoji = "🛡️"
            expected_apy = "5-12%"
        elif config.risk_level in ["low", "medium"] and config.min_tvl >= 500000:
            strategy = "Balanced"
            emoji = "⚖️"
            expected_apy = "10-25%"
        elif config.risk_level in ["medium", "high"]:
            strategy = "Growth"
            emoji = "📈"
            expected_apy = "20-50%"
        else:
            strategy = "Aggressive"
            emoji = "🚀"
            expected_apy = "30%+"
        
        protocols = ", ".join(config.protocols[:3]) if config.protocols else "All"
        chain = config.chain.capitalize() if config.chain != "all" else "Multi-chain"
        
        return f"""
🎯 *Your Strategy Profile*

{emoji} *{strategy}* Strategy

━━━━━━━━━━━━━━━━━━━━

📊 *Current Settings*
├ Risk Level: {config.risk_level.capitalize()}
├ Min TVL: ${config.min_tvl/1000:.0f}K
├ Min APY: {config.min_apy}%
├ Chain: {chain}
└ Protocols: {protocols}

💰 *Expected Returns*
├ Target APY: {expected_apy}
└ Risk: {'Lower' if strategy == 'Conservative' else 'Moderate' if strategy == 'Balanced' else 'Higher'}

━━━━━━━━━━━━━━━━━━━━

💡 *AI Insights*
Based on your settings, you're optimized for {'capital preservation' if strategy == 'Conservative' else 'balanced growth' if strategy == 'Balanced' else 'high returns'}.

Use /recommend to get personalized pool suggestions.
"""


# Global instance
smart_recommendations = SmartRecommendations()
