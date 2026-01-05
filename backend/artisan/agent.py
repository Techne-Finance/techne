"""
Artisan Agent - Yield Data Aggregator
Fetches and filters yield data from DefiLlama for Base chain
"""

import httpx
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import asyncio

# DefiLlama API endpoint
DEFILLAMA_YIELDS_URL = "https://yields.llama.fi/pools"

# Cache settings
_cache = {
    "data": None,
    "timestamp": None,
    "ttl_minutes": 5
}


async def fetch_yields() -> List[Dict[str, Any]]:
    """
    Fetch all yield pools from DefiLlama
    Uses cache to avoid hammering the API
    """
    now = datetime.now()
    
    # Return cached data if fresh
    if _cache["data"] and _cache["timestamp"]:
        if now - _cache["timestamp"] < timedelta(minutes=_cache["ttl_minutes"]):
            return _cache["data"]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(DEFILLAMA_YIELDS_URL)
        response.raise_for_status()
        data = response.json()
        
        _cache["data"] = data.get("data", [])
        _cache["timestamp"] = now
        
        return _cache["data"]


def filter_yields(
    pools: List[Dict[str, Any]],
    chain: str = "Base",
    min_tvl: float = 100000,
    min_apy: float = 1.0,
    max_apy: float = 100.0,
    stablecoin_only: bool = False,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Filter yield pools based on criteria
    
    Args:
        chain: Blockchain to filter (Base, Ethereum, etc.)
        min_tvl: Minimum TVL in USD
        min_apy: Minimum APY percentage
        max_apy: Maximum APY (filter out suspicious yields)
        stablecoin_only: Only show stablecoin pools
        limit: Max results to return
    """
    df = pd.DataFrame(pools)
    
    if df.empty:
        return []
    
    # Apply filters
    filtered = df[
        (df['chain'].str.lower() == chain.lower()) &
        (df['tvlUsd'] >= min_tvl) &
        (df['apy'].notna()) &
        (df['apy'] >= min_apy) &
        (df['apy'] <= max_apy)
    ]
    
    if stablecoin_only:
        filtered = filtered[filtered['stablecoin'] == True]
    
    # Sort by APY descending
    filtered = filtered.sort_values('apy', ascending=False)
    
    # Take top results
    filtered = filtered.head(limit)
    
    return filtered.to_dict('records')


def calculate_risk_score(pool: Dict[str, Any]) -> str:
    """
    Calculate risk score for a pool
    
    Returns: "Low", "Medium", "High"
    """
    tvl = pool.get('tvlUsd', 0)
    apy = pool.get('apy', 0)
    il_risk = pool.get('ilRisk', 'no')
    predictions = pool.get('predictions', {})
    predicted_class = predictions.get('predictedClass', '')
    
    risk_points = 0
    
    # TVL scoring
    if tvl < 500000:
        risk_points += 3  # Very low TVL = high risk
    elif tvl < 1000000:
        risk_points += 2
    elif tvl < 5000000:
        risk_points += 1
    
    # APY scoring (suspiciously high = risky)
    if apy > 50:
        risk_points += 3
    elif apy > 25:
        risk_points += 2
    elif apy > 15:
        risk_points += 1
    
    # IL risk
    if il_risk == 'yes':
        risk_points += 2
    
    # Prediction scoring
    if 'Down' in predicted_class:
        risk_points += 1
    
    # Classify
    if risk_points <= 2:
        return "Low"
    elif risk_points <= 5:
        return "Medium"
    else:
        return "High"


def format_pool_for_api(pool: Dict[str, Any], include_details: bool = False) -> Dict[str, Any]:
    """
    Format a pool for API response
    
    Args:
        pool: Raw pool data from DefiLlama
        include_details: If False, blur sensitive info (requires payment)
    """
    base_info = {
        "id": pool.get('pool'),
        "chain": pool.get('chain'),
        "apy": round(pool.get('apy', 0), 2),
        "tvl": round(pool.get('tvlUsd', 0)),
        "tvl_formatted": f"${pool.get('tvlUsd', 0):,.0f}",
        "stablecoin": pool.get('stablecoin', False),
        "risk_score": calculate_risk_score(pool),
        "il_risk": pool.get('ilRisk', 'no'),
    }
    
    if include_details:
        # Full details for paid users
        base_info.update({
            "project": pool.get('project'),
            "symbol": pool.get('symbol'),
            "apy_base": pool.get('apyBase'),
            "apy_reward": pool.get('apyReward'),
            "reward_tokens": pool.get('rewardTokens'),
            "pool_meta": pool.get('poolMeta'),
            "underlying_tokens": pool.get('underlyingTokens'),
            "exposure": pool.get('exposure'),
            "predictions": pool.get('predictions'),
        })
    else:
        # Blurred info for free tier
        base_info.update({
            "project": "***",  # Hidden
            "symbol": pool.get('symbol', '???')[:3] + "***",  # Partially hidden
            "unlock_price_usd": 0.50,  # Price to unlock
        })
    
    return base_info


async def get_top_yields(
    chain: str = "Base",
    min_tvl: float = 1000000,
    min_apy: float = 5.0,
    stablecoin_only: bool = True,
    limit: int = 10,
    include_details: bool = False
) -> List[Dict[str, Any]]:
    """
    Main function to get top yields for a chain
    """
    pools = await fetch_yields()
    filtered = filter_yields(
        pools,
        chain=chain,
        min_tvl=min_tvl,
        min_apy=min_apy,
        stablecoin_only=stablecoin_only,
        limit=limit
    )
    
    return [format_pool_for_api(p, include_details) for p in filtered]


# CLI test
if __name__ == "__main__":
    async def test():
        print("🔍 Artisan Agent - Fetching Base chain yields...")
        results = await get_top_yields(
            chain="Base",
            min_tvl=1000000,
            min_apy=3.0,
            stablecoin_only=True,
            limit=10,
            include_details=True  # Show all for testing
        )
        
        print(f"\n📊 Found {len(results)} yields:\n")
        for i, pool in enumerate(results, 1):
            print(f"{i}. {pool.get('project', '?')} - {pool.get('symbol', '?')}")
            print(f"   APY: {pool['apy']}% | TVL: {pool['tvl_formatted']} | Risk: {pool['risk_score']}")
            print()
    
    asyncio.run(test())
