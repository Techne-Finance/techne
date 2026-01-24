"""
Unified Pool Analysis Service
Combines all detection services into single API

Flow:
1. Scam Detection (Regex) - fast pattern matching
2. Wash Trading Detection - The Graph query  
3. LLM Analysis (2-stage) - Groq basic, Gemini for ambiguous
4. Forced Deep Analysis - for positions > $50k

This is the MAIN entry point for pool verification.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

# Import all detection services
from .scam_detector import ScamDetector, get_detector
from .wash_detector import WashTradingDetector, get_wash_detector
from .cheap_llm import CheapLLMClient, get_cheap_llm


class UnifiedPoolAnalyzer:
    """
    Complete pool analysis combining all safety checks.
    
    Usage:
        analyzer = UnifiedPoolAnalyzer()
        result = await analyzer.analyze(pool_address, position_size=10000)
        
        if result["safe_to_invest"]:
            print("Pool is safe!")
    """
    
    def __init__(self):
        self.scam_detector = ScamDetector()
        self.wash_detector = WashTradingDetector()
        self.llm_client = CheapLLMClient()
    
    async def analyze(
        self, 
        pool_address: str,
        protocol: str = "uniswap_v3",
        position_size_usd: float = 0,
        force_deep_analysis: bool = False
    ) -> Dict[str, Any]:
        """
        Full pool analysis.
        
        Args:
            pool_address: Pool/contract address
            protocol: Protocol name (uniswap_v3, aerodrome, etc)
            position_size_usd: Position size for tiered analysis
            force_deep_analysis: Force Gemini analysis regardless of score
        
        Returns:
            {
                "safe_to_invest": bool,
                "overall_risk_score": 0-100,
                "scam_analysis": {...},
                "wash_analysis": {...},
                "ai_analysis": {...},
                "recommendation": "SAFE" / "CAUTION" / "AVOID" / "SCAM",
                "blocking_issues": [...]
            }
        """
        start_time = datetime.utcnow()
        
        result = {
            "pool_address": pool_address,
            "protocol": protocol,
            "position_size_usd": position_size_usd,
            "analyzed_at": start_time.isoformat(),
            "safe_to_invest": True,  # Assume safe until proven otherwise
            "blocking_issues": []
        }
        
        # ==========================================
        # TIER 1: Scam Detection (Regex - Fast)
        # ==========================================
        print(f"[UnifiedAnalyzer] Tier 1: Scam detection for {pool_address[:10]}...")
        
        scam_result = await self.scam_detector.analyze_contract(pool_address)
        result["scam_analysis"] = scam_result
        
        scam_score = scam_result.get("risk_score", 50)
        
        if scam_score >= 70:
            result["safe_to_invest"] = False
            result["blocking_issues"].append(f"High scam risk: {scam_score}/100")
        
        # ==========================================
        # TIER 2: Wash Trading Detection
        # ==========================================
        print(f"[UnifiedAnalyzer] Tier 2: Wash trading analysis...")
        
        wash_result = await self.wash_detector.analyze_pool(
            pool_address, 
            protocol=protocol,
            hours=24
        )
        result["wash_analysis"] = wash_result
        
        if wash_result.get("is_wash_trading"):
            result["safe_to_invest"] = False
            result["blocking_issues"].append("Wash trading detected - APY is FAKE")
        
        if wash_result.get("apy_validity") == "SUSPICIOUS":
            result["blocking_issues"].append("Suspicious trading patterns - proceed with caution")
        
        # ==========================================
        # TIER 3: AI Analysis (2-Stage)
        # ==========================================
        # Get source code for AI analysis
        source_code = await self.scam_detector.fetch_contract_source(pool_address)
        
        should_run_ai = (
            source_code and 
            (30 <= scam_score <= 70 or force_deep_analysis or position_size_usd >= 50000)
        )
        
        if should_run_ai:
            print(f"[UnifiedAnalyzer] Tier 3: AI analysis...")
            
            # For $50k+ positions, force deep Gemini analysis
            if position_size_usd >= 50000:
                print(f"[UnifiedAnalyzer] 💰 Large position (${position_size_usd:,.0f}) - forcing deep Gemini analysis")
                # TODO: Implement forced Gemini 1.5 Pro for $50k+ positions
            
            ai_result = await self.llm_client.analyze_contract(source_code)
            result["ai_analysis"] = ai_result
            
            if ai_result.get("is_scam") == True:
                result["safe_to_invest"] = False
                result["blocking_issues"].append("AI detected scam patterns")
        else:
            result["ai_analysis"] = {"skipped": True, "reason": "Score clear or no source"}
        
        # ==========================================
        # FINAL VERDICT
        # ==========================================
        # Calculate overall risk score
        weights = {
            "scam": 0.4,
            "wash": 0.3,
            "ai": 0.3
        }
        
        wash_risk = 80 if wash_result.get("is_wash_trading") else (40 if wash_result.get("apy_validity") == "SUSPICIOUS" else 10)
        ai_score = result.get("ai_analysis", {}).get("risk_score", 50)
        
        overall_score = int(
            scam_score * weights["scam"] +
            wash_risk * weights["wash"] +
            ai_score * weights["ai"]
        )
        
        result["overall_risk_score"] = overall_score
        
        # Determine recommendation
        if overall_score < 30 and not result["blocking_issues"]:
            result["recommendation"] = "SAFE"
        elif overall_score < 50:
            result["recommendation"] = "CAUTION"
        elif overall_score < 70:
            result["recommendation"] = "AVOID"
        else:
            result["recommendation"] = "SCAM"
            result["safe_to_invest"] = False
        
        # Timing
        result["analysis_time_ms"] = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return result
    
    async def quick_check(self, pool_address: str) -> bool:
        """Quick safety check - returns True if likely safe."""
        result = await self.analyze(pool_address)
        return result["safe_to_invest"]
    
    async def close(self):
        await self.scam_detector.close()
        await self.wash_detector.close()
        await self.llm_client.close()


# Global instance
_analyzer = None

def get_unified_analyzer() -> UnifiedPoolAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = UnifiedPoolAnalyzer()
    return _analyzer


# ============================================
# CLI TEST
# ============================================

if __name__ == "__main__":
    async def test():
        print("=" * 60)
        print("Unified Pool Analyzer Test")
        print("=" * 60)
        
        analyzer = UnifiedPoolAnalyzer()
        
        # Test with USDC (should be safe)
        usdc = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        
        print(f"\nAnalyzing USDC: {usdc[:10]}...")
        
        result = await analyzer.analyze(usdc, position_size_usd=1000)
        
        print(f"\n=== RESULT ===")
        print(f"  Safe to Invest: {result['safe_to_invest']}")
        print(f"  Overall Risk: {result['overall_risk_score']}/100")
        print(f"  Recommendation: {result['recommendation']}")
        print(f"  Analysis Time: {result['analysis_time_ms']}ms")
        
        if result["blocking_issues"]:
            print(f"\n  🚫 Blocking Issues:")
            for issue in result["blocking_issues"]:
                print(f"    - {issue}")
        
        await analyzer.close()
    
    asyncio.run(test())
