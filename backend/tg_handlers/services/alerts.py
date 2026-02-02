"""
Techne Telegram Bot - Alert Service
Generates real-time alerts for APY spikes, TVL changes, risk warnings
"""

import httpx
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from ..models.user_config import UserConfig, user_store


# Cache for previous pool states (for comparison)
_pool_cache: Dict[str, Dict[str, Any]] = {}
_cache_timestamp: Optional[datetime] = None
CACHE_TTL_SECONDS = 300  # 5 minutes


async def fetch_all_pools_for_alerts() -> List[Dict[str, Any]]:
    """
    Fetch a broad set of pools for alert checking
    """
    global _pool_cache, _cache_timestamp
    
    # Use cache if fresh
    if _cache_timestamp and (datetime.utcnow() - _cache_timestamp).seconds < CACHE_TTL_SECONDS:
        return list(_pool_cache.values())
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Fetch from multiple chains
            all_pools = []
            for chain in ["Base", "Ethereum", "Arbitrum"]:
                response = await client.get(
                    "http://localhost:8000/api/pools",
                    params={"chain": chain, "min_tvl": 50000, "limit": 100}
                )
                if response.status_code == 200:
                    data = response.json()
                    all_pools.extend(data.get("combined", []))
            
            # Update cache
            _pool_cache = {p.get("pool", p.get("id", "")): p for p in all_pools if p.get("pool") or p.get("id")}
            _cache_timestamp = datetime.utcnow()
            
            return all_pools
    except Exception as e:
        print(f"[AlertService] Error fetching pools: {e}")
        return list(_pool_cache.values())


def check_apy_spike(pool: Dict, previous_pool: Optional[Dict], threshold_percent: float) -> Optional[Tuple[str, float, float]]:
    """
    Check if pool APY spiked above threshold
    Returns: (pool_id, old_apy, new_apy) or None
    """
    if not previous_pool:
        return None
    
    old_apy = previous_pool.get("apy", 0)
    new_apy = pool.get("apy", 0)
    
    if old_apy <= 0:
        return None
    
    change_percent = ((new_apy - old_apy) / old_apy) * 100
    
    if change_percent >= threshold_percent:
        pool_id = pool.get("pool", pool.get("id", "unknown"))
        return (pool_id, old_apy, new_apy)
    
    return None


def check_tvl_change(pool: Dict, previous_pool: Optional[Dict], threshold_percent: float) -> Optional[Tuple[str, float, float, str]]:
    """
    Check if pool TVL changed significantly
    Returns: (pool_id, old_tvl, new_tvl, direction) or None
    """
    if not previous_pool:
        return None
    
    old_tvl = previous_pool.get("tvl", 0)
    new_tvl = pool.get("tvl", 0)
    
    if old_tvl <= 0:
        return None
    
    change_percent = ((new_tvl - old_tvl) / old_tvl) * 100
    
    if abs(change_percent) >= threshold_percent:
        pool_id = pool.get("pool", pool.get("id", "unknown"))
        direction = "increase" if change_percent > 0 else "decrease"
        return (pool_id, old_tvl, new_tvl, direction)
    
    return None


def check_risk_change(pool: Dict, previous_pool: Optional[Dict]) -> Optional[Tuple[str, str, str]]:
    """
    Check if pool risk level changed
    Returns: (pool_id, old_risk, new_risk) or None
    """
    if not previous_pool:
        return None
    
    old_risk = previous_pool.get("risk_level", "Unknown")
    new_risk = pool.get("risk_level", "Unknown")
    
    risk_order = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
    
    # Only alert if risk increased
    if risk_order.get(new_risk, 0) > risk_order.get(old_risk, 0):
        pool_id = pool.get("pool", pool.get("id", "unknown"))
        return (pool_id, old_risk, new_risk)
    
    return None


