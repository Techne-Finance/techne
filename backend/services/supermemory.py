"""
Artisan Bot - Supermemory System
Persistent memory across sessions using Supabase

Features:
- Conversation history persistence
- User preferences storage
- Project context (trading style, risk tolerance)
- Long-term facts extraction
"""

import os
import json
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("Supermemory")

# Supabase config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


class Supermemory:
    """
    Persistent memory for Artisan Bot.
    
    Stores:
    - Recent conversation history (last 50 messages)
    - User preferences (trading style, risk, chains)
    - Long-term facts extracted from conversations
    - Important decisions and their outcomes
    """
    
    def __init__(self, user_address: str):
        self.user_address = user_address.lower()
        self.client = httpx.AsyncClient(
            base_url=SUPABASE_URL,
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            },
            timeout=30.0
        ) if SUPABASE_URL and SUPABASE_KEY else None
        
        # Local cache
        self._preferences: Dict = {}
        self._facts: List[str] = []
        self._history: List[Dict] = []
    
    async def load(self) -> None:
        """Load memory from Supabase"""
        if not self.client:
            logger.warning("Supabase not configured - using in-memory only")
            return
        
        try:
            # Load preferences
            resp = await self.client.get(
                f"/rest/v1/artisan_memory",
                params={
                    "user_address": f"eq.{self.user_address}",
                    "select": "*"
                }
            )
            
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    memory = data[0]
                    self._preferences = memory.get("preferences", {})
                    self._facts = memory.get("facts", [])
                    self._history = memory.get("conversation_history", [])[-50:]
                    logger.info(f"Loaded memory for {self.user_address}: {len(self._history)} messages, {len(self._facts)} facts")
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")
    
    async def save(self) -> None:
        """Save memory to Supabase"""
        if not self.client:
            return
        
        try:
            data = {
                "user_address": self.user_address,
                "preferences": self._preferences,
                "facts": self._facts[-100],  # Keep last 100 facts
                "conversation_history": self._history[-50],  # Keep last 50 messages
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Upsert
            await self.client.post(
                "/rest/v1/artisan_memory",
                json=data,
                params={"on_conflict": "user_address"}
            )
            logger.debug(f"Saved memory for {self.user_address}")
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    def add_message(self, role: str, content: str) -> None:
        """Add message to conversation history"""
        self._history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        # Trim to last 50
        if len(self._history) > 50:
            self._history = self._history[-50:]
    
    def add_fact(self, fact: str) -> None:
        """Add long-term fact about the user"""
        # Avoid duplicates
        if fact not in self._facts:
            self._facts.append(fact)
            logger.info(f"New fact for {self.user_address}: {fact}")
    
    def set_preference(self, key: str, value: Any) -> None:
        """Set user preference"""
        self._preferences[key] = value
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get user preference"""
        return self._preferences.get(key, default)
    
    def get_context_prompt(self) -> str:
        """Generate context prompt for LLM with user's memory"""
        parts = []
        
        if self._preferences:
            pref_str = ", ".join(f"{k}={v}" for k, v in self._preferences.items())
            parts.append(f"User preferences: {pref_str}")
        
        if self._facts:
            facts_str = "; ".join(self._facts[-10])  # Last 10 facts
            parts.append(f"Known facts about user: {facts_str}")
        
        return "\n".join(parts) if parts else ""
    
    def get_history(self, last_n: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        return self._history[-last_n:]
    
    async def close(self) -> None:
        """Close client and save"""
        await self.save()
        if self.client:
            await self.client.aclose()


# Memory cache per user
_memory_cache: Dict[str, Supermemory] = {}


async def get_memory(user_address: str) -> Supermemory:
    """Get or create memory for user"""
    addr = user_address.lower()
    
    if addr not in _memory_cache:
        memory = Supermemory(addr)
        await memory.load()
        _memory_cache[addr] = memory
    
    return _memory_cache[addr]


async def extract_facts_from_response(user_message: str, assistant_response: str) -> List[str]:
    """
    Extract long-term facts from conversation.
    Uses simple pattern matching - could be enhanced with LLM.
    """
    facts = []
    
    user_lower = user_message.lower()
    
    # Preference patterns
    if "prefer" in user_lower or "like" in user_lower or "want" in user_lower:
        if "stablecoin" in user_lower:
            facts.append("User prefers stablecoin pools")
        if "low risk" in user_lower:
            facts.append("User has low risk tolerance")
        if "high apy" in user_lower:
            facts.append("User prioritizes high APY")
        if "base" in user_lower and "chain" in user_lower:
            facts.append("User prefers Base chain")
    
    # Trading style patterns
    if "conservative" in user_lower:
        facts.append("User has conservative trading style")
    elif "aggressive" in user_lower:
        facts.append("User has aggressive trading style")
    
    # Amount patterns
    if "budget" in user_lower or "invest" in user_lower:
        import re
        amounts = re.findall(r'\$(\d+[,\d]*)', user_message)
        if amounts:
            facts.append(f"User mentioned budget/investment of ${amounts[0]}")
    
    return facts
