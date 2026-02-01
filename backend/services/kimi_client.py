"""
Kimi K2.5 API Client
Moonshot AI's latest multimodal LLM with Agent Swarm capabilities
"""

import httpx
import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("KimiClient")

# Kimi K2.5 API configuration
KIMI_API_BASE = "https://api.moonshot.cn/v1"  # Official Moonshot API
KIMI_MODEL = "moonshot-v1-auto"  # Auto-selects best model (K2.5)


class KimiClient:
    """
    Kimi K2.5 API Client for Artisan Agent.
    
    Features:
    - 1T parameter MoE model
    - Agent Swarm (up to 100 sub-agents)
    - 200k context window
    - Vision + text multimodal
    """
    
    def __init__(self):
        self.api_key = os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY")
        if not self.api_key:
            logger.warning("KIMI_API_KEY not set - Kimi features disabled")
        
        self.client = httpx.AsyncClient(
            base_url=KIMI_API_BASE,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=120.0  # Long timeout for complex reasoning
        )
        
        self.total_tokens = 0
        self.total_cost = 0.0
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Send chat completion request to Kimi K2.5.
        
        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
            tools: Optional tool definitions for function calling
            temperature: Creativity (0-1)
            max_tokens: Max response length
            
        Returns:
            Kimi response with content and optional tool_calls
        """
        if not self.api_key:
            return {
                "error": "KIMI_API_KEY not configured",
                "content": "I'm unable to process requests right now. Please configure the API key."
            }
        
        try:
            payload = {
                "model": KIMI_MODEL,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"
            
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Track usage
            if "usage" in data:
                self.total_tokens += data["usage"].get("total_tokens", 0)
                # Estimate cost (Kimi is very cheap)
                self.total_cost += data["usage"].get("total_tokens", 0) * 0.000001
            
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            
            return {
                "content": message.get("content", ""),
                "tool_calls": message.get("tool_calls", []),
                "finish_reason": choice.get("finish_reason"),
                "usage": data.get("usage", {})
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Kimi API error: {e.response.status_code} - {e.response.text}")
            return {
                "error": f"API error: {e.response.status_code}",
                "content": "I encountered an error processing your request."
            }
        except Exception as e:
            logger.error(f"Kimi request failed: {e}")
            return {
                "error": str(e),
                "content": "An unexpected error occurred."
            }
    
    async def analyze_portfolio(
        self,
        positions: List[Dict],
        market_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze portfolio using Kimi K2.5's reasoning.
        
        Returns structured analysis with recommendations.
        """
        system_prompt = """You are an expert DeFi portfolio analyst for Techne Finance.
Analyze the user's positions and provide actionable recommendations.

For each position, evaluate:
1. Current APY sustainability
2. Risk level (IL, protocol risk, market risk)
3. Opportunity cost vs alternatives

Respond in JSON format:
{
    "summary": "Brief portfolio overview",
    "total_value_usd": 0,
    "total_daily_yield_usd": 0,
    "risk_score": 0-100,
    "positions": [
        {
            "pool_id": "...",
            "status": "healthy|warning|critical",
            "recommendation": "hold|exit|increase",
            "reason": "..."
        }
    ],
    "suggested_actions": [
        {"action": "move", "from": "...", "to": "...", "reason": "..."}
    ]
}"""
        
        user_message = f"Analyze my DeFi portfolio:\n\n{json.dumps(positions, indent=2)}"
        
        if market_context:
            user_message += f"\n\nMarket context: {market_context}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        response = await self.chat(messages, temperature=0.3)
        
        # Try to parse JSON from response
        try:
            content = response.get("content", "")
            # Extract JSON from markdown code block if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content)
        except:
            return {
                "summary": response.get("content", "Analysis failed"),
                "error": "Could not parse structured response"
            }
    
    async def find_opportunities(
        self,
        user_preferences: Dict,
        available_pools: List[Dict],
        current_positions: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Find best yield opportunities matching user preferences.
        """
        system_prompt = """You are a DeFi yield hunter for Techne Finance.
Find the best yield opportunities matching the user's preferences.

Consider:
1. Risk tolerance (from preferences)
2. Preferred chains and protocols
3. APY sustainability (avoid unsustainable high APY)
4. Protocol safety and TVL

Respond in JSON:
{
    "top_opportunities": [
        {
            "pool_id": "...",
            "protocol": "...",
            "chain": "...",
            "apy": 0,
            "risk_score": 0-100,
            "confidence": 0-100,
            "reason": "Why this is a good opportunity"
        }
    ],
    "strategy_suggestion": "Overall strategy recommendation"
}"""
        
        user_message = f"""User preferences: {json.dumps(user_preferences)}

Available pools (top 20):
{json.dumps(available_pools[:20], indent=2)}

Current positions: {json.dumps(current_positions) if current_positions else "None"}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        response = await self.chat(messages, temperature=0.4)
        
        try:
            content = response.get("content", "")
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content)
        except:
            return {
                "top_opportunities": [],
                "strategy_suggestion": response.get("content", "Could not find opportunities"),
                "error": "Could not parse structured response"
            }
    
    async def process_command(
        self,
        user_message: str,
        conversation_history: List[Dict],
        tools: List[Dict],
        user_context: Dict
    ) -> Dict[str, Any]:
        """
        Process natural language command from user.
        Uses Smart Router for cost-effective LLM selection.
        """
        from services.smart_llm_router import get_smart_router
        
        system_prompt = f"""You are the Artisan Agent for Techne Finance, an AI-powered DeFi assistant.
You help users manage their yield farming portfolio through natural conversation.

User context:
- Wallet: {user_context.get('wallet_address', 'Unknown')}
- Autonomy mode: {user_context.get('autonomy_mode', 'advisor')}
- Total portfolio value: ${user_context.get('portfolio_value', 0):,.2f}

You have access to tools to:
1. analyze_portfolio - Get current positions and analysis
2. find_pools - Search for yield opportunities
3. execute_trade - Execute deposits/withdrawals (if autonomy allows)
4. exit_position - Close a position
5. get_market_sentiment - Check market conditions

Be helpful, concise, and proactive. For advisor mode, always explain before acting.
For full_auto mode, you can execute actions directly but still report what you did."""
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history[-10:])  # Last 10 messages for context
        messages.append({"role": "user", "content": user_message})
        
        # Use Smart Router for cost-effective model selection
        router = get_smart_router()
        response = await router.chat(messages, tools=tools, temperature=0.7)
        
        # Log which tier was used
        logger.info(f"[Artisan] Query processed via {response.get('tier_used', 'unknown')} ({response.get('complexity', 'unknown')})")
        
        return response
    
    def get_usage_summary(self) -> Dict:
        """Get API usage summary"""
        return {
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.total_cost
        }
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Singleton instance
_kimi_client: Optional[KimiClient] = None