async def generate_alerts_for_user(config: UserConfig, previous_pools: Dict[str, Dict]) -> List[Dict[str, Any]]:
    """
    Generate alerts for a specific user based on their config
    """
    if not config.alerts_enabled:
        return []
    
    # Get fresh pools
    current_pools = await fetch_all_pools_for_alerts()
    
    alerts = []
    
    for pool in current_pools:
        pool_id = pool.get("pool", pool.get("id"))
        if not pool_id:
            continue
        
        # Filter by user preferences
        chain = pool.get("chain", "").lower()
        project = pool.get("project", "").lower()
        
        # Chain filter
        if config.chain != "all" and chain != config.chain.lower():
            continue
        
        # Protocol filter
        if config.protocols and not any(p.lower() in project for p in config.protocols):
            continue
        
        previous = previous_pools.get(pool_id)
        
        # Check APY spike
        apy_result = check_apy_spike(pool, previous, config.apy_spike_threshold)
        if apy_result:
            alerts.append({
                "type": "apy_spike",
                "pool_id": apy_result[0],
                "pool": pool,
                "old_value": apy_result[1],
                "new_value": apy_result[2],
                "message": format_apy_alert(pool, apy_result[1], apy_result[2])
            })
        
        # Check TVL change
        tvl_result = check_tvl_change(pool, previous, config.tvl_change_threshold)
        if tvl_result:
            alerts.append({
                "type": "tvl_change",
                "pool_id": tvl_result[0],
                "pool": pool,
                "old_value": tvl_result[1],
                "new_value": tvl_result[2],
                "direction": tvl_result[3],
                "message": format_tvl_alert(pool, tvl_result[1], tvl_result[2], tvl_result[3])
            })
        
        # Check risk change
        risk_result = check_risk_change(pool, previous)
        if risk_result:
            alerts.append({
                "type": "risk_change",
                "pool_id": risk_result[0],
                "pool": pool,
                "old_value": risk_result[1],
                "new_value": risk_result[2],
                "message": format_risk_alert(pool, risk_result[1], risk_result[2])
            })
    
    return alerts


def format_apy_alert(pool: Dict, old_apy: float, new_apy: float) -> str:
    """Format APY spike alert message"""
    symbol = pool.get("symbol", "Unknown")
    project = pool.get("project", "Unknown")
    chain = pool.get("chain", "Unknown")
    change = ((new_apy - old_apy) / old_apy) * 100
    
    return f"""
🚀 *APY Spike Alert!*

*{symbol}* on {project}

📈 APY jumped *+{change:.0f}%*
├ Old: {old_apy:.2f}%
└ New: *{new_apy:.2f}%*

Chain: {chain}

⚡ _This could be a temporary boost_
"""


def format_tvl_alert(pool: Dict, old_tvl: float, new_tvl: float, direction: str) -> str:
    """Format TVL change alert message"""
    symbol = pool.get("symbol", "Unknown")
    project = pool.get("project", "Unknown")
    change = ((new_tvl - old_tvl) / old_tvl) * 100
    
    emoji = "🐋" if direction == "increase" else "📉"
    old_str = f"${old_tvl/1_000_000:.2f}M" if old_tvl >= 1_000_000 else f"${old_tvl/1_000:.0f}K"
    new_str = f"${new_tvl/1_000_000:.2f}M" if new_tvl >= 1_000_000 else f"${new_tvl/1_000:.0f}K"
    
    action = "Whale deposit detected!" if direction == "increase" else "Significant outflow!"
    
    return f"""
{emoji} *TVL Alert!*

*{symbol}* on {project}

{action}
├ Old TVL: {old_str}
└ New TVL: *{new_str}* ({'+' if change > 0 else ''}{change:.0f}%)

{'🟢 Confidence boost' if direction == 'increase' else '⚠️ Monitor closely'}
"""


def format_risk_alert(pool: Dict, old_risk: str, new_risk: str) -> str:
    """Format risk level change alert message"""
    symbol = pool.get("symbol", "Unknown")
    project = pool.get("project", "Unknown")
    
    risk_emoji = {"Low": "🟢", "Medium": "🟡", "High": "🟠", "Critical": "🔴"}.get(new_risk, "⚪")
    
    return f"""
⚠️ *Risk Level Changed!*

*{symbol}* on {project}

Risk increased: {old_risk} → *{new_risk}* {risk_emoji}

🛡️ _Review your positions in this pool_
"""


def format_depeg_alert(stablecoin: str, price: float, peg: float = 1.0) -> str:
    """Format stablecoin depeg alert"""
    deviation = abs(price - peg) * 100
    
    return f"""
🚨 *DEPEG ALERT!*

*{stablecoin}* trading at *${price:.4f}*

Deviation from peg: *{deviation:.2f}%*

⚠️ _Consider reviewing positions with this stablecoin_
"""
