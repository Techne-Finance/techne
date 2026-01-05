"""
Scout Chat - Conversational AI Interface for Scout Agent v2.0 Phase 3
Natural language interface for pool discovery and recommendations

Capabilities:
- Intent recognition (find, compare, recommend, explain, risk_check)
- Entity extraction (chain, asset, apy_min, risk_level)
- Pool search and filtering
- Contextual recommendations
- Multi-turn conversation support
- Memory integration for personalization
- Observability tracing
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import logging

from artisan.data_sources import get_aggregated_pools
from agents.risk_intelligence import get_pool_risk
from agents.yield_predictor import predict_yield

# Memory and Observability integration
try:
    from agents.memory_engine import memory_engine, MemoryType
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

try:
    from agents.observability_engine import observability, traced
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False
    def traced(agent, op):  # Dummy decorator
        def decorator(func):
            return func
        return decorator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ScoutChat")


class ScoutChat:
    """
    Natural language interface for Scout Agent.
    Supports queries like:
    - "Find USDC pools on Solana with >5% APY"
    - "What's the safest stablecoin yield?"
    - "Compare Aave vs Compound for USDC"
    """
    
    # Intent patterns
    INTENT_PATTERNS = {
        "find": [
            r"find\s+", r"show\s+", r"list\s+", r"get\s+", 
            r"search\s+", r"looking\s+for", r"need\s+", r"want\s+"
        ],
        "compare": [
            r"compare\s+", r"versus\s+", r"\bvs\b", r"difference\s+between",
            r"which\s+is\s+better"
        ],
        "recommend": [
            r"recommend", r"suggest", r"best\s+", r"top\s+", 
            r"safest\s+", r"highest\s+", r"what\s+should"
        ],
        "explain": [
            r"explain\s+", r"what\s+is\s+", r"how\s+does\s+", 
            r"tell\s+me\s+about", r"what\s+are\s+"
        ],
        "risk_check": [
            r"is\s+.*\s+safe", r"risk\s+", r"secure\s+", r"audit"
        ]
    }
    
    # Entity patterns
    CHAIN_PATTERNS = {
        "solana": ["solana", "sol", "phantom"],
        "ethereum": ["ethereum", "eth", "mainnet"],
        "base": ["base"],
        "arbitrum": ["arbitrum", "arb"],
        "polygon": ["polygon", "matic"],
        "avalanche": ["avalanche", "avax"],
        "optimism": ["optimism", "op"]
    }
    
    ASSET_PATTERNS = {
        "USDC": ["usdc"],
        "USDT": ["usdt", "tether"],
        "DAI": ["dai"],
        "stablecoin": ["stablecoin", "stable", "dollars", "usd"],
        "ETH": ["eth", "ethereum", "weth"],
        "SOL": ["sol", "solana"]
    }
    
    PROTOCOL_PATTERNS = {
        "aave": ["aave"],
        "compound": ["compound"],
        "morpho": ["morpho"],
        "uniswap": ["uniswap", "uni"],
        "curve": ["curve"],
        "kamino": ["kamino"],
        "orca": ["orca"],
        "raydium": ["raydium"]
    }
    
    def __init__(self):
        self.conversation_history = []
        logger.info("💬 Scout Chat initialized")
    
    async def query(self, message: str, context: Dict[str, Any] = None, user_id: str = "default") -> Dict[str, Any]:
        """
        Process a natural language query and return structured response.
        
        Args:
            message: User's natural language query
            context: Optional conversation context
            user_id: User ID for personalization
            
        Returns:
            Response with answer, pools/data, and suggested follow-ups
        """
        message_lower = message.lower().strip()
        
        # Start trace if observability available
        trace_id = None
        if OBSERVABILITY_AVAILABLE:
            trace_id = observability.start_trace("scout_chat", "query", user_id)
        
        # Get user preferences from memory for personalization
        user_prefs = {}
        best_protocols = []
        if MEMORY_AVAILABLE:
            try:
                user_prefs = await memory_engine.get_user_preferences(user_id)
                best_protocols = await memory_engine.get_best_protocols(user_id, limit=3)
            except:
                pass
        
        # Track conversation
        self.conversation_history.append({
            "role": "user",
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Detect intent
        intent = self._detect_intent(message_lower)
        
        # Extract entities (enhanced with user preferences)
        entities = self._extract_entities(message_lower)
        
        # Apply user preferences if no explicit choice
        if not entities.get("chain") and user_prefs.get("favorite_chain"):
            entities["preferred_chain"] = user_prefs.get("favorite_chain")
        if not entities.get("risk_level") and user_prefs.get("risk_tolerance"):
            entities["preferred_risk"] = user_prefs.get("risk_tolerance")
        
        # Add learned best protocols for recommendations
        entities["learned_protocols"] = [p["protocol"] for p in best_protocols]
        
        # Route to appropriate handler
        if intent == "find":
            response = await self._handle_find(entities, message_lower)
        elif intent == "compare":
            response = await self._handle_compare(entities, message_lower)
        elif intent == "recommend":
            response = await self._handle_recommend(entities, message_lower)
        elif intent == "risk_check":
            response = await self._handle_risk_check(entities, message_lower)
        elif intent == "explain":
            response = await self._handle_explain(entities, message_lower)
        else:
            response = await self._handle_general(entities, message_lower)
        
        # Add personalization info to response
        if best_protocols:
            response["personalization"] = {
                "based_on_history": True,
                "top_protocols": [p["protocol"] for p in best_protocols]
            }
        
        # End trace
        if OBSERVABILITY_AVAILABLE and trace_id:
            observability.end_trace(trace_id)
        
        # Store conversation in memory
        if MEMORY_AVAILABLE:
            try:
                await memory_engine.store(
                    memory_type=MemoryType.CONVERSATION,
                    content={
                        "intent": intent,
                        "query": message,
                        "entities": entities,
                        "success": response.get("success", True)
                    },
                    user_id=user_id,
                    agent_id="scout_chat"
                )
            except:
                pass
        
        # Add to history
        self.conversation_history.append({
            "role": "assistant",
            "message": response.get("text", ""),
            "timestamp": datetime.now().isoformat()
        })
        
        return response
    
    def _detect_intent(self, message: str) -> str:
        """Detect the primary intent of the message"""
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    return intent
        return "general"
    
    def _extract_entities(self, message: str) -> Dict[str, Any]:
        """Extract entities like chain, asset, APY thresholds, etc."""
        entities = {
            "chain": None,
            "asset": None,
            "protocols": [],
            "min_apy": None,
            "max_apy": None,
            "risk_level": None
        }
        
        # Extract chain
        for chain, patterns in self.CHAIN_PATTERNS.items():
            if any(p in message for p in patterns):
                entities["chain"] = chain.capitalize()
                break
        
        # Extract asset
        for asset, patterns in self.ASSET_PATTERNS.items():
            if any(p in message for p in patterns):
                entities["asset"] = asset
                break
        
        # Extract protocols
        for protocol, patterns in self.PROTOCOL_PATTERNS.items():
            if any(p in message for p in patterns):
                entities["protocols"].append(protocol)
        
        # Extract APY thresholds
        apy_match = re.search(r"(\d+(?:\.\d+)?)\s*%", message)
        if apy_match:
            apy_value = float(apy_match.group(1))
            if "over" in message or "above" in message or ">" in message or "more than" in message:
                entities["min_apy"] = apy_value
            elif "under" in message or "below" in message or "<" in message or "less than" in message:
                entities["max_apy"] = apy_value
            else:
                entities["min_apy"] = apy_value  # Default to minimum
        
        # Extract risk preference
        if "safe" in message or "low risk" in message:
            entities["risk_level"] = "low"
        elif "high risk" in message or "aggressive" in message:
            entities["risk_level"] = "high"
        
        return entities
    
    async def _handle_find(self, entities: Dict, message: str) -> Dict[str, Any]:
        """Handle pool search queries"""
        chain = entities.get("chain") or "all"
        asset = entities.get("asset")
        min_apy = entities.get("min_apy") or 0
        
        # Determine asset type for API
        if asset in ["USDC", "USDT", "DAI", "stablecoin"]:
            asset_type = "stablecoin"
        elif asset == "ETH":
            asset_type = "eth"
        elif asset == "SOL":
            asset_type = "sol"
        else:
            asset_type = "all"
        
        # Fetch pools
        try:
            chains = [chain] if chain != "all" else ["Base", "Ethereum", "Solana"]
            all_pools = []
            
            for c in chains:
                result = await get_aggregated_pools(
                    chain=c,
                    min_tvl=100000,
                    min_apy=min_apy,
                    stablecoin_only=(asset_type == "stablecoin"),
                    limit=20,
                    blur=False
                )
                all_pools.extend(result.get("combined", []))
            
            # Filter by risk if specified
            if entities.get("risk_level") == "low":
                all_pools = [p for p in all_pools if p.get("apy", 0) < 15]
            
            # Sort by APY
            all_pools.sort(key=lambda p: p.get("apy", 0), reverse=True)
            pools = all_pools[:10]
            
            if not pools:
                return {
                    "intent": "find",
                    "success": False,
                    "text": f"No pools found matching your criteria. Try adjusting filters.",
                    "pools": [],
                    "suggestions": [
                        "Find stablecoin pools on Base",
                        "Show me the highest yields",
                        "Find safe USDC pools"
                    ]
                }
            
            # Generate response text
            top_pool = pools[0]
            text = f"Found {len(pools)} pools matching your search. "
            text += f"Top result: **{top_pool.get('project')}** on {top_pool.get('chain')} "
            text += f"with **{top_pool.get('apy', 0):.2f}% APY** and ${top_pool.get('tvl', 0)/1e6:.1f}M TVL."
            
            return {
                "intent": "find",
                "success": True,
                "text": text,
                "entities": entities,
                "pools": pools,
                "count": len(pools),
                "suggestions": [
                    f"Tell me more about {top_pool.get('project')}",
                    f"Is {top_pool.get('project')} safe?",
                    "Show pools with higher TVL"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in find handler: {e}")
            return {
                "intent": "find",
                "success": False,
                "text": f"Error searching pools: {str(e)}",
                "pools": []
            }
    
    async def _handle_compare(self, entities: Dict, message: str) -> Dict[str, Any]:
        """Handle protocol comparison queries"""
        protocols = entities.get("protocols", [])
        
        if len(protocols) < 2:
            # Extract from message pattern "X vs Y"
            vs_match = re.search(r"(\w+)\s+(?:vs|versus|or)\s+(\w+)", message, re.IGNORECASE)
            if vs_match:
                protocols = [vs_match.group(1).lower(), vs_match.group(2).lower()]
        
        if len(protocols) < 2:
            return {
                "intent": "compare",
                "success": False,
                "text": "Please specify two protocols to compare, e.g., 'Compare Aave vs Compound'",
                "suggestions": [
                    "Compare Aave vs Compound",
                    "Compare Morpho vs Aave",
                    "Compare Kamino vs Marginfi"
                ]
            }
        
        # Fetch pools for each protocol
        comparisons = []
        for proto in protocols[:2]:
            result = await get_aggregated_pools(
                chain="all",
                min_tvl=0,
                limit=50,
                blur=False
            )
            
            proto_pools = [
                p for p in result.get("combined", [])
                if proto in p.get("project", "").lower()
            ]
            
            if proto_pools:
                avg_apy = sum(p.get("apy", 0) for p in proto_pools) / len(proto_pools)
                total_tvl = sum(p.get("tvl", 0) for p in proto_pools)
                
                # Get risk score
                risk_data = await get_pool_risk(proto_pools[0])
                
                comparisons.append({
                    "protocol": proto,
                    "pools": len(proto_pools),
                    "avg_apy": round(avg_apy, 2),
                    "total_tvl": total_tvl,
                    "risk_score": risk_data.get("overall_score", 0),
                    "risk_level": risk_data.get("risk_level", "Unknown")
                })
        
        if len(comparisons) < 2:
            return {
                "intent": "compare",
                "success": False,
                "text": "Could not find data for both protocols.",
                "suggestions": ["Try different protocols"]
            }
        
        # Generate comparison text
        p1, p2 = comparisons[:2]
        winner_apy = p1 if p1["avg_apy"] > p2["avg_apy"] else p2
        winner_safety = p1 if p1["risk_score"] > p2["risk_score"] else p2
        
        text = f"**{p1['protocol'].title()}** vs **{p2['protocol'].title()}**:\n\n"
        text += f"📈 APY: {p1['protocol'].title()} ({p1['avg_apy']}%) vs {p2['protocol'].title()} ({p2['avg_apy']}%)\n"
        text += f"💰 TVL: ${p1['total_tvl']/1e6:.0f}M vs ${p2['total_tvl']/1e6:.0f}M\n"
        text += f"🛡️ Safety: {p1['risk_level']} ({p1['risk_score']}) vs {p2['risk_level']} ({p2['risk_score']})\n\n"
        text += f"**For yield**: {winner_apy['protocol'].title()} offers higher APY\n"
        text += f"**For safety**: {winner_safety['protocol'].title()} has better risk score"
        
        return {
            "intent": "compare",
            "success": True,
            "text": text,
            "comparisons": comparisons,
            "winner_apy": winner_apy["protocol"],
            "winner_safety": winner_safety["protocol"],
            "suggestions": [
                f"Show {winner_apy['protocol']} pools",
                f"Is {winner_safety['protocol']} audited?",
                "Find similar protocols"
            ]
        }
    
    async def _handle_recommend(self, entities: Dict, message: str) -> Dict[str, Any]:
        """Handle recommendation queries"""
        # Determine what they want recommended
        if "safe" in message or "safest" in message:
            criteria = "safety"
        elif "high" in message or "highest" in message or "best" in message:
            criteria = "apy"
        else:
            criteria = "balanced"
        
        chain = entities.get("chain") or "all"
        asset = entities.get("asset") or "stablecoin"
        
        # Fetch pools
        chains = [chain] if chain != "all" else ["Base", "Ethereum", "Solana"]
        all_pools = []
        
        for c in chains:
            result = await get_aggregated_pools(
                chain=c,
                min_tvl=1000000,  # Higher TVL for recommendations
                stablecoin_only=(asset in ["stablecoin", "USDC", "USDT", "DAI"]),
                limit=30,
                blur=False
            )
            all_pools.extend(result.get("combined", []))
        
        if not all_pools:
            return {
                "intent": "recommend",
                "success": False,
                "text": "No suitable pools found for recommendations.",
                "pools": []
            }
        
        # Get risk scores
        for pool in all_pools:
            risk = await get_pool_risk(pool)
            pool["risk_score"] = risk.get("overall_score", 50)
            pool["risk_level"] = risk.get("risk_level", "Medium")
        
        # Sort by criteria
        if criteria == "safety":
            all_pools.sort(key=lambda p: p.get("risk_score", 0), reverse=True)
            all_pools = [p for p in all_pools if p.get("risk_score", 0) >= 70]
        elif criteria == "apy":
            all_pools.sort(key=lambda p: p.get("apy", 0), reverse=True)
        else:
            # Balanced: score = APY * risk_score
            for p in all_pools:
                p["balanced_score"] = p.get("apy", 0) * (p.get("risk_score", 50) / 100)
            all_pools.sort(key=lambda p: p.get("balanced_score", 0), reverse=True)
        
        top_pool = all_pools[0] if all_pools else None
        
        if not top_pool:
            return {
                "intent": "recommend",
                "success": False,
                "text": "Could not generate recommendations with current criteria.",
                "pools": []
            }
        
        text = f"🎯 **My recommendation**: **{top_pool.get('project')}** on {top_pool.get('chain')}\n\n"
        text += f"• APY: **{top_pool.get('apy', 0):.2f}%**\n"
        text += f"• TVL: ${top_pool.get('tvl', 0)/1e6:.1f}M\n"
        text += f"• Risk: {top_pool.get('risk_level')} ({top_pool.get('risk_score')}/100)\n"
        text += f"• Asset: {top_pool.get('symbol')}\n\n"
        
        if criteria == "safety":
            text += "This is the safest option meeting your criteria."
        elif criteria == "apy":
            text += "This offers the highest yield in its category."
        else:
            text += "This offers the best balance of yield and safety."
        
        return {
            "intent": "recommend",
            "success": True,
            "text": text,
            "recommended_pool": top_pool,
            "criteria": criteria,
            "alternatives": all_pools[1:4],
            "suggestions": [
                f"Is {top_pool.get('project')} audited?",
                "Show alternative options",
                "What about higher APY options?"
            ]
        }
    
    async def _handle_risk_check(self, entities: Dict, message: str) -> Dict[str, Any]:
        """Handle risk/safety check queries"""
        # Extract protocol name
        protocol = entities.get("protocols")[0] if entities.get("protocols") else None
        
        if not protocol:
            # Try to extract from message
            word_match = re.search(r"is\s+(\w+)\s+safe", message, re.IGNORECASE)
            if word_match:
                protocol = word_match.group(1).lower()
        
        if not protocol:
            return {
                "intent": "risk_check",
                "success": False,
                "text": "Please specify a protocol to check, e.g., 'Is Aave safe?'",
                "suggestions": [
                    "Is Aave safe?",
                    "Check Compound risk",
                    "Is Morpho audited?"
                ]
            }
        
        # Create mock pool for risk check
        mock_pool = {
            "project": protocol,
            "tvl": 100_000_000,
            "apy": 5.0,
            "chain": "Unknown"
        }
        
        risk_data = await get_pool_risk(mock_pool)
        
        score = risk_data.get("overall_score", 0)
        level = risk_data.get("risk_level", "Unknown")
        
        if score >= 80:
            verdict = f"✅ **{protocol.title()}** is considered **safe** with a risk score of {score}/100."
        elif score >= 60:
            verdict = f"⚠️ **{protocol.title()}** has **moderate risk** with a score of {score}/100."
        else:
            verdict = f"🚨 **{protocol.title()}** is considered **high risk** with a score of {score}/100."
        
        factors = risk_data.get("factors", {})
        text = verdict + "\n\n**Risk Breakdown:**\n"
        
        for factor_name, factor_data in factors.items():
            text += f"• {factor_name.replace('_', ' ').title()}: {factor_data.get('score', 0)}/100 - {factor_data.get('reason', '')}\n"
        
        if risk_data.get("warnings"):
            text += "\n**⚠️ Warnings:**\n"
            for warning in risk_data.get("warnings", [])[:3]:
                text += f"• {warning}\n"
        
        return {
            "intent": "risk_check",
            "success": True,
            "text": text,
            "protocol": protocol,
            "risk_data": risk_data,
            "suggestions": [
                f"Find {protocol} pools",
                "Compare to similar protocols",
                "Show safer alternatives"
            ]
        }
    
    async def _handle_explain(self, entities: Dict, message: str) -> Dict[str, Any]:
        """Handle explanation queries"""
        # Simple keyword-based explanations
        explanations = {
            "apy": "**APY (Annual Percentage Yield)** is the yearly return on your deposit, including compound interest. A 10% APY means $100 becomes ~$110 after one year.",
            "tvl": "**TVL (Total Value Locked)** is the total amount of money deposited in a protocol. Higher TVL often indicates more trust and stability.",
            "impermanent loss": "**Impermanent Loss (IL)** occurs in liquidity pools when the price ratio of paired assets changes. The more the ratio changes, the greater the loss compared to just holding.",
            "risk score": "**Risk Score** (0-100) assesses a pool's safety based on: TVL stability, protocol age, audits, APY sustainability, and smart contract reputation. Higher = safer.",
            "stablecoin": "**Stablecoins** are cryptocurrencies pegged to a stable asset like USD. Examples: USDC, USDT, DAI. They're popular for yield farming with lower volatility risk.",
            "lending": "**Lending protocols** (like Aave, Compound) let you deposit assets to earn interest from borrowers. Generally safer than LPs but lower yields.",
            "lp": "**LP (Liquidity Pools)** involve providing two assets to enable trading. Higher yields but exposure to impermanent loss."
        }
        
        for topic, explanation in explanations.items():
            if topic in message.lower():
                return {
                    "intent": "explain",
                    "success": True,
                    "text": explanation,
                    "topic": topic,
                    "suggestions": [
                        "Find high APY pools",
                        "Show safest options",
                        "Explain impermanent loss"
                    ]
                }
        
        return {
            "intent": "explain",
            "success": False,
            "text": "I can explain: APY, TVL, impermanent loss, risk score, stablecoins, lending, and LP pools. What would you like to know about?",
            "suggestions": [
                "What is APY?",
                "Explain impermanent loss",
                "What is TVL?"
            ]
        }
    
    async def _handle_general(self, entities: Dict, message: str) -> Dict[str, Any]:
        """Handle general queries that don't match specific intents"""
        return {
            "intent": "general",
            "success": True,
            "text": "I'm Scout, your DeFi yield assistant! I can help you:\n\n"
                   "🔍 **Find pools**: 'Find USDC pools on Solana'\n"
                   "⚖️ **Compare protocols**: 'Compare Aave vs Compound'\n"
                   "🎯 **Get recommendations**: 'What's the safest yield?'\n"
                   "🛡️ **Check risks**: 'Is Morpho safe?'\n"
                   "📚 **Learn concepts**: 'What is APY?'\n\n"
                   "What would you like to do?",
            "suggestions": [
                "Find the best stablecoin yields",
                "What's the safest pool right now?",
                "Compare Aave vs Morpho"
            ]
        }


# Singleton instance
scout_chat = ScoutChat()


# Convenience function
async def chat_query(message: str, context: Dict = None) -> Dict[str, Any]:
    """Process a chat query"""
    return await scout_chat.query(message, context)
