"""
Techne Telegram Bot - Protocol Intelligence Service
Deep protocol analysis and monitoring
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class ProtocolIntelligence:
    """Provides deep analysis of DeFi protocols"""
    
    # Protocol database with risk scores and metadata
    PROTOCOLS = {
        "aave": {
            "name": "Aave",
            "category": "Lending",
            "chains": ["Ethereum", "Base", "Arbitrum", "Polygon"],
            "tvl": 8_500_000_000,
            "risk_score": 9.2,  # out of 10 (higher = safer)
            "audit_status": "Audited by OpenZeppelin, Trail of Bits",
            "founded": 2020,
            "token": "AAVE",
            "website": "aave.com"
        },
        "compound": {
            "name": "Compound",
            "category": "Lending",
            "chains": ["Ethereum", "Base", "Arbitrum"],
            "tvl": 2_100_000_000,
            "risk_score": 9.0,
            "audit_status": "Audited by OpenZeppelin",
            "founded": 2018,
            "token": "COMP",
            "website": "compound.finance"
        },
        "lido": {
            "name": "Lido",
            "category": "Liquid Staking",
            "chains": ["Ethereum", "Polygon"],
            "tvl": 15_800_000_000,
            "risk_score": 8.8,
            "audit_status": "Multiple audits, Sigma Prime, MixBytes",
            "founded": 2020,
            "token": "LDO",
            "website": "lido.fi"
        },
        "uniswap": {
            "name": "Uniswap",
            "category": "DEX",
            "chains": ["Ethereum", "Base", "Arbitrum", "Polygon", "Optimism"],
            "tvl": 4_200_000_000,
            "risk_score": 9.5,
            "audit_status": "Audited by multiple firms",
            "founded": 2018,
            "token": "UNI",
            "website": "uniswap.org"
        },
        "curve": {
            "name": "Curve Finance",
            "category": "DEX (Stablecoins)",
            "chains": ["Ethereum", "Base", "Arbitrum", "Polygon"],
            "tvl": 1_800_000_000,
            "risk_score": 8.5,
            "audit_status": "Audited by Trail of Bits",
            "founded": 2020,
            "token": "CRV",
            "website": "curve.fi"
        },
        "aerodrome": {
            "name": "Aerodrome",
            "category": "DEX (ve(3,3))",
            "chains": ["Base"],
            "tvl": 420_000_000,
            "risk_score": 7.5,
            "audit_status": "Audited, forked from Velodrome",
            "founded": 2023,
            "token": "AERO",
            "website": "aerodrome.finance"
        },
        "morpho": {
            "name": "Morpho",
            "category": "Lending Optimizer",
            "chains": ["Ethereum", "Base"],
            "tvl": 580_000_000,
            "risk_score": 8.0,
            "audit_status": "Audited by Spearbit, Trail of Bits",
            "founded": 2022,
            "token": "MORPHO",
            "website": "morpho.org"
        },
        "pendle": {
            "name": "Pendle",
            "category": "Yield Trading",
            "chains": ["Ethereum", "Arbitrum"],
            "tvl": 320_000_000,
            "risk_score": 7.2,
            "audit_status": "Audited by Ackee",
            "founded": 2021,
            "token": "PENDLE",
            "website": "pendle.finance"
        },
        "gmx": {
            "name": "GMX",
            "category": "Perpetuals",
            "chains": ["Arbitrum", "Avalanche"],
            "tvl": 520_000_000,
            "risk_score": 7.8,
            "audit_status": "Audited by ABDK",
            "founded": 2021,
            "token": "GMX",
            "website": "gmx.io"
        },
        "spark": {
            "name": "Spark",
            "category": "Lending",
            "chains": ["Ethereum"],
            "tvl": 1_200_000_000,
            "risk_score": 8.5,
            "audit_status": "MakerDAO affiliated, audited",
            "founded": 2023,
            "token": "SPK",
            "website": "sparkfi.xyz"
        }
    }
    
    def get_protocol_info(self, protocol_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed protocol information"""
        key = protocol_name.lower().replace(" ", "-").replace("_", "-")
        return self.PROTOCOLS.get(key)
    
    def format_protocol_card(self, protocol_name: str) -> str:
        """Format protocol as detailed card"""
        info = self.get_protocol_info(protocol_name)
        
        if not info:
            return f"❌ Protocol '{protocol_name}' not found in database."
        
        # Risk emoji based on score
        score = info["risk_score"]
        if score >= 9:
            risk_emoji = "🟢"
            risk_label = "Very Safe"
        elif score >= 8:
            risk_emoji = "🟢"
            risk_label = "Safe"
        elif score >= 7:
            risk_emoji = "🟡"
            risk_label = "Moderate"
        else:
            risk_emoji = "🟠"
            risk_label = "Higher Risk"
        
        tvl = info["tvl"]
        tvl_str = f"${tvl/1_000_000_000:.1f}B" if tvl >= 1_000_000_000 else f"${tvl/1_000_000:.0f}M"
        
        chains = ", ".join(info["chains"][:3])
        if len(info["chains"]) > 3:
            chains += f" +{len(info['chains'])-3}"
        
        return f"""
🏛️ *{info['name']}*

*Category:* {info['category']}
*TVL:* {tvl_str}
*Chains:* {chains}
*Token:* ${info['token']}

━━━━━━━━━━━━━━━━━━━━

🛡️ *Safety Score*
{risk_emoji} *{score}/10* ({risk_label})

*Audits:* {info['audit_status']}
*Founded:* {info['founded']}
*Website:* {info['website']}

━━━━━━━━━━━━━━━━━━━━

Use /pools to find opportunities on {info['name']}
"""
    
    def get_all_protocols(self) -> List[Dict[str, Any]]:
        """Get list of all tracked protocols"""
        return [
            {"key": k, **v} 
            for k, v in sorted(
                self.PROTOCOLS.items(), 
                key=lambda x: x[1]["tvl"], 
                reverse=True
            )
        ]
    
    def format_protocol_list(self) -> str:
        """Format list of all protocols"""
        lines = ["🏛️ *Tracked Protocols*\n"]
        
        for p in self.get_all_protocols():
            tvl = p["tvl"]
            tvl_str = f"${tvl/1_000_000_000:.1f}B" if tvl >= 1_000_000_000 else f"${tvl/1_000_000:.0f}M"
            
            score = p["risk_score"]
            emoji = "🟢" if score >= 8 else "🟡" if score >= 7 else "🟠"
            
            lines.append(
                f"{emoji} *{p['name']}* - {tvl_str} TVL\n"
                f"   {p['category']} • {p['risk_score']}/10 safety\n"
            )
        
        lines.append(f"\n_Total: {len(self.PROTOCOLS)} protocols tracked_")
        lines.append("Use /protocol [name] for details")
        
        return "\n".join(lines)


# Global instance
protocol_intel = ProtocolIntelligence()
