"""
Techne Telegram Bot - News & Alpha Aggregator
Aggregates DeFi news, macro updates, and security alerts
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# ===========================================
# Verified X/Twitter Sources for Aggregation
# ===========================================

X_SOURCES = {
    # Airdrop Intel
    "airdrop": [
        {"handle": "@defi_airdrops", "name": "DeFi Airdrops", "type": "airdrop"},
        {"handle": "@airdrops_one", "name": "Airdrops One", "type": "airdrop"},
        {"handle": "@heycape_", "name": "Cape", "type": "airdrop"},
    ],
    
    # DeFi Analytics & Data
    "defi": [
        {"handle": "@DefiLlama", "name": "DefiLlama", "type": "analytics", "verified": True},
        {"handle": "@0xngmi", "name": "0xngmi (DefiLlama founder)", "type": "dev", "verified": True},
        {"handle": "@definalist", "name": "DeFi Nalist", "type": "analytics"},
        {"handle": "@tokenomist_ai", "name": "Tokenomist AI", "type": "analytics"},
    ],
    
    # News & Intel
    "news": [
        {"handle": "@solidintel_x", "name": "Solid Intel", "type": "news", "followers": "89K"},
        {"handle": "@WalterBloomberg", "name": "Walter Bloomberg", "type": "news", "followers": "800K", "note": "Aggregator, verify news"},
        {"handle": "@tree_news_feed", "name": "Tree News Feed", "type": "news"},
        {"handle": "@LiveSquawk", "name": "LiveSquawk", "type": "macro"},
    ],
    
    # Whale & Trading
    "whale": [
        {"handle": "@whaletrades", "name": "Whale Trades", "type": "whale"},
        {"handle": "@0xsleuth_", "name": "0xSleuth", "type": "onchain"},
        {"handle": "@degeneratenews", "name": "Degenerate News", "type": "trading"},
    ],
    
    # Alpha & Research
    "alpha": [
        {"handle": "@cryptophileee", "name": "Cryptophile", "type": "alpha"},
        {"handle": "@hooeem", "name": "Hooeem", "type": "alpha"},
        {"handle": "@mi_zielono", "name": "Mi Zielono", "type": "alpha"},
    ],
}

# All sources flattened for iteration
ALL_X_SOURCES = [
    source for category in X_SOURCES.values() for source in category
]


@dataclass
class NewsItem:
    """A news item"""
    title: str
    summary: str
    category: str  # "macro", "defi", "security", "airdrop", "protocol"
    source: str
    url: Optional[str]
    timestamp: datetime
    importance: int  # 1-5
    protocols: List[str]  # Related protocols


class NewsAggregator:
    """
    Aggregates news from multiple sources:
    - Macro: Fed announcements, CPI, jobs data
    - DeFi: Protocol updates, TVL changes, new launches
    - Security: Hacks, exploits, rug pulls (from Rekt News, etc.)
    - Airdrop: Token launches, snapshot dates
    """
    
    # In production, these would be fetched from APIs
    # For MVP, curated list that would be updated periodically
    
    def __init__(self):
        self._news_cache: List[NewsItem] = []
        self._last_fetch: Optional[datetime] = None
    
    async def fetch_latest_news(self) -> List[NewsItem]:
        """
        Fetch latest news from all sources
        In production, this would call:
        - CoinGecko/CoinMarketCap for market data
        - DeFiLlama for protocol updates
        - Rekt News API for security
        - Twitter/X API for alpha
        """
        
        # Curated news items (would be real API calls in production)
        news = [
            # Macro news
            NewsItem(
                title="Fed Holds Rates Steady at 5.25-5.50%",
                summary="Federal Reserve maintains interest rates, signals possible cuts in 2024. Crypto markets react positively.",
                category="macro",
                source="Federal Reserve",
                url="https://federalreserve.gov",
                timestamp=datetime.utcnow() - timedelta(hours=6),
                importance=5,
                protocols=[]
            ),
            NewsItem(
                title="Bitcoin ETF Inflows Hit $500M Daily",
                summary="BlackRock and Fidelity Bitcoin ETFs see massive institutional inflows. Total AUM exceeds $30B.",
                category="macro",
                source="Bloomberg",
                url="https://bloomberg.com",
                timestamp=datetime.utcnow() - timedelta(hours=3),
                importance=5,
                protocols=["bitcoin"]
            ),
            NewsItem(
                title="US CPI Data: Inflation at 3.1%",
                summary="Core inflation continues to decline, supporting rate cut expectations for Q2.",
                category="macro",
                source="BLS",
                url="https://bls.gov",
                timestamp=datetime.utcnow() - timedelta(hours=12),
                importance=4,
                protocols=[]
            ),
            
            # DeFi protocol news
            NewsItem(
                title="EigenLayer Season 2 Points Program Ending",
                summary="EigenLayer hints at token launch. Current stakers will receive proportional allocation based on points.",
                category="airdrop",
                source="@eigenlayer",
                url="https://twitter.com/eigenlayer",
                timestamp=datetime.utcnow() - timedelta(hours=2),
                importance=5,
                protocols=["eigenlayer"]
            ),
            NewsItem(
                title="Aerodrome TVL Hits $500M on Base",
                summary="Aerodrome becomes largest DEX on Base. AERO token up 40% this week.",
                category="defi",
                source="DeFiLlama",
                url="https://defillama.com/protocol/aerodrome",
                timestamp=datetime.utcnow() - timedelta(hours=4),
                importance=4,
                protocols=["aerodrome", "base"]
            ),
            NewsItem(
                title="Morpho Blue Launches on Base",
                summary="Permission-less lending protocol Morpho expands to Base. $50M deposited in first 24h.",
                category="defi",
                source="@MorphoLabs",
                url="https://twitter.com/MorphoLabs",
                timestamp=datetime.utcnow() - timedelta(hours=8),
                importance=4,
                protocols=["morpho", "base"]
            ),
            NewsItem(
                title="Lido V2 Upgrade Complete",
                summary="Lido successfully upgrades staking infrastructure. Withdrawals now faster.",
                category="protocol",
                source="@LidoFinance",
                url="https://twitter.com/LidoFinance",
                timestamp=datetime.utcnow() - timedelta(hours=10),
                importance=3,
                protocols=["lido"]
            ),
            NewsItem(
                title="Uniswap Launches on zkSync",
                summary="Uniswap v3 now live on zkSync Era. Gas fees 10x cheaper than mainnet.",
                category="defi",
                source="@Uniswap",
                url="https://twitter.com/Uniswap",
                timestamp=datetime.utcnow() - timedelta(hours=14),
                importance=4,
                protocols=["uniswap", "zksync"]
            ),
            
            # Security alerts
            NewsItem(
                title="⚠️ Fake Airdrop Scam Alert",
                summary="Scammers impersonating EigenLayer on X. Never connect wallet to unverified links! Official site: eigenlayer.xyz",
                category="security",
                source="@web3isgoinggreat",
                url="https://twitter.com/web3isgoinggreat",
                timestamp=datetime.utcnow() - timedelta(hours=1),
                importance=5,
                protocols=["eigenlayer"]
            ),
            NewsItem(
                title="🔴 $2M Rug Pull: SolanaYield",
                summary="New Solana yield protocol rugged users after 3 days. Team wallets drained to Tornado Cash.",
                category="security",
                source="Rekt News",
                url="https://rekt.news",
                timestamp=datetime.utcnow() - timedelta(hours=5),
                importance=5,
                protocols=["solana"]
            ),
            NewsItem(
                title="Curve Finance Recovers $62M",
                summary="White hat hackers return majority of funds from re-entrancy exploit. CRV stabilizes.",
                category="security",
                source="@CurveFinance",
                url="https://twitter.com/CurveFinance",
                timestamp=datetime.utcnow() - timedelta(hours=20),
                importance=4,
                protocols=["curve"]
            ),
            
            # Airdrop news
            NewsItem(
                title="zkSync Token Launch Imminent",
                summary="Multiple sources confirm ZK token launching in Q1. Bridge activity spiking.",
                category="airdrop",
                source="@zkSync",
                url="https://twitter.com/zksync",
                timestamp=datetime.utcnow() - timedelta(hours=7),
                importance=5,
                protocols=["zksync"]
            ),
            NewsItem(
                title="LayerZero Snapshot Rumors",
                summary="Community speculates on upcoming LayerZero airdrop. Stargate volume increasing.",
                category="airdrop",
                source="CT Alpha",
                url="https://twitter.com/layerzero_labs",
                timestamp=datetime.utcnow() - timedelta(hours=9),
                importance=4,
                protocols=["layerzero"]
            ),
            NewsItem(
                title="Blast Points Multiplier Active",
                summary="Blast running 2x points event this week. ETH and USDB deposits boosted.",
                category="airdrop",
                source="@Blast_L2",
                url="https://twitter.com/Blast_L2",
                timestamp=datetime.utcnow() - timedelta(hours=11),
                importance=4,
                protocols=["blast"]
            ),
        ]
        
        # Sort by importance and recency
        news.sort(key=lambda x: (x.importance, x.timestamp), reverse=True)
        
        self._news_cache = news
        self._last_fetch = datetime.utcnow()
        
        return news
    
    def get_news_by_category(self, category: str) -> List[NewsItem]:
        """Get news filtered by category"""
        return [n for n in self._news_cache if n.category == category]
    
    def format_news_digest(self, limit: int = 10) -> str:
        """Format news digest for Telegram"""
        if not self._news_cache:
            return "❌ No news available. Try again later."
        
        lines = ["📰 *DeFi News Digest*\n"]
        lines.append(f"_Last 24 hours • {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC_\n")
        
        # Group by category
        macro = [n for n in self._news_cache if n.category == "macro"][:3]
        defi = [n for n in self._news_cache if n.category in ["defi", "protocol"]][:3]
        security = [n for n in self._news_cache if n.category == "security"][:3]
        airdrop = [n for n in self._news_cache if n.category == "airdrop"][:3]
        
        if macro:
            lines.append("━━━ *🌍 Macro* ━━━\n")
            for n in macro:
                importance = "🔴" if n.importance >= 5 else "🟡" if n.importance >= 4 else "⚪"
                lines.append(f"{importance} *{n.title}*\n_{n.summary[:100]}..._\n")
        
        if security:
            lines.append("\n━━━ *🚨 Security Alerts* ━━━\n")
            for n in security:
                lines.append(f"⚠️ *{n.title}*\n_{n.summary[:100]}..._\n")
        
        if airdrop:
            lines.append("\n━━━ *🎁 Airdrops* ━━━\n")
            for n in airdrop:
                lines.append(f"🎁 *{n.title}*\n_{n.summary[:80]}..._\n")
        
        if defi:
            lines.append("\n━━━ *📊 DeFi Updates* ━━━\n")
            for n in defi:
                protocols = ", ".join(n.protocols[:2]) if n.protocols else ""
                lines.append(f"📊 *{n.title}*\n_{n.summary[:80]}..._\n")
        
        lines.append("\n_Use /news macro | security | airdrop for filtered view_")
        
        return "\n".join(lines)
    
    def format_category_news(self, category: str) -> str:
        """Format news for specific category"""
        category_map = {
            "macro": ("🌍", "Macro & Markets"),
            "security": ("🚨", "Security Alerts"),
            "airdrop": ("🎁", "Airdrop News"),
            "defi": ("📊", "DeFi Updates"),
        }
        
        emoji, title = category_map.get(category, ("📰", "News"))
        news = self.get_news_by_category(category)
        
        if not news:
            return f"❌ No {category} news available."
        
        lines = [f"{emoji} *{title}*\n"]
        
        for n in news[:5]:
            hours_ago = int((datetime.utcnow() - n.timestamp).total_seconds() / 3600)
            lines.append(
                f"\n*{n.title}*\n"
                f"{n.summary}\n"
                f"📍 {n.source} • {hours_ago}h ago\n"
            )
        
        return "\n".join(lines)
    
    def format_alpha_feed(self) -> str:
        """Format curated alpha feed"""
        return """
