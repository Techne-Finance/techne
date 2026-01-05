"""
Techne Airdrop Agent - Airdrop Opportunity Scanner
Skanuje protokoły pod kątem potencjalnych airdropów
"""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class AirdropOpportunity:
    """Pojedyncza okazja airdropowa"""
    protocol: str
    display_name: str
    chain: str
    potential: str  # high, medium, low
    probability: float  # 0.0 - 1.0
    estimated_value: str  # "$100-$1000"
    actions_required: List[str]
    deadline: Optional[str]
    notes: str


class AirdropAgent:
    """
    Airdrop Agent - Opportunity Scanner
    Śledzi protokoły bez tokena i ocenia prawdopodobieństwo airdropa
    """
    
    def __init__(self):
        # Protokoły bez tokena z potencjałem airdropa
        self.airdrop_candidates = {
            # HIGH POTENTIAL - silne sygnały
            "midas": {
                "display_name": "Midas Protocol",
                "chain": "Multi-Chain",
                "has_token": False,
                "potential": "high",
                "probability": 0.85,
                "estimated_value": "$500-$5000",
                "funding": "$10M+",
                "actions": [
                    "Deposit into Midas vaults",
                    "Provide liquidity",
                    "Use cross-chain features",
                    "Refer friends"
                ],
                "deadline": "Q1 2025 (speculated)",
                "notes": "RWA protocol with strong backing. Points system active.",
                "signals": ["points_system", "no_token", "high_tvl", "vc_backed"]
            },
            "infinifi": {
                "display_name": "InfiniFi",
                "chain": "Ethereum",
                "has_token": False,
                "potential": "high",
                "probability": 0.80,
                "estimated_value": "$200-$2000",
                "funding": "Unknown",
                "actions": [
                    "Deposit ETH/stablecoins",
                    "Use lending features",
                    "Be early adopter"
                ],
                "deadline": "TBD",
                "notes": "New DeFi protocol. Early users likely rewarded.",
                "signals": ["no_token", "new_protocol", "growing_tvl"]
            },
            "scroll": {
                "display_name": "Scroll",
                "chain": "Scroll",
                "has_token": False,
                "potential": "high",
                "probability": 0.90,
                "estimated_value": "$1000-$10000",
                "funding": "$80M",
                "actions": [
                    "Bridge to Scroll",
                    "Use DEXes (Ambient, Syncswap)",
                    "Deploy contracts",
                    "Provide liquidity",
                    "Use lending (Aave, Compound)"
                ],
                "deadline": "Q1-Q2 2025",
                "notes": "zkEVM L2. Session/Marks system confirmed.",
                "signals": ["no_token", "vc_backed", "high_tvl", "marks_system"]
            },
            "linea": {
                "display_name": "Linea",
                "chain": "Linea",
                "has_token": False,
                "potential": "high",
                "probability": 0.88,
                "estimated_value": "$500-$5000",
                "funding": "ConsenSys backed",
                "actions": [
                    "Bridge via official bridge",
                    "Use DEXes (Syncswap, Velocore)",
                    "Provide LP",
                    "Mint NFTs",
                    "Complete Voyage quests"
                ],
                "deadline": "2025",
                "notes": "ConsenSys L2. LXP points system active.",
                "signals": ["no_token", "major_backer", "points_system", "quests"]
            },
            
            # MEDIUM POTENTIAL
            "pendle": {
                "display_name": "Pendle (Additional)",
                "chain": "Ethereum, Arbitrum",
                "has_token": True,  # Ma token, ale points system
                "potential": "medium",
                "probability": 0.60,
                "estimated_value": "$100-$500",
                "funding": "$3.7M",
                "actions": [
                    "Provide liquidity in PT/YT pools",
                    "Hold vePENDLE",
                    "Trade yield tokens"
                ],
                "deadline": "Ongoing",
                "notes": "Points for vePENDLE holders. Additional rewards likely.",
                "signals": ["points_system", "existing_token"]
            },
            "eigenlayer": {
                "display_name": "EigenLayer (Season 2)",
                "chain": "Ethereum",
                "has_token": True,  # EIGEN już jest
                "potential": "medium",
                "probability": 0.70,
                "estimated_value": "$500-$2000",
                "funding": "$50M+",
                "actions": [
                    "Restake ETH/LSTs",
                    "Delegate to operators",
                    "Participate in AVS"
                ],
                "deadline": "Season 2 - 2025",
                "notes": "Season 1 done. Season 2 rewards expected.",
                "signals": ["season_based", "existing_token", "ongoing_rewards"]
            },
            "hyperliquid": {
                "display_name": "Hyperliquid (Additional)",
                "chain": "Hyperliquid L1",
                "has_token": True,  # HYPE już jest
                "potential": "medium",
                "probability": 0.65,
                "estimated_value": "$200-$1000",
                "funding": "Community funded",
                "actions": [
                    "Trade perpetuals",
                    "Provide HLP liquidity",
                    "Stake HYPE"
                ],
                "deadline": "Ongoing",
                "notes": "Additional rewards for active users.",
                "signals": ["points_system", "existing_token", "high_volume"]
            },
            
            # NEW L2s with airdrop potential
            "zksync": {
                "display_name": "zkSync Era DeFi",
                "chain": "zkSync Era",
                "has_token": True,  # ZK token dropped
                "potential": "low",
                "probability": 0.30,
                "estimated_value": "$50-$200",
                "funding": "$200M+",
                "actions": [
                    "Use native DEXes",
                    "Provide liquidity"
                ],
                "deadline": "Future seasons possible",
                "notes": "Token dropped but ecosystem projects may airdrop.",
                "signals": ["ecosystem_airdrops", "existing_l2_token"]
            },
            "starknet": {
                "display_name": "Starknet DeFi",
                "chain": "Starknet",
                "has_token": True,  # STRK dropped
                "potential": "low",
                "probability": 0.25,
                "estimated_value": "$50-$200",
                "funding": "$100M+",
                "actions": [
                    "Use JediSwap, mySwap",
                    "Provide liquidity",
                    "Use lending protocols"
                ],
                "deadline": "Ecosystem airdrops",
                "notes": "STRK dropped. Ecosystem projects may follow.",
                "signals": ["ecosystem_airdrops", "existing_l2_token"]
            },
        }
        
        # Aktywne punkty/nagrody do zbierania
        self.active_points_systems = [
            {"name": "Scroll Marks", "protocol": "scroll", "multiplier": "1.5x for LP"},
            {"name": "Linea LXP", "protocol": "linea", "multiplier": "2x for Voyage"},
            {"name": "Midas Points", "protocol": "midas", "multiplier": "Varies by pool"},
            {"name": "Eigenlayer Points", "protocol": "eigenlayer", "multiplier": "Based on restaked amount"},
        ]
    
    def scan_opportunities(self, chain: Optional[str] = None, min_probability: float = 0.0) -> List[AirdropOpportunity]:
        """Skanuje wszystkie okazje airdropowe"""
        opportunities = []
        
        for proto_id, data in self.airdrop_candidates.items():
            # Filter by chain
            if chain and chain.lower() not in data["chain"].lower():
                if "multi-chain" not in data["chain"].lower():
                    continue
            
            # Filter by probability
            if data["probability"] < min_probability:
                continue
            
            opportunities.append(AirdropOpportunity(
                protocol=proto_id,
                display_name=data["display_name"],
                chain=data["chain"],
                potential=data["potential"],
                probability=data["probability"],
                estimated_value=data["estimated_value"],
                actions_required=data["actions"],
                deadline=data.get("deadline"),
                notes=data["notes"]
            ))
        
        # Sort by probability
        opportunities.sort(key=lambda x: x.probability, reverse=True)
        
        return opportunities
    
    def get_pool_airdrop_potential(self, project: str, chain: str) -> Dict:
        """Ocenia potencjał airdropowy dla konkretnego poola"""
        project_lower = project.lower()
        
        for proto_id, data in self.airdrop_candidates.items():
            if proto_id in project_lower or project_lower in proto_id:
                return {
                    "has_potential": True,
                    "potential": data["potential"],
                    "probability": data["probability"],
                    "estimated_value": data["estimated_value"],
                    "actions": data["actions"],
                    "deadline": data.get("deadline"),
                    "badge": self._get_airdrop_badge(data["potential"]),
                    "signals": data.get("signals", [])
                }
        
        # Check chain-based potential
        chain_airdrops = {
            "scroll": {"potential": "medium", "probability": 0.5},
            "linea": {"potential": "medium", "probability": 0.5},
            "zksync": {"potential": "low", "probability": 0.2},
        }
        
        for chain_name, chain_data in chain_airdrops.items():
            if chain_name in chain.lower():
                return {
                    "has_potential": True,
                    "potential": chain_data["potential"],
                    "probability": chain_data["probability"],
                    "estimated_value": "$50-$500",
                    "actions": ["Use protocol regularly", "Provide liquidity"],
                    "deadline": None,
                    "badge": self._get_airdrop_badge(chain_data["potential"]),
                    "signals": ["chain_ecosystem"]
                }
        
        return {
            "has_potential": False,
            "potential": "none",
            "probability": 0.0,
            "badge": "",
            "signals": []
        }
    
    def _get_airdrop_badge(self, potential: str) -> str:
        """Zwraca badge na podstawie potencjału"""
        badges = {
            "high": "🎁🎁 High Potential",
            "medium": "🎁 Medium Potential",
            "low": "💫 Low Potential"
        }
        return badges.get(potential, "")
    
    def get_recommended_actions(self, wallet_address: Optional[str] = None) -> List[Dict]:
        """Zwraca rekomendowane akcje dla maksymalizacji airdropów"""
        actions = []
        
        # High priority actions
        high_potential = [p for p in self.airdrop_candidates.values() if p["potential"] == "high"]
        
        for proto in high_potential:
            actions.append({
                "protocol": proto["display_name"],
                "priority": "HIGH",
                "actions": proto["actions"][:3],  # Top 3 actions
                "estimated_value": proto["estimated_value"],
                "deadline": proto.get("deadline", "Unknown")
            })
        
        return actions
    
    def get_active_points_systems(self) -> List[Dict]:
        """Zwraca listę aktywnych systemów punktowych"""
        return self.active_points_systems
    
    def calculate_airdrop_score(self, pools: List[Dict]) -> Dict:
        """Oblicza łączny potencjał airdropowy dla listy pooli"""
        total_probability = 0
        high_count = 0
        medium_count = 0
        
        protocols_found = set()
        
        for pool in pools:
            project = pool.get('project', '').lower()
            chain = pool.get('chain', '')
            
            potential = self.get_pool_airdrop_potential(project, chain)
            
            if potential["has_potential"]:
                protocols_found.add(project)
                total_probability += potential["probability"]
                
                if potential["potential"] == "high":
                    high_count += 1
                elif potential["potential"] == "medium":
                    medium_count += 1
        
        return {
            "total_pools_with_potential": len(protocols_found),
            "high_potential_count": high_count,
            "medium_potential_count": medium_count,
            "average_probability": total_probability / max(len(pools), 1),
            "recommended_focus": "high" if high_count > 0 else ("medium" if medium_count > 0 else "low")
        }


# Singleton
airdrop_agent = AirdropAgent()


def get_airdrop_opportunities(chain: Optional[str] = None, min_probability: float = 0.3) -> List[Dict]:
    """Get all airdrop opportunities"""
    opportunities = airdrop_agent.scan_opportunities(chain, min_probability)
    return [
        {
            "protocol": o.protocol,
            "display_name": o.display_name,
            "chain": o.chain,
            "potential": o.potential,
            "probability": o.probability,
            "estimated_value": o.estimated_value,
            "actions": o.actions_required,
            "deadline": o.deadline,
            "notes": o.notes
        }
        for o in opportunities
    ]


def get_pool_airdrop_info(project: str, chain: str) -> Dict:
    """Get airdrop info for a specific pool"""
    return airdrop_agent.get_pool_airdrop_potential(project, chain)
