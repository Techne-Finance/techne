"""
Techne Telegram Bot - Airdrop Hunter Service
Detects protocols with high airdrop probability and related pools
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class AirdropOpportunity:
    """An airdrop farming opportunity"""
    protocol: str
    chain: str
    symbol: str
    apy: float
    tvl: float
    airdrop_score: int  # 1-100
    reasons: List[str]
    pools: List[Dict]
    category: str  # "confirmed", "likely", "speculative"
    deadline: Optional[str] = None
    source_url: Optional[str] = None


class AirdropHunter:
    """
    Tracks protocols with high airdrop probability
    Analyzes pools and identifies farming opportunities
    """
    
    # Known protocols with high airdrop probability
    # Updated January 2025 - VERIFIED status
    # Categories: "upcoming" (no token), "season2" (had S1, more coming), "completed" (done)
    AIRDROP_PROTOCOLS = {
        # ===== UPCOMING - No token yet =====
        "scroll": {
            "name": "Scroll",
            "category": "upcoming",
            "score": 85,
            "reasons": ["No token yet (as of Jan 2025)", "zkEVM rollup", "$80M+ VC backed", "Growing TVL"],
            "chains": ["scroll"],
            "assets": ["ETH", "USDC"],
            "source": "https://scroll.io"
        },
        "linea": {
            "name": "Linea",
            "category": "upcoming",
            "score": 80,
            "reasons": ["No token yet", "ConsenSys/MetaMask backed", "Active Surge points program"],
            "chains": ["linea"],
            "assets": ["ETH", "USDC"],
            "source": "https://linea.build"
        },
        "berachain": {
            "name": "Berachain",
            "category": "upcoming",
            "score": 90,
            "reasons": ["Mainnet Q1 2025", "Novel PoL mechanism", "$142M raised", "Massive community"],
            "chains": ["berachain"],
            "assets": ["BERA", "HONEY", "BGT"],
            "source": "https://berachain.com"
        },
        "monad": {
            "name": "Monad",
            "category": "upcoming",
            "score": 85,
            "reasons": ["Testnet 2025", "$225M raised", "High-performance EVM", "No token yet"],
            "chains": ["monad"],
            "assets": ["ETH"],
            "source": "https://monad.xyz"
        },
        "hyperliquid": {
            "name": "Hyperliquid",
            "category": "upcoming",
            "score": 80,
            "reasons": ["No VC = fair launch likely", "Top perp DEX", "Self-funded team"],
            "chains": ["hyperliquid"],
            "assets": ["USDC"],
            "source": "https://hyperliquid.xyz"
        },
        "eclipse": {
            "name": "Eclipse",
            "category": "upcoming",
            "score": 75,
            "reasons": ["SVM on Ethereum", "$65M raised", "Polychain backed", "Mainnet live"],
            "chains": ["eclipse"],
            "assets": ["ETH", "SOL"],
            "source": "https://eclipse.xyz"
        },
        "fuel": {
            "name": "Fuel Network",
            "category": "upcoming", 
            "score": 70,
            "reasons": ["Modular execution layer", "$80M raised", "Unique UTXO model"],
            "chains": ["fuel"],
            "assets": ["ETH"],
            "source": "https://fuel.network"
        },
        
        # ===== SEASON 2 - Had airdrop, more distributions expected =====
        "eigenlayer_s3": {
            "name": "EigenLayer (Season 3)",
            "category": "season2",
            "score": 75,
            "reasons": ["Season 3 expected 2025", "8.25% supply reserved", "Keep restaking for future drops"],
            "chains": ["ethereum"],
            "assets": ["stETH", "rETH", "cbETH"],
            "source": "https://eigenlayer.xyz"
        },
        "layerzero_s2": {
            "name": "LayerZero (Season 2)",
            "category": "season2",
            "score": 70,
            "reasons": ["Season 2 expected Q2 2025", "15.3% for future distributions", "Use Stargate/bridges"],
            "chains": ["multi-chain"],
            "assets": ["ETH", "USDC"],
            "source": "https://layerzero.network"
        },
        
        # ===== POINTS PROGRAMS - Ongoing yield + potential rewards =====
        "etherfi": {
            "name": "Ether.fi",
            "category": "points",
            "score": 80,
            "reasons": ["Ongoing loyalty points", "LRT leader", "ETHFI staking rewards"],
            "chains": ["ethereum", "base"],
            "assets": ["ETH", "weETH", "eETH"],
            "source": "https://ether.fi"
        },
        "pendle": {
            "name": "Pendle (Points Meta)",
            "category": "points",
            "score": 85,
            "reasons": ["YT tokens = leveraged points", "Multiple airdrops exposure", "Growing TVL"],
            "chains": ["ethereum", "arbitrum"],
            "assets": ["YT-weETH", "YT-ezETH", "PT-*"],
            "source": "https://pendle.finance"
        },
        "symbiotic": {
            "name": "Symbiotic",
            "category": "points",
            "score": 80,
            "reasons": ["New restaking protocol", "Paradigm backed", "Points program active"],
            "chains": ["ethereum"],
            "assets": ["wstETH", "cbETH", "rETH"],
            "source": "https://symbiotic.fi"
        },
        "karak": {
            "name": "Karak",
            "category": "points",
            "score": 75,
            "reasons": ["EigenLayer competitor", "Multi-asset restaking", "XP points system"],
            "chains": ["ethereum", "arbitrum"],
            "assets": ["ETH", "stETH", "USDC"],
            "source": "https://karak.network"
        },
    }
    
    # DeFi protocols on airdrop-likely chains worth farming
    FARM_STRATEGIES = {
        "base": [
            {"protocol": "Aerodrome", "action": "Provide LP", "assets": ["USDC", "WETH", "cbETH"]},
            {"protocol": "Morpho", "action": "Lend/Borrow", "assets": ["USDC", "WETH"]},
            {"protocol": "Moonwell", "action": "Lend", "assets": ["USDC", "cbETH"]},
        ],
        "arbitrum": [
            {"protocol": "Camelot", "action": "Provide LP", "assets": ["ETH", "USDC", "ARB"]},
            {"protocol": "GMX", "action": "Provide GLP", "assets": ["ETH", "USDC"]},
            {"protocol": "Radiant", "action": "Lend", "assets": ["ETH", "USDC"]},
        ],
        "ethereum": [
            {"protocol": "EigenLayer", "action": "Restake", "assets": ["stETH", "rETH"]},
            {"protocol": "Ether.fi", "action": "Stake ETH", "assets": ["ETH"]},
            {"protocol": "Pendle", "action": "Buy YT tokens", "assets": ["PT/YT"]},
        ],
    }
    
    def __init__(self):
        self._last_check: Optional[datetime] = None
    
    def get_all_opportunities(self) -> List[AirdropOpportunity]:
        """Get all current airdrop opportunities"""
        opportunities = []
        
        for key, protocol in self.AIRDROP_PROTOCOLS.items():
            opp = AirdropOpportunity(
                protocol=protocol["name"],
                chain=", ".join(protocol["chains"][:2]),
                symbol="/".join(protocol["assets"][:3]),
                apy=0,  # Would be calculated from actual pools
                tvl=0,
                airdrop_score=protocol["score"],
                reasons=protocol["reasons"],
                pools=[],
                category=protocol["category"],
                source_url=protocol.get("source")
            )
            opportunities.append(opp)
        
        # Sort by score
        opportunities.sort(key=lambda x: x.airdrop_score, reverse=True)
        return opportunities
    
    def get_opportunities_by_category(self, category: str) -> List[AirdropOpportunity]:
        """Get opportunities filtered by category"""
        return [o for o in self.get_all_opportunities() if o.category == category]
    
    def analyze_pool_for_airdrop(self, pool: Dict) -> Optional[Dict]:
        """
        Analyze if a pool has airdrop potential
        Returns airdrop info if likely, None otherwise
        """
        protocol = pool.get("project", "").lower()
        chain = pool.get("chain", "").lower()
        symbol = pool.get("symbol", "").upper()
        
        # Check if on airdrop-likely chain
        airdrop_chains = ["zksync", "scroll", "linea", "blast", "mode", "base"]
        chain_score = 20 if any(c in chain for c in airdrop_chains) else 0
        
        # Check if uses airdrop-likely assets
        airdrop_assets = ["ETH", "WETH", "STETH", "RETH", "CBETH", "USDC", "USDT", "WEETH", "EETH", "EZETH"]
        asset_score = 15 if any(a in symbol for a in airdrop_assets) else 0
        
        # Check if protocol is known for airdrops
        protocol_score = 0
        protocol_name = None
        for key, p in self.AIRDROP_PROTOCOLS.items():
            if key in protocol or protocol in p["name"].lower():
                protocol_score = 30
                protocol_name = p["name"]
                break
        
        total_score = chain_score + asset_score + protocol_score
        
        if total_score >= 30:
            return {
                "pool": pool,
                "airdrop_score": total_score,
                "protocol": protocol_name or pool.get("project"),
                "chain": chain,
                "reason": f"{'Airdrop chain' if chain_score else ''} {'Eligible assets' if asset_score else ''} {'Known protocol' if protocol_score else ''}".strip()
            }
        
        return None
    
    def format_airdrop_list(self) -> str:
        """Format list of airdrop opportunities"""
        opportunities = self.get_all_opportunities()
        
        lines = ["🎁 *Airdrop Opportunities*\n"]
        lines.append("_Updated January 2025 - Verified status_\n")
        
        # Group by category
        upcoming = [o for o in opportunities if o.category == "upcoming"]
        season2 = [o for o in opportunities if o.category == "season2"]
        points = [o for o in opportunities if o.category == "points"]
        
        if upcoming:
            lines.append("━━━ *🆕 Upcoming (No Token Yet)* ━━━\n")
            for o in upcoming[:5]:
                lines.append(
                    f"*{o.protocol}* ({o.airdrop_score}%)\n"
                    f"   {o.chain} • {o.symbol}\n"
                    f"   💡 _{o.reasons[0]}_\n"
                )
        
        if season2:
            lines.append("\n━━━ *🔄 Season 2 Expected* ━━━\n")
            for o in season2[:3]:
                lines.append(
                    f"*{o.protocol}* ({o.airdrop_score}%)\n"
                    f"   💡 _{o.reasons[0]}_\n"
                )
        
        if points:
            lines.append("\n━━━ *⭐ Active Points Programs* ━━━\n")
            for o in points[:4]:
                lines.append(
                    f"*{o.protocol}* ({o.airdrop_score}%)\n"
                    f"   {o.chain} • {o.symbol}\n"
                )
        
        lines.append("\n_Use /airdrop [name] for details_")
        
        return "\n".join(lines)
    
    def format_airdrop_detail(self, protocol_name: str) -> str:
        """Format detailed view of single airdrop opportunity"""
        opportunities = self.get_all_opportunities()
        
        # Find matching protocol
        opp = None
        for o in opportunities:
            if protocol_name.lower() in o.protocol.lower():
                opp = o
                break
        
        if not opp:
            return f"❌ Protocol '{protocol_name}' not found. Use /airdrop to see list."
        
        category_emoji = {"confirmed": "🟢", "likely": "🟡", "speculative": "🟠"}.get(opp.category, "⚪")
        
        reasons_formatted = "\n".join(f"• {r}" for r in opp.reasons)
        
        # Get farming strategies for this chain
        strategies = []
        for chain in opp.chain.split(", "):
            if chain.lower() in self.FARM_STRATEGIES:
                strategies.extend(self.FARM_STRATEGIES[chain.lower()])
        
        strategy_text = ""
        if strategies:
            strategy_lines = [f"• {s['action']} on {s['protocol']}" for s in strategies[:3]]
            strategy_text = "\n".join(strategy_lines)
        
        return f"""
