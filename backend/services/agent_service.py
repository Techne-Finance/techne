"""
Agent Service - Supabase-backed Agent Management
Scalable architecture for thousands of users with multiple agents
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger("AgentService")

# Supabase REST client (no SDK dependency — avoids httpcore version conflict)
from infrastructure.supabase_rest import get_supabase_rest

supabase = get_supabase_rest()
SUPABASE_AVAILABLE = supabase.is_available


@dataclass
class AgentConfig:
    """Agent configuration"""
    chain: str = "base"
    preset: str = "balanced"
    pool_type: str = "single"
    risk_level: str = "moderate"
    min_apy: float = 5.0
    max_apy: float = 1000.0
    max_drawdown: float = 20.0
    protocols: List[str] = None
    preferred_assets: List[str] = None
    is_pro_mode: bool = False
    
    def __post_init__(self):
        if self.protocols is None:
            self.protocols = ["aerodrome", "aave", "morpho"]
        if self.preferred_assets is None:
            self.preferred_assets = ["USDC", "WETH"]


class AgentService:
    """
    Supabase-backed agent management service.
    Handles CRUD operations for agents, transactions, balances.
    """
    
    def __init__(self):
        self.supabase = supabase
        if not SUPABASE_AVAILABLE:
            logger.warning("Supabase not available - using fallback mode")
    
    # ==========================================
    # AGENT CRUD
    # ==========================================
    
    async def create_agent(
        self,
        user_address: str,
        agent_address: str,
        encrypted_private_key: str,
        config: AgentConfig = None,
        agent_name: str = None
    ) -> Dict:
        """
        Create new agent in Supabase
        
        Args:
            user_address: Owner's wallet address
            agent_address: Agent's wallet address  
            encrypted_private_key: Encrypted private key
            config: Agent configuration
            agent_name: Display name for agent
        """
        if not self.supabase:
            return {"success": False, "error": "Supabase not available"}
        
        config = config or AgentConfig()
        
        data = {
            "user_address": user_address.lower(),
            "agent_address": agent_address,
            "agent_name": agent_name or f"Agent #{self._count_user_agents(user_address) + 1}",
            "encrypted_private_key": encrypted_private_key,
            "chain": config.chain,
            "preset": config.preset,
            "pool_type": config.pool_type,
            "risk_level": config.risk_level,
            "min_apy": config.min_apy,
            "max_apy": config.max_apy,
            "max_drawdown": config.max_drawdown,
            "protocols": config.protocols,
            "preferred_assets": config.preferred_assets,
            "is_pro_mode": config.is_pro_mode,
            "is_active": True,
            "status": "active"
        }
        
        try:
            result = self.supabase.table("user_agents").insert(data).execute()
            
            if result.data:
                logger.info(f"✅ Created agent {agent_address[:10]}... for user {user_address[:10]}...")
                
                # Log to audit trail
                await self.log_audit(
                    agent_address=agent_address,
                    user_address=user_address,
                    action="create",
                    message=f"Agent created with {config.preset} preset",
                    severity="success"
                )
                
                return {"success": True, "agent": result.data[0]}
            else:
                return {"success": False, "error": "Insert failed"}
                
        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            return {"success": False, "error": str(e)}
    
    def _count_user_agents(self, user_address: str) -> int:
        """Count existing agents for user"""
        try:
            result = self.supabase.table("user_agents") \
                .select("id", count="exact") \
                .eq("user_address", user_address.lower()) \
                .execute()
            return result.count or 0
        except:
            return 0
    
    async def get_user_agents(self, user_address: str) -> List[Dict]:
        """Get all agents for a user"""
        if not self.supabase:
            return []
        
        try:
            result = self.supabase.table("user_agents") \
                .select("*") \
                .eq("user_address", user_address.lower()) \
                .order("deployed_at", desc=True) \
                .execute()
            
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get user agents: {e}")
            return []
    
    async def get_agent(self, agent_address: str) -> Optional[Dict]:
        """Get single agent by address"""
        if not self.supabase:
            return None
        
        try:
            result = self.supabase.table("user_agents") \
                .select("*") \
                .eq("agent_address", agent_address) \
                .single() \
                .execute()
            
            return result.data
        except Exception as e:
            logger.error(f"Failed to get agent: {e}")
            return None
    
    async def update_agent(self, agent_address: str, updates: Dict) -> bool:
        """Update agent configuration"""
        if not self.supabase:
            return False
        
        # Extract top-level DB columns from nested 'settings' dict
        # DB schema: pool_type is a top-level column, not inside settings JSONB
        if "settings" in updates and isinstance(updates["settings"], dict):
            settings = updates["settings"]
            # Fields that are top-level columns in user_agents table
            TOP_LEVEL_FIELDS = ["pool_type"]
            for field in TOP_LEVEL_FIELDS:
                if field in settings:
                    updates[field] = settings.pop(field)
            # If settings dict is now empty, remove it
            if not settings:
                del updates["settings"]
        
        # Add updated timestamp
        updates["updated_at"] = datetime.now().isoformat()
        
        try:
            result = self.supabase.table("user_agents") \
                .update(updates) \
                .eq("agent_address", agent_address) \
                .execute()
            
            if result.data:
                logger.info(f"Updated agent {agent_address[:10]}...")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update agent: {e}")
            return False
    
    async def set_agent_status(self, agent_address: str, status: str, is_active: bool = None) -> bool:
        """Set agent status (active, paused, draining)"""
        updates = {"status": status, "last_activity": datetime.now().isoformat()}
        if is_active is not None:
            updates["is_active"] = is_active
        return await self.update_agent(agent_address, updates)
    
    async def delete_agent(self, agent_address: str) -> bool:
        """Soft delete - set status to 'deleted'"""
        return await self.update_agent(agent_address, {
            "status": "deleted",
            "is_active": False
        })
    
    # ==========================================
    # TRANSACTIONS
    # ==========================================
    
    async def record_transaction(
        self,
        user_address: str,
        agent_address: str,
        tx_type: str,
        token: str,
        amount: float,
        tx_hash: str = None,
        status: str = "completed",
        destination: str = None,
        pool_id: str = None,
        metadata: Dict = None
    ) -> Dict:
        """Record a transaction"""
        if not self.supabase:
            return {"success": False, "error": "Supabase not available"}
        
        data = {
            "user_address": user_address.lower(),
            "agent_address": agent_address,
            "tx_type": tx_type,
            "token": token,
            "amount": amount,
            "tx_hash": tx_hash,
            "status": status,
            "destination": destination,
            "pool_id": pool_id,
            "metadata": metadata or {}
        }
        
        try:
            result = self.supabase.table("agent_transactions").insert(data).execute()
            
            if result.data:
                logger.info(f"📝 Recorded {tx_type}: {amount} {token}")
                return {"success": True, "transaction": result.data[0]}
            return {"success": False, "error": "Insert failed"}
        except Exception as e:
            logger.error(f"Failed to record transaction: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_agent_transactions(
        self,
        agent_address: str,
        limit: int = 50,
        tx_type: str = None
    ) -> List[Dict]:
        """Get transaction history for agent"""
        if not self.supabase:
            return []
        
        try:
            query = self.supabase.table("agent_transactions") \
                .select("*") \
                .eq("agent_address", agent_address) \
                .order("created_at", desc=True) \
                .limit(limit)
            
            if tx_type:
                query = query.eq("tx_type", tx_type)
            
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get transactions: {e}")
            return []
    
    # ==========================================
    # BALANCES
    # ==========================================
    
    async def update_balance(
        self,
        agent_address: str,
        token: str,
        balance: float,
        balance_usd: float = 0
    ) -> bool:
        """Update or insert balance for agent"""
        if not self.supabase:
            return False
        
        try:
            # Upsert - insert or update
            result = self.supabase.table("agent_balances").upsert({
                "agent_address": agent_address,
                "token": token,
                "balance": balance,
                "balance_usd": balance_usd,
                "last_verified": datetime.now().isoformat()
            }, on_conflict="agent_address,token").execute()
            
            return bool(result.data)
        except Exception as e:
            logger.error(f"Failed to update balance: {e}")
            return False
    
    async def get_agent_balances(self, agent_address: str) -> Dict[str, float]:
        """Get all balances for agent"""
        if not self.supabase:
            return {}
        
        try:
            result = self.supabase.table("agent_balances") \
                .select("token, balance, balance_usd") \
                .eq("agent_address", agent_address) \
                .execute()
            
            return {
                row["token"]: {
                    "balance": row["balance"],
                    "balance_usd": row["balance_usd"]
                }
                for row in (result.data or [])
            }
        except Exception as e:
            logger.error(f"Failed to get balances: {e}")
            return {}
    
    # ==========================================
    # POSITIONS
    # ==========================================
    
    async def create_position(
        self,
        agent_address: str,
        user_address: str,
        protocol: str,
        pool_address: str,
        pool_name: str,
        entry_value_usd: float,
        token0: str = None,
        token1: str = None,
        amount0: float = 0,
        amount1: float = 0,
        lp_tokens: float = 0,
        apy: float = 0,
        metadata: Dict = None
    ) -> Dict:
        """Create new position"""
        if not self.supabase:
            return {"success": False, "error": "Supabase not available"}
        
        data = {
            "agent_address": agent_address,
            "user_address": user_address.lower(),
            "protocol": protocol,
            "pool_address": pool_address,
            "pool_name": pool_name,
            "token0": token0,
            "token1": token1,
            "amount0": amount0,
            "amount1": amount1,
            "lp_tokens": lp_tokens,
            "entry_value_usd": entry_value_usd,
            "current_value_usd": entry_value_usd,
            "apy": apy,
            "status": "active",
            "metadata": metadata or {}
        }
        
        try:
            result = self.supabase.table("agent_positions").insert(data).execute()
            
            if result.data:
                logger.info(f"📊 Created position in {protocol}: {pool_name}")
                return {"success": True, "position": result.data[0]}
            return {"success": False, "error": "Insert failed"}
        except Exception as e:
            logger.error(f"Failed to create position: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_agent_positions(self, agent_address: str, status: str = "active") -> List[Dict]:
        """Get positions for agent"""
        if not self.supabase:
            return []
        
        try:
            query = self.supabase.table("agent_positions") \
                .select("*") \
                .eq("agent_address", agent_address) \
                .order("entry_time", desc=True)
            
            if status:
                query = query.eq("status", status)
            
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    async def close_position(self, position_id: int, exit_value_usd: float = None) -> bool:
        """Close a position"""
        if not self.supabase:
            return False
        
        updates = {
            "status": "closed",
            "exit_time": datetime.now().isoformat()
        }
        if exit_value_usd is not None:
            updates["current_value_usd"] = exit_value_usd
        
        try:
            result = self.supabase.table("agent_positions") \
                .update(updates) \
                .eq("id", position_id) \
                .execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            return False
    
    # ==========================================
    # AUDIT TRAIL
    # ==========================================
    
    async def log_audit(
        self,
        agent_address: str,
        user_address: str,
        action: str,
        message: str,
        severity: str = "info",
        metadata: Dict = None
    ) -> bool:
        """Log to audit trail"""
        if not self.supabase:
            return False
        
        try:
            self.supabase.table("audit_trail").insert({
                "agent_address": agent_address,
                "user_address": user_address.lower(),
                "action": action,
                "message": message,
                "severity": severity,
                "metadata": metadata or {}
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")
            return False
    
    async def get_audit_trail(
        self,
        agent_address: str = None,
        user_address: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get audit trail entries"""
        if not self.supabase:
            return []
        
        try:
            query = self.supabase.table("audit_trail") \
                .select("*") \
                .order("created_at", desc=True) \
                .limit(limit)
            
            if agent_address:
                query = query.eq("agent_address", agent_address)
            if user_address:
                query = query.eq("user_address", user_address.lower())
            
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get audit trail: {e}")
            return []
    
    # ==========================================
    # AGGREGATES
    # ==========================================
    
    async def get_user_portfolio_summary(self, user_address: str) -> Dict:
        """Get portfolio summary across all user's agents"""
        agents = await self.get_user_agents(user_address)
        
        total_value = 0
        total_deposited = 0
        active_positions = 0
        
        for agent in agents:
            total_value += agent.get("total_value", 0) or 0
            total_deposited += agent.get("total_deposited", 0) or 0
            
            positions = await self.get_agent_positions(agent["agent_address"])
            active_positions += len(positions)
        
        pnl = total_value - total_deposited
        pnl_percent = (pnl / total_deposited * 100) if total_deposited > 0 else 0
        
        return {
            "user_address": user_address,
            "agents_count": len(agents),
            "active_agents": len([a for a in agents if a.get("is_active")]),
            "total_deposited": total_deposited,
            "total_value": total_value,
            "pnl": pnl,
            "pnl_percent": round(pnl_percent, 2),
            "active_positions": active_positions
        }


# Singleton instance
agent_service = AgentService()
