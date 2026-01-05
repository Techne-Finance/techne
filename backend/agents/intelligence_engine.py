"""
Enhanced AI Memory System for Techne Finance
Cross-agent memory sharing, predictive learning, and pattern detection

This is THE MOAT - the feature that makes Techne worth a billion dollars.
No other yield aggregator learns from outcomes like this.

Features:
- Cross-agent memory sharing
- Outcome-based learning (+success, -failure)
- Pattern clustering
- Protocol trust scoring
- User preference personalization
- Predictive recommendations
"""

import asyncio
import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IntelligenceEngine")


# ============================================
# MEMORY TYPES
# ============================================

class MemoryType(str, Enum):
    POOL_OUTCOME = "pool_outcome"       # How a pool performed
    STRATEGY_RESULT = "strategy_result" # Strategy success/failure
    USER_PREFERENCE = "user_preference" # User behaviors
    PROTOCOL_TRUST = "protocol_trust"   # Protocol reliability
    MARKET_PATTERN = "market_pattern"   # Market trends
    CONVERSATION = "conversation"       # Chat history
    AGENT_INSIGHT = "agent_insight"     # Cross-agent learning


class OutcomeType(str, Enum):
    SUCCESS = "success"     # Good outcome
    FAILURE = "failure"     # Bad outcome
    NEUTRAL = "neutral"     # Neither good nor bad
    PENDING = "pending"     # Awaiting result


@dataclass
class Memory:
    """A single memory unit"""
    id: str
    type: MemoryType
    content: Dict[str, Any]
    score: float = 0.5  # 0=bad, 1=great
    confidence: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    tags: Set[str] = field(default_factory=set)
    source_agent: str = "system"
    related_memories: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "score": self.score,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "tags": list(self.tags),
            "source_agent": self.source_agent
        }


@dataclass
class PoolOutcome:
    """Tracks pool performance outcome"""
    pool_id: str
    protocol: str
    chain: str
    entry_apy: float
    exit_apy: float
    actual_return: float  # %
    expected_return: float  # %
    duration_days: int
    outcome: OutcomeType
    notes: str = ""


@dataclass
class ProtocolTrust:
    """Protocol trust score"""
    protocol: str
    trust_score: float  # 0-100
    success_count: int = 0
    failure_count: int = 0
    total_tvl_seen: float = 0
    avg_apy_accuracy: float = 0
    rug_pull_history: bool = False
    last_updated: datetime = field(default_factory=datetime.now)


# ============================================
# PATTERN DETECTION
# ============================================

class PatternDetector:
    """Detects patterns in historical data"""
    
    @staticmethod
    def detect_apy_decay_pattern(apy_history: List[float]) -> Dict:
        """Detect if APY is consistently declining"""
        if len(apy_history) < 5:
            return {"pattern": "insufficient_data"}
        
        declines = sum(1 for i in range(1, len(apy_history)) if apy_history[i] < apy_history[i-1])
        decline_ratio = declines / (len(apy_history) - 1)
        
        if decline_ratio > 0.7:
            return {
                "pattern": "consistent_decline",
                "decline_ratio": decline_ratio,
                "recommendation": "Consider exit - APY trending down"
            }
        elif decline_ratio > 0.5:
            return {
                "pattern": "moderate_decline",
                "decline_ratio": decline_ratio,
                "recommendation": "Monitor closely"
            }
        else:
            return {
                "pattern": "stable_or_rising",
                "decline_ratio": decline_ratio,
                "recommendation": "Hold or increase position"
            }
    
    @staticmethod
    def detect_tvl_divergence(tvl_history: List[float], apy_history: List[float]) -> Dict:
        """Detect when TVL and APY diverge (warning sign)"""
        if len(tvl_history) < 3 or len(apy_history) < 3:
            return {"pattern": "insufficient_data"}
        
        # TVL dropping while APY rising = warning
        tvl_trend = (tvl_history[-1] - tvl_history[0]) / tvl_history[0]
        apy_trend = (apy_history[-1] - apy_history[0]) / max(apy_history[0], 0.01)
        
        if tvl_trend < -0.2 and apy_trend > 0.2:
            return {
                "pattern": "divergence_warning",
                "tvl_change": tvl_trend,
                "apy_change": apy_trend,
                "recommendation": "High risk - TVL exit while APY pumped"
            }
        
        return {"pattern": "normal", "tvl_trend": tvl_trend, "apy_trend": apy_trend}
    
    @staticmethod
    def detect_whale_behavior(large_tx_history: List[Dict]) -> Dict:
        """Detect whale accumulation or distribution"""
        if not large_tx_history:
            return {"pattern": "no_whale_data"}
        
        deposits = sum(1 for tx in large_tx_history if tx.get("type") == "deposit")
        withdrawals = len(large_tx_history) - deposits
        
        if deposits > withdrawals * 2:
            return {
                "pattern": "whale_accumulation",
                "sentiment": "bullish",
                "recommendation": "Follow smart money - consider entry"
            }
        elif withdrawals > deposits * 2:
            return {
                "pattern": "whale_distribution",
                "sentiment": "bearish",
                "recommendation": "Smart money exiting - consider exit"
            }
        
        return {"pattern": "neutral", "deposits": deposits, "withdrawals": withdrawals}


