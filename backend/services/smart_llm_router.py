"""
Smart LLM Router for Artisan Agent
Automatically routes queries to the most cost-effective model

Tier System:
- Tier 1 (Free/Cheap): Groq Llama 3.3 70B or OpenRouter - simple queries
- Tier 2 (Low Cost): GPT-4o-mini or DeepSeek - medium complexity  
- Tier 3 (Premium): Kimi K2.5 - complex analysis, multi-step reasoning

OpenRouter: Single API for multiple cheap models (Llama, Mistral, Gemma, etc.)
Cost savings: ~80% of queries can use Tier 1-2
"""

import os
import re
import httpx
import logging
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger("SmartRouter")


class QueryComplexity(Enum):
    """Query complexity levels"""
    SIMPLE = "simple"      # Balance check, status, basic info
    MEDIUM = "medium"      # Pool comparison, single analysis
    COMPLEX = "complex"    # Multi-step reasoning, market analysis, rebalancing


class LLMTier(Enum):
    """LLM tiers by cost"""
    GROQ = "groq"             # Free/cheap - Llama 3.3 70B
    OPENROUTER = "openrouter" # Cheap - Many models via one API
    DEEPSEEK = "deepseek"     # Very cheap - DeepSeek V3
    GPT4_MINI = "gpt4-mini"   # Low cost - GPT-4o-mini
    KIMI = "kimi"             # Premium - Kimi K2.5


# Complexity detection patterns
SIMPLE_PATTERNS = [
    r"balance",
    r"status",
    r"show",
    r"list",
    r"what is",
    r"how much",
    r"price",
    r"apy",
    r"help",
    r"settings",
    r"mode"
]

COMPLEX_PATTERNS = [
    r"analyze",
    r"rebalance",
    r"strategy",
    r"compare.*multiple",
    r"market.*analysis",
    r"predict",
    r"should i",
    r"recommend",
    r"optimize",
    r"emergency",
    r"exit all",
    r"find.*best"
]


