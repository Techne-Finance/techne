"""
Techne Telegram Bot - Agent Status Service
Real-time monitoring of AI Agent activity
"""

import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime


async def get_agent_status(wallet_address: str) -> Optional[Dict[str, Any]]:
    """
    Get current status of user's AI Agent
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"http://localhost:8000/api/agent/status",
                params={"wallet": wallet_address}
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        print(f"[AgentStatus] Error: {e}")
    return None


async def get_agent_positions(wallet_address: str) -> List[Dict[str, Any]]:
    """
    Get agent's current positions
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"http://localhost:8000/api/agent/positions",
                params={"wallet": wallet_address}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("positions", [])
    except Exception as e:
        print(f"[AgentStatus] Error fetching positions: {e}")
    return []


async def get_agent_history(wallet_address: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get agent's recent transaction history
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"http://localhost:8000/api/agent/history",
                params={"wallet": wallet_address, "limit": limit}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("transactions", [])
    except Exception as e:
        print(f"[AgentStatus] Error fetching history: {e}")
    return []


def format_agent_status(status: Optional[Dict], wallet: str) -> str:
    """
    Format agent status for Telegram message
    """
    if not status:
        return f"""
🤖 *Agent Status*

No active agent found for wallet:
`{wallet[:10]}...{wallet[-6:]}`

Use the Techne web app to deploy your AI Agent.
"""
    
    is_active = status.get("is_active", False)
    agent_address = status.get("agent_address", "Not created")
    strategy = status.get("strategy", "balanced-growth")
    current_action = status.get("current_action", "Idle")
    total_value = status.get("total_value_usd", 0)
    positions_count = status.get("positions_count", 0)
    last_action_time = status.get("last_action_time", "N/A")
    pnl = status.get("pnl_percent", 0)
    
    status_emoji = "🟢" if is_active else "🔴"
    pnl_emoji = "📈" if pnl >= 0 else "📉"
    
    return f"""
🤖 *AI Agent Status*

*Status:* {status_emoji} {'Active' if is_active else 'Inactive'}
*Agent Wallet:* `{agent_address[:10]}...`
*Strategy:* {strategy.replace('-', ' ').title()}

━━━━━━━━━━━━━━━━━━━━

💰 *Portfolio*
├ Total Value: *${total_value:,.2f}*
├ Positions: {positions_count}
└ P&L: {pnl_emoji} {'+' if pnl >= 0 else ''}{pnl:.2f}%

⚡ *Current Action*
{current_action}

🕐 Last activity: {last_action_time}

Use /positions for detailed breakdown
"""


def format_agent_positions(positions: List[Dict]) -> str:
    """
    Format agent positions for Telegram message
    """
    if not positions:
        return """
📊 *Agent Positions*

No active positions.

Your agent will automatically find and enter positions based on your strategy configuration.
"""
    
    lines = ["📊 *Agent Positions*\n"]
    
    total_value = 0
    
    for i, pos in enumerate(positions, 1):
        protocol = pos.get("protocol", "Unknown")
        symbol = pos.get("symbol", "?")
        value = pos.get("value_usd", 0)
        apy = pos.get("apy", 0)
        pnl = pos.get("pnl_percent", 0)
        
        total_value += value
        pnl_emoji = "🟢" if pnl >= 0 else "🔴"
        
        lines.append(
            f"{i}. *{symbol}* ({protocol})\n"
            f"   💵 ${value:,.2f} • {apy:.1f}% APY\n"
            f"   {pnl_emoji} P&L: {'+' if pnl >= 0 else ''}{pnl:.2f}%\n"
        )
    
    lines.append(f"\n*Total Value:* ${total_value:,.2f}")
    lines.append("\nUse /withdraw [position] to exit")
    
    return "\n".join(lines)


def format_agent_action(action: Dict) -> str:
    """
    Format agent action notification
    """
    action_type = action.get("type", "unknown")
    protocol = action.get("protocol", "Unknown")
    symbol = action.get("symbol", "?")
    amount = action.get("amount", 0)
    token = action.get("token", "USDC")
    tx_hash = action.get("tx_hash", "")
    status = action.get("status", "pending")
    
    type_emoji = {
        "deposit": "📥",
        "withdraw": "📤",
        "swap": "🔄",
        "rebalance": "⚖️",
        "harvest": "🌾"
    }.get(action_type, "🤖")
    
    status_emoji = {
        "pending": "⏳",
        "confirmed": "✅",
        "failed": "❌"
    }.get(status, "⏳")
    
    message = f"""
{type_emoji} *Agent {action_type.title()}*

*Pool:* {symbol} on {protocol}
*Amount:* {amount:,.2f} {token}
*Status:* {status_emoji} {status.title()}
"""
    
    if tx_hash and status == "confirmed":
        message += f"\n🔗 [View on Explorer](https://basescan.org/tx/{tx_hash})"
    
    return message


def format_agent_summary(wallet: str, positions: List, history: List) -> str:
    """
    Format comprehensive agent summary
    """
    total_value = sum(p.get("value_usd", 0) for p in positions)
    total_pnl = sum(p.get("pnl_usd", 0) for p in positions)
    recent_actions = len([h for h in history if h.get("timestamp", "")[:10] == datetime.utcnow().strftime("%Y-%m-%d")])
    
    return f"""
🤖 *Agent Summary*

*Wallet:* `{wallet[:10]}...{wallet[-6:]}`

━━━━━━━━━━━━━━━━━━━━

💰 *Portfolio Overview*
├ Total Value: *${total_value:,.2f}*
├ Total P&L: {'🟢' if total_pnl >= 0 else '🔴'} ${total_pnl:,.2f}
├ Active Positions: {len(positions)}
└ Actions Today: {recent_actions}

━━━━━━━━━━━━━━━━━━━━

📋 *Quick Actions*
• /positions - View all positions
• /history - Recent transactions
• /pause - Pause agent
• /resume - Resume agent
"""
