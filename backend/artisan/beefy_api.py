"""
Beefy Finance API Integration
Aggregates auto-compounding vault data from Beefy across multiple chains
"""

import httpx
from typing import List, Dict, Optional
from datetime import datetime
import asyncio

# Beefy API endpoints
BEEFY_API_BASE = "https://api.beefy.finance"
BEEFY_ENDPOINTS = {
    "vaults": f"{BEEFY_API_BASE}/vaults",
    "apy": f"{BEEFY_API_BASE}/apy",
    "tvl": f"{BEEFY_API_BASE}/tvl",
    "lps": f"{BEEFY_API_BASE}/lps",
}

# Chain ID mapping for Beefy
BEEFY_CHAIN_MAP = {
    "ethereum": "ethereum",
    "base": "base",
    "arbitrum": "arbitrum",
    "optimism": "optimism",
    "polygon": "polygon",
    "bsc": "bsc",
    "avalanche": "avax",
    "fantom": "fantom",
    "linea": "linea",
    "zksync": "zksync",
}


async def fetch_beefy_vaults(chain: str = None) -> List[Dict]:
    """
    Fetch all Beefy vaults with APY and TVL data
    
    Beefy is a yield aggregator that:
    - Auto-compounds rewards
    - Optimizes gas costs
    - Provides single-click deposits to complex strategies
    """
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            # Fetch all data in parallel
            vaults_task = client.get(BEEFY_ENDPOINTS["vaults"])
            apy_task = client.get(BEEFY_ENDPOINTS["apy"])
            tvl_task = client.get(BEEFY_ENDPOINTS["tvl"])
            
            vaults_resp, apy_resp, tvl_resp = await asyncio.gather(
                vaults_task, apy_task, tvl_task
            )
            
            vaults = vaults_resp.json()
            apys = apy_resp.json()
            tvls = tvl_resp.json()
            
            # Process and combine data
            result = []
            for vault in vaults:
                vault_id = vault.get("id", "")
                vault_chain = vault.get("chain", "")
                
                # Filter by chain if specified
                if chain:
                    beefy_chain = BEEFY_CHAIN_MAP.get(chain.lower(), chain.lower())
                    if vault_chain.lower() != beefy_chain:
                        continue
                
                # Skip inactive or eol vaults
                if vault.get("status") != "active":
                    continue
                
                # Get APY and TVL
                apy = apys.get(vault_id, 0)
                tvl = tvls.get(vault_id, 0)
                
                # Skip low TVL vaults
                if tvl < 50000:
                    continue
                
                # Format as standard pool format
                pool = {
                    "id": f"beefy-{vault_id}",
                    "pool": vault_id,
                    "project": "Beefy",
                    "chain": vault_chain.capitalize(),
                    "symbol": vault.get("name", vault_id),
                    "apy": apy * 100 if apy < 1 else apy,  # Convert to percentage
                    "tvl": tvl,
                    "stablecoin": is_stablecoin_vault(vault),
                    "underlyingTokens": vault.get("assets", []),
                    "verified": True,
                    "agent_verified": True,
                    "source": "beefy",
                    "auto_compound": True,
                    "vault_type": vault.get("type", "standard"),
                    "platform": vault.get("platform", ""),
                    "risk_level": get_beefy_risk(vault),
                }
                
                result.append(pool)
            
            # Sort by APY
            result.sort(key=lambda x: x.get("apy", 0), reverse=True)
            
            return result[:50]  # Limit to top 50
            
        except Exception as e:
            print(f"[Beefy] Error fetching vaults: {e}")
            return []


def is_stablecoin_vault(vault: Dict) -> bool:
    """Check if vault contains stablecoins"""
    stablecoins = ["usdc", "usdt", "dai", "frax", "lusd", "tusd", "busd", "gusd"]
    name = vault.get("name", "").lower()
    assets = vault.get("assets", [])
    
    for stable in stablecoins:
        if stable in name:
            return True
        for asset in assets:
            if stable in asset.lower():
                return True
    return False


def get_beefy_risk(vault: Dict) -> str:
    """Estimate risk level for Beefy vault"""
    safety_score = vault.get("safetyScore", 0)
    
    if safety_score >= 9:
        return "Low"
    elif safety_score >= 7:
        return "Medium" 
    elif safety_score >= 5:
        return "High"
    else:
        return "Critical"


async def get_beefy_tvl_by_chain() -> Dict[str, float]:
    """Get total TVL per chain from Beefy"""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(BEEFY_ENDPOINTS["tvl"])
            tvls = resp.json()
            
            # Sum by chain
            chain_tvl = {}
            for vault_id, tvl in tvls.items():
                chain = vault_id.split("-")[0] if "-" in vault_id else "unknown"
                chain_tvl[chain] = chain_tvl.get(chain, 0) + tvl
                
            return chain_tvl
        except Exception as e:
            print(f"[Beefy] Error fetching TVL: {e}")
            return {}


# Sync wrapper for non-async contexts
def fetch_beefy_vaults_sync(chain: str = None) -> List[Dict]:
    """Synchronous wrapper for fetch_beefy_vaults"""
    try:
        return asyncio.run(fetch_beefy_vaults(chain))
    except RuntimeError:
        # Already in async context
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, fetch_beefy_vaults(chain))
                return future.result()
        return loop.run_until_complete(fetch_beefy_vaults(chain))