class SmartLLMRouter:
    """
    Routes queries to the most cost-effective LLM.
    
    Usage:
        router = SmartLLMRouter()
        response = await router.chat(messages, tools=tools)
    """
    
    def __init__(self):
        # API Keys
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.kimi_key = os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY")
        
        # HTTP clients
        self.clients: Dict[LLMTier, httpx.AsyncClient] = {}
        self._init_clients()
        
        # Usage tracking
        self.usage_stats = {
            "groq": {"calls": 0, "tokens": 0, "cost": 0.0},
            "openrouter": {"calls": 0, "tokens": 0, "cost": 0.0},
            "deepseek": {"calls": 0, "tokens": 0, "cost": 0.0},
            "gpt4-mini": {"calls": 0, "tokens": 0, "cost": 0.0},
            "kimi": {"calls": 0, "tokens": 0, "cost": 0.0}
        }
    
    def _init_clients(self):
        """Initialize HTTP clients for each provider"""
        if self.groq_key:
            self.clients[LLMTier.GROQ] = httpx.AsyncClient(
                base_url="https://api.groq.com/openai/v1",
                headers={"Authorization": f"Bearer {self.groq_key}"},
                timeout=60.0
            )
        
        if self.openrouter_key:
            self.clients[LLMTier.OPENROUTER] = httpx.AsyncClient(
                base_url="https://openrouter.ai/api/v1",
                headers={
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "HTTP-Referer": "https://techne.finance",
                    "X-Title": "Techne Finance"
                },
                timeout=60.0
            )
        
        if self.deepseek_key:
            self.clients[LLMTier.DEEPSEEK] = httpx.AsyncClient(
                base_url="https://api.deepseek.com/v1",
                headers={"Authorization": f"Bearer {self.deepseek_key}"},
                timeout=60.0
            )
        
        if self.openai_key:
            self.clients[LLMTier.GPT4_MINI] = httpx.AsyncClient(
                base_url="https://api.openai.com/v1",
                headers={"Authorization": f"Bearer {self.openai_key}"},
                timeout=60.0
            )
        
        if self.kimi_key:
            self.clients[LLMTier.KIMI] = httpx.AsyncClient(
                base_url="https://api.moonshot.cn/v1",
                headers={"Authorization": f"Bearer {self.kimi_key}"},
                timeout=120.0
            )
    
    def detect_complexity(self, query: str) -> QueryComplexity:
        """
        Detect query complexity based on patterns.
        
        Args:
            query: User's message
            
        Returns:
            QueryComplexity level
        """
        query_lower = query.lower()
        
        # Check for complex patterns first
        for pattern in COMPLEX_PATTERNS:
            if re.search(pattern, query_lower):
                return QueryComplexity.COMPLEX
        
        # Check for simple patterns
        for pattern in SIMPLE_PATTERNS:
            if re.search(pattern, query_lower):
                return QueryComplexity.SIMPLE
        
        # Default to medium
        return QueryComplexity.MEDIUM
    
    def select_tier(
        self,
        complexity: QueryComplexity,
        requires_tools: bool = False
    ) -> LLMTier:
        """
        Select the best LLM tier based on complexity and requirements.
        
        Args:
            complexity: Query complexity
            requires_tools: Whether tool calling is needed
            
        Returns:
            Selected LLM tier
        """
        # Complex queries always use Kimi
        if complexity == QueryComplexity.COMPLEX:
            if LLMTier.KIMI in self.clients:
                return LLMTier.KIMI
            elif LLMTier.GPT4_MINI in self.clients:
                return LLMTier.GPT4_MINI
        
        # Simple queries prefer Groq (free) or OpenRouter
        if complexity == QueryComplexity.SIMPLE:
            if LLMTier.GROQ in self.clients:
                return LLMTier.GROQ
            elif LLMTier.OPENROUTER in self.clients:
                return LLMTier.OPENROUTER
            elif LLMTier.DEEPSEEK in self.clients:
                return LLMTier.DEEPSEEK
        
        # Medium or tool-requiring queries
        if requires_tools:
            # Tool calling works best with GPT-4o-mini or Kimi
            if LLMTier.GPT4_MINI in self.clients:
                return LLMTier.GPT4_MINI
            elif LLMTier.KIMI in self.clients:
                return LLMTier.KIMI
        
        # Fallback chain: OpenRouter → DeepSeek → GPT-4o-mini → Groq → Kimi
        for tier in [LLMTier.OPENROUTER, LLMTier.DEEPSEEK, LLMTier.GPT4_MINI, LLMTier.GROQ, LLMTier.KIMI]:
            if tier in self.clients:
                return tier
        
        raise RuntimeError("No LLM provider configured!")
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        force_tier: Optional[LLMTier] = None
    ) -> Dict[str, Any]:
        """
        Send chat request to the optimal LLM.
        
        Args:
            messages: Chat messages
            tools: Optional tool definitions
            temperature: Creativity
            max_tokens: Max response length
            force_tier: Force specific tier (bypass auto-selection)
            
        Returns:
            Response with content, tool_calls, and tier used
        """
        # Extract query from last user message
        query = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                query = msg.get("content", "")
                break
        
        # Detect complexity and select tier
        complexity = self.detect_complexity(query)
        tier = force_tier or self.select_tier(complexity, requires_tools=bool(tools))
        
        logger.info(f"[SmartRouter] Query: '{query[:50]}...' → Complexity: {complexity.value} → Tier: {tier.value}")
        
        # Build request
        client = self.clients.get(tier)
        if not client:
            return {"error": f"No client for tier {tier.value}"}
        
        model = self._get_model_name(tier)
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if tools and tier in [LLMTier.GPT4_MINI, LLMTier.KIMI]:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        try:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Track usage
            self._track_usage(tier, data.get("usage", {}))
            
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            
            return {
                "content": message.get("content", ""),
                "tool_calls": message.get("tool_calls", []),
                "finish_reason": choice.get("finish_reason"),
                "tier_used": tier.value,
                "complexity": complexity.value,
                "model": model,
                "usage": data.get("usage", {})
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[SmartRouter] {tier.value} error: {e.response.status_code}")
            
            # Fallback to next tier
            fallback = self._get_fallback_tier(tier)
            if fallback:
                logger.info(f"[SmartRouter] Falling back to {fallback.value}")
                return await self.chat(messages, tools, temperature, max_tokens, force_tier=fallback)
            
            return {"error": str(e), "content": "I'm having trouble processing your request."}
            
        except Exception as e:
            logger.error(f"[SmartRouter] Error: {e}")
            return {"error": str(e), "content": "An error occurred."}
    
    def _get_model_name(self, tier: LLMTier) -> str:
        """Get model name for tier"""
        return {
            LLMTier.GROQ: "llama-3.3-70b-versatile",
            LLMTier.OPENROUTER: "meta-llama/llama-3.3-70b-instruct",  # Cheap via OpenRouter
            LLMTier.DEEPSEEK: "deepseek-chat",
            LLMTier.GPT4_MINI: "gpt-4o-mini",
            LLMTier.KIMI: "moonshot-v1-auto"
        }.get(tier, "gpt-4o-mini")
    
    def _get_fallback_tier(self, current: LLMTier) -> Optional[LLMTier]:
        """Get fallback tier if current fails"""
        fallback_chain = {
            LLMTier.GROQ: LLMTier.OPENROUTER,
            LLMTier.OPENROUTER: LLMTier.DEEPSEEK,
            LLMTier.DEEPSEEK: LLMTier.GPT4_MINI,
            LLMTier.GPT4_MINI: LLMTier.KIMI,
            LLMTier.KIMI: None
        }
        fallback = fallback_chain.get(current)
        if fallback and fallback in self.clients:
            return fallback
        return None
    
    def _track_usage(self, tier: LLMTier, usage: Dict):
        """Track token usage and costs"""
        tokens = usage.get("total_tokens", 0)
        self.usage_stats[tier.value]["calls"] += 1
        self.usage_stats[tier.value]["tokens"] += tokens
        
        # Approximate costs per 1M tokens
        costs = {
            "groq": 0.0,        # Free tier
            "openrouter": 0.10, # Very cheap via OpenRouter
            "deepseek": 0.14,
            "gpt4-mini": 0.15,
            "kimi": 0.55
        }
        
        cost = tokens * costs.get(tier.value, 0.5) / 1_000_000
        self.usage_stats[tier.value]["cost"] += cost
    
    def get_usage_summary(self) -> Dict:
        """Get usage summary with costs"""
        total_calls = sum(s["calls"] for s in self.usage_stats.values())
        total_cost = sum(s["cost"] for s in self.usage_stats.values())
        
        return {
            "by_tier": self.usage_stats,
            "total_calls": total_calls,
            "total_cost_usd": total_cost,
            "savings_estimate": f"~${total_cost * 0.8:.2f} saved vs Kimi-only"
        }
    
    async def close(self):
        """Close all HTTP clients"""
        for client in self.clients.values():
            await client.aclose()


# Singleton
_router: Optional[SmartLLMRouter] = None

def get_smart_router() -> SmartLLMRouter:
    """Get or create Smart Router singleton"""
    global _router
    if _router is None:
        _router = SmartLLMRouter()
    return _router
