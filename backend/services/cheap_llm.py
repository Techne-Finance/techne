"""
Cheap LLM Client for Contract Analysis
Uses the cheapest available LLMs for AI-powered scam detection

Pricing (per 1M tokens, as of Jan 2026):
1. Groq (Llama 3.1 8B) - FREE tier / $0.05 paid
2. Gemini 1.5 Flash - $0.075 input / $0.30 output
3. GPT-4o-mini - $0.15 input / $0.60 output
4. Claude Haiku - $0.25 input / $1.25 output

Strategy: Try Groq first (free), then Gemini, then GPT-4o-mini
"""

import os
import json
import httpx
from typing import Dict, Any, Optional

# API Keys from environment
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# API Endpoints
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# Analysis prompt template (optimized for token efficiency)
ANALYSIS_PROMPT = """Analyze this smart contract for security risks. Return ONLY valid JSON.

CONTRACT:
{source_code}

Check for:
- Hidden mint functions
- Blacklist/honeypot logic
- Owner-only withdrawals
- High/changeable fees (>10%)
- Reentrancy vulnerabilities
- Unsafe external calls

Return JSON format:
{{"risk_score": 0-100, "findings": ["finding1", "finding2"], "is_scam": true/false, "summary": "brief summary"}}"""


class CheapLLMClient:
    """
    2-Stage LLM Analysis Pipeline:
    
    Stage 1 (Basic): Groq Llama 3.1 8B - fast screening of ALL contracts
    Stage 2 (Advanced): Gemini 1.5 Flash - deep analysis for ambiguous cases (30-70 score)
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.last_provider = None
        self.total_cost_cents = 0  # Track spending
    
    async def analyze_contract(self, source_code: str) -> Dict[str, Any]:
        """
        2-Stage Contract Analysis:
        
        Stage 1: Groq (fast, free) - screens all contracts
        Stage 2: Gemini (advanced) - deep analysis if Stage 1 score is 30-70
        """
        # Truncate to save tokens (most patterns in first 8k chars)
        truncated = source_code[:8000]
        prompt = ANALYSIS_PROMPT.format(source_code=truncated)
        
        # ==========================================
        # STAGE 1: Basic Analysis (Groq - FREE)
        # ==========================================
        print("[CheapLLM] Stage 1: Groq basic screening...")
        stage1_result = await self._call_groq(prompt)
        
        if not stage1_result:
            # Groq failed - try Gemini directly
            print("[CheapLLM] Groq failed, falling back to Gemini...")
            stage1_result = await self._call_gemini(prompt)
        
        if not stage1_result:
            # Both failed - return fallback
            return {
                "risk_score": 50,
                "findings": ["AI analysis unavailable"],
                "is_scam": None,
                "provider": "fallback",
                "stage": 0,
                "summary": "Could not analyze - treat with caution"
            }
        
        stage1_result["provider"] = "groq"
        stage1_result["stage"] = 1
        self.last_provider = "groq"
        
        stage1_score = stage1_result.get("risk_score", 50)
        print(f"[CheapLLM] Stage 1 result: score={stage1_score}")
        
        # ==========================================
        # STAGE 2: Advanced Analysis (Gemini)
        # Only for TRULY ambiguous cases (40-60)
        # Narrower range = fewer Gemini calls = lower cost
        # ==========================================
        if 40 <= stage1_score <= 60:
            print("[CheapLLM] Stage 2: Gemini advanced analysis (ambiguous case)...")
            
            advanced_prompt = f"""You are an expert smart contract security auditor.
The basic screening gave this contract a risk score of {stage1_score}/100.

Perform a DEEP analysis. Look for:
1. Hidden admin functions
2. Fee manipulation (can owner change fees after deployment?)
3. Reentrancy vulnerabilities
4. Token balance manipulation
5. Withdrawal restrictions

CONTRACT:
{truncated}

