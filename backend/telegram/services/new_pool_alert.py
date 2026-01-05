"""
Techne Telegram Bot - New Pool Alert Service
Detects new pools matching user filters and sends notifications
"""

import asyncio
from typing import Dict, List, Set, Optional
from datetime import datetime
import logging

from ..models.user_config import UserConfig, user_store
from .pools import fetch_pools

logger = logging.getLogger(__name__)


class NewPoolDetector:
    """
    Detects new pools and notifies users when they match their filters
    """
    
    def __init__(self):
        # Cache of seen pool IDs per user
        # Format: {telegram_id: {pool_id1, pool_id2, ...}}
        self._seen_pools: Dict[int, Set[str]] = {}
        
        # Global seen pools (for first-time detection)
        self._global_seen: Set[str] = set()
        
        # Last update time
        self._last_check: Optional[datetime] = None
    
    def _get_pool_id(self, pool: Dict) -> str:
        """Generate unique pool identifier"""
        return pool.get("pool", f"{pool.get('chain', '')}_{pool.get('project', '')}_{pool.get('symbol', '')}")
    
    def _pool_matches_filters(self, pool: Dict, config: UserConfig) -> bool:
        """Check if pool matches user's filter configuration"""
        # Chain filter
        if config.chain != "all":
            pool_chain = pool.get("chain", "").lower()
            if pool_chain != config.chain.lower():
                return False
        
        # TVL filter
        tvl = pool.get("tvl", 0)
        if tvl < config.min_tvl:
            return False
        if config.max_tvl and tvl > config.max_tvl:
            return False
        
        # APY filter
        apy = pool.get("apy", 0)
        if apy < config.min_apy:
            return False
        if apy > config.max_apy:
            return False
        
        # Protocol filter
        if config.protocols:
            pool_protocol = pool.get("project", "").lower()
            if not any(p.lower() in pool_protocol for p in config.protocols):
                return False
        
        # Pool type filter (single/dual)
        if config.pool_type != "all":
            symbol = pool.get("symbol", "")
            is_dual = "/" in symbol or "-" in symbol
            if config.pool_type == "dual" and not is_dual:
                return False
            if config.pool_type == "single" and is_dual:
                return False
        
        # Stablecoin filter
        if config.stablecoin_only:
            symbol = pool.get("symbol", "").upper()
            stables = ["USDC", "USDT", "DAI", "FRAX", "LUSD", "TUSD", "BUSD"]
            if not any(s in symbol for s in stables):
                return False
        
        # Risk filter
        if config.risk_level != "all":
            pool_risk = pool.get("risk_level", "Medium").lower()
            allowed_risks = {
                "low": ["low"],
                "medium": ["low", "medium"],
                "high": ["low", "medium", "high"]
            }
            if pool_risk not in allowed_risks.get(config.risk_level.lower(), ["low", "medium", "high"]):
                return False
        
        return True
    
    async def detect_new_pools_for_user(self, config: UserConfig, all_pools: List[Dict]) -> List[Dict]:
        """
        Detect new pools that match user's filters
        Returns list of newly discovered pools
        """
        telegram_id = config.telegram_id
        
        # Initialize seen set for user if needed
        if telegram_id not in self._seen_pools:
            self._seen_pools[telegram_id] = set()
        
        seen = self._seen_pools[telegram_id]
        new_pools = []
        
        for pool in all_pools:
            pool_id = self._get_pool_id(pool)
            
            # Skip if already seen by this user
            if pool_id in seen:
                continue
            
            # Check if matches user's filters
            if self._pool_matches_filters(pool, config):
                # Only notify if we've done at least one check before
                # (prevents spam on first run)
                if self._last_check is not None:
                    new_pools.append(pool)
                
                # Mark as seen
                seen.add(pool_id)
        
        return new_pools
    
    def format_new_pool_alert(self, pool: Dict) -> str:
        """Format a new pool alert message"""
        symbol = pool.get("symbol", "?")
        project = pool.get("project", "?")
        chain = pool.get("chain", "?")
        apy = pool.get("apy", 0)
        tvl = pool.get("tvl", 0)
        risk = pool.get("risk_level", "?")
        
        tvl_str = f"${tvl/1_000_000:.1f}M" if tvl >= 1_000_000 else f"${tvl/1_000:.0f}K"
        risk_emoji = {"Low": "🟢", "Medium": "🟡", "High": "🟠"}.get(risk, "⚪")
        
        # Determine pool type
        is_dual = "/" in symbol or "-" in symbol
        pool_type = "LP Pool" if is_dual else "Single Asset"
        
        return f"""
🆕 *New Pool Detected!*

*{symbol}*
{project} • {chain}

━━━━━━━━━━━━━━━━━━━━

📈 *APY:* {apy:.1f}%
💰 *TVL:* {tvl_str}
🏷️ *Type:* {pool_type}
{risk_emoji} *Risk:* {risk}

━━━━━━━━━━━━━━━━━━━━

_This pool matches your alert filters!_
Use /pool to see more details
"""
    
    def format_new_pools_summary(self, pools: List[Dict]) -> str:
        """Format summary of multiple new pools"""
        if len(pools) == 1:
            return self.format_new_pool_alert(pools[0])
        
        lines = [f"🆕 *{len(pools)} New Pools Detected!*\n"]
        lines.append("_Matching your alert filters_\n")
        
        for i, pool in enumerate(pools[:5], 1):
            symbol = pool.get("symbol", "?")
            project = pool.get("project", "?")
            apy = pool.get("apy", 0)
            tvl = pool.get("tvl", 0)
            
            tvl_str = f"${tvl/1_000_000:.1f}M" if tvl >= 1_000_000 else f"${tvl/1_000:.0f}K"
            
            lines.append(
                f"*{i}. {symbol}*\n"
                f"   {apy:.1f}% APY • {tvl_str} • {project}\n"
            )
        
        if len(pools) > 5:
            lines.append(f"\n_+{len(pools) - 5} more pools_")
        
        lines.append("\nUse /pools to see all matching pools")
        
        return "\n".join(lines)
    
    async def check_all_users(self, bot) -> int:
        """
        Check for new pools for all premium users with alerts enabled
        Returns number of alerts sent
        """
        try:
            # Get all premium users with alerts
            users = await user_store.get_premium_users()
            users = [u for u in users if u.alerts_enabled]
            
            if not users:
                return 0
            
            alerts_sent = 0
            
            # Fetch pools once (all chains, broad filters)
            from .pools import API_BASE
            import httpx
            
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(
                        f"{API_BASE}/api/pools",
                        params={"min_tvl": 100000, "min_apy": 1, "limit": 200},
                        timeout=30.0
                    )
                    if response.status_code == 200:
                        all_pools = response.json().get("pools", [])
                    else:
                        all_pools = []
                except Exception as e:
                    logger.error(f"Failed to fetch pools: {e}")
                    all_pools = []
            
            if not all_pools:
                return 0
            
            # Check each user
            for user in users:
                try:
                    new_pools = await self.detect_new_pools_for_user(user, all_pools)
                    
                    if new_pools:
                        message = self.format_new_pools_summary(new_pools)
                        await bot.send_message(user.telegram_id, message, parse_mode="Markdown")
                        
                        # Log alert
                        pool_ids = ",".join(self._get_pool_id(p) for p in new_pools[:3])
                        await user_store.log_alert(
                            user.telegram_id,
                            "new_pool",
                            pool_ids,
                            f"Found {len(new_pools)} new pools"
                        )
                        
                        alerts_sent += 1
                        
                except Exception as e:
                    logger.error(f"Error checking user {user.telegram_id}: {e}")
            
            # Update last check time
            self._last_check = datetime.utcnow()
            
            return alerts_sent
            
        except Exception as e:
            logger.error(f"Error in check_all_users: {e}")
            return 0
    
    def get_user_filter_summary(self, config: UserConfig) -> str:
        """Get summary of user's current filters for alerts"""
        filters = []
        
        if config.chain != "all":
            filters.append(f"Chain: {config.chain.capitalize()}")
        
        if config.protocols:
            filters.append(f"Protocols: {', '.join(config.protocols[:3])}")
        
        if config.pool_type != "all":
            filters.append(f"Type: {config.pool_type.capitalize()}")
        
        filters.append(f"APY ≥ {config.min_apy}%")
        
        tvl_str = f"${config.min_tvl/1_000_000:.1f}M" if config.min_tvl >= 1_000_000 else f"${config.min_tvl/1_000:.0f}K"
        filters.append(f"TVL ≥ {tvl_str}")
        
        if config.stablecoin_only:
            filters.append("Stablecoins only")
        
        if config.risk_level != "all":
            filters.append(f"Risk ≤ {config.risk_level.capitalize()}")
        
        return "\n".join(f"• {f}" for f in filters)


# Global instance
new_pool_detector = NewPoolDetector()
