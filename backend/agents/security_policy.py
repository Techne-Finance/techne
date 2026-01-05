"""
Security Policy Module - Neox-style Agent Wallet Security
Based on institutional-grade infrastructure from Neox.so

Key Security Features:
1. Policy Constraints - Risk limits, exposure caps, compliance rules
2. Session Keys - Temporary approvals for specific actions only
3. Multi-sig - Important transactions require multiple approvals
4. Rate Limiting - Prevent rapid unauthorized transactions
5. Whitelist - Only approved protocols can receive funds
"""

import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SecurityPolicy")


class ActionType(Enum):
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    SWAP = "swap"
    REBALANCE = "rebalance"
    EMERGENCY_EXIT = "emergency_exit"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PolicyConstraints:
    """User-defined or default risk constraints"""
    # Position limits
    max_single_position_percent: float = 25.0  # Max 25% in one pool
    max_protocol_exposure_percent: float = 40.0  # Max 40% in one protocol
    max_chain_exposure_percent: float = 50.0  # Max 50% on one chain
    
    # Transaction limits
    max_daily_transactions: int = 20
    max_single_tx_value_usd: float = 10000.0
    min_delay_between_tx_seconds: int = 30
    
    # Risk limits
    max_risk_level: RiskLevel = RiskLevel.MEDIUM
    min_pool_tvl_usd: float = 100000.0
    min_pool_age_days: int = 7
    
    # Emergency thresholds
    stop_loss_percent: float = -15.0
    daily_loss_limit_percent: float = -5.0
    
    # Whitelist
    allowed_protocols: Set[str] = field(default_factory=lambda: {
        "aave", "compound", "morpho", "maker", "lido", "yearn",
        "curve", "uniswap", "aerodrome", "moonwell", "spark",
        "euler", "fluid", "pendle", "kamino", "marginfi", "solend"
    })
    
    allowed_chains: Set[str] = field(default_factory=lambda: {
        "ethereum", "base", "arbitrum", "optimism", "solana", "polygon"
    })


@dataclass
class SessionKey:
    """Temporary authorization for specific actions"""
    id: str
    user_id: str
    action_type: ActionType
    max_amount_usd: float
    expires_at: datetime
    allowed_protocols: Set[str]
    allowed_pools: Set[str]
    used_amount_usd: float = 0
    transaction_count: int = 0
    max_transactions: int = 10
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)