Return JSON: {{"risk_score": 0-100, "findings": ["detailed finding 1", ...], "is_scam": bool, "confidence": "high/medium/low", "summary": "analysis"}}"""
            
            stage2_result = await self._call_gemini(advanced_prompt)
            
            if stage2_result:
                # Blend scores: 40% basic + 60% advanced
                stage2_score = stage2_result.get("risk_score", stage1_score)
                blended_score = int(stage1_score * 0.4 + stage2_score * 0.6)
                
                print(f"[CheapLLM] Stage 2 result: score={stage2_score}, blended={blended_score}")
                
                return {
                    "risk_score": blended_score,
                    "findings": stage1_result.get("findings", []) + stage2_result.get("findings", []),
                    "is_scam": stage2_result.get("is_scam"),
                    "provider": "groq+gemini",
                    "stage": 2,
                    "stage1_score": stage1_score,
                    "stage2_score": stage2_score,
                    "confidence": stage2_result.get("confidence", "medium"),
                    "summary": stage2_result.get("summary", stage1_result.get("summary", ""))
                }
        
        # Clear case (score < 30 or > 70) - return Stage 1 only
        return stage1_result
    
    async def _call_groq(self, prompt: str) -> Optional[Dict]:
        """Call Groq API (Llama 3.1 8B - FREE tier)."""
        if not GROQ_API_KEY:
            return None
        
        response = await self.client.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 500,
                "response_format": {"type": "json_object"}
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            # Track token usage (free tier so $0)
            return json.loads(content)
        
        return None
    
    async def _call_gemini(self, prompt: str) -> Optional[Dict]:
        """Call Gemini 1.5 Flash ($0.075/1M tokens)."""
        if not GEMINI_API_KEY:
            return None
        
        url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
        
        response = await self.client.post(
            url,
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 500,
                    "responseMimeType": "application/json"
                }
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            # Estimate cost: ~2k tokens * $0.075/1M = $0.00015
            self.total_cost_cents += 0.015
            return json.loads(content)
        
        return None
    
    async def _call_openai(self, prompt: str) -> Optional[Dict]:
        """Call GPT-4o-mini ($0.15/1M tokens)."""
        if not OPENAI_API_KEY:
            return None
        
        response = await self.client.post(
            OPENAI_URL,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 500,
                "response_format": {"type": "json_object"}
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            # Estimate cost: ~2k tokens * $0.15/1M = $0.0003
            self.total_cost_cents += 0.03
            return json.loads(content)
        
        return None
    
    async def quick_check(self, source_code: str) -> bool:
        """Quick scam check - returns True if likely safe."""
        result = await self.analyze_contract(source_code)
        return result.get("risk_score", 50) < 50 and not result.get("is_scam", False)
    
    def get_cost_summary(self) -> str:
        """Get total estimated cost."""
        return f"${self.total_cost_cents / 100:.4f}"
    
    async def close(self):
        await self.client.aclose()


# Global instance
_llm_client = None

def get_cheap_llm() -> CheapLLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = CheapLLMClient()
    return _llm_client


# ============================================
# INTEGRATION WITH SCAM DETECTOR
# ============================================

async def enhance_scam_detection(address: str, source_code: str, base_result: Dict) -> Dict:
    """
    Enhance regex-based scam detection with AI analysis.
    
    Only calls LLM if:
    1. Base score is ambiguous (30-70)
    2. Contract is large enough to warrant analysis
    
    This minimizes API costs while adding AI where it matters.
    """
    base_score = base_result.get("risk_score", 50)
    
    # Skip AI for clear-cut cases (saves money)
    if base_score < 30 or base_score > 70:
        base_result["ai_enhanced"] = False
        base_result["ai_reason"] = "Score clear - AI skipped"
        return base_result
    
    # Skip tiny contracts
    if len(source_code) < 500:
        base_result["ai_enhanced"] = False
        base_result["ai_reason"] = "Contract too small"
        return base_result
    
    # Run AI analysis
    llm = get_cheap_llm()
    ai_result = await llm.analyze_contract(source_code)
    
    # Blend scores: 70% regex + 30% AI
    ai_score = ai_result.get("risk_score", 50)
    blended_score = int(base_score * 0.7 + ai_score * 0.3)
    
    base_result["risk_score"] = blended_score
    base_result["ai_enhanced"] = True
    base_result["ai_provider"] = ai_result.get("provider", "unknown")
    base_result["ai_findings"] = ai_result.get("findings", [])
    base_result["ai_summary"] = ai_result.get("summary", "")
    
    return base_result


# ============================================
# CLI TEST
# ============================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("=" * 60)
        print("Cheap LLM Client Test")
        print("=" * 60)
        
        # Check which providers are available
        print("\nProvider Status:")
        print(f"  Groq:   {'✓ Configured' if GROQ_API_KEY else '✗ No key'}")
        print(f"  Gemini: {'✓ Configured' if GEMINI_API_KEY else '✗ No key'}")
        print(f"  OpenAI: {'✓ Configured' if OPENAI_API_KEY else '✗ No key'}")
        
        # Test with sample code
        sample_code = """
        pragma solidity ^0.8.0;
        
        contract SafeToken {
            mapping(address => uint256) public balances;
            address public owner;
            
            function transfer(address to, uint256 amount) public {
                require(balances[msg.sender] >= amount, "Insufficient");
                balances[msg.sender] -= amount;
                balances[to] += amount;
            }
        }
        """
        
        client = CheapLLMClient()
        
        if any([GROQ_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY]):
            print("\nAnalyzing sample contract...")
            result = await client.analyze_contract(sample_code)
            
            print(f"\nResult:")
            print(f"  Provider: {result.get('provider')}")
            print(f"  Risk Score: {result.get('risk_score')}/100")
            print(f"  Is Scam: {result.get('is_scam')}")
            print(f"  Findings: {result.get('findings', [])}")
            print(f"  Total Cost: {client.get_cost_summary()}")
        else:
            print("\n⚠ No API keys configured. Set one of:")
            print("  - GROQ_API_KEY (recommended - free tier)")
            print("  - GEMINI_API_KEY")
            print("  - OPENAI_API_KEY")
        
        await client.close()
    
    asyncio.run(test())
