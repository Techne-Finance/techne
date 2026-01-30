"""
Pool Data Enricher
Fetches additional pool metadata from multiple sources for LLM analysis.

Sources:
- Moralis: Holder count for LP tokens
- DefiLlama: Historical APY data
- Basescan: Contract creation date (pool age)
"""
import asyncio
import os
import httpx
from typing import Dict, Optional
from datetime import datetime, timedelta

# Try to load dotenv at import
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# API Keys
MORALIS_API_KEY = os.getenv("MORALIS_API_KEY", "")
BASESCAN_API_KEY = os.getenv("BASESCAN_API_KEY", "")

# API Endpoints
MORALIS_API = "https://deep-index.moralis.io/api/v2.2"
BASESCAN_API = "https://api.basescan.org/api"
DEFILLAMA_API = "https://yields.llama.fi"


class PoolEnricher:
    """
    Enriches pool data with additional metadata from external sources.
    
    Usage:
        enricher = PoolEnricher()
        enriched_pool = await enricher.enrich(pool_data)
    """
    
    def __init__(self):
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 1800  # 30 min cache
        
    async def enrich(self, pool: Dict) -> Dict:
        """
        Enrich pool with APY history, pool age, volume, IL risk from DefiLlama.
        
        Note: Moralis NOT used here (reserved for scam_detector verify only).
        """
        enriched = pool.copy()
        
        # Get DefiLlama rich data
        llama = await self._get_defillama_data(pool)
        
        enriched["apy_7d_ago"] = llama.get("apy_7d_ago", 0)
        enriched["apy_mean_30d"] = llama.get("apy_mean_30d", 0)
        enriched["age_days"] = llama.get("pool_age_days", 0)
        enriched["volume_24h"] = llama.get("volume_24h", 0)
        enriched["il_risk"] = llama.get("il_risk", "unknown")
        enriched["prediction"] = llama.get("prediction", "unknown")
        
        return enriched
    
    async def _get_holder_count(self, token_address: str) -> int:
        """Get LP token holder count from Moralis"""
        if not MORALIS_API_KEY:
            return 0
        
        # Check cache
        cache_key = f"holders_{token_address}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now().timestamp() - cached["time"]) < self.cache_ttl:
                return cached["value"]
        
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # Get token owners count from Moralis
                # Use /owners endpoint to get actual holder list and count
                resp = await client.get(
                    f"{MORALIS_API}/erc20/{token_address}/owners",
                    params={"chain": "base", "limit": 1},  # Just need count, not all owners
                    headers={"X-API-Key": MORALIS_API_KEY}
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    # Try to get total from pagination or result count
                    holders = int(data.get("total", len(data.get("result", []))))
                    
                    # If that doesn't work, try the transfers endpoint as fallback
                    if holders == 0:
                        resp2 = await client.get(
                            f"{MORALIS_API}/erc20/{token_address}/stats",
                            params={"chain": "base"},
                            headers={"X-API-Key": MORALIS_API_KEY}
                        )
                        if resp2.status_code == 200:
                            data2 = resp2.json()
                            # Use transfer count as proxy for activity
                            transfers = int(data2.get("transfers", {}).get("total", 0))
                            holders = min(transfers // 10, 10000)  # Rough estimate
                    
                    # Cache
                    self.cache[cache_key] = {"value": holders, "time": datetime.now().timestamp()}
                    return holders
                    
        except Exception as e:
            print(f"[Enricher] Moralis error: {e}")
        
        return 0
    
    async def _get_defillama_data(self, pool: Dict) -> Dict:
        """
        Get rich data from DefiLlama pools endpoint.
        
        Returns:
            - apy_7d_ago: APY change from 7 days
            - apy_mean_30d: Mean APY over 30 days
            - pool_age_days: Days of data (count field)
            - volume_24h: USD volume
            - il_risk: IL risk assessment
            - prediction: Trend prediction
        """
        symbol = pool.get("symbol", "")
        
        # Check cache
        cache_key = f"defillama_{symbol}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now().timestamp() - cached["time"]) < self.cache_ttl:
                return cached["value"]
        
        result = {
            "apy_7d_ago": 0,
            "apy_mean_30d": 0,
            "pool_age_days": 0,
            "volume_24h": 0,
            "il_risk": "unknown",
            "prediction": "unknown"
        }
        
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(f"{DEFILLAMA_API}/pools")
                
                if resp.status_code == 200:
                    pools = resp.json().get("data", [])
                    
                    # Find matching pool (Aerodrome on Base - v1 or slipstream)
                    matched = None
                    for p in pools:
                        if (p.get("chain") == "Base" and 
                            "aerodrome" in p.get("project", "").lower() and
                            self._symbols_match(symbol, p.get("symbol", ""))):
                            matched = p
                            break
                    
                    if matched:
                        # Extract rich data
                        current_apy = matched.get("apy", 0) or 0
                        apy_pct_7d = matched.get("apyPct7D", 0) or 0
                        
                        result = {
                            "apy_7d_ago": current_apy - apy_pct_7d,  # Approximate
                            "apy_mean_30d": matched.get("apyMean30d", 0) or 0,
                            "pool_age_days": matched.get("count", 0) or 0,  # Days of data = age
                            "volume_24h": matched.get("volumeUsd1d", 0) or 0,
                            "il_risk": matched.get("ilRisk", "unknown") or "unknown",
                            "prediction": matched.get("predictions", {}).get("predictedClass", "unknown")
                        }
                        
                        # Cache
                        self.cache[cache_key] = {"value": result, "time": datetime.now().timestamp()}
                        
        except Exception as e:
            print(f"[Enricher] DefiLlama error: {e}")
        
        return result
    
    def _symbols_match(self, our_symbol: str, llama_symbol: str) -> bool:
        """Check if symbols match (handle different formats)"""
        # Normalize: WETH-USDC vs WETH/USDC
        our_tokens = set(our_symbol.upper().replace("-", "/").split("/"))
        llama_tokens = set(llama_symbol.upper().replace("-", "/").split("/"))
        return our_tokens == llama_tokens
    
    async def _get_pool_age(self, contract_address: str) -> int:
        """
        Get pool age in days using Alchemy RPC.
        Uses eth_getLogs to find first Transfer event (pool creation).
        """
        if not contract_address or contract_address == "unknown":
            return 0
        
        # Check cache
        cache_key = f"age_{contract_address}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now().timestamp() - cached["time"]) < self.cache_ttl:
                return cached["value"]
        
        alchemy_rpc = os.getenv("ALCHEMY_RPC_URL", "")
        if not alchemy_rpc:
            return 0
        
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # Get first Transfer event (topic0 = Transfer signature)
                transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
                
                resp = await client.post(
                    alchemy_rpc,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_getLogs",
                        "params": [{
                            "address": contract_address,
                            "topics": [transfer_topic],
                            "fromBlock": "0x1",  # Base requires > 0x0
                            "toBlock": "0xF00000"  # ~15M blocks, covers all Base history
                        }]
                    }
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    logs = data.get("result", [])
                    
                    if logs and len(logs) > 0:
                        # Get block number of first event
                        first_block_hex = logs[0].get("blockNumber", "0x0")
                        first_block = int(first_block_hex, 16)
                        
                        # Get block timestamp
                        block_resp = await client.post(
                            alchemy_rpc,
                            json={
                                "jsonrpc": "2.0",
                                "id": 1,
                                "method": "eth_getBlockByNumber",
                                "params": [first_block_hex, False]
                            }
                        )
                        
                        if block_resp.status_code == 200:
                            block_data = block_resp.json().get("result", {})
                            timestamp_hex = block_data.get("timestamp", "0x0")
                            timestamp = int(timestamp_hex, 16)
                            
                            created_date = datetime.fromtimestamp(timestamp)
                            age_days = (datetime.now() - created_date).days
                            
                            # Cache
                            self.cache[cache_key] = {"value": age_days, "time": datetime.now().timestamp()}
                            return age_days
                            
        except Exception as e:
            print(f"[Enricher] RPC pool age error: {e}")
        
        return 0


# Singleton
pool_enricher = PoolEnricher()


async def enrich_pool(pool: Dict) -> Dict:
    """Quick function to enrich a pool with additional data"""
    return await pool_enricher.enrich(pool)


# Test
if __name__ == "__main__":
    async def test():
        enricher = PoolEnricher()
        
        # Test with a real Aerodrome pool
        test_pool = {
            "symbol": "WETH-USDC",
            "apy": 45.5,
            "tvl": 50000000,
            "protocol": "aerodrome"
        }
        
        print("\n" + "="*60)
        print("POOL ENRICHER TEST (DefiLlama Only)")
        print("="*60)
        print(f"\nOriginal pool: {test_pool['symbol']}")
        
        enriched = await enricher.enrich(test_pool)
        
        print(f"\n✅ Enriched data from DefiLlama:")
        print(f"  APY 7d ago:    {enriched.get('apy_7d_ago', 0):.2f}%")
        print(f"  APY mean 30d:  {enriched.get('apy_mean_30d', 0):.2f}%")
        print(f"  Pool Age:      {enriched.get('age_days', 0)} days")
        print(f"  Volume 24h:    ${enriched.get('volume_24h', 0)/1e6:.2f}M")
        print(f"  IL Risk:       {enriched.get('il_risk', 'unknown')}")
        print(f"  Prediction:    {enriched.get('prediction', 'unknown')}")
    
    asyncio.run(test())