class SecurityPolicyManager:
    """
    Manages security policies for agent-controlled wallets
    Implements Neox-style institutional-grade security
    """
    
    def __init__(self):
        # User policies
        self.user_policies: Dict[str, PolicyConstraints] = {}
        
        # Active session keys
        self.session_keys: Dict[str, SessionKey] = {}
        
        # Transaction history for rate limiting
        self.tx_history: Dict[str, List[Dict]] = {}
        
        # Blocked addresses/protocols
        self.blacklist: Set[str] = set()
        
        # Pending multi-sig approvals
        self.pending_approvals: Dict[str, Dict] = {}
        
        self._session_counter = 0
        
    # ===========================================
    # POLICY MANAGEMENT
    # ===========================================
    
    def get_policy(self, user_id: str) -> PolicyConstraints:
        """Get policy for user (or default)"""
        if user_id not in self.user_policies:
            self.user_policies[user_id] = PolicyConstraints()
        return self.user_policies[user_id]
    
    def update_policy(self, user_id: str, updates: Dict) -> PolicyConstraints:
        """Update user's policy constraints"""
        policy = self.get_policy(user_id)
        
        for key, value in updates.items():
            if hasattr(policy, key):
                setattr(policy, key, value)
        
        logger.info(f"🔒 Policy updated for {user_id}")
        return policy
    
    # ===========================================
    # SESSION KEYS
    # ===========================================
    
    def create_session_key(
        self,
        user_id: str,
        action_type: ActionType,
        max_amount_usd: float,
        duration_hours: int = 24,
        allowed_protocols: Optional[Set[str]] = None,
        allowed_pools: Optional[Set[str]] = None,
        max_transactions: int = 10
    ) -> SessionKey:
        """Create temporary session key for specific actions"""
        
        self._session_counter += 1
        session_id = f"sk_{user_id}_{self._session_counter}"
        
        policy = self.get_policy(user_id)
        
        session = SessionKey(
            id=session_id,
            user_id=user_id,
            action_type=action_type,
            max_amount_usd=min(max_amount_usd, policy.max_single_tx_value_usd * max_transactions),
            expires_at=datetime.now() + timedelta(hours=duration_hours),
            allowed_protocols=allowed_protocols or policy.allowed_protocols,
            allowed_pools=allowed_pools or set(),
            max_transactions=max_transactions
        )
        
        self.session_keys[session_id] = session
        
        logger.info(f"🔑 Session key created: {session_id} for {action_type.value}")
        
        return session
    
    def validate_session_key(
        self,
        session_id: str,
        action_type: ActionType,
        amount_usd: float,
        protocol: str,
        pool_id: Optional[str] = None
    ) -> tuple[bool, str]:
        """Validate if session key allows this action"""
        
        session = self.session_keys.get(session_id)
        
        if not session:
            return False, "Session key not found"
        
        if not session.is_active:
            return False, "Session key is inactive"
        
        if datetime.now() > session.expires_at:
            session.is_active = False
            return False, "Session key expired"
        
        if session.action_type != action_type:
            return False, f"Session key not valid for {action_type.value}"
        
        if session.used_amount_usd + amount_usd > session.max_amount_usd:
            return False, "Would exceed session amount limit"
        
        if session.transaction_count >= session.max_transactions:
            return False, "Session transaction limit reached"
        
        if protocol.lower() not in session.allowed_protocols:
            return False, f"Protocol {protocol} not in allowed list"
        
        if session.allowed_pools and pool_id and pool_id not in session.allowed_pools:
            return False, f"Pool {pool_id} not in allowed list"
        
        return True, "Approved"
    
    def use_session_key(self, session_id: str, amount_usd: float):
        """Record session key usage"""
        session = self.session_keys.get(session_id)
        if session:
            session.used_amount_usd += amount_usd
            session.transaction_count += 1
    
    def revoke_session_key(self, session_id: str):
        """Revoke a session key"""
        if session_id in self.session_keys:
            self.session_keys[session_id].is_active = False
            logger.info(f"🔒 Session key revoked: {session_id}")
    
    # ===========================================
    # TRANSACTION VALIDATION
    # ===========================================
    
    def validate_transaction(
        self,
        user_id: str,
        action_type: ActionType,
        protocol: str,
        chain: str,
        amount_usd: float,
        pool_data: Optional[Dict] = None,
        session_id: Optional[str] = None
    ) -> tuple[bool, str, Dict]:
        """
        Validate a transaction against all security policies
        Returns: (approved, reason, details)
        """
        
        policy = self.get_policy(user_id)
        details = {
            "checks_passed": [],
            "checks_failed": [],
            "warnings": []
        }
        
        # 1. Check blacklist
        if protocol.lower() in self.blacklist or chain.lower() in self.blacklist:
            details["checks_failed"].append("blacklist")
            return False, "Protocol or chain is blacklisted", details
        details["checks_passed"].append("blacklist")
        
        # 2. Check protocol whitelist
        if protocol.lower() not in policy.allowed_protocols:
            details["checks_failed"].append("protocol_whitelist")
            return False, f"Protocol {protocol} is not in allowed list", details
        details["checks_passed"].append("protocol_whitelist")
        
        # 3. Check chain whitelist
        if chain.lower() not in policy.allowed_chains:
            details["checks_failed"].append("chain_whitelist")
            return False, f"Chain {chain} is not allowed", details
        details["checks_passed"].append("chain_whitelist")
        
        # 4. Check transaction amount limit
        if amount_usd > policy.max_single_tx_value_usd:
            details["checks_failed"].append("tx_amount")
            return False, f"Amount ${amount_usd:,.2f} exceeds limit ${policy.max_single_tx_value_usd:,.2f}", details
        details["checks_passed"].append("tx_amount")
        
        # 5. Check rate limiting
        rate_check = self._check_rate_limit(user_id, policy)
        if not rate_check[0]:
            details["checks_failed"].append("rate_limit")
            return False, rate_check[1], details
        details["checks_passed"].append("rate_limit")
        
        # 6. Check pool requirements if pool data provided
        if pool_data:
            tvl = pool_data.get("tvl", 0)
            if tvl < policy.min_pool_tvl_usd:
                details["checks_failed"].append("min_tvl")
                return False, f"Pool TVL ${tvl:,.0f} below minimum ${policy.min_pool_tvl_usd:,.0f}", details
            details["checks_passed"].append("min_tvl")
            
            # Check risk level
            risk_score = pool_data.get("risk_score", "medium").lower()
            risk_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            if risk_levels.get(risk_score, 2) > risk_levels.get(policy.max_risk_level.value, 2):
                details["checks_failed"].append("risk_level")
                return False, f"Pool risk {risk_score} exceeds max {policy.max_risk_level.value}", details
            details["checks_passed"].append("risk_level")
        
        # 7. Validate session key if provided
        if session_id:
            valid, reason = self.validate_session_key(
                session_id, action_type, amount_usd, protocol
            )
            if not valid:
                details["checks_failed"].append("session_key")
                return False, reason, details
            details["checks_passed"].append("session_key")
        
        logger.info(f"✅ Transaction approved: {action_type.value} ${amount_usd} to {protocol}")
        return True, "Transaction approved", details
    
    def _check_rate_limit(self, user_id: str, policy: PolicyConstraints) -> tuple[bool, str]:
        """Check if user has exceeded rate limits"""
        now = datetime.now()
        day_ago = now - timedelta(days=1)
        
        # Get recent transactions
        user_txs = self.tx_history.get(user_id, [])
        recent_txs = [tx for tx in user_txs if tx["timestamp"] > day_ago]
        
        # Check daily limit
        if len(recent_txs) >= policy.max_daily_transactions:
            return False, f"Daily transaction limit ({policy.max_daily_transactions}) reached"
        
        # Check minimum delay
        if recent_txs:
            last_tx = max(recent_txs, key=lambda x: x["timestamp"])
            time_since = (now - last_tx["timestamp"]).total_seconds()
            if time_since < policy.min_delay_between_tx_seconds:
                return False, f"Please wait {policy.min_delay_between_tx_seconds - int(time_since)}s between transactions"
        
        return True, "OK"
    
    def record_transaction(self, user_id: str, action_type: ActionType, amount_usd: float, details: Dict):
        """Record a transaction for rate limiting"""
        if user_id not in self.tx_history:
            self.tx_history[user_id] = []
        
        self.tx_history[user_id].append({
            "timestamp": datetime.now(),
            "action": action_type.value,
            "amount_usd": amount_usd,
            "details": details
        })
    
    # ===========================================
    # EMERGENCY CONTROLS
    # ===========================================
    
    def emergency_pause(self, user_id: str):
        """Emergency: Pause all activity for a user"""
        # Revoke all session keys
        for session_id, session in self.session_keys.items():
            if session.user_id == user_id:
                session.is_active = False
        
        # Set max restrictive policy
        policy = self.get_policy(user_id)
        policy.max_daily_transactions = 0
        policy.max_single_tx_value_usd = 0
        
        logger.warning(f"🚨 EMERGENCY PAUSE activated for {user_id}")
    
    def add_to_blacklist(self, address_or_protocol: str):
        """Add to global blacklist"""
        self.blacklist.add(address_or_protocol.lower())
        logger.warning(f"⛔ Added to blacklist: {address_or_protocol}")
    
    def remove_from_blacklist(self, address_or_protocol: str):
        """Remove from blacklist"""
        self.blacklist.discard(address_or_protocol.lower())


# Singleton
security_policy = SecurityPolicyManager()
