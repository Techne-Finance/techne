"""
Outcome-Based Memory Engine for Techne Finance Agents
Inspired by RoamPal's 5-Tier Memory Architecture

Memory Types:
- Working Memory: Short-term (24h) - current session context
- History Memory: Medium-term (30 days) - past interactions
- Pattern Memory: Permanent - learned successful patterns
- Strategy Memory: Permanent - profitable strategies
- Preference Bank: Permanent - user identity/preferences

Key Features:
- Outcome Tracking: +0.2 for success, -0.3 for failure
- Smart Promotion: Good memories become permanent
- Cross-Agent Sharing: Agents share knowledge
- Pattern Recognition: Detects what works
"""

import json
import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MemoryEngine")


class MemoryTier(Enum):
    """Memory tiers with different retention policies"""
    WORKING = "working"       # 24 hours
    HISTORY = "history"       # 30 days
    PATTERN = "pattern"       # Permanent, learned
    STRATEGY = "strategy"     # Permanent, profitable strategies
    PREFERENCE = "preference" # Permanent, user identity


class MemoryType(Enum):
    """Types of memories stored"""
    POOL_OUTCOME = "pool_outcome"           # APY prediction vs reality
    STRATEGY_RESULT = "strategy_result"     # Strategy profit/loss
    USER_PREFERENCE = "user_preference"     # User preferences
    PROTOCOL_TRUST = "protocol_trust"       # Protocol reliability
    CHAIN_PREFERENCE = "chain_preference"   # Preferred chains
    RISK_TOLERANCE = "risk_tolerance"       # Learned risk profile
    AGENT_INSIGHT = "agent_insight"         # Agent-learned patterns
    CONVERSATION = "conversation"           # Chat context


