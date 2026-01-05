"""
Techne Guardian Agent - Risk Analysis
Analizuje ryzyko protokołów i pooli
"""

import asyncio
import httpx
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class RiskFactor:
    """Pojedynczy czynnik ryzyka"""
    name: str
    weight: float  # 0.0 - 1.0
    score: float   # 0 - 10 (10 = najniższe ryzyko)
    reason: str


class GuardianAgent:
    """
    Guardian Agent - Risk Analysis
    Analizuje ryzyko protokołów na podstawie:
    - Audytów smart contractów
    - Historii TVL
    - Reputacji zespołu
    - Social media sentiment
    - Exploit history
    """
    
    def __init__(self):
        self.defillama_base = "https://api.llama.fi"
        
        # Znane protokoły z audytami
        self.audited_protocols = {
            "aave": {"audits": ["OpenZeppelin", "Trail of Bits", "SigmaPrime"], "score": 9},
            "compound": {"audits": ["OpenZeppelin", "Trail of Bits"], "score": 9},
            "curve": {"audits": ["Trail of Bits", "Quantstamp"], "score": 8},
            "uniswap": {"audits": ["Trail of Bits", "ABDK"], "score": 9},
            "lido": {"audits": ["Statemind", "MixBytes"], "score": 8},
            "aerodrome": {"audits": ["OpenZeppelin"], "score": 7},
            "velodrome": {"audits": ["OpenZeppelin"], "score": 7},
            "morpho": {"audits": ["Spearbit", "Trail of Bits"], "score": 8},
            "sparklend": {"audits": ["Trail of Bits"], "score": 8},
            "pendle": {"audits": ["Ackee", "Dedaub"], "score": 7},
        }
        
        # Znane exploity
        self.known_exploits = {
            "euler": {"date": "2023-03", "amount": 197000000, "recovered": True},
            "curve": {"date": "2023-07", "amount": 70000000, "recovered": True},
            "ronin": {"date": "2022-03", "amount": 625000000, "recovered": False},
            "wormhole": {"date": "2022-02", "amount": 320000000, "recovered": False},
        }
        
        # Czas działania protokołów (w miesiącach)
        self.protocol_age = {
            "aave": 60,      # 5 lat
            "compound": 72,  # 6 lat
            "uniswap": 48,   # 4 lata
            "curve": 48,     # 4 lata
            "lido": 36,      # 3 lata
            "aerodrome": 18, # 1.5 roku
            "pendle": 24,    # 2 lata
            "morpho": 18,    # 1.5 roku
        }
    
    async def analyze_pool_risk(self, pool: Dict) -> Dict:
        """Pełna analiza ryzyka dla poola"""
        project = (pool.get('project') or '').lower()
        
        risk_factors = []
        
        # 1. Audit Check
        audit_factor = self._check_audits(project)
        risk_factors.append(audit_factor)
        
        # 2. TVL Analysis
        tvl_factor = self._analyze_tvl(pool.get('tvl', 0))
        risk_factors.append(tvl_factor)
        
        # 3. APY Sustainability
        apy_factor = self._analyze_apy_sustainability(pool.get('apy', 0), pool.get('apyBase', 0))
        risk_factors.append(apy_factor)
        
        # 4. Protocol Age
        age_factor = self._check_protocol_age(project)
        risk_factors.append(age_factor)
        
        # 5. Exploit History
        exploit_factor = self._check_exploit_history(project)
        risk_factors.append(exploit_factor)
        
        # 6. Impermanent Loss Risk (for LP pools)
        il_factor = self._analyze_impermanent_loss(pool)
        if il_factor:
            risk_factors.append(il_factor)
        
        # Calculate overall score
        total_weight = sum(f.weight for f in risk_factors)
        weighted_score = sum(f.score * f.weight for f in risk_factors) / total_weight
        
        # Convert to risk level
        if weighted_score >= 7:
            risk_level = "Low"
        elif weighted_score >= 4:
            risk_level = "Medium"
        else:
            risk_level = "High"
        
        return {
            "risk_score": risk_level,
            "risk_score_numeric": round(weighted_score, 1),
            "risk_factors": [
                {"name": f.name, "score": f.score, "reason": f.reason}
                for f in risk_factors
            ],
            "risk_reasons": [f.reason for f in risk_factors if f.score < 7],
            "recommendations": self._generate_recommendations(risk_factors, weighted_score)
        }
    
    def _check_audits(self, project: str) -> RiskFactor:
        """Sprawdza audyty protokołu"""
        for proto_name, data in self.audited_protocols.items():
            if proto_name in project:
                return RiskFactor(
                    name="Audits",
                    weight=0.25,
                    score=data["score"],
                    reason=f"Audited by: {', '.join(data['audits'])}"
                )
        
        return RiskFactor(
            name="Audits",
            weight=0.25,
            score=3,
            reason="No known audits - higher risk"
        )
    
    def _analyze_tvl(self, tvl: float) -> RiskFactor:
        """Analizuje TVL jako wskaźnik bezpieczeństwa"""
        if tvl >= 100_000_000:
            return RiskFactor(
                name="TVL",
                weight=0.20,
                score=9,
                reason=f"Very high TVL (${tvl/1e6:.0f}M) - battle tested"
            )
        elif tvl >= 10_000_000:
            return RiskFactor(
                name="TVL",
                weight=0.20,
                score=7,
                reason=f"Good TVL (${tvl/1e6:.1f}M)"
            )
        elif tvl >= 1_000_000:
            return RiskFactor(
                name="TVL",
                weight=0.20,
                score=5,
                reason=f"Medium TVL (${tvl/1e6:.1f}M)"
            )
        else:
            return RiskFactor(
                name="TVL",
                weight=0.20,
                score=3,
                reason=f"Low TVL (${tvl/1e3:.0f}K) - higher risk"
            )
    
    def _analyze_apy_sustainability(self, apy: float, apy_base: float) -> RiskFactor:
        """Analizuje czy APY jest zrównoważone"""
        if apy <= 10:
            return RiskFactor(
                name="APY Sustainability",
                weight=0.15,
                score=9,
                reason="Conservative APY - sustainable"
            )
        elif apy <= 30:
            return RiskFactor(
                name="APY Sustainability",
                weight=0.15,
                score=7,
                reason="Moderate APY"
            )
        elif apy <= 100:
            base_ratio = apy_base / apy if apy > 0 else 0
            if base_ratio > 0.5:
                return RiskFactor(
                    name="APY Sustainability",
                    weight=0.15,
                    score=6,
                    reason=f"High APY but {base_ratio*100:.0f}% from base fees"
                )
            return RiskFactor(
                name="APY Sustainability",
                weight=0.15,
                score=4,
                reason="High APY - may not be sustainable"
            )
        else:
            return RiskFactor(
                name="APY Sustainability",
                weight=0.15,
                score=2,
                reason="Very high APY - likely unsustainable, caution advised"
            )
    
    def _check_protocol_age(self, project: str) -> RiskFactor:
        """Sprawdza wiek protokołu"""
        for proto_name, age_months in self.protocol_age.items():
            if proto_name in project:
                if age_months >= 36:
                    return RiskFactor(
                        name="Protocol Age",
                        weight=0.15,
                        score=9,
                        reason=f"Established protocol ({age_months//12}+ years)"
                    )
                elif age_months >= 12:
                    return RiskFactor(
                        name="Protocol Age",
                        weight=0.15,
                        score=6,
                        reason=f"Newer protocol ({age_months} months)"
                    )
        
        return RiskFactor(
            name="Protocol Age",
            weight=0.15,
            score=4,
            reason="Unknown protocol age - exercise caution"
        )
    
    def _check_exploit_history(self, project: str) -> RiskFactor:
        """Sprawdza historię exploitów"""
        for proto_name, exploit in self.known_exploits.items():
            if proto_name in project:
                if exploit["recovered"]:
                    return RiskFactor(
                        name="Security History",
                        weight=0.15,
                        score=5,
                        reason=f"Past exploit ({exploit['date']}) but recovered"
                    )
                else:
                    return RiskFactor(
                        name="Security History",
                        weight=0.15,
                        score=2,
                        reason=f"Past exploit ({exploit['date']}) - ${exploit['amount']/1e6:.0f}M lost"
                    )
        
        return RiskFactor(
            name="Security History",
            weight=0.15,
            score=8,
            reason="No known exploits"
        )
    
    def _analyze_impermanent_loss(self, pool: Dict) -> Optional[RiskFactor]:
        """Analizuje ryzyko impermanent loss"""
        symbol = pool.get('symbol', '')
        
        # Stablecoin pairs have minimal IL
        stables = ['usdc', 'usdt', 'dai', 'frax', 'tusd', 'lusd']
        symbol_lower = symbol.lower()
        
        stable_count = sum(1 for s in stables if s in symbol_lower)
        
        if stable_count >= 2:
            return RiskFactor(
                name="Impermanent Loss",
                weight=0.10,
                score=9,
                reason="Stablecoin pair - minimal IL risk"
            )
        elif stable_count == 1:
            return RiskFactor(
                name="Impermanent Loss",
                weight=0.10,
                score=5,
                reason="One stablecoin - moderate IL risk"
            )
        elif 'eth' in symbol_lower and 'weth' not in symbol_lower:
            return RiskFactor(
                name="Impermanent Loss",
                weight=0.10,
                score=4,
                reason="Volatile pair - higher IL risk"
            )
        
        return None
    
    def _generate_recommendations(self, factors: List[RiskFactor], score: float) -> List[str]:
        """Generuje rekomendacje na podstawie analizy"""
        recommendations = []
        
        low_score_factors = [f for f in factors if f.score < 5]
        
        for factor in low_score_factors:
            if factor.name == "Audits":
                recommendations.append("⚠️ Consider only allocating small amounts to unaudited protocols")
            elif factor.name == "TVL":
                recommendations.append("⚠️ Low TVL pools may have liquidity issues")
            elif factor.name == "APY Sustainability":
                recommendations.append("⚠️ High APY may not be sustainable - monitor regularly")
            elif factor.name == "Security History":
                recommendations.append("⚠️ Protocol has past security issues - extra caution advised")
        
        if score >= 7:
            recommendations.append("✅ This pool appears relatively safe for DeFi standards")
        elif score >= 4:
            recommendations.append("⚠️ Moderate risk - consider position sizing carefully")
        else:
            recommendations.append("🚨 High risk pool - only for experienced users with small allocations")
        
        return recommendations
    
    def get_quick_risk_score(self, project: str, tvl: float, apy: float) -> str:
        """Quick risk score without full analysis"""
        score = 5.0
        
        # Trusted protocols
        trusted = ['aave', 'compound', 'curve', 'uniswap', 'lido']
        if any(t in project.lower() for t in trusted):
            score += 2
        
        # TVL bonus
        if tvl >= 10_000_000:
            score += 1
        elif tvl < 1_000_000:
            score -= 1
        
        # APY risk
        if apy > 100:
            score -= 2
        elif apy > 50:
            score -= 1
        elif apy < 20:
            score += 1
        
        if score >= 7:
            return "Low"
        elif score >= 4:
            return "Medium"
        return "High"


# Singleton
guardian_agent = GuardianAgent()


async def analyze_pool_risk(pool: Dict) -> Dict:
    """Main function to analyze pool risk"""
    return await guardian_agent.analyze_pool_risk(pool)


def get_quick_risk(project: str, tvl: float, apy: float) -> str:
    """Quick risk assessment"""
    return guardian_agent.get_quick_risk_score(project, tvl, apy)
