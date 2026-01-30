"""
Techne Protocol - Multi-Agent System
Scalable Architecture for 1000+ Users

Core Agents (Shared Services):
- Scout: Data collection (DeFiLlama, Beefy, whales)
- Appraiser: Risk analysis and verification
- Merchant: x402/Meridian payments
- Concierge: User-facing formatting
- Engineer: Execution layer

Extended Agents (Security & Optimization):
- Sentinel: Security monitoring, rug detection
- Historian: Historical data, trends, backtesting
- Arbitrageur: Yield optimization, rebalancing
- Guardian: Position monitoring, stop-loss, alerts

Scalable Execution (Per-User):
- strategy_executor.py: Executes user strategies with their agent wallet
- agent_wallet.py: Per-user sovereign EOA agent

Infrastructure:
- Chainlink Oracle: Depeg monitoring
"""

# Core Agents
from artisan.scout_agent import scout_agent as scout, ScoutAgent
from .appraiser_agent import appraiser, AppraiserAgent, RiskLevel, VerificationStatus
from .merchant_agent import merchant, MerchantAgent, PaymentType, PaymentStatus
from .concierge_agent import concierge, ConciergeAgent

# NEW: Engineer Agent (Execution Layer)
from .engineer_agent import engineer, EngineerAgent, TaskType, TaskStatus

# Extended Agents
from .sentinel_agent import sentinel, SentinelAgent, ThreatLevel, SecurityFlag
from .historian_agent import historian, HistorianAgent
from .arbitrageur_agent import arbitrageur, ArbitrageurAgent
from .guardian_agent import guardian, GuardianAgent, AlertType, AlertSeverity
from .security_policy import security_policy, SecurityPolicyManager, ActionType, PolicyConstraints, SessionKey

# Infrastructure
from .chainlink_oracle import oracle as chainlink

# Coordinator removed - replaced by strategy_executor.py for scalable per-user execution

__all__ = [
    # Core singleton instances
    "scout",
    "appraiser", 
    "merchant",
    "concierge",
    "engineer",  # NEW
    
    # Extended singleton instances
    "sentinel",
    "historian",
    "arbitrageur",
    "guardian",
    
    # Infrastructure
    "chainlink",
    
    # Core Classes
    "ScoutAgent",
    "AppraiserAgent",
    "MerchantAgent",
    "ConciergeAgent",
    "EngineerAgent",
    
    # Extended Classes
    "SentinelAgent",
    "HistorianAgent",
    "ArbitrageurAgent",
    "GuardianAgent",
    
    # Enums
    "RiskLevel",
    "VerificationStatus",
    "PaymentType",
    "PaymentStatus",
    "ThreatLevel",
    "SecurityFlag",
    "AlertType",
    "AlertSeverity",
    "TaskType",  # NEW
    "TaskStatus",  # NEW
]