@dataclass
class Memory:
    """A single memory unit"""
    id: str
    tier: MemoryTier
    memory_type: MemoryType
    content: Dict[str, Any]
    score: float  # Effectiveness score (0.0 to 1.0)
    created_at: datetime
    updated_at: datetime
    access_count: int = 0
    user_id: str = "default"
    agent_id: str = "system"
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class OutcomeBasedMemory:
    """
    Outcome-Based Memory Engine with 5-Tier Architecture.
    Memories adapt based on feedback - successful advice is boosted,
    failed advice is penalized and eventually forgotten.
    """
    
    # Outcome scoring
    SUCCESS_BOOST = 0.2      # Score increase for successful outcome
    FAILURE_PENALTY = -0.3   # Score decrease for failed outcome
    NEUTRAL_DECAY = -0.01    # Natural decay per day for unused memories
    
    # Promotion thresholds
    PROMOTE_THRESHOLD = 0.8  # Score needed to promote to permanent
    FORGET_THRESHOLD = 0.2   # Score below which memory is forgotten
    
    # Retention periods
    WORKING_RETENTION = timedelta(hours=24)
    HISTORY_RETENTION = timedelta(days=30)
    
    def __init__(self, db_path: str = "techne_memory.db"):
        self.db_path = db_path
        self._init_database()
        logger.info("🧠 Outcome-Based Memory Engine initialized")
    
    def _init_database(self):
        """Initialize SQLite database for memory persistence"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                tier TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                score REAL DEFAULT 0.5,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                access_count INTEGER DEFAULT 0,
                user_id TEXT DEFAULT 'default',
                agent_id TEXT DEFAULT 'system',
                tags TEXT DEFAULT '[]'
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tier ON memories(tier)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_type ON memories(memory_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user ON memories(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_score ON memories(score)
        """)
        
        conn.commit()
        conn.close()
    
    # ==========================================
    # CORE MEMORY OPERATIONS
    # ==========================================
    
    async def store(
        self,
        memory_type: MemoryType,
        content: Dict[str, Any],
        tier: MemoryTier = MemoryTier.WORKING,
        user_id: str = "default",
        agent_id: str = "system",
        tags: List[str] = None
    ) -> Memory:
        """
        Store a new memory in the system.
        
        Args:
            memory_type: Type of memory (pool_outcome, strategy_result, etc.)
            content: The actual memory content
            tier: Which tier to store in (default: working)
            user_id: User this memory belongs to
            agent_id: Agent that created this memory
            tags: Searchable tags
            
        Returns:
            The created Memory object
        """
        memory_id = self._generate_id(content)
        now = datetime.now()
        
        memory = Memory(
            id=memory_id,
            tier=tier,
            memory_type=memory_type,
            content=content,
            score=0.5,  # Start neutral
            created_at=now,
            updated_at=now,
            user_id=user_id,
            agent_id=agent_id,
            tags=tags or []
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO memories 
            (id, tier, memory_type, content, score, created_at, updated_at, 
             access_count, user_id, agent_id, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory.id,
            memory.tier.value,
            memory.memory_type.value,
            json.dumps(memory.content),
            memory.score,
            memory.created_at.isoformat(),
            memory.updated_at.isoformat(),
            memory.access_count,
            memory.user_id,
            memory.agent_id,
            json.dumps(memory.tags)
        ))
        
        conn.commit()
        conn.close()
        
        logger.debug(f"Stored memory: {memory_id} ({memory_type.value})")
        return memory
    
    async def recall(
        self,
        query: str = None,
        memory_type: MemoryType = None,
        user_id: str = "default",
        limit: int = 10,
        min_score: float = 0.3
    ) -> List[Memory]:
        """
        Recall memories matching the query.
        
        Args:
            query: Search query (matches content)
            memory_type: Filter by type
            user_id: Filter by user
            limit: Max memories to return
            min_score: Minimum score threshold
            
        Returns:
            List of matching memories, sorted by relevance
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = """
            SELECT id, tier, memory_type, content, score, created_at, 
                   updated_at, access_count, user_id, agent_id, tags
            FROM memories
            WHERE score >= ? AND user_id = ?
        """
        params = [min_score, user_id]
        
        if memory_type:
            sql += " AND memory_type = ?"
            params.append(memory_type.value)
        
        if query:
            sql += " AND content LIKE ?"
            params.append(f"%{query}%")
        
        sql += " ORDER BY score DESC, updated_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        memories = []
        for row in rows:
            memory = Memory(
                id=row[0],
                tier=MemoryTier(row[1]),
                memory_type=MemoryType(row[2]),
                content=json.loads(row[3]),
                score=row[4],
                created_at=datetime.fromisoformat(row[5]),
                updated_at=datetime.fromisoformat(row[6]),
                access_count=row[7],
                user_id=row[8],
                agent_id=row[9],
                tags=json.loads(row[10])
            )
            memories.append(memory)
            
            # Update access count
            await self._update_access(memory.id)
        
        return memories
    
    # ==========================================
    # OUTCOME TRACKING - THE KEY INNOVATION
    # ==========================================
    
    async def record_outcome(
        self,
        memory_id: str,
        success: bool,
        details: Dict[str, Any] = None
    ) -> float:
        """
        Record the outcome of using a memory (the key to learning!).
        
        Args:
            memory_id: ID of the memory that was used
            success: Whether the advice/memory was helpful
            details: Additional outcome details
            
        Returns:
            New score after adjustment
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current memory
        cursor.execute("SELECT score, tier FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return 0.0
        
        current_score = row[0]
        current_tier = row[1]
        
        # Apply outcome adjustment
        if success:
            new_score = min(1.0, current_score + self.SUCCESS_BOOST)
            logger.info(f"✅ Memory {memory_id[:8]}... SUCCESS: {current_score:.2f} → {new_score:.2f}")
        else:
            new_score = max(0.0, current_score + self.FAILURE_PENALTY)
            logger.info(f"❌ Memory {memory_id[:8]}... FAILED: {current_score:.2f} → {new_score:.2f}")
        
        # Update score
        cursor.execute("""
            UPDATE memories 
            SET score = ?, updated_at = ?
            WHERE id = ?
        """, (new_score, datetime.now().isoformat(), memory_id))
        
        conn.commit()
        conn.close()
        
        # Check for promotion or deletion
        await self._check_promotion(memory_id, new_score, current_tier)
        
        return new_score
    
    async def _check_promotion(self, memory_id: str, score: float, current_tier: str):
        """Check if memory should be promoted to permanent or forgotten"""
        
        if score >= self.PROMOTE_THRESHOLD and current_tier in ["working", "history"]:
            # Promote to pattern (permanent)
            await self._promote_memory(memory_id, MemoryTier.PATTERN)
            logger.info(f"🌟 Memory {memory_id[:8]}... promoted to PATTERN tier!")
            
        elif score <= self.FORGET_THRESHOLD:
            # Memory is unreliable - archive or delete
            await self._archive_memory(memory_id)
            logger.info(f"🗑️ Memory {memory_id[:8]}... archived (low score)")
    
    async def _promote_memory(self, memory_id: str, new_tier: MemoryTier):
        """Promote memory to a higher tier"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE memories SET tier = ?, updated_at = ? WHERE id = ?
        """, (new_tier.value, datetime.now().isoformat(), memory_id))
        conn.commit()
        conn.close()
    
    async def _archive_memory(self, memory_id: str):
        """Archive low-scoring memory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        conn.commit()
        conn.close()
    
    async def _update_access(self, memory_id: str):
        """Update access count and timestamp"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE memories 
            SET access_count = access_count + 1, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), memory_id))
        conn.commit()
        conn.close()
    
    # ==========================================
    # SPECIALIZED MEMORY OPERATIONS
    # ==========================================
    
    async def store_pool_outcome(
        self,
        pool_id: str,
        project: str,
        chain: str,
        predicted_apy: float,
        actual_apy: float,
        profit_loss: float,
        user_id: str = "default"
    ) -> Memory:
        """Store the outcome of a pool investment"""
        content = {
            "pool_id": pool_id,
            "project": project,
            "chain": chain,
            "predicted_apy": predicted_apy,
            "actual_apy": actual_apy,
            "apy_accuracy": 1 - abs(predicted_apy - actual_apy) / max(predicted_apy, 1),
            "profit_loss": profit_loss,
            "profitable": profit_loss > 0
        }
        
        memory = await self.store(
            memory_type=MemoryType.POOL_OUTCOME,
            content=content,
            tier=MemoryTier.HISTORY,
            user_id=user_id,
            agent_id="scout",
            tags=[project, chain, "pool"]
        )
        
        # Automatically record outcome based on profit
        await self.record_outcome(memory.id, success=profit_loss > 0)
        
        return memory
    
    async def store_strategy_result(
        self,
        strategy_name: str,
        strategy_params: Dict[str, Any],
        result: Dict[str, Any],
        user_id: str = "default"
    ) -> Memory:
        """Store the result of a trading strategy"""
        success = result.get("profit", 0) > 0
        
        content = {
            "strategy_name": strategy_name,
            "params": strategy_params,
            "result": result,
            "success": success
        }
        
        memory = await self.store(
            memory_type=MemoryType.STRATEGY_RESULT,
            content=content,
            tier=MemoryTier.HISTORY,
            user_id=user_id,
            agent_id="engineer",
            tags=[strategy_name, "strategy"]
        )
        
        await self.record_outcome(memory.id, success=success)
        return memory
    
    async def store_user_preference(
        self,
        preference_key: str,
        preference_value: Any,
        user_id: str = "default"
    ) -> Memory:
        """Store a user preference (permanent)"""
        content = {
            "key": preference_key,
            "value": preference_value
        }
        
        return await self.store(
            memory_type=MemoryType.USER_PREFERENCE,
            content=content,
            tier=MemoryTier.PREFERENCE,
            user_id=user_id,
            agent_id="system",
            tags=[preference_key, "preference"]
        )
    
    async def get_user_preferences(self, user_id: str = "default") -> Dict[str, Any]:
        """Get all preferences for a user"""
        memories = await self.recall(
            memory_type=MemoryType.USER_PREFERENCE,
            user_id=user_id,
            limit=100,
            min_score=0.0
        )
        
        return {m.content["key"]: m.content["value"] for m in memories}
    
    async def get_best_protocols(
        self,
        user_id: str = "default",
        chain: str = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get highest-scoring protocols from memory"""
        memories = await self.recall(
            memory_type=MemoryType.POOL_OUTCOME,
            user_id=user_id,
            limit=50,
            min_score=0.5
        )
        
        # Aggregate by protocol
        protocol_scores = {}
        for m in memories:
            project = m.content.get("project")
            if chain and m.content.get("chain") != chain:
                continue
            
            if project not in protocol_scores:
                protocol_scores[project] = {"total_score": 0, "count": 0}
            
            protocol_scores[project]["total_score"] += m.score
            protocol_scores[project]["count"] += 1
        
        # Calculate average and sort
        results = []
        for protocol, data in protocol_scores.items():
            avg_score = data["total_score"] / data["count"]
            results.append({
                "protocol": protocol,
                "average_score": round(avg_score, 2),
                "experience_count": data["count"]
            })
        
        results.sort(key=lambda x: x["average_score"], reverse=True)
        return results[:limit]
    
    async def learn_risk_tolerance(
        self,
        user_id: str,
        action: str,
        pool_risk_level: str,
        apy: float
    ):
        """Learn user's risk tolerance from their actions"""
        content = {
            "action": action,
            "risk_level": pool_risk_level,
            "apy": apy,
            "risk_score": {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}.get(pool_risk_level, 2)
        }
        
        await self.store(
            memory_type=MemoryType.RISK_TOLERANCE,
            content=content,
            tier=MemoryTier.PATTERN,
            user_id=user_id,
            agent_id="guardian",
            tags=["risk", "behavior"]
        )
    
    async def get_learned_risk_profile(self, user_id: str = "default") -> Dict[str, Any]:
        """Get learned risk profile for a user"""
        memories = await self.recall(
            memory_type=MemoryType.RISK_TOLERANCE,
            user_id=user_id,
            limit=100,
            min_score=0.0
        )
        
        if not memories:
            return {"profile": "unknown", "avg_risk": 2, "data_points": 0}
        
        risk_scores = [m.content.get("risk_score", 2) for m in memories]
        avg_risk = sum(risk_scores) / len(risk_scores)
        
        if avg_risk < 1.5:
            profile = "conservative"
        elif avg_risk < 2.5:
            profile = "moderate"
        elif avg_risk < 3.5:
            profile = "aggressive"
        else:
            profile = "degen"
        
        return {
            "profile": profile,
            "avg_risk": round(avg_risk, 2),
            "data_points": len(memories)
        }
    
    # ==========================================
    # MAINTENANCE
    # ==========================================
    
    async def cleanup_expired(self):
        """Remove expired memories based on retention policies"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        working_cutoff = (now - self.WORKING_RETENTION).isoformat()
        history_cutoff = (now - self.HISTORY_RETENTION).isoformat()
        
        # Delete expired working memories
        cursor.execute("""
            DELETE FROM memories 
            WHERE tier = 'working' AND created_at < ?
        """, (working_cutoff,))
        
        # Delete expired history memories (unless promoted)
        cursor.execute("""
            DELETE FROM memories 
            WHERE tier = 'history' AND created_at < ? AND score < ?
        """, (history_cutoff, self.PROMOTE_THRESHOLD))
        
        conn.commit()
        deleted = cursor.rowcount
        conn.close()
        
        if deleted > 0:
            logger.info(f"🧹 Cleaned up {deleted} expired memories")
        
        return deleted
    
    async def get_stats(self, user_id: str = "default") -> Dict[str, Any]:
        """Get memory statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT tier, COUNT(*), AVG(score) 
            FROM memories 
            WHERE user_id = ?
            GROUP BY tier
        """, (user_id,))
        
        stats = {"tiers": {}, "total": 0}
        for row in cursor.fetchall():
            stats["tiers"][row[0]] = {
                "count": row[1],
                "avg_score": round(row[2], 2) if row[2] else 0
            }
            stats["total"] += row[1]
        
        conn.close()
        return stats
    
    def _generate_id(self, content: Dict) -> str:
        """Generate unique ID for memory"""
        content_str = json.dumps(content, sort_keys=True)
        timestamp = datetime.now().isoformat()
        return hashlib.sha256(f"{content_str}{timestamp}".encode()).hexdigest()[:16]


# ==========================================
# SINGLETON & CONVENIENCE FUNCTIONS
# ==========================================

# Singleton instance
memory_engine = OutcomeBasedMemory()


async def store_memory(
    memory_type: MemoryType,
    content: Dict[str, Any],
    user_id: str = "default"
) -> Memory:
    """Quick store function"""
    return await memory_engine.store(memory_type, content, user_id=user_id)


async def recall_memories(
    query: str = None,
    memory_type: MemoryType = None,
    user_id: str = "default"
) -> List[Memory]:
    """Quick recall function"""
    return await memory_engine.recall(query, memory_type, user_id)


async def record_success(memory_id: str) -> float:
    """Record successful outcome"""
    return await memory_engine.record_outcome(memory_id, success=True)


async def record_failure(memory_id: str) -> float:
    """Record failed outcome"""
    return await memory_engine.record_outcome(memory_id, success=False)
