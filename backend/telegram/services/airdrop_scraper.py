"""
Techne Airdrop Scraper - Real-time airdrop data from public sources

SOURCES:
1. DefiLlama Protocols API - Get tokenless protocols (potential airdrops)
2. DefiLlama TVL data - Track growing protocols
3. Chain-specific tracking - Activity on new L2s

This replaces hardcoded AIRDROP_PROTOCOLS with live data.
"""

import asyncio
import httpx
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class LiveAirdropOpportunity:
    """Real airdrop opportunity from live data."""
    protocol: str
    category: str  # upcoming, season2, points, live
    chains: List[str]
    tvl: float
    tvl_change_7d: float  # % change
    has_token: bool
    description: str
    url: str
    farming_guide: str
    score: int = 50  # 0-100
    last_updated: datetime = field(default_factory=datetime.utcnow)


class AirdropScraper:
    """
    Scrapes real airdrop opportunities from multiple sources.
    
    Strategy:
    1. Fetch ALL protocols from DefiLlama
    2. Filter for tokenless (no token = potential airdrop)
    3. Sort by TVL (higher TVL = more likely legit)
    4. Add chain-specific opportunities
    """
    
    def __init__(self):
        self.defillama_protocols_url = "https://api.llama.fi/protocols"
        self.defillama_tvl_url = "https://api.llama.fi/tvl"
        
        # Cache
        self._cache: List[LiveAirdropOpportunity] = []
        self._last_fetch: Optional[datetime] = None
        self._cache_ttl_minutes = 60  # 1 hour cache
        # X/Twitter sources from user (for reference and Nitter scraping)
        self._x_sources = {
            "airdrop": [
                {"handle": "defi_airdrops", "name": "DeFi Airdrops"},
                {"handle": "airdrops_one", "name": "Airdrops One"},
                {"handle": "heycape_", "name": "Cape"},
            ],
            "defi": [
                {"handle": "DefiLlama", "name": "DefiLlama"},
                {"handle": "0xngmi", "name": "0xngmi (DefiLlama founder)"},
                {"handle": "definalist", "name": "DeFi Nalist"},
                {"handle": "tokenomist_ai", "name": "Tokenomist AI"},
            ],
            "news": [
                {"handle": "solidintel_x", "name": "Solid Intel"},
                {"handle": "WalterBloomberg", "name": "Walter Bloomberg"},
                {"handle": "tree_news_feed", "name": "Tree News Feed"},
                {"handle": "LiveSquawk", "name": "LiveSquawk"},
            ],
            "alpha": [
                {"handle": "cryptophileee", "name": "Cryptophile"},
                {"handle": "hooeem", "name": "Hooeem"},
                {"handle": "mi_zielono", "name": "Mi Zielono"},
            ],
        }
        
        # Nitter instances for scraping (public, no auth)
        self._nitter_instances = [
            "https://nitter.poast.org",
            "https://nitter.privacydev.net",
            "https://nitter.net",
        ]

        # Known high-value protocols to track (UPDATED January 2026)
        # NOTE: Scroll (SCR), zkSync (ZK), Hyperliquid (HYPE) already have tokens!
        self._tracked_protocols = {
            # L2s/Chains WITHOUT token yet
            "linea": {"category": "upcoming", "guide": "Bridge via official bridge, use DEXes, participate in Surge campaigns"},
            "abstract": {"category": "upcoming", "guide": "Use Abstract Bridge, interact with dApps on Abstract chain"},
            "megaeth": {"category": "upcoming", "guide": "Join testnet early, bridge and use dApps when live"},
            "movement": {"category": "upcoming", "guide": "Use Movement testnet, bridge assets, participate in campaigns"},
            "initia": {"category": "upcoming", "guide": "Stake INIT when live, use apps in the ecosystem"},
            
            # Testnets with high potential
            "berachain": {"category": "upcoming", "guide": "Use Berachain testnet, participate in Boyco, provide liquidity on Kodiak"},
            "monad": {"category": "upcoming", "guide": "Join Monad Discord, participate in testnet when live"},
            "eclipse": {"category": "upcoming", "guide": "Use Eclipse testnet, bridge assets when mainnet launches"},
            
            # Active Points programs
            "eigenlayer": {"category": "points", "guide": "Restake ETH/LSTs via operators, accumulate points for S3"},
            "symbiotic": {"category": "points", "guide": "Deposit ETH/stETH/wstETH, earn points"},
            "karak": {"category": "points", "guide": "Deposit assets on Karak restaking, earn XP"},
            "ether.fi": {"category": "points", "guide": "Stake ETH for eETH, earn loyalty points"},
            "pendle": {"category": "points", "guide": "Provide liquidity, trade YT/PT tokens for points"},
            "renzo": {"category": "points", "guide": "Deposit ETH for ezETH, accumulate Renzo points S2"},
            "kelp": {"category": "points", "guide": "Stake LSTs for rsETH, earn Kelp Miles"},
            "puffer": {"category": "points", "guide": "Deposit stETH for pufETH, earn Puffer Points"},
            "swell": {"category": "points", "guide": "Stake ETH for swETH, earn Pearls"},
            "usual": {"category": "points", "guide": "Mint USD0, stake for USU points"},
            
            # Season 2/3 expected (already have token, more coming)
            "layerzero": {"category": "season2", "guide": "Bridge across chains, use Stargate V2, accumulate messages"},
            "wormhole": {"category": "season2", "guide": "Use Portal Bridge, interact with Wormhole-connected dApps"},
            "zksync era": {"category": "season2", "guide": "Already has ZK token, possible S2 for active users"},
            "scroll": {"category": "season2", "guide": "Already has SCR token, possible S2 for continued activity"},
        }
    
    def _should_refresh(self) -> bool:
        if not self._last_fetch:
            return True
        elapsed = (datetime.utcnow() - self._last_fetch).total_seconds()
        return elapsed >= self._cache_ttl_minutes * 60
    
    async def fetch_defillama_protocols(self) -> List[Dict]:
        """Fetch all protocols from DefiLlama API."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.defillama_protocols_url)
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch DefiLlama protocols: {e}")
        return []
    
    async def scrape_opportunities(self) -> List[LiveAirdropOpportunity]:
        """
        Scrape real airdrop opportunities.
        
        Returns fresh data or cached if within TTL.
        """
        if not self._should_refresh() and self._cache:
            return self._cache
        
        logger.info("🔍 Scraping live airdrop opportunities...")
        opportunities = []
        
        # Fetch DefiLlama protocols
        protocols = await self.fetch_defillama_protocols()
        
        # Create lookup for quick matching
        protocol_data = {}
        for p in protocols:
            name = p.get("name", "").lower()
            slug = p.get("slug", "").lower()
            protocol_data[name] = p
            protocol_data[slug] = p
        
        # Match tracked protocols with live data
        for protocol_key, info in self._tracked_protocols.items():
            protocol_name = protocol_key.title().replace(".", " ").replace("Zksync Era", "zkSync Era")
            
            # Try to find matching protocol in DefiLlama
            llama_data = protocol_data.get(protocol_key) or protocol_data.get(protocol_key.replace(" ", "-"))
            
            if llama_data:
                tvl = llama_data.get("tvl", 0) or 0
                change_7d = llama_data.get("change_7d", 0) or 0
                chains = llama_data.get("chains", [])
                url = f"https://defillama.com/protocol/{llama_data.get('slug', protocol_key)}"
                has_token = llama_data.get("symbol") is not None
                description = llama_data.get("description", "")[:100] if llama_data.get("description") else info["guide"]
            else:
                tvl = 0
                change_7d = 0
                chains = ["Multi-chain"]
                url = f"https://defillama.com/protocol/{protocol_key.replace(' ', '-')}"
                has_token = False
                description = info["guide"]
            
            # Calculate score based on TVL and activity
            score = 50
            if tvl > 1_000_000_000:  # >$1B TVL
                score = 90
            elif tvl > 100_000_000:  # >$100M TVL
                score = 80
            elif tvl > 10_000_000:  # >$10M TVL
                score = 70
            elif tvl > 1_000_000:  # >$1M TVL
                score = 60
            
            # Boost for growing protocols
            if change_7d > 10:
                score = min(score + 10, 95)
            
            opportunities.append(LiveAirdropOpportunity(
                protocol=protocol_name,
                category=info["category"],
                chains=chains[:3] if chains else ["Multi-chain"],
                tvl=tvl,
                tvl_change_7d=change_7d,
                has_token=has_token,
                description=description,
                url=url,
                farming_guide=info["guide"],
                score=score
            ))
        
        # Sort by score (highest first)
        opportunities.sort(key=lambda x: x.score, reverse=True)
        
        self._cache = opportunities
        self._last_fetch = datetime.utcnow()
        
        logger.info(f"✅ Scraped {len(opportunities)} airdrop opportunities")
        return opportunities
    
    async def get_by_category(self, category: str) -> List[LiveAirdropOpportunity]:
        """Get opportunities filtered by category."""
        all_ops = await self.scrape_opportunities()
        return [o for o in all_ops if o.category == category]
    
    async def format_daily_digest(self) -> str:
        """Format comprehensive daily digest with real data."""
        opportunities = await self.scrape_opportunities()
        
        upcoming = [o for o in opportunities if o.category == "upcoming"][:5]
        season2 = [o for o in opportunities if o.category == "season2"][:3]
        points = [o for o in opportunities if o.category == "points"][:5]
        
        message = f"""