# ============================================
# PREDICTION ENGINE
# ============================================

class PredictionEngine:
    """AI-powered predictions based on learned patterns"""
    
    def __init__(self):
        self.prediction_history: List[Dict] = []
        self.accuracy_by_type: Dict[str, List[float]] = defaultdict(list)
    
    def predict_apy_sustainability(self, pool: Dict, memories: List[Memory]) -> Dict:
        """Predict if current APY is sustainable"""
        apy = pool.get("apy", 0)
        tvl = pool.get("tvlUsd", 0)
        protocol = pool.get("project", "unknown")
        
        # Base prediction from pool metrics
        sustainability_score = 100
        factors = []
        
        # Factor 1: High APY = less sustainable
        if apy > 100:
            sustainability_score -= 40
            factors.append(f"Very high APY ({apy}%) is unsustainable")
        elif apy > 50:
            sustainability_score -= 20
            factors.append(f"High APY ({apy}%) may decline")
        
        # Factor 2: Low TVL = higher risk
        if tvl < 1_000_000:
            sustainability_score -= 20
            factors.append(f"Low TVL (${tvl/1e6:.1f}M) increases risk")
        
        # Factor 3: Learn from similar pools in memory
        similar_outcomes = [m for m in memories if 
                          m.type == MemoryType.POOL_OUTCOME and 
                          m.content.get("protocol") == protocol]
        
        if similar_outcomes:
            avg_score = sum(m.score for m in similar_outcomes) / len(similar_outcomes)
            if avg_score < 0.4:
                sustainability_score -= 25
                factors.append(f"Protocol has poor historical performance")
            elif avg_score > 0.7:
                sustainability_score += 10
                factors.append(f"Protocol has strong track record")
        
        sustainability_score = max(0, min(100, sustainability_score))
        
        prediction = {
            "pool_id": pool.get("pool"),
            "current_apy": apy,
            "sustainability_score": sustainability_score,
            "prediction": "sustainable" if sustainability_score > 60 else "likely_to_decline",
            "confidence": 0.6 + (len(similar_outcomes) * 0.05),  # More data = more confident
            "factors": factors,
            "predicted_at": datetime.now().isoformat()
        }
        
        return prediction
    
    def predict_protocol_safety(self, protocol: str, trust: Optional[ProtocolTrust]) -> Dict:
        """Predict protocol safety based on history"""
        if not trust:
            return {
                "protocol": protocol,
                "safety_score": 50,
                "prediction": "unknown",
                "confidence": 0.3,
                "reason": "No historical data"
            }
        
        safety_score = trust.trust_score
        
        if trust.rug_pull_history:
            return {
                "protocol": protocol,
                "safety_score": 0,
                "prediction": "avoid",
                "confidence": 1.0,
                "reason": "History of rug pull"
            }
        
        success_rate = trust.success_count / max(trust.success_count + trust.failure_count, 1)
        
        return {
            "protocol": protocol,
            "safety_score": safety_score,
            "success_rate": success_rate,
            "prediction": "safe" if safety_score > 70 else "moderate" if safety_score > 40 else "risky",
            "confidence": min(0.9, 0.4 + (trust.success_count * 0.02)),
            "total_observations": trust.success_count + trust.failure_count
        }


# ============================================
# RECOMMENDATION ENGINE
# ============================================

