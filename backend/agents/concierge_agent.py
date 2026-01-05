"""
Concierge Agent - "The Face" of Artisan System
User-facing communication and formatting

Responsibilities:
- Translate technical data to human-readable text
- Handle chatbot interactions
- Send Telegram notifications
- Format responses with Artisan personality
- Learn user preferences via Memory Engine
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ConciergeAgent")


class ConciergeAgent:
    """
    The Concierge - User Communication Agent
    Makes data beautiful and understandable
    """
    
    def __init__(self):
        # Artisan personality
        self.personality = {
            "name": "Master Artisan",
            "emoji": "🎩",
            "greeting": "Greetings from the Master Artisan's workshop...",
            "style": "refined_craftsman"
        }
        
        # Response templates
        self.templates = {
            "pool_found": "🔍 {name} has discovered a {quality} opportunity on {chain}...",
            "risk_warning": "⚠️ A word of caution from the workshop: {warning}",
            "verified_badge": "✨ Artisan Verified - This opportunity meets our quality standards.",
            "new_opportunity": "🚀 New Opportunity Alert!\n\n*{pool_name}*\nProtocol: {protocol}\nAPY: {apy}%\nTVL: ${tvl}\nRisk: {risk}",
            "subscription_welcome": "🌟 Welcome to the Artisan's Inner Circle!\nYou now have unlimited access to all opportunities.",
        }
        
        # FAQ responses
        self.faq = {
            "what is il": "Impermanent Loss (IL) occurs when the price of your deposited assets changes compared to when you deposited them. It's called 'impermanent' because it can be reversed if prices return to their original ratio.",
            "what is apy": "APY (Annual Percentage Yield) represents the total return you'd earn in one year, including compound interest. A 20% APY means $1000 would become $1200 after one year.",
            "how to bridge": "To bridge assets to Base:\n1. Visit bridge.base.org\n2. Connect your wallet\n3. Select the token and amount\n4. Confirm the transaction\n\nBridging typically takes 10-20 minutes.",
            "what is zap": "Zap is when the protocol automatically converts your single token into the required LP pair. Instead of manually swapping half your ETH to USDC, the 'Zap' does it for you in one transaction.",
            "is it safe": "Safety in DeFi depends on many factors. We analyze: protocol audits, TVL, APY sustainability, and contract age. Always start with small amounts and never invest more than you can afford to lose.",
        }
        
        # Telegram bot config
        self.telegram_config = {
            "bot_token": None,  # Set via environment
            "enabled": False
        }
        
    # ===========================================
    # POOL FORMATTING
    # ===========================================
    
    def format_pool_card(self, pool: Dict, include_analysis: bool = True) -> str:
        """Format pool data for display"""
        symbol = pool.get("symbol", "Unknown")
        project = pool.get("project", "Unknown").title()
        apy = pool.get("apy", 0)
        tvl = pool.get("tvlUsd", 0)
        risk = pool.get("risk_level", "unknown")
        
        # Format TVL
        tvl_str = self._format_currency(tvl)
        
        # Risk emoji
        risk_emoji = {
            "safe": "🟢",
            "low": "🟢", 
            "moderate": "🟡",
            "elevated": "🟠",
            "high": "🔴",
            "extreme": "🔴",
            "suspicious": "⚠️"
        }.get(risk, "⚪")
        
        # Build card
        card = f"""
**{symbol}** on {project}
{risk_emoji} {risk.title()} Risk

📈 APY: {apy:.1f}%
💰 TVL: {tvl_str}
"""
        
        if include_analysis and pool.get("recommendation"):
            card += f"\n💡 {pool['recommendation']}"
        
        if pool.get("verification_status") == "artisan_verified":
            card += "\n\n✨ Artisan Verified"
        
        return card.strip()
    
    def format_pool_list(self, pools: List[Dict], limit: int = 5) -> str:
        """Format list of pools for display"""
        if not pools:
            return "No opportunities match your criteria at this time."
        
        header = f"🔍 **Top {min(len(pools), limit)} Opportunities**\n\n"
        
        items = []
        for i, pool in enumerate(pools[:limit], 1):
            symbol = pool.get("symbol", "Unknown")
            apy = pool.get("apy", 0)
            risk = pool.get("risk_level", "unknown")
            
            risk_emoji = "🟢" if risk in ["safe", "low"] else "🟡" if risk in ["moderate"] else "🔴"
            
            items.append(f"{i}. **{symbol}** - {apy:.1f}% APY {risk_emoji}")
        
        return header + "\n".join(items)
    
    def format_analysis_response(self, pool: Dict, analysis: Dict) -> str:
        """Format full analysis for premium users"""
        return f"""
{self.personality['emoji']} **Master Artisan's Analysis**

**{pool.get('symbol', 'Unknown')}**
Protocol: {pool.get('project', 'Unknown').title()}
Chain: {pool.get('chain', 'Unknown').title()}

📊 **Metrics**
• APY: {pool.get('apy', 0):.2f}%
• TVL: {self._format_currency(pool.get('tvlUsd', 0))}
• Risk Score: {analysis.get('risk_score', 0)}/100

⚡ **Risk Assessment**
{self._format_risk_level(analysis.get('risk_level', 'unknown'))}

{self._format_warnings(analysis.get('warnings', []))}

💡 **Recommendation**
{analysis.get('recommendation', 'No recommendation available.')}

