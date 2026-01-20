"""
Pool Data API Router
Exposes The Graph pool data via REST API
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter(prefix="/api/pools", tags=["Pool Data"])


@router.get("/")
async def get_all_pools():
    """Get data for all tracked pools from The Graph"""
    from agents.pool_data_fetcher import pool_data_fetcher
    
    data = await pool_data_fetcher.refresh_all_pools()
    
    return {
        "success": True,
        "source": "thegraph",
        "pools": data,
        "count": len(data)
    }


@router.get("/{protocol}")
async def get_protocol_pools(protocol: str):
    """Get pool data for a specific protocol"""
    from agents.pool_data_fetcher import pool_data_fetcher, TRACKED_POOLS
    
    # Find pools for this protocol
    protocol_pools = {
        name: addr for name, addr in TRACKED_POOLS.items()
        if name.startswith(protocol)
    }
    
    if not protocol_pools:
        raise HTTPException(status_code=404, detail=f"No pools found for {protocol}")
    
    results = {}
    for pool_name, pool_address in protocol_pools.items():
        data = await pool_data_fetcher.get_pool_data(protocol, pool_address)
        if data:
            results[pool_name] = data
    
    return {
        "protocol": protocol,
        "pools": results,
        "source": "thegraph"
    }


@router.get("/best")
async def get_best_pool(min_tvl: float = 0, asset: str = "usdc"):
    """Find the best performing pool based on APY"""
    from agents.pool_data_fetcher import pool_data_fetcher
    
    best_pool = await pool_data_fetcher.get_best_lending_pool(min_tvl=min_tvl)
    
    if not best_pool:
        raise HTTPException(status_code=404, detail="No pools found matching criteria")
    
    pool_data = pool_data_fetcher.cache.get(best_pool, {})
    
    return {
        "best_pool": best_pool,
        "apy": pool_data.get("apy", 0),
        "tvl": pool_data.get("tvl", 0),
        "source": "thegraph"
    }


@router.get("/compare")
async def compare_pools():
    """Compare all pools side by side"""
    from agents.pool_data_fetcher import pool_data_fetcher
    
    await pool_data_fetcher.refresh_all_pools()
    
    # Sort by APY
    sorted_pools = sorted(
        pool_data_fetcher.cache.items(),
        key=lambda x: x[1].get("apy", 0),
        reverse=True
    )
    
    comparison = []
    for pool_name, data in sorted_pools:
        protocol = pool_name.split("_")[0]
        comparison.append({
            "pool": pool_name,
            "protocol": protocol,
            "apy": round(data.get("apy", 0), 2),
            "tvl": round(data.get("tvl", 0), 2),
            "utilization": data.get("utilization", "N/A")
        })
    
    return {
        "comparison": comparison,
        "best": comparison[0]["pool"] if comparison else None,
        "source": "thegraph"
    }


@router.post("/refresh")
async def force_refresh():
    """Force refresh all pool data from The Graph"""
    from agents.pool_data_fetcher import pool_data_fetcher
    
    data = await pool_data_fetcher.refresh_all_pools()
    
    return {
        "success": True,
        "refreshed_pools": len(data),
        "message": "Pool data refreshed from The Graph"
    }