class RecommendationEngine:
    """Generates personalized recommendations"""
    
    def __init__(self, intelligence: "IntelligenceEngine"):
        self.intelligence = intelligence
    
    def get_personalized_pools(
        self, 
        user_id: str, 
        available_pools: List[Dict],
        limit: int = 10
    ) -> List[Dict]:
        """Get pools personalized for user preferences"""
        
        # Get user preferences from memory
        preferences = self.intelligence.get_user_preferences(user_id)
        
        risk_tolerance = preferences.get("risk_tolerance", "medium")
        preferred_chains = preferences.get("preferred_chains", [])
        min_apy = preferences.get("min_apy_threshold", 5.0)
        avoided_protocols = preferences.get("avoided_protocols", [])
        
        scored_pools = []
        
        for pool in available_pools:
            score = 100
            reasons = []
            
            # Filter by minimum APY
            if pool.get("apy", 0) < min_apy:
                continue
            
            # Filter by avoided protocols
            if pool.get("project") in avoided_protocols:
                continue
            
            # Prefer user's chains
            if preferred_chains and pool.get("chain") in preferred_chains:
                score += 20
                reasons.append(f"Preferred chain: {pool.get('chain')}")
            
            # Adjust for risk tolerance
            pool_risk = pool.get("risk_level", "medium")
            if risk_tolerance == "low":
                if pool_risk in ["high", "critical"]:
                    continue
                if pool_risk == "low":
                    score += 15
            elif risk_tolerance == "high":
                if pool.get("apy", 0) > 30:
                    score += 10
            
            # Add protocol trust score
            trust = self.intelligence.get_protocol_trust(pool.get("project", ""))
            if trust:
                score += trust.trust_score * 0.3
                if trust.trust_score > 70:
                    reasons.append("Trusted protocol")
            
            pool["recommendation_score"] = score
            pool["recommendation_reasons"] = reasons
            scored_pools.append(pool)
        
        # Sort by recommendation score
        scored_pools.sort(key=lambda p: p.get("recommendation_score", 0), reverse=True)
        
        return scored_pools[:limit]
    
    def generate_action_recommendations(
        self,
        user_id: str,
        current_positions: List[Dict]
    ) -> List[Dict]:
        """Generate action recommendations for user's positions"""
        recommendations = []
        
        for position in current_positions:
            pool_id = position.get("pool_id")
            entry_apy = position.get("entry_apy", 0)
            current_apy = position.get("current_apy", 0)
            
            # Check APY decline
            if current_apy < entry_apy * 0.7:
                recommendations.append({
                    "type": "consider_exit",
                    "pool_id": pool_id,
                    "reason": f"APY dropped {((entry_apy - current_apy) / entry_apy * 100):.1f}%",
                    "priority": "high"
                })
            
            # Check for better alternatives
            # (Would query available pools here)
            
        return recommendations


# ============================================
# MAIN INTELLIGENCE ENGINE
# ============================================

