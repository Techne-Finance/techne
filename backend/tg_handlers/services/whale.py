"""
Techne Telegram Bot - Whale Tracking Service
Monitors large transactions and whale movements
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime


class WhaleTracker:
    """Tracks whale movements across DeFi protocols"""
    
    def __init__(self):
        self.min_whale_amount = 100000  # $100K minimum for whale
        self.mega_whale_amount = 1000000  # $1M for mega whale
        self._recent_whales: List[Dict] = []
    
    async def fetch_recent_whales(self, chain: str = "Base", hours: int = 24) -> List[Dict]:
        """
        Fetch recent whale transactions
        In production, this would connect to chain indexers
        """
        # Simulated whale data for MVP
        whales = [
            {
                "type": "deposit",
                "protocol": "Aave",
                "chain": "Base",
                "amount": 2500000,
                "token": "USDC",
                "wallet": "0x1234...abcd",
                "timestamp": datetime.utcnow().isoformat(),
                "tx_hash": "0xabc...123"
            },
            {
                "type": "withdraw",
                "protocol": "Compound",
                "chain": "Base",
                "amount": 1800000,
                "token": "USDC",
                "wallet": "0x5678...efgh",
                "timestamp": datetime.utcnow().isoformat(),
                "tx_hash": "0xdef...456"
            },
            {
                "type": "deposit",
                "protocol": "Aerodrome",
                "chain": "Base",
                "amount": 500000,
                "token": "ETH",
                "wallet": "0x9abc...ijkl",
                "timestamp": datetime.utcnow().isoformat(),
                "tx_hash": "0xghi...789"
            }
        ]
        
        # Filter by chain
        if chain and chain.lower() != "all":
            whales = [w for w in whales if w["chain"].lower() == chain.lower()]
        
        return whales
    
    def format_whale_alert(self, whale: Dict) -> str:
        """Format a whale movement as alert message"""
        amount = whale.get("amount", 0)
        emoji = "🐋" if amount >= self.mega_whale_amount else "🐳"
        action_emoji = "📥" if whale.get("type") == "deposit" else "📤"
        
        amount_str = f"${amount/1_000_000:.1f}M" if amount >= 1_000_000 else f"${amount/1_000:.0f}K"
        
        return f"""
{emoji} *Whale Alert!*

{action_emoji} *{whale.get('type', 'unknown').title()}* detected

*Protocol:* {whale.get('protocol', 'Unknown')}
*Amount:* {amount_str} {whale.get('token', '')}
*Chain:* {whale.get('chain', 'Unknown')}

🔗 [View TX](https://basescan.org/tx/{whale.get('tx_hash', '')})

_Smart money is moving!_
"""
    
    def format_whale_list(self, whales: List[Dict]) -> str:
        """Format list of whale movements"""
        if not whales:
            return "🐋 No whale movements in the last 24h matching your filters."
        
        lines = ["🐋 *Recent Whale Movements*\n"]
        
        for w in whales[:5]:
            amount = w.get("amount", 0)
            amount_str = f"${amount/1_000_000:.1f}M" if amount >= 1_000_000 else f"${amount/1_000:.0f}K"
            action = "📥" if w.get("type") == "deposit" else "📤"
            
            lines.append(
                f"{action} *{amount_str}* {w.get('token', '')} → {w.get('protocol', '?')}\n"
            )
        
        lines.append(f"\n_Showing {min(len(whales), 5)} of {len(whales)} movements_")
        return "\n".join(lines)


# Global tracker instance
whale_tracker = WhaleTracker()
