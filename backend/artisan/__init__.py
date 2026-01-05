"""
Artisan AI Agents Package
"""

# Original exports (from agent.py)
from .agent import get_top_yields, fetch_yields, filter_yields, calculate_risk_score, format_pool_for_api

# Scout Agent
from .scout_agent import ScoutAgent, scout_agent, get_scout_pools, TOP_PROTOCOLS

# Guardian Agent
from .guardian_agent import GuardianAgent, guardian_agent, analyze_pool_risk, get_quick_risk

# Airdrop Agent
from .airdrop_agent import AirdropAgent, airdrop_agent, get_airdrop_opportunities, get_pool_airdrop_info

__all__ = [
    # Original
    "get_top_yields",
    "fetch_yields",
    "filter_yields",
    "calculate_risk_score",
    "format_pool_for_api",
    
    # Scout Agent
    "ScoutAgent",
    "scout_agent", 
    "get_scout_pools",
    "TOP_PROTOCOLS",
    
    # Guardian Agent
    "GuardianAgent",
    "guardian_agent",
    "analyze_pool_risk",
    "get_quick_risk",
    
    # Airdrop Agent
    "AirdropAgent",
    "airdrop_agent",
    "get_airdrop_opportunities",
    "get_pool_airdrop_info",
]