class IntelligenceEngine:
    """
    The brain of Techne Finance.
    Manages all AI memory, learning, and predictions.
    """
    
    def __init__(self):
        self.memories: Dict[str, Memory] = {}
        self.protocol_trust: Dict[str, ProtocolTrust] = {}
        self.user_preferences: Dict[str, Dict] = {}
        
        self.pattern_detector = PatternDetector()
        self.prediction_engine = PredictionEngine()
        self.recommendation_engine = RecommendationEngine(self)
        
        # Learning parameters
        self.success_boost = 0.2  # Score increase on success
        self.failure_penalty = 0.3  # Score decrease on failure
        
        # Initialize with known trusted protocols
        self._init_known_protocols()
        
        logger.info("Intelligence Engine initialized")
    
    def _init_known_protocols(self):
        """Initialize with known protocol trust scores"""
        known_protocols = {
            "aave-v3": 85,
            "compound-v3": 82,
            "morpho": 78,
            "lido": 80,
            "rocket-pool": 75,
            "curve": 75,
            "convex": 73,
            "yearn": 72,
            "beefy": 70,
            "velodrome": 68,
            "aerodrome": 67,
        }
        
        for protocol, score in known_protocols.items():
            self.protocol_trust[protocol] = ProtocolTrust(
                protocol=protocol,
                trust_score=score,
                success_count=10,  # Assumed successful history
            )
    
    def _generate_id(self, prefix: str = "mem") -> str:
        """Generate unique memory ID"""
        timestamp = datetime.now().isoformat()
        return f"{prefix}_{hashlib.md5(timestamp.encode()).hexdigest()[:12]}"
    
    # ============================================
    # MEMORY OPERATIONS
    # ============================================
    
    def store_memory(
        self,
        type: MemoryType,
        content: Dict,
        tags: Set[str] = None,
        source_agent: str = "system"
    ) -> Memory:
        """Store a new memory"""
        memory_id = self._generate_id("mem")
        
        memory = Memory(
            id=memory_id,
            type=type,
            content=content,
            tags=tags or set(),
            source_agent=source_agent
        )
        
        self.memories[memory_id] = memory
        
        # Auto-extract tags from content
        self._auto_tag_memory(memory)
        
        logger.debug(f"Stored memory {memory_id}: {type.value}")
        
        return memory
    
    def recall_memories(
        self,
        type: Optional[MemoryType] = None,
        tags: Set[str] = None,
        min_score: float = 0,
        limit: int = 100
    ) -> List[Memory]:
        """Recall memories matching criteria"""
        results = []
        
        for memory in self.memories.values():
            # Filter by type
            if type and memory.type != type:
                continue
            
            # Filter by tags (any match)
            if tags and not tags.intersection(memory.tags):
                continue
            
            # Filter by score
            if memory.score < min_score:
                continue
            
            results.append(memory)
            memory.access_count += 1
        
        # Sort by score and recency
        results.sort(key=lambda m: (m.score, m.updated_at), reverse=True)
        
        return results[:limit]
    
    def _auto_tag_memory(self, memory: Memory):
        """Automatically extract tags from memory content"""
        content = memory.content
        
        if "protocol" in content:
            memory.tags.add(f"protocol:{content['protocol']}")
        
        if "chain" in content:
            memory.tags.add(f"chain:{content['chain']}")
        
        if "pool_id" in content:
            memory.tags.add(f"pool:{content['pool_id'][:20]}")
        
        if "user_id" in content:
            memory.tags.add(f"user:{content['user_id']}")
    
    # ============================================
    # OUTCOME LEARNING
    # ============================================
    
    def record_outcome(
        self,
        outcome: PoolOutcome
    ):
        """Record and learn from a pool outcome"""
        
        # Store as memory
        memory = self.store_memory(
            type=MemoryType.POOL_OUTCOME,
            content={
                "pool_id": outcome.pool_id,
                "protocol": outcome.protocol,
                "chain": outcome.chain,
                "entry_apy": outcome.entry_apy,
                "exit_apy": outcome.exit_apy,
                "actual_return": outcome.actual_return,
                "expected_return": outcome.expected_return,
                "duration_days": outcome.duration_days,
                "outcome": outcome.outcome.value
            },
            tags={f"protocol:{outcome.protocol}", f"chain:{outcome.chain}"}
        )
        
        # Update score based on outcome
        if outcome.outcome == OutcomeType.SUCCESS:
            memory.score = 0.7 + min(0.3, outcome.actual_return / 100)
        elif outcome.outcome == OutcomeType.FAILURE:
            memory.score = max(0.1, 0.5 - abs(outcome.actual_return) / 100)
        else:
            memory.score = 0.5
        
        # Update protocol trust
        self._update_protocol_trust(outcome)
        
        logger.info(f"Recorded {outcome.outcome.value} outcome for {outcome.pool_id}")
    
    def _update_protocol_trust(self, outcome: PoolOutcome):
        """Update protocol trust score based on outcome"""
        protocol = outcome.protocol.lower()
        
        if protocol not in self.protocol_trust:
            self.protocol_trust[protocol] = ProtocolTrust(protocol=protocol, trust_score=50)
        
        trust = self.protocol_trust[protocol]
        
        if outcome.outcome == OutcomeType.SUCCESS:
            trust.success_count += 1
            trust.trust_score = min(100, trust.trust_score + self.success_boost * 10)
        elif outcome.outcome == OutcomeType.FAILURE:
            trust.failure_count += 1
            trust.trust_score = max(0, trust.trust_score - self.failure_penalty * 10)
        
        # Update APY accuracy
        if outcome.expected_return > 0:
            accuracy = 1 - abs(outcome.actual_return - outcome.expected_return) / outcome.expected_return
            trust.avg_apy_accuracy = (trust.avg_apy_accuracy + max(0, accuracy)) / 2
        
        trust.last_updated = datetime.now()
    
    # ============================================
    # USER PREFERENCES
    # ============================================
    
    def update_user_preference(
        self,
        user_id: str,
        key: str,
        value: Any
    ):
        """Update a user preference"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
        
        self.user_preferences[user_id][key] = value
        
        # Store as memory for cross-session persistence
        self.store_memory(
            type=MemoryType.USER_PREFERENCE,
            content={"user_id": user_id, "key": key, "value": value},
            tags={f"user:{user_id}"}
        )
    
    def get_user_preferences(self, user_id: str) -> Dict:
        """Get all preferences for a user"""
        return self.user_preferences.get(user_id, {
            "risk_tolerance": "medium",
            "preferred_chains": [],
            "min_apy_threshold": 5.0,
            "avoided_protocols": []
        })
    
    def learn_from_user_action(
        self,
        user_id: str,
        action: str,
        context: Dict
    ):
        """Learn from user actions to update preferences"""
        if action == "deposit":
            # User deposited - they like this chain/protocol
            chain = context.get("chain")
            if chain:
                prefs = self.get_user_preferences(user_id)
                chains = prefs.get("preferred_chains", [])
                if chain not in chains:
                    chains.append(chain)
                    self.update_user_preference(user_id, "preferred_chains", chains)
        
        elif action == "avoid_pool":
            # User explicitly avoided - add to avoided list
            protocol = context.get("protocol")
            if protocol:
                prefs = self.get_user_preferences(user_id)
                avoided = prefs.get("avoided_protocols", [])
                if protocol not in avoided:
                    avoided.append(protocol)
                    self.update_user_preference(user_id, "avoided_protocols", avoided)
    
    # ============================================
    # CROSS-AGENT SHARING
    # ============================================
    
    def share_insight(
        self,
        source_agent: str,
        insight_type: str,
        content: Dict
    ):
        """Share insight between agents"""
        self.store_memory(
            type=MemoryType.AGENT_INSIGHT,
            content={
                "insight_type": insight_type,
                **content
            },
            source_agent=source_agent,
            tags={f"agent:{source_agent}", f"insight:{insight_type}"}
        )
    
    def get_agent_insights(
        self,
        requesting_agent: str,
        insight_types: List[str] = None,
        limit: int = 50
    ) -> List[Memory]:
        """Get insights shared by other agents"""
        return self.recall_memories(
            type=MemoryType.AGENT_INSIGHT,
            min_score=0.3,
            limit=limit
        )
    
    # ============================================
    # PUBLIC API
    # ============================================
    
    def get_protocol_trust(self, protocol: str) -> Optional[ProtocolTrust]:
        """Get trust score for a protocol"""
        return self.protocol_trust.get(protocol.lower())
    
    def get_predictions(self, pool: Dict) -> Dict:
        """Get all predictions for a pool"""
        memories = self.recall_memories(
            type=MemoryType.POOL_OUTCOME,
            tags={f"protocol:{pool.get('project', '')}"},
            limit=50
        )
        
        return {
            "apy_sustainability": self.prediction_engine.predict_apy_sustainability(pool, memories),
            "protocol_safety": self.prediction_engine.predict_protocol_safety(
                pool.get("project", ""),
                self.get_protocol_trust(pool.get("project", ""))
            )
        }
    
    def get_recommendations(
        self,
        user_id: str,
        available_pools: List[Dict],
        limit: int = 10
    ) -> List[Dict]:
        """Get personalized pool recommendations"""
        return self.recommendation_engine.get_personalized_pools(
            user_id=user_id,
            available_pools=available_pools,
            limit=limit
        )
    
    def get_stats(self) -> Dict:
        """Get intelligence engine statistics"""
        return {
            "total_memories": len(self.memories),
            "memories_by_type": {
                t.value: len([m for m in self.memories.values() if m.type == t])
                for t in MemoryType
            },
            "protocols_tracked": len(self.protocol_trust),
            "users_profiled": len(self.user_preferences),
            "avg_memory_score": sum(m.score for m in self.memories.values()) / max(len(self.memories), 1)
        }


# ============================================
# GLOBAL INSTANCE
# ============================================

intelligence = IntelligenceEngine()


def get_intelligence() -> IntelligenceEngine:
    """Get the global intelligence engine"""
    return intelligence
