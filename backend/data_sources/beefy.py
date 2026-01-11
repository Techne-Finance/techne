"""
Beefy Finance API Client
Fetches vault data, APY, and TVL from Beefy's public API.
"""
import httpx
import logging
from typing import Optional, Dict, List, Any
from functools import lru_cache
import time

logger = logging.getLogger("Beefy")

class BeefyClient:
    """
    Client for Beefy Finance API.
    Provides vault lookup, APY, and TVL data.
    """
    BASE_URL = "https://api.beefy.finance"
    CACHE_TTL = 300  # 5 minutes
    
    def __init__(self):
        self._vaults_cache: Optional[List[Dict]] = None
        self._vaults_cache_time: float = 0
        self._apy_cache: Optional[Dict[str, float]] = None
        self._apy_cache_time: float = 0
        self._tvl_cache: Optional[Dict[str, float]] = None
        self._tvl_cache_time: float = 0
    
    async def _fetch_json(self, endpoint: str, timeout: float = 10.0) -> Any:
        """Fetch JSON from Beefy API."""
        url = f"{self.BASE_URL}{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Beefy API error for {endpoint}: {e}")
            return None
    
    async def get_all_vaults(self) -> List[Dict]:
        """
        Get all Beefy vaults (cached).
        Returns list of vault objects with id, chain, token info, etc.
        """
        now = time.time()
        if self._vaults_cache and (now - self._vaults_cache_time) < self.CACHE_TTL:
            return self._vaults_cache
        
        vaults = await self._fetch_json("/vaults")
        if vaults:
            self._vaults_cache = vaults
            self._vaults_cache_time = now
            logger.info(f"Cached {len(vaults)} Beefy vaults")
        return self._vaults_cache or []
    
    async def get_all_apys(self) -> Dict[str, float]:
        """
        Get APYs for all vaults (cached).
        Returns dict mapping vault_id -> apy (as decimal, e.g. 0.15 = 15%)
        """
        now = time.time()
        if self._apy_cache and (now - self._apy_cache_time) < self.CACHE_TTL:
            return self._apy_cache
        
        apys = await self._fetch_json("/apy")
        if apys:
            self._apy_cache = apys
            self._apy_cache_time = now
        return self._apy_cache or {}
    
    async def get_all_tvls(self) -> Dict[str, float]:
        """
        Get TVLs for all vaults (cached).
        Returns dict mapping vault_id -> tvl in USD
        """
        now = time.time()
        if self._tvl_cache and (now - self._tvl_cache_time) < self.CACHE_TTL:
            return self._tvl_cache
        
        tvls = await self._fetch_json("/tvl")
        if tvls:
            self._tvl_cache = tvls
            self._tvl_cache_time = now
        return self._tvl_cache or {}
    
    def _normalize_chain(self, chain: str) -> str:
        """Normalize chain name to Beefy format."""
        chain_map = {
            "base": "base",
            "ethereum": "ethereum",
            "eth": "ethereum",
            "optimism": "optimism",
            "arbitrum": "arbitrum",
            "polygon": "polygon",
            "bsc": "bsc",
            "avalanche": "avax",
            "avax": "avax",
        }
        return chain_map.get(chain.lower(), chain.lower())
    
    async def get_vault_by_id(self, vault_id: str) -> Optional[Dict]:
        """
        Get vault by its ID (e.g. 'base-aerodrome-usdc-weth').
        """
        vaults = await self.get_all_vaults()
        for vault in vaults:
            if vault.get("id") == vault_id:
                return vault
        return None
    
    async def get_vault_by_address(self, address: str, chain: str = "base") -> Optional[Dict]:
        """
        Get vault by contract address.
        """
        address = address.lower()
        chain = self._normalize_chain(chain)
        vaults = await self.get_all_vaults()
        
        for vault in vaults:
            vault_chain = vault.get("chain", "").lower()
            vault_address = vault.get("earnContractAddress", "").lower()
            
            if vault_chain == chain and vault_address == address:
                return vault
        
        return None
    
    async def get_vault_full_data(self, vault_id: str) -> Optional[Dict]:
        """
        Get complete vault data including APY and TVL.
        Returns normalized data structure compatible with SmartRouter.
        """
        vault = await self.get_vault_by_id(vault_id)
        if not vault:
            return None
        
        apys = await self.get_all_apys()
        tvls = await self.get_all_tvls()
        
        apy = apys.get(vault_id, 0) * 100  # Convert to percentage
        tvl = tvls.get(vault_id, 0)
        
        # Normalize to SmartRouter format
        return {
            "pool_address": vault.get("earnContractAddress", ""),
            "chain": vault.get("chain", ""),
            "project": "Beefy",
            "symbol": vault.get("name", vault_id),
            "pool_type": "vault",  # Single-sided vault
            "tokens": [vault.get("token", "")],
            "token_symbols": [vault.get("tokenSymbol", vault.get("oracleId", ""))],
            "tvl": tvl,
            "apy": round(apy, 2),
            "apy_source": "beefy_api",
            
            # Vault-specific fields
            "vault_id": vault_id,
            "vault_status": vault.get("status", "active"),
            "vault_platform": vault.get("platformId", ""),
            "vault_strategy": vault.get("strategyTypeId", ""),
            "vault_risks": vault.get("risks", []),
            "vault_assets": vault.get("assets", []),
            "vault_withdrawal_fee": vault.get("withdrawalFee", 0),
            
            # Links
            "pool_link": f"https://app.beefy.com/vault/{vault_id}",
            "explorer_link": f"https://basescan.org/address/{vault.get('earnContractAddress', '')}",
        }
    
    async def search_vaults(self, query: str, chain: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        Search vaults by name/token.
        """
        vaults = await self.get_all_vaults()
        query = query.lower()
        
        results = []
        for vault in vaults:
            if vault.get("status") == "eol":  # Skip retired vaults
                continue
            
            if chain and vault.get("chain", "").lower() != chain.lower():
                continue
            
            # Match by name, token, or id
            name = vault.get("name", "").lower()
            token = vault.get("token", "").lower()
            vault_id = vault.get("id", "").lower()
            
            if query in name or query in token or query in vault_id:
                results.append(vault)
                if len(results) >= limit:
                    break
        
        return results


# Singleton instance
beefy_client = BeefyClient()