{self._format_verification(analysis.get('verification_status', 'pending'))}
"""
    
    # ===========================================
    # CHAT RESPONSES
    # ===========================================
    
    def handle_chat_message(self, message: str, user_context: Optional[Dict] = None) -> str:
        """Process user chat message and return response"""
        message_lower = message.lower().strip()
        
        # Check FAQ
        for key, answer in self.faq.items():
            if key in message_lower or any(word in message_lower for word in key.split()):
                return f"{self.personality['emoji']} {answer}"
        
        # Common intents
        if any(word in message_lower for word in ["hello", "hi", "hey"]):
            return f"{self.personality['greeting']}\n\nHow may I assist you today? I can help you find yield opportunities, explain DeFi concepts, or analyze specific pools."
        
        if "help" in message_lower:
            return self._get_help_response()
        
        if any(word in message_lower for word in ["top", "best", "highest"]):
            return "I'd be happy to show you our top opportunities. Let me analyze the current market...\n\n[Use /explore to see top pools]"
        
        if "safe" in message_lower or "low risk" in message_lower:
            return "For safe, conservative yields, I recommend:\n• USDC lending on Aave (5-8% APY)\n• DAI/USDC stable pools (8-15% APY)\n\nThese are Artisan Verified for lower risk."
        
        # Default response
        return f"""
{self.personality['emoji']} I understand you're asking about: "{message}"

I can help with:
• Finding yield opportunities
• Explaining DeFi concepts (IL, APY, bridging)
• Analyzing specific pools
• Risk assessment

What would you like to know more about?
"""
    
    def _get_help_response(self) -> str:
        return f"""
{self.personality['emoji']} **Master Artisan's Help**

Here's what I can help you with:

📊 **Finding Yields**
• "Show me safe stablecoin yields"
• "What are the top opportunities on Base?"
• "Find pools with 20%+ APY"

📚 **Learning DeFi**
• "What is impermanent loss?"
• "How do I bridge to Base?"
• "What is APY?"

🔍 **Analysis**
• "Analyze this pool: [pool name]"
• "Is this APY realistic?"
• "What's the risk?"

💳 **Access**
• Free: Basic pool list
• $0.10: Detailed analysis per pool
• $10/mo: Unlimited access + Telegram alerts

Type your question and I'll do my best to help!
"""
    
    # ===========================================
    # TELEGRAM NOTIFICATIONS
    # ===========================================
    
    def format_telegram_alert(self, alert_type: str, data: Dict) -> str:
        """Format alert for Telegram"""
        if alert_type == "new_pool":
            return f"""
🚀 *New Opportunity Detected!*

*{data.get('symbol', 'Unknown')}*
Protocol: {data.get('project', 'Unknown')}
APY: {data.get('apy', 0):.1f}%
TVL: ${self._format_number(data.get('tvlUsd', 0))}

Risk: {data.get('risk_level', 'Unknown').title()}

[View Details](https://techne.artisan.fi/pool/{data.get('pool', '')})
"""
        
        elif alert_type == "high_apy":
            return f"""
💰 *High Yield Alert!*

*{data.get('symbol', 'Unknown')}*
APY just hit *{data.get('apy', 0):.1f}%* 🔥

⚠️ High APY may be temporary.

[Analyze Now](https://techne.artisan.fi/pool/{data.get('pool', '')})
"""
        
        elif alert_type == "whale":
            return f"""
🐋 *Whale Movement Detected!*

Amount: ${self._format_number(data.get('amount', 0))}
Action: {data.get('action', 'Unknown')}
Pool: {data.get('pool_name', 'Unknown')}

Smart money is moving!
"""
        
        elif alert_type == "apy_drop":
            return f"""
📉 *APY Alert*

*{data.get('symbol', 'Unknown')}*
APY dropped: {data.get('old_apy', 0):.1f}% → {data.get('new_apy', 0):.1f}%

Consider reviewing your position.
"""
        
        return f"📢 {json.dumps(data)}"
    
    # ===========================================
    # HELPERS
    # ===========================================
    
    def _format_currency(self, amount: float) -> str:
        if amount >= 1_000_000_000:
            return f"${amount / 1_000_000_000:.2f}B"
        elif amount >= 1_000_000:
            return f"${amount / 1_000_000:.2f}M"
        elif amount >= 1_000:
            return f"${amount / 1_000:.1f}K"
        else:
            return f"${amount:.2f}"
    
    def _format_number(self, num: float) -> str:
        if num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}K"
        return f"{num:.0f}"
    
    def _format_risk_level(self, level: str) -> str:
        icons = {
            "safe": "🟢 Safe - Low risk, suitable for passive income",
            "low": "🟢 Low - Well-established with good fundamentals",
            "moderate": "🟡 Moderate - Standard DeFi risk level",
            "elevated": "🟠 Elevated - Higher than average risk",
            "high": "🔴 High - Significant risk, monitor closely",
            "extreme": "🔴 Extreme - Very high risk, proceed with caution",
            "suspicious": "⚠️ Suspicious - Not recommended"
        }
        return icons.get(level, f"⚪ {level.title()}")
    
    def _format_warnings(self, warnings: List[str]) -> str:
        if not warnings:
            return "✅ No major warnings detected."
        
        return "⚠️ **Warnings:**\n" + "\n".join(f"• {w}" for w in warnings)
    
    def _format_verification(self, status: str) -> str:
        if status == "artisan_verified":
            return "✨ **Artisan Verified** - Meets our quality standards"
        elif status == "degen_play":
            return "🎰 **Degen Play** - High risk, high reward"
        elif status == "suspicious":
            return "⚠️ **Suspicious** - Proceed with extreme caution"
        return f"📋 Status: {status.replace('_', ' ').title()}"


# Singleton instance
concierge = ConciergeAgent()
