"""
Risk Intelligence Engine - Scout Agent v2.0
Real-time protocol and pool risk assessment using multiple data sources

Risk Factors:
- TVL Stability (25%) - 7-day TVL change analysis
- Protocol Age (15%) - Time since launch
- Audit Status (20%) - Known audits and security reviews
- Concentration (15%) - Whale concentration risk
- APY Sustainability (15%) - High APY = higher risk
- Smart Contract Risk (10%) - Based on protocol reputation
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RiskIntelligence")


class RiskIntelligence:
    """
    Multi-factor risk scoring engine for DeFi pools and protocols.
    Provides real-time risk assessment with detailed breakdowns.
    """
    
    # Risk factor weights (must sum to 1.0)
    WEIGHTS = {
        "tvl_stability": 0.25,
        "protocol_age": 0.15,
        "audit_status": 0.20,
        "concentration": 0.15,
        "apy_sustainability": 0.15,
        "smart_contract": 0.10
    }
    
    # Known audited protocols with their audit info
    AUDIT_DATABASE = {
        "aave": {"audits": ["OpenZeppelin", "Trail of Bits", "Certik"], "last_audit": "2024-06", "score": 95},
        "aave-v3": {"audits": ["OpenZeppelin", "SigmaPrime"], "last_audit": "2024-08", "score": 95},
        "compound": {"audits": ["OpenZeppelin", "Trail of Bits"], "last_audit": "2024-03", "score": 92},
        "compound-v3": {"audits": ["OpenZeppelin"], "last_audit": "2024-05", "score": 90},
        "morpho": {"audits": ["Spearbit", "Cantina"], "last_audit": "2024-07", "score": 88},
        "morpho-blue": {"audits": ["Spearbit"], "last_audit": "2024-09", "score": 88},
        "uniswap-v3": {"audits": ["OpenZeppelin", "Trail of Bits"], "last_audit": "2023-12", "score": 94},
        "aerodrome": {"audits": ["Code4rena"], "last_audit": "2024-04", "score": 82},
        "moonwell": {"audits": ["Halborn"], "last_audit": "2024-02", "score": 80},
        "kamino": {"audits": ["OtterSec", "Neodyme"], "last_audit": "2024-06", "score": 85},
        "marginfi": {"audits": ["OtterSec"], "last_audit": "2024-01", "score": 78},
        "drift": {"audits": ["Kudelski"], "last_audit": "2024-05", "score": 82},
        "raydium": {"audits": ["SlowMist"], "last_audit": "2024-03", "score": 75},
        "orca": {"audits": ["Kudelski"], "last_audit": "2024-04", "score": 80},
        "solend": {"audits": ["Kudelski", "OtterSec"], "last_audit": "2024-02", "score": 78},
    }
    
    # Protocol launch dates for age scoring
    PROTOCOL_LAUNCHES = {
        "aave": "2020-01-01",
        "aave-v3": "2022-03-16",
        "compound": "2018-09-27",
        "compound-v3": "2022-08-25",
        "uniswap-v3": "2021-05-05",
        "morpho": "2022-06-01",
        "aerodrome": "2023-08-28",
        "moonwell": "2022-02-01",
        "kamino": "2023-01-15",
        "marginfi": "2022-09-01",
        "drift": "2021-11-01",
        "raydium": "2021-02-21",
        "orca": "2021-02-01",
        "solend": "2021-08-01",
    }
    
    # Known risky/exploited protocols
    BLACKLIST = {
        "euler": {"reason": "Exploited March 2023", "severity": "critical"},
        "harvest": {"reason": "Flash loan exploit", "severity": "high"},
        "cream": {"reason": "Multiple exploits", "severity": "critical"},
    }
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.alerts = []
        logger.info("🛡️ Risk Intelligence Engine initialized")
    
    async def get_risk_score(self, pool: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate comprehensive risk score for a pool.
        
        Args:
            pool: Pool data with project, apy, tvl, chain info
            
        Returns:
            Risk assessment with overall score, factors, and warnings
        """
        project = pool.get("project", "").lower()
        tvl = pool.get("tvl", 0)
        apy = pool.get("apy", 0)
        chain = pool.get("chain", "Unknown")
        
        # Check blacklist first
        if project in self.BLACKLIST:
            return self._blacklisted_response(project)
        
        # Calculate individual factor scores
        factors = {
            "tvl_stability": await self._score_tvl_stability(pool),
            "protocol_age": self._score_protocol_age(project),
            "audit_status": self._score_audit_status(project),
            "concentration": self._score_concentration(tvl),
            "apy_sustainability": self._score_apy_sustainability(apy),
            "smart_contract": self._score_smart_contract(project)
        }
        
        # Calculate weighted overall score
        overall_score = sum(
            factors[factor]["score"] * self.WEIGHTS[factor]
            for factor in factors
        )
        
        # Determine risk level
        risk_level = self._get_risk_level(overall_score)
        
        # Collect warnings
        warnings = self._collect_warnings(factors, apy, tvl, project)
        
        return {
            "pool_id": pool.get("id"),
            "project": pool.get("project"),
            "chain": chain,
            "overall_score": round(overall_score, 1),
            "risk_level": risk_level,
            "risk_color": self._get_risk_color(risk_level),
            "factors": factors,
            "warnings": warnings,
            "recommendation": self._get_recommendation(risk_level, apy),
            "last_updated": datetime.now().isoformat()
        }
    
    async def _score_tvl_stability(self, pool: Dict[str, Any]) -> Dict[str, Any]:
        """Score based on TVL stability over 7 days"""
        tvl = pool.get("tvl", 0)
        tvl_change_7d = pool.get("tvlChange7d", 0)  # Percentage change
        
        # If no 7d data, estimate from TVL size (larger = more stable)
        if tvl_change_7d == 0:
            if tvl > 100_000_000:
                score = 90
                reason = "Large TVL ($100M+) indicates stability"
            elif tvl > 10_000_000:
                score = 75
                reason = "Medium TVL ($10M+)"
            elif tvl > 1_000_000:
                score = 60
                reason = "Small TVL ($1M+)"
            else:
                score = 40
                reason = "Low TVL - higher volatility risk"
        else:
            # Score based on 7d change
            if abs(tvl_change_7d) < 5:
                score = 95
                reason = "Very stable TVL (±5%)"
            elif abs(tvl_change_7d) < 15:
                score = 75
                reason = f"Moderate TVL change ({tvl_change_7d:+.1f}%)"
            elif abs(tvl_change_7d) < 30:
                score = 50
                reason = f"Significant TVL change ({tvl_change_7d:+.1f}%)"
            else:
                score = 25
                reason = f"⚠️ Large TVL swing ({tvl_change_7d:+.1f}%)"
        
        return {"score": score, "reason": reason, "weight": self.WEIGHTS["tvl_stability"]}
    
    def _score_protocol_age(self, project: str) -> Dict[str, Any]:
        """Score based on how long protocol has been operational"""
        project_key = project.lower().replace(" ", "-").replace("_", "-")
        
        launch_date_str = self.PROTOCOL_LAUNCHES.get(project_key)
        
        if not launch_date_str:
            # Unknown protocol - conservative score
            return {
                "score": 50,
                "reason": "Protocol age unknown",
                "weight": self.WEIGHTS["protocol_age"]
            }
        
        launch_date = datetime.fromisoformat(launch_date_str)
        age_days = (datetime.now() - launch_date).days
        age_years = age_days / 365
        
        if age_years >= 3:
            score = 95
            reason = f"Battle-tested ({age_years:.1f} years)"
        elif age_years >= 2:
            score = 85
            reason = f"Established ({age_years:.1f} years)"
        elif age_years >= 1:
            score = 70
            reason = f"Maturing ({age_years:.1f} years)"
        elif age_days >= 180:
            score = 55
            reason = f"Relatively new ({age_days} days)"
        else:
            score = 35
            reason = f"⚠️ Very new protocol ({age_days} days)"
        
        return {"score": score, "reason": reason, "weight": self.WEIGHTS["protocol_age"]}
    
    def _score_audit_status(self, project: str) -> Dict[str, Any]:
        """Score based on security audits"""
        project_key = project.lower().replace(" ", "-").replace("_", "-")
        
        audit_info = self.AUDIT_DATABASE.get(project_key)
        
        if not audit_info:
            return {
                "score": 40,
                "reason": "No known audits on record",
                "weight": self.WEIGHTS["audit_status"]
            }
        
        score = audit_info["score"]
        audits = audit_info["audits"]
        last_audit = audit_info["last_audit"]
        
        # Bonus for multiple auditors
        if len(audits) >= 3:
            score = min(100, score + 5)
        
        # Check if audit is recent (within 12 months)
        try:
            last_audit_date = datetime.strptime(last_audit, "%Y-%m")
            months_since = (datetime.now() - last_audit_date).days / 30
            if months_since > 12:
                score = max(50, score - 10)
                reason = f"Audited by {', '.join(audits[:2])} (last: {last_audit}, needs refresh)"
            else:
                reason = f"✅ Audited by {', '.join(audits[:2])} (last: {last_audit})"
        except:
            reason = f"Audited by {', '.join(audits[:2])}"
        
        return {"score": score, "reason": reason, "weight": self.WEIGHTS["audit_status"]}
    
    def _score_concentration(self, tvl: float) -> Dict[str, Any]:
        """Score based on TVL concentration risk (higher TVL = less concentration risk)"""
        # Without on-chain data, we estimate based on TVL
        # Larger pools tend to have more distributed holdings
        
        if tvl > 500_000_000:
            score = 90
            reason = "Very large pool - likely well distributed"
        elif tvl > 100_000_000:
            score = 80
            reason = "Large pool - good distribution expected"
        elif tvl > 10_000_000:
            score = 65
            reason = "Medium pool - moderate concentration risk"
        elif tvl > 1_000_000:
            score = 50
            reason = "Smaller pool - higher concentration risk"
        else:
            score = 35
            reason = "⚠️ Small pool - whale dominance risk"
        
        return {"score": score, "reason": reason, "weight": self.WEIGHTS["concentration"]}
    
    def _score_apy_sustainability(self, apy: float) -> Dict[str, Any]:
        """Score based on APY sustainability (very high APY = unsustainable)"""
        if apy < 5:
            score = 95
            reason = "Conservative yield - highly sustainable"
        elif apy < 10:
            score = 85
            reason = "Moderate yield - sustainable"
        elif apy < 20:
            score = 70
            reason = "Good yield - monitor sustainability"
        elif apy < 50:
            score = 50
            reason = "⚠️ High yield - verify source"
        elif apy < 100:
            score = 30
            reason = "⚠️ Very high yield - likely unsustainable"
        else:
            score = 15
            reason = "🚨 Extreme yield - high risk of collapse"
        
        return {"score": score, "reason": reason, "weight": self.WEIGHTS["apy_sustainability"]}
    
    def _score_smart_contract(self, project: str) -> Dict[str, Any]:
        """Score based on smart contract reputation and complexity"""
        project_key = project.lower().replace(" ", "-").replace("_", "-")
        
        # Tier 1: Blue chip protocols
        tier1 = ["aave", "aave-v3", "compound", "compound-v3", "uniswap-v3", "makerdao"]
        if project_key in tier1:
            return {
                "score": 95,
                "reason": "Blue-chip protocol - battle-tested contracts",
                "weight": self.WEIGHTS["smart_contract"]
            }
        
        # Tier 2: Established protocols
        tier2 = ["morpho", "morpho-blue", "curve", "balancer", "convex", "yearn"]
        if project_key in tier2:
            return {
                "score": 85,
                "reason": "Established protocol - proven contracts",
                "weight": self.WEIGHTS["smart_contract"]
            }
        
        # Tier 3: Growing protocols
        tier3 = ["aerodrome", "moonwell", "kamino", "orca", "raydium"]
        if project_key in tier3:
            return {
                "score": 70,
                "reason": "Growing protocol - contracts maturing",
                "weight": self.WEIGHTS["smart_contract"]
            }
        
        # Unknown - conservative
        return {
            "score": 50,
            "reason": "Protocol reputation unknown",
            "weight": self.WEIGHTS["smart_contract"]
        }
    
    def _blacklisted_response(self, project: str) -> Dict[str, Any]:
        """Return response for blacklisted protocols"""
        info = self.BLACKLIST[project]
        return {
            "pool_id": None,
            "project": project,
            "overall_score": 0,
            "risk_level": "Critical",
            "risk_color": "#FF0000",
            "factors": {},
            "warnings": [f"🚨 BLACKLISTED: {info['reason']}"],
            "recommendation": "AVOID - Protocol has critical security history",
            "last_updated": datetime.now().isoformat()
        }
    
    def _get_risk_level(self, score: float) -> str:
        """Convert score to risk level - calibrated for real DeFi pools"""
        # Low: 45+, Medium: 35-44, High: 25-34, Critical: <25
        if score >= 45:
            return "Low"
        elif score >= 35:
            return "Medium"
        elif score >= 25:
            return "High"
        else:
            return "Critical"

    
    def _get_risk_color(self, level: str) -> str:
        """Get color for risk level"""
        colors = {
            "Low": "#22C55E",      # Green
            "Medium": "#F59E0B",   # Amber
            "High": "#EF4444",     # Red
            "Critical": "#DC2626"  # Dark red
        }
        return colors.get(level, "#6B7280")
    
    def _collect_warnings(self, factors: Dict, apy: float, tvl: float, project: str) -> List[str]:
        """Collect all warnings from factors"""
        warnings = []
        
        for factor, data in factors.items():
            if data["score"] < 50:
                warnings.append(data["reason"])
        
        # Additional contextual warnings
        if apy > 50:
            warnings.append(f"⚠️ APY of {apy:.1f}% is unusually high")
        
        if tvl < 500_000:
            warnings.append("⚠️ Low TVL - liquidity risk")
        
        return warnings
    
    def _get_recommendation(self, risk_level: str, apy: float) -> str:
        """Generate recommendation based on risk and APY"""
        if risk_level == "Low":
            return "✅ Suitable for long-term deposits"
        elif risk_level == "Medium":
            if apy > 15:
                return "⚠️ Monitor regularly, consider taking profits"
            return "📊 Acceptable with regular monitoring"
        elif risk_level == "High":
            return "⚠️ Only for experienced users, small allocations"
        else:
            return "🚨 Not recommended - significant risk"
    
    # ==========================================
    # ALERT SYSTEM
    # ==========================================
    
    async def check_for_alerts(self, pools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check pools for alert conditions"""
        new_alerts = []
        
        for pool in pools:
            # TVL drop alert
            tvl_change = pool.get("tvlChange7d", 0)
            if tvl_change < -20:
                new_alerts.append({
                    "type": "tvl_drop",
                    "severity": "high",
                    "pool": pool.get("id"),
                    "project": pool.get("project"),
                    "message": f"🔴 TVL dropped {abs(tvl_change):.1f}% in 7 days",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Unusual APY spike
            apy = pool.get("apy", 0)
            if apy > 100:
                new_alerts.append({
                    "type": "apy_spike",
                    "severity": "medium",
                    "pool": pool.get("id"),
                    "project": pool.get("project"),
                    "message": f"⚠️ Unusual APY spike: {apy:.1f}%",
                    "timestamp": datetime.now().isoformat()
                })
        
        self.alerts.extend(new_alerts)
        return new_alerts
    
    def get_active_alerts(self, max_age_hours: int = 24) -> List[Dict[str, Any]]:
        """Get alerts from the last N hours"""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        return [
            alert for alert in self.alerts
            if datetime.fromisoformat(alert["timestamp"]) > cutoff
        ]


# Singleton instance
risk_engine = RiskIntelligence()


# Convenience functions
async def get_pool_risk(pool: Dict[str, Any]) -> Dict[str, Any]:
    """Get risk assessment for a single pool"""
    return await risk_engine.get_risk_score(pool)


async def get_bulk_risk(pools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get risk assessments for multiple pools"""
    return [await risk_engine.get_risk_score(pool) for pool in pools]
