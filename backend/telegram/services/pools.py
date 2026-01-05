"""
Techne Telegram Bot - Pool Service
Fetches and formats pool data for Telegram messages
"""

import httpx
from typing import List, Dict, Any, Optional
from ..models.user_config import UserConfig


API_BASE = "http://localhost:8000"


async def fetch_pools(config: UserConfig, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch pools from Techne API based on user config
    """
    params = {
        "chain": "" if config.chain == "all" else config.chain,
        "min_tvl": config.min_tvl,
        "min_apy": config.min_apy,
        "max_apy": config.max_apy,
        "asset_type": config.asset_type,
        "pool_type": config.pool_type,
        "stablecoin_only": config.stablecoin_only,
        "protocols": ",".join(config.protocols) if config.protocols else "",
        "limit": limit
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{API_BASE}/api/pools", params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("combined", data.get("pools", []))
    except Exception as e:
        print(f"[TelegramBot] Error fetching pools: {e}")
        return []


async def fetch_pool_detail(pool_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch detailed info for a specific pool
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{API_BASE}/api/pool/{pool_id}")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        print(f"[TelegramBot] Error fetching pool detail: {e}")
    return None


def format_pool_card(pool: Dict[str, Any], index: int = None) -> str:
    """
    Format a single pool as a Telegram message card
    """
    symbol = pool.get("symbol", "Unknown")
    project = pool.get("project", "Unknown")
    apy = pool.get("apy", 0)
    tvl = pool.get("tvl", 0)
    chain = pool.get("chain", "Unknown")
    risk = pool.get("risk_level", "Unknown")
    
    # Format TVL
    if tvl >= 1_000_000:
        tvl_str = f"${tvl/1_000_000:.1f}M"
    elif tvl >= 1_000:
        tvl_str = f"${tvl/1_000:.0f}K"
    else:
        tvl_str = f"${tvl:.0f}"
    
    # Risk emoji
    risk_emoji = {
        "Low": "🟢",
        "Medium": "🟡",
        "High": "🟠",
        "Critical": "🔴"
    }.get(risk, "⚪")
    
    # Chain emoji
    chain_emoji = {
        "Base": "🔵",
        "Ethereum": "⟠",
        "Solana": "🟣",
        "Arbitrum": "🔷"
    }.get(chain, "🌐")
    
    prefix = f"{index}. " if index else ""
    
    return (
        f"{prefix}*{symbol}*\n"
        f"├ Protocol: {project}\n"
        f"├ APY: *{apy:.2f}%* 📈\n"
        f"├ TVL: {tvl_str}\n"
        f"├ Chain: {chain_emoji} {chain}\n"
        f"└ Risk: {risk_emoji} {risk}"
    )


def format_pool_list(pools: List[Dict[str, Any]], title: str = "🔍 Top Pools") -> str:
    """
    Format list of pools for Telegram
    """
    if not pools:
        return "❌ No pools found matching your filters.\n\nTry adjusting with /setmintvl or /setchain"
    
    lines = [f"*{title}*\n"]
    
    for i, pool in enumerate(pools[:10], 1):
        symbol = pool.get("symbol", "?")
        project = pool.get("project", "?")
        apy = pool.get("apy", 0)
        tvl = pool.get("tvl", 0)
        risk = pool.get("risk_level", "?")
        
        # Compact format
        tvl_str = f"${tvl/1_000_000:.1f}M" if tvl >= 1_000_000 else f"${tvl/1_000:.0f}K"
        risk_emoji = {"Low": "🟢", "Medium": "🟡", "High": "🟠"}.get(risk, "⚪")
        
        lines.append(
            f"{i}. *{symbol}* ({project})\n"
            f"   {apy:.1f}% APY • {tvl_str} • {risk_emoji}\n"
        )
    
    lines.append(f"\n_Showing {min(len(pools), 10)} of {len(pools)} pools_")
    lines.append("Use /pool [number] for details")
    
    return "\n".join(lines)


def format_pool_detail(pool: Dict[str, Any]) -> str:
    """
    Format detailed pool info for Telegram
    """
    symbol = pool.get("symbol", "Unknown")
    project = pool.get("project", "Unknown")
    apy = pool.get("apy", 0)
    apy_base = pool.get("apyBase", 0)
    apy_reward = pool.get("apyReward", 0)
    tvl = pool.get("tvl", 0)
    chain = pool.get("chain", "Unknown")
    risk = pool.get("risk_level", "Unknown")
    pool_id = pool.get("pool", pool.get("id", "N/A"))
    
    # Format TVL
    tvl_str = f"${tvl/1_000_000:.2f}M" if tvl >= 1_000_000 else f"${tvl/1_000:.1f}K"
    
    # Risk details
    risk_emoji = {"Low": "🟢", "Medium": "🟡", "High": "🟠", "Critical": "🔴"}.get(risk, "⚪")
    
    text = f"""
📊 *{symbol}* - Detailed Analysis

*Protocol:* {project}
*Chain:* {chain}
*Pool ID:* `{pool_id[:20]}...`

━━━━━━━━━━━━━━━━━━━━

💰 *Yield Breakdown*
├ Total APY: *{apy:.2f}%*
├ Base APY: {apy_base:.2f}%
└ Reward APY: {apy_reward:.2f}%

📈 *Metrics*
├ TVL: {tvl_str}
└ Risk: {risk_emoji} {risk}

━━━━━━━━━━━━━━━━━━━━

🤖 _AI Agent can deposit into this pool_
Use /deposit {pool_id[:8]} to proceed
"""
    return text.strip()


def format_filters_summary(config: UserConfig) -> str:
    """
    Format current user filters as readable summary
    """
    chain = config.chain.capitalize() if config.chain != "all" else "All Chains"
    protocols = ", ".join(config.protocols) if config.protocols else "All Protocols"
    
    return f"""
⚙️ *Your Current Filters*

*Chain:* {chain}
*Min TVL:* ${config.min_tvl:,.0f}
*APY Range:* {config.min_apy}% - {config.max_apy}%
*Risk Level:* {config.risk_level.capitalize()}
*Asset Type:* {config.asset_type.capitalize()}
*Pool Type:* {config.pool_type.capitalize()}
*Protocols:* {protocols}

*Alerts:* {'✅ Enabled' if config.alerts_enabled else '❌ Disabled'}
*APY Spike Alert:* +{config.apy_spike_threshold}%
*TVL Change Alert:* ±{config.tvl_change_threshold}%

Use commands like /setchain, /setmintvl to modify
"""
