"""
Instruction Parser - LLM-based natural language → conditional rules
Uses cheap_llm.py (Groq/Gemini) to parse user instructions into structured rules.
"""

import os
import json
import httpx
from typing import List, Dict, Any, Optional
from .conditional_rules import ConditionalRule, RuleCondition, RuleAction

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# Parser prompt optimized for rule extraction
PARSE_PROMPT = '''Parse the following trading instructions into structured rules.

INSTRUCTIONS:
"{instructions}"

RULES FORMAT:
Each rule has a CONDITION (when to apply) and an ACTION (what to do).

CONDITION fields (all optional, use null if not specified):
- tvl_min: Minimum TVL in USD (e.g., 1000000 for $1M)
- tvl_max: Maximum TVL in USD  
- protocol: Protocol name (aerodrome, morpho, aave, etc.)
- pool_type: "single" or "dual"
- asset: Asset symbol (USDC, WETH, etc.)
- apy_min: Minimum APY percentage
- apy_max: Maximum APY percentage

ACTION fields (all optional, use null if not specified):
- max_duration_hours: Maximum time to hold position in hours
- trailing_stop_percent: Exit if price drops X% from peak value
- stop_loss_percent: Exit if total loss reaches X% from entry
- take_profit_percent: Exit if total profit reaches X%
- exit_if_apy_below: Exit if APY drops below X%
- auto_compound: true/false for auto-compounding

EXAMPLES:
Input: "hold aerodrome pools max 2 hours"
Output: [{{"condition": {{"protocol": "aerodrome"}}, "action": {{"max_duration_hours": 2}}}}]

Input: "for pools between 1m and 5m TVL, trailing stop at 10%"
Output: [{{"condition": {{"tvl_min": 1000000, "tvl_max": 5000000}}, "action": {{"trailing_stop_percent": 10}}}}]

Input: "dual sided pools max 1 hour, single sided pools trailing stop 15%"
Output: [
  {{"condition": {{"pool_type": "dual"}}, "action": {{"max_duration_hours": 1}}}},
  {{"condition": {{"pool_type": "single"}}, "action": {{"trailing_stop_percent": 15}}}}
]

Return ONLY a valid JSON array of rules. No explanation.'''


class InstructionParser:
    """Parse natural language instructions into ConditionalRule objects"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def parse(self, instructions: str) -> List[ConditionalRule]:
        """
        Parse natural language instructions into structured rules.
        
        Args:
            instructions: User's natural language trading instructions
            
        Returns:
            List of ConditionalRule objects
        """
        if not instructions or not instructions.strip():
            return []
        
        prompt = PARSE_PROMPT.format(instructions=instructions)
        
        # Try Groq first (free), then Gemini
        result = await self._call_groq(prompt)
        if result is None:
            result = await self._call_gemini(prompt)
        
        if result is None:
            print("[InstructionParser] All LLM providers failed")
            return []
        
        # Parse JSON response into rules
        try:
            rules_data = result if isinstance(result, list) else []
            rules = []
            
            for i, rule_dict in enumerate(rules_data):
                condition_data = rule_dict.get('condition', {})
                action_data = rule_dict.get('action', {})
                
                # Clean nulls
                condition_data = {k: v for k, v in condition_data.items() if v is not None}
                action_data = {k: v for k, v in action_data.items() if v is not None}
                
                rule = ConditionalRule(
                    condition=RuleCondition(**condition_data),
                    action=RuleAction(**action_data),
                    priority=len(rules_data) - i,  # First rules have higher priority
                    name=f"Rule {i+1}"
                )
                rules.append(rule)
                print(f"[InstructionParser] Parsed: {rule}")
            
            return rules
            
        except Exception as e:
            print(f"[InstructionParser] Parse error: {e}")
            return []
    
    async def _call_groq(self, prompt: str) -> Optional[List[Dict]]:
        """Call Groq API (Llama 3.1 8B - FREE tier)"""
        if not GROQ_API_KEY:
            print("[InstructionParser] No GROQ_API_KEY")
            return None
        
        try:
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
                    "max_tokens": 1000,
                    "response_format": {"type": "json_object"}
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                # Handle both {"rules": [...]} and [...] formats
                if isinstance(parsed, dict) and 'rules' in parsed:
                    return parsed['rules']
                elif isinstance(parsed, list):
                    return parsed
                return []
            else:
                print(f"[InstructionParser] Groq error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"[InstructionParser] Groq exception: {e}")
            return None
    
    async def _call_gemini(self, prompt: str) -> Optional[List[Dict]]:
        """Call Gemini 1.5 Flash"""
        if not GEMINI_API_KEY:
            print("[InstructionParser] No GEMINI_API_KEY")
            return None
        
        try:
            url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
            
            response = await self.client.post(
                url,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 1000,
                        "responseMimeType": "application/json"
                    }
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(content)
                if isinstance(parsed, dict) and 'rules' in parsed:
                    return parsed['rules']
                elif isinstance(parsed, list):
                    return parsed
                return []
            else:
                print(f"[InstructionParser] Gemini error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"[InstructionParser] Gemini exception: {e}")
            return None
    
    async def close(self):
        await self.client.aclose()


# Singleton instance
_parser = None

def get_instruction_parser() -> InstructionParser:
    global _parser
    if _parser is None:
        _parser = InstructionParser()
    return _parser


# CLI Test
if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("=" * 60)
        print("Instruction Parser Test")
        print("=" * 60)
        
        parser = InstructionParser()
        
        # Test cases
        test_instructions = [
            "for pools between 1m-5m TVL for aerodrome dual-sided, hold max 1h",
            "pools 5m-20m TVL, trailing stop at 15%",
            "exit USDC positions if APY drops below 5%",
            "morpho single-sided: take profit at 20%, stop loss at 10%"
        ]
        
        for instruction in test_instructions:
            print(f"\n{'='*60}")
            print(f"Input: {instruction}")
            print("-" * 60)
            
            rules = await parser.parse(instruction)
            
            for rule in rules:
                print(f"  → {rule}")
                print(f"    JSON: {json.dumps(rule.to_dict(), indent=2, default=str)}")
        
        await parser.close()
    
    asyncio.run(test())
