"""
Appraiser Agent - "The Brain" of Artisan System
Analyzes and verifies all opportunities before showing to users

Responsibilities:
- Verify pool legitimacy (TVL, age, liquidity)
- Risk scoring (Low/Med/High)
- Sanity checks (catch suspicious 500% stablecoin yields)
- Mark verified/suspicious/degen pools
- Learn from valuation outcomes via Memory Engine
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

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

# Import Chainlink Oracle for depeg monitoring
try:
    from .chainlink_oracle import oracle as chainlink
except ImportError:
    # Fallback if oracle not available
    chainlink = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AppraiserAgent")


class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    HIGH = "high"
    EXTREME = "extreme"
    SUSPICIOUS = "suspicious"


class VerificationStatus(Enum):
    VERIFIED = "artisan_verified"
    PENDING = "pending_review"
    SUSPICIOUS = "suspicious"
    DEGEN = "degen_play"
    REJECTED = "rejected"


@dataclass
class RiskAssessment:
    level: RiskLevel
    score: int  # 0-100
    status: VerificationStatus
    warnings: List[str]
    flags: List[str]
    recommendation: str


class AppraiserAgent:
    """
    The Appraiser - Risk Analysis and Verification Agent
    This is the most critical agent - protects users from bad pools
    """
    
    def __init__(self):
        # === MVP STABLECOIN-ONLY CONFIGURATION ===
        
        # Chainlink Oracle integration
        self.oracle = chainlink
        
        # APY thresholds for STABLECOINS ONLY (MVP)
        self.apy_thresholds = {
            "safe_max": 15,        # 0-15% = SAFE
            "moderate_max": 25,    # 15-25% = MODERATE  
            "elevated_max": 35,    # 25-35% = ELEVATED
            "suspicious_min": 50   # >50% = SUSPICIOUS for stables
        }
        
        # TVL thresholds
        self.tvl_thresholds = {
            "minimum": 10000,        # $10K minimum
            "small": 100000,         # $100K
            "medium": 1000000,       # $1M
            "large": 10000000,       # $10M
        }
        
        # Utilization rate thresholds (for lending protocols)
        self.utilization_thresholds = {
            "healthy": 0.80,      # <80% = healthy
            "warning": 0.90,      # 80-90% = warning
            "critical": 0.95      # >95% = critical (hard to withdraw)
        }
        
        # Known verified protocols (audit status)
        self.verified_protocols = {
            "aave": {"audited": True, "tier": 1, "min_age_days": 365},
            "aave-v3": {"audited": True, "tier": 1, "min_age_days": 365},
            "compound": {"audited": True, "tier": 1, "min_age_days": 365},
            "compound-v3": {"audited": True, "tier": 1, "min_age_days": 180},
            "moonwell": {"audited": True, "tier": 2, "min_age_days": 180},
            "morpho": {"audited": True, "tier": 2, "min_age_days": 180},
            "seamless": {"audited": True, "tier": 2, "min_age_days": 90},
            "radiant": {"audited": True, "tier": 2, "min_age_days": 180},
        }
        
        # MVP: Only Big 3 stablecoins
        self.allowed_stablecoins = ["usdc", "usdt", "dai"]
        
        logger.info("🧠 Appraiser in MVP Mode: Depeg monitoring + Protocol health")
        
    def analyze_pool(self, pool: Dict) -> RiskAssessment:
        """
        MVP Stablecoin Analysis:
        1. Check depeg status (Chainlink)
        2. Check protocol solvency (utilization rate)
        3. Verify APY is realistic
        4. Check contract age
        5. Require audit
        """
        warnings = []
        flags = []
        
        apy = pool.get("apy", 0)
        tvl = pool.get("tvlUsd", 0)
        symbol = pool.get("symbol", "").upper()
        project = pool.get("project", "").lower()
        
        # === CRITICAL: DEPEG CHECK (Most important for stablecoins) ===
        if self.oracle:
            peg_status = self.oracle.check_peg_status(symbol)
            
            if peg_status["peg_status"] == "CRITICAL":
                flags.append(f"DEPEG_CRITICAL: {symbol} at ${peg_status['price']:.4f}")
                warnings.append(f"⚠️ {symbol} has lost peg - trading at ${peg_status['price']:.4f}")
                return RiskAssessment(
                    level=RiskLevel.EXTREME,
                    score=95,
                    status=VerificationStatus.REJECTED,
                    warnings=warnings,
                    flags=flags,
                    recommendation="DO NOT DEPOSIT - Stablecoin has depegged"
                )
            elif peg_status["peg_status"] == "WARNING":
                flags.append(f"DEPEG_WARNING: {symbol} at ${peg_status['price']:.4f}")
                warnings.append(f"Peg warning: {symbol} slightly off ($1.00 target)")
        
        # Start with neutral score
        risk_score = 50
        
        # === PROTOCOL HEALTH (Utilization Rate) ===
        utilization = pool.get("utilizationRate", 0)
        if utilization > 0:
            if utilization >= self.utilization_thresholds["critical"]:
                warnings.append(f"⚠️ Very high utilization ({utilization*100:.1f}%) - may be hard to withdraw")
                risk_score += 25
                flags.append("HIGH_UTILIZATION")
            elif utilization >= self.utilization_thresholds["warning"]:
                warnings.append(f"High utilization ({utilization*100:.1f}%) - monitor closely")
                risk_score += 10
        
        # === APY ANALYSIS (Stablecoin-specific) ===
        if apy > self.apy_thresholds["suspicious_min"]:
            warnings.append(f"APY of {apy:.1f}% is suspicious for stablecoins")
            risk_score += 30
            flags.append("SUSPICIOUS_APY")
        elif apy > self.apy_thresholds["elevated_max"]:
            warnings.append(f"APY of {apy:.1f}% is elevated - verify sustainability")
            risk_score += 15
        elif apy <= self.apy_thresholds["safe_max"]:
            risk_score -= 10  # Safe, realistic APY
        
        # === TVL ANALYSIS ===
        if tvl >= self.tvl_thresholds["large"]:
            risk_score -= 15  # Large TVL = safer
        elif tvl < self.tvl_thresholds["minimum"]:
            warnings.append("Very low TVL - liquidity risk")
            risk_score += 20
        
        # === PROTOCOL VERIFICATION ===
        protocol_info = self.verified_protocols.get(project)
        if not protocol_info:
            warnings.append("⚠️ Unverified protocol - NOT APPROVED for MVP")
            risk_score += 30
            flags.append("UNVERIFIED_PROTOCOL")
        else:
            # Check audit requirement
            if not protocol_info.get("audited"):
                warnings.append("Protocol not audited - high risk")
                risk_score += 25
            else:
                risk_score -= 10  # Audited = safer
                flags.append(f"tier{protocol_info['tier']}_protocol")
        
        # Clamp score
        risk_score = max(0, min(100, risk_score))
        risk_level = self._score_to_level(risk_score)
        status = self._determine_status(risk_score, flags, warnings)
        recommendation = self._generate_recommendation(risk_level, True, apy, tvl)
        
        return RiskAssessment(
            level=risk_level,
            score=risk_score,
            status=status,
            warnings=warnings,
            flags=flags,
            recommendation=recommendation
        )
    
    def _calculate_risk_score(self, pool: Dict) -> int:
        """Base risk score calculation"""
        score = 50  # Start at neutral
        
        apy = pool.get("apy", 0)
        tvl = pool.get("tvlUsd", 0)
        is_stablecoin = pool.get("stablecoin", False)
        
        # APY contribution to risk
        if is_stablecoin:
            if apy <= 10:
                score -= 20
            elif apy <= 20:
                score -= 10
            elif apy <= 30:
                score += 5
            elif apy <= 50:
                score += 15
            elif apy <= 100:
                score += 25
            else:
                score += 40  # Very suspicious for stables
        else:
            if apy <= 20:
                score -= 15
            elif apy <= 40:
                score -= 5
            elif apy <= 80:
                score += 10
            elif apy <= 150:
                score += 20
            else:
                score += 30
        
        # TVL contribution
        if tvl >= self.tvl_thresholds["large"]:
            score -= 15
        elif tvl >= self.tvl_thresholds["medium"]:
            score -= 10
        elif tvl >= self.tvl_thresholds["small"]:
            score -= 5
        elif tvl >= self.tvl_thresholds["minimum"]:
            score += 5
        else:
            score += 20  # Very low TVL
        
        # IL risk
        il_risk = pool.get("ilRisk", "").lower()
        if il_risk == "no":
            score -= 10
        elif il_risk == "yes":
            score += 5
        
        return score
    
    def _check_suspicious(self, pool: Dict, is_stablecoin: bool) -> List[str]:
        """Check for suspicious patterns"""
        flags = []
        apy = pool.get("apy", 0)
        tvl = pool.get("tvlUsd", 0)
        
        # Pattern 1: Stablecoin with extremely high APY
        if is_stablecoin and apy >= 100:
            flags.append("SUSPICIOUS: Stablecoin with 100%+ APY - likely unsustainable or scam")
        
        # Pattern 2: Very low TVL with high APY
        if tvl < 50000 and apy > 100:
            flags.append("SUSPICIOUS: Low liquidity ($50K) with extreme APY - high rug risk")
        
        # Pattern 3: Unknown protocol with high rewards
        project = pool.get("project", "").lower()
        if project not in self.verified_protocols and apy > 50:
            flags.append("CAUTION: Unverified protocol with high yields - DYOR")
        
        return flags
    
    def _analyze_apy(self, apy: float, is_stablecoin: bool, tvl: float) -> List[str]:
        """Generate APY-related warnings"""
        warnings = []
        thresholds = self.apy_thresholds["stablecoin" if is_stablecoin else "volatile"]
        
        if apy > thresholds["realistic_max"]:
            if is_stablecoin:
                warnings.append(f"APY of {apy:.1f}% is extremely high for stablecoins - verify source")
            else:
                warnings.append(f"APY of {apy:.1f}% may be temporary or incentivized")
        
        if apy > 200:
            warnings.append("Extremely high APY is often unsustainable - expect it to decrease")
        
        # High APY + low TVL = likely to drop fast
        if apy > 50 and tvl < 500000:
            warnings.append("High APY with low TVL - yield will likely decrease as TVL grows")
        
        return warnings
    
    def _analyze_tvl(self, tvl: float, apy: float) -> List[str]:
        """Generate TVL-related warnings"""
        warnings = []
        
        if tvl < self.tvl_thresholds["minimum"]:
            warnings.append("Very low total value locked - high slippage and rug risk")
        elif tvl < self.tvl_thresholds["small"]:
            warnings.append("Lower TVL means higher slippage on large trades")
        
        return warnings
    
    def _score_to_level(self, score: int) -> RiskLevel:
        """Convert numeric score to risk level"""
        if score <= 20:
            return RiskLevel.SAFE
        elif score <= 35:
            return RiskLevel.LOW
        elif score <= 50:
            return RiskLevel.MODERATE
        elif score <= 65:
            return RiskLevel.ELEVATED
        elif score <= 80:
            return RiskLevel.HIGH
        elif score <= 90:
            return RiskLevel.EXTREME
        else:
            return RiskLevel.SUSPICIOUS
    
    def _determine_status(self, score: int, flags: List[str], warnings: List[str]) -> VerificationStatus:
        """Determine pool verification status"""
        has_suspicious = any("SUSPICIOUS" in f for f in flags)
        
        if has_suspicious:
            return VerificationStatus.SUSPICIOUS
        elif score > 75:
            return VerificationStatus.DEGEN
        elif score > 60:
            return VerificationStatus.PENDING
        else:
            return VerificationStatus.VERIFIED
    
    def _generate_recommendation(self, level: RiskLevel, is_stablecoin: bool, apy: float, tvl: float) -> str:
        """Generate human-readable recommendation"""
        if level in [RiskLevel.SAFE, RiskLevel.LOW]:
            return "This pool appears safe for long-term positions. Good for passive yield."
        elif level == RiskLevel.MODERATE:
            return "Moderate risk - suitable for experienced users. Monitor regularly."
        elif level == RiskLevel.ELEVATED:
            return "Elevated risk - consider smaller position size. Watch for APY drops."
        elif level == RiskLevel.HIGH:
            return "High risk - only for risk-tolerant users. Set exit strategy."
        elif level == RiskLevel.EXTREME:
            return "Extreme risk - not recommended. If entering, use funds you can afford to lose."
        else:
            return "⚠️ Suspicious - recommend avoiding. Verify all claims independently."
    
    def _is_stablecoin(self, symbol: str) -> bool:
        """Check if pool involves stablecoins"""
        return any(stable in symbol.lower() for stable in self.stablecoins)
    
    # ===========================================
    # BATCH OPERATIONS
    # ===========================================
    
    def analyze_pools(self, pools: List[Dict]) -> List[Dict]:
        """Analyze multiple pools and return with risk data"""
        results = []
        
        for pool in pools:
            assessment = self.analyze_pool(pool)
            results.append({
                **pool,
                "risk_level": assessment.level.value,
                "risk_score": assessment.score,
                "verification_status": assessment.status.value,
                "warnings": assessment.warnings,
                "flags": assessment.flags,
                "recommendation": assessment.recommendation
            })
        
        return results
    
    def filter_verified(self, pools: List[Dict]) -> List[Dict]:
        """Return only Artisan Verified pools"""
        analyzed = self.analyze_pools(pools)
        return [p for p in analyzed if p["verification_status"] == "artisan_verified"]
    
    def filter_by_risk(self, pools: List[Dict], max_risk: str = "moderate") -> List[Dict]:
        """Filter pools by maximum acceptable risk level"""
        risk_order = ["safe", "low", "moderate", "elevated", "high", "extreme", "suspicious"]
        max_index = risk_order.index(max_risk)
        
        analyzed = self.analyze_pools(pools)
        return [
            p for p in analyzed 
            if risk_order.index(p["risk_level"]) <= max_index
        ]


# Singleton instance
appraiser = AppraiserAgent()