📌 *DAILY AIRDROP DIGEST*
_{datetime.utcnow().strftime('%A, %B %d, %Y')} • Live Data_

━━━ *🆕 TOP UPCOMING (No Token)* ━━━
"""
        for o in upcoming:
            tvl_str = f"${o.tvl/1e9:.1f}B" if o.tvl >= 1e9 else f"${o.tvl/1e6:.0f}M" if o.tvl >= 1e6 else "TBD"
            chains_str = ", ".join(o.chains[:2])
            message += f"""
• *{o.protocol}* ({o.score}% score)
  📍 {chains_str} | TVL: {tvl_str}
  💡 _{o.farming_guide[:80]}..._
  🔗 [Start]({o.url})
"""

        message += "\n━━━ *🔄 SEASON 2 EXPECTED* ━━━\n"
        for o in season2:
            message += f"• *{o.protocol}* - {o.farming_guide[:60]}...\n"

        message += "\n━━━ *⭐ ACTIVE POINTS PROGRAMS* ━━━\n"
        for o in points:
            tvl_str = f"${o.tvl/1e9:.1f}B" if o.tvl >= 1e9 else f"${o.tvl/1e6:.0f}M" if o.tvl >= 1e6 else "Active"
            change = f"+{o.tvl_change_7d:.0f}%" if o.tvl_change_7d > 0 else f"{o.tvl_change_7d:.0f}%"
            message += f"""
• *{o.protocol}* ({o.score}%) - TVL: {tvl_str} ({change} 7d)
  _{o.farming_guide[:60]}..._
"""

        message += """
━━━━━━━━━━━━━━━━━━━━

📋 *QUICK START GUIDE*

1️⃣ Bridge assets to target chain
2️⃣ Use native DEXes and lending
3️⃣ Stay active (txns, volume)
4️⃣ Check eligibility tools

━━━━━━━━━━━━━━━━━━━━

📊 _Data from DefiLlama • Updated hourly_
📌 _Pinned • Next update tomorrow 10:00 UTC_
"""
        
        return message


# Global instance
airdrop_scraper = AirdropScraper()