def get_kimi_client() -> KimiClient:
    """Get or create Kimi client singleton"""
    global _kimi_client
    if _kimi_client is None:
        _kimi_client = KimiClient()
    return _kimi_client


# Artisan Agent tool definitions for Kimi
ARTISAN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_portfolio",
            "description": "Get current portfolio positions with values, APY, and profit/loss analysis",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_pools",
            "description": "Search for yield pools matching criteria",
            "parameters": {
                "type": "object",
                "properties": {
                    "chain": {"type": "string", "description": "Blockchain (Base, Arbitrum, or all)"},
                    "min_apy": {"type": "number", "description": "Minimum APY percentage"},
                    "max_risk": {"type": "string", "enum": ["low", "medium", "high"], "description": "Maximum risk level"},
                    "stablecoin_only": {"type": "boolean", "description": "Only stablecoin pools"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_pool",
            "description": "Get detailed analysis of a specific pool",
            "parameters": {
                "type": "object",
                "properties": {
                    "pool_id": {"type": "string", "description": "Pool ID to analyze"}
                },
                "required": ["pool_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_trade",
            "description": "Execute a trade (deposit, withdraw, or swap)",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["deposit", "withdraw", "swap"]},
                    "pool_id": {"type": "string", "description": "Target pool ID"},
                    "amount_usd": {"type": "number", "description": "Amount in USD"}
                },
                "required": ["action", "pool_id", "amount_usd"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "exit_position",
            "description": "Exit (close) a specific position",
            "parameters": {
                "type": "object",
                "properties": {
                    "position_id": {"type": "string", "description": "Position ID to exit"}
                },
                "required": ["position_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "emergency_exit_all",
            "description": "Exit ALL positions and park funds in Aave USDC (use with caution)",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Reason for emergency exit"}
                },
                "required": ["reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_sentiment",
            "description": "Get current market conditions and sentiment analysis",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_report",
            "description": "Generate and send a portfolio report to the user",
            "parameters": {
                "type": "object",
                "properties": {
                    "report_type": {"type": "string", "enum": ["daily", "weekly", "custom"]}
                },
                "required": ["report_type"]
            }
        }
    }
]
