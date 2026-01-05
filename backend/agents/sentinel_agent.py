"""
Sentinel Agent - "The Guardian Eye" of Artisan System
Security monitoring, rug pull detection, contract analysis

Responsibilities:
- Monitor contract security signals
- Detect potential rug pulls (liquidity removal)
- Track team wallet movements
- Verify contract age and audit status
- Real-time security alerts
- Log security events via Memory Engine
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Observability integration
try:
    from agents.observability_engine import observability, traced, SpanStatus
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False
    def traced(agent, op):
        def decorator(func): return func
        return decorator

# Memory integration
try:
    from agents.memory_engine import memory_engine, MemoryType
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SentinelAgent")


class ThreatLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityFlag(Enum):
    RUG_PULL_RISK = "rug_pull_risk"
    LIQUIDITY_DRAIN = "liquidity_drain"
    HONEYPOT = "honeypot"
    UNVERIFIED_CONTRACT = "unverified_contract"
    NEW_CONTRACT = "new_contract"
    TEAM_DUMP = "team_dump"
    FLASH_LOAN_ATTACK = "flash_loan_attack"
    ORACLE_MANIPULATION = "oracle_manipulation"


@dataclass
class SecurityReport:
    pool_id: str
    threat_level: ThreatLevel
    flags: List[SecurityFlag]
    warnings: List[str]
    recommendations: List[str]
    contract_age_days: int
    is_audited: bool
    liquidity_locked: bool
    team_token_percent: float


class SentinelAgent:
    """
    The Sentinel - Security Monitoring Agent
    Never sleeps, always watching for threats
    """
    
    def __init__(self):
        # Known auditors
        self.trusted_auditors = [
            "certik", "slowmist", "peckshield", "openzeppelin",
            "trail_of_bits", "consensys", "hacken", "quantstamp"
        ]
        
        # Risk thresholds
        self.thresholds = {
            "min_contract_age_days": 7,
            "min_liquidity_locked_percent": 80,
            "max_team_token_percent": 20,
            "min_tvl_for_trust": 100000,
            "tvl_drop_alert_percent": 30,  # Alert if TVL drops 30% in 24h
        }
        
        # Blacklisted contracts/protocols
        self.blacklist = set()
        
        # Watchlist (under observation)
        self.watchlist: Dict[str, Dict] = {}
        
        # Security events history
        self.security_events: List[Dict] = []
        
        self.subscribers = []
        
    def subscribe(self, callback):
        """Subscribe to security alerts"""
        self.subscribers.append(callback)
        
    async def _notify_alert(self, alert_type: str, data: Dict):
        """Send security alert to subscribers"""
        for callback in self.subscribers:
            try:
                await callback(alert_type, data)
            except Exception as e:
                logger.error(f"Failed to notify subscriber: {e}")
    
    # ===========================================
    # SECURITY ANALYSIS
    # ===========================================
    
    def analyze_pool_security(self, pool: Dict) -> SecurityReport:
        """Comprehensive security analysis of a pool"""
        flags = []
        warnings = []
        recommendations = []
        
        pool_id = pool.get("pool", "unknown")
        project = pool.get("project", "").lower()
        tvl = pool.get("tvlUsd", 0)
        apy = pool.get("apy", 0)
        
        # Mock data (in production, fetch from blockchain/APIs)
        contract_age_days = 30  # Would query blockchain
        is_audited = project in ["aave-v3", "compound-v3", "uniswap-v3", "aerodrome"]
        liquidity_locked = True  # Would check LP locks
        team_token_percent = 10  # Would analyze token distribution
        
        # Check 1: Contract age
        if contract_age_days < self.thresholds["min_contract_age_days"]:
            flags.append(SecurityFlag.NEW_CONTRACT)
            warnings.append(f"Contract is only {contract_age_days} days old")
            recommendations.append("Wait for contract to mature before large deposits")
        
        # Check 2: Audit status
        if not is_audited:
            flags.append(SecurityFlag.UNVERIFIED_CONTRACT)
            warnings.append("No known audit from trusted auditors")
            recommendations.append("Verify contract code manually or use smaller amounts")
        
        # Check 3: TVL sanity
        if tvl < self.thresholds["min_tvl_for_trust"] and apy > 50:
            flags.append(SecurityFlag.RUG_PULL_RISK)
            warnings.append("Low TVL with high APY - potential honeypot or rug")
            recommendations.append("Avoid or use minimal test amounts only")
        
        # Check 4: Team token concentration
        if team_token_percent > self.thresholds["max_team_token_percent"]:
            flags.append(SecurityFlag.TEAM_DUMP)
            warnings.append(f"Team holds {team_token_percent}% of tokens - dump risk")
        
        # Check 5: Blacklist
        if pool_id in self.blacklist or project in self.blacklist:
            flags.append(SecurityFlag.RUG_PULL_RISK)
            warnings.append("This pool/protocol is on our blacklist")
            recommendations.append("DO NOT DEPOSIT - Known bad actor")
        
        # Determine threat level
        threat_level = self._calculate_threat_level(flags)
        
        return SecurityReport(
            pool_id=pool_id,
            threat_level=threat_level,
            flags=flags,
            warnings=warnings,
            recommendations=recommendations,
            contract_age_days=contract_age_days,
            is_audited=is_audited,
            liquidity_locked=liquidity_locked,
            team_token_percent=team_token_percent
        )
    
    def _calculate_threat_level(self, flags: List[SecurityFlag]) -> ThreatLevel:
        """Calculate overall threat level from flags"""
        critical_flags = [SecurityFlag.RUG_PULL_RISK, SecurityFlag.HONEYPOT, SecurityFlag.FLASH_LOAN_ATTACK]
        high_flags = [SecurityFlag.LIQUIDITY_DRAIN, SecurityFlag.TEAM_DUMP, SecurityFlag.ORACLE_MANIPULATION]
        
        if any(f in flags for f in critical_flags):
            return ThreatLevel.CRITICAL
        elif any(f in flags for f in high_flags):
            return ThreatLevel.HIGH
        elif SecurityFlag.UNVERIFIED_CONTRACT in flags:
            return ThreatLevel.MEDIUM
        elif SecurityFlag.NEW_CONTRACT in flags:
            return ThreatLevel.LOW
        else:
            return ThreatLevel.SAFE
    
    # ===========================================
    # REAL-TIME MONITORING
    # ===========================================
    
    async def monitor_tvl_changes(self, pools: List[Dict], previous_pools: List[Dict]):
        """Detect suspicious TVL drops"""
        if not previous_pools:
            return
        
        prev_map = {p.get("pool"): p for p in previous_pools}
        
        for pool in pools:
            pool_id = pool.get("pool")
            if pool_id not in prev_map:
                continue
            
            old_tvl = prev_map[pool_id].get("tvlUsd", 0)
            new_tvl = pool.get("tvlUsd", 0)
            
            if old_tvl > 0:
                change_pct = ((new_tvl - old_tvl) / old_tvl) * 100
                
                if change_pct < -self.thresholds["tvl_drop_alert_percent"]:
                    await self._notify_alert("tvl_drop", {
                        "pool": pool,
                        "old_tvl": old_tvl,
                        "new_tvl": new_tvl,
                        "change_pct": change_pct,
                        "severity": "high" if change_pct < -50 else "medium"
                    })
                    
                    self.security_events.append({
                        "type": "tvl_drop",
                        "pool_id": pool_id,
                        "change_pct": change_pct,
                        "timestamp": datetime.now()
                    })
    
    async def check_liquidity_locks(self, pool: Dict) -> Dict:
        """Check if liquidity is locked"""
        # In production: Query LP locker contracts (Unicrypt, Team Finance, etc.)
        return {
            "is_locked": True,
            "lock_percent": 95,
            "unlock_date": datetime.now() + timedelta(days=365),
            "locker": "unicrypt"
        }
    
    # ===========================================
    # BLACKLIST MANAGEMENT
    # ===========================================
    
    def add_to_blacklist(self, identifier: str, reason: str):
        """Add pool/protocol to blacklist"""
        self.blacklist.add(identifier)
        self.security_events.append({
            "type": "blacklist_add",
            "identifier": identifier,
            "reason": reason,
            "timestamp": datetime.now()
        })
        logger.warning(f"🚫 Blacklisted: {identifier} - {reason}")
    
    def add_to_watchlist(self, pool_id: str, reason: str):
        """Add pool to watchlist for monitoring"""
        self.watchlist[pool_id] = {
            "reason": reason,
            "added": datetime.now(),
            "tvl_at_add": 0,  # Would fetch current TVL
        }
        logger.info(f"👁️ Watching: {pool_id} - {reason}")
    
    # ===========================================
    # REPORTS
    # ===========================================
    
    def get_security_summary(self, pools: List[Dict]) -> Dict:
        """Get security summary for multiple pools"""
        reports = [self.analyze_pool_security(p) for p in pools]
        
        threat_counts = {}
        for report in reports:
            level = report.threat_level.value
            threat_counts[level] = threat_counts.get(level, 0) + 1
        
        return {
            "total_pools": len(pools),
            "threat_distribution": threat_counts,
            "blacklisted_count": len(self.blacklist),
            "watchlist_count": len(self.watchlist),
            "recent_events": self.security_events[-10:]
        }
    
    def is_safe_to_deposit(self, pool: Dict) -> tuple[bool, str]:
        """Quick safety check"""
        report = self.analyze_pool_security(pool)
        
        if report.threat_level == ThreatLevel.CRITICAL:
            return False, "CRITICAL: Do not deposit - high risk of loss"
        elif report.threat_level == ThreatLevel.HIGH:
            return False, "HIGH RISK: Not recommended for deposits"
        elif report.threat_level == ThreatLevel.MEDIUM:
            return True, "CAUTION: Proceed with small amounts only"
        else:
            return True, "Safe for deposits"


# Singleton
sentinel = SentinelAgent()