🔥 *Today's Alpha Feed*

━━━ *🎁 Airdrop Intel* ━━━
• Berachain mainnet Q1 2025 - farm testnet!
• Scroll still no token - bridge & use dApps
• Linea Surge points - deposit ETH/USDC
• Symbiotic restaking - points program live

━━━ *📈 Yield Opportunities* ━━━
• Aerodrome USDC/WETH - 45% APY + AERO
• Morpho Blue USDC - 12% + future token
• Pendle YT-weETH - points leverage play
• Lido stETH - 3.8% + restaking opportunities

━━━ *🐋 Smart Money Moves* ━━━
• Whale accumulation on new L2s
• LRT protocols seeing inflows
• Points meta still strong

━━━ *⚠️ Avoid These* ━━━
• Fake airdrop links on X (verify URLs!)
• "Guaranteed APY" Telegram groups
• Unaudited new protocols

━━━ *📊 Sources* ━━━
@DefiLlama @0xngmi @solidintel_x
@WalterBloomberg @whaletrades
@defi_airdrops @heycape_

_Use /sources for full list_
_Updated: Every 4 hours_
"""
    
    def format_sources(self) -> str:
        """Format list of tracked X/Twitter sources"""
        lines = ["📡 *Tracked X/Twitter Sources*\n"]
        lines.append("_News aggregated from these accounts_\n")
        
        for category, sources in X_SOURCES.items():
            category_names = {
                "airdrop": "🎁 Airdrop Intel",
                "defi": "📊 DeFi Analytics",
                "news": "📰 News & Intel",
                "whale": "🐋 Whale Tracking",
                "alpha": "🔥 Alpha Research"
            }
            
            lines.append(f"\n*{category_names.get(category, category)}*")
            for source in sources:
                verified = "✓" if source.get("verified") else ""
                followers = f" ({source['followers']})" if source.get("followers") else ""
                lines.append(f"• {source['handle']} {verified}{followers}")
        
        lines.append("\n━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"\n📈 *Total: {len(ALL_X_SOURCES)} sources*")
        lines.append("\n_In production: real-time X API aggregation_")
        
        return "\n".join(lines)


# Global instance
news_aggregator = NewsAggregator()


async def initialize_news():
    """Initialize news on startup"""
    await news_aggregator.fetch_latest_news()