🎁 *{opp.protocol}*

{category_emoji} *Category:* {opp.category.capitalize()}
📊 *Airdrop Score:* {opp.airdrop_score}/100

━━━━━━━━━━━━━━━━━━━━

*Why it's likely:*
{reasons_formatted}

*Eligible Assets:*
{opp.symbol}

*Chain(s):* {opp.chain}

━━━━━━━━━━━━━━━━━━━━

🎯 *How to Farm:*
{strategy_text if strategy_text else "• Use protocol regularly\n• Bridge assets to chain\n• Interact with dApps"}

📚 *Learn More:*
{opp.source_url or 'Check protocol docs'}

━━━━━━━━━━━━━━━━━━━━

⚠️ _NFA - Always DYOR before farming_
"""
    
    def format_farming_guide(self, chain: str = "base") -> str:
        """Format airdrop farming guide for a chain"""
        strategies = self.FARM_STRATEGIES.get(chain.lower(), [])
        
        if not strategies:
            return f"❌ No farming strategies for {chain}. Try: base, ethereum, arbitrum"
        
        lines = [f"🌾 *Airdrop Farming: {chain.capitalize()}*\n"]
        lines.append("_Best strategies for potential airdrops_\n")
        
        for s in strategies:
            lines.append(
                f"*{s['protocol']}*\n"
                f"   📍 {s['action']}\n"
                f"   💰 Assets: {', '.join(s['assets'])}\n"
            )
        
        lines.append("\n_Interact regularly to maximize eligibility_")
        
        return "\n".join(lines)


# Global instance
airdrop_hunter = AirdropHunter()
