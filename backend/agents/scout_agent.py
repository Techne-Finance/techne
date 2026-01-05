"""
Scout Agent - "The Eyes" of Artisan System
Constantly monitors DeFi data sources for new opportunities

Responsibilities:
- Poll DeFiLlama API for pools/vaults
- Scan The Graph for new pools on Aerodrome/Uniswap
- Monitor whale wallets for large movements
- Cache data for system resilience
- Record discoveries in Memory Engine
- Trace all operations via Observability
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json

# Observability integration
try:
    from agents.observability_engine import observability, traced, SpanStatus
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False
    def traced(agent, op):
        def decorator(func): return func
        return decorator

# Memory integration
try:
    from agents.memory_engine import memory_engine, MemoryType
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False


# Top DeFi Protocols by TVL (from DefiLlama research)
TOP_PROTOCOLS = {
    "tier1": [  # Najpopularniejsze - widoczne na górze
        {"name": "aave", "displayName": "Aave", "tvl": "32B", "chains": ["Ethereum", "Base", "Arbitrum", "Polygon", "Optimism"]},
        {"name": "lido", "displayName": "Lido", "tvl": "25B", "chains": ["Ethereum"]},
        {"name": "uniswap", "displayName": "Uniswap", "tvl": "2.1B", "chains": ["Ethereum", "Base", "Arbitrum", "Polygon", "Optimism"]},
        {"name": "curve", "displayName": "Curve", "tvl": "2.1B", "chains": ["Ethereum", "Base", "Arbitrum", "Polygon"]},
        {"name": "compound", "displayName": "Compound", "tvl": "1.6B", "chains": ["Ethereum", "Base", "Arbitrum", "Polygon"]},
        {"name": "aerodrome", "displayName": "Aerodrome", "tvl": "500M", "chains": ["Base"]},
    ],
    "tier2": [  # Drugorzędne - w slidebar
        {"name": "pendle", "displayName": "Pendle", "tvl": "3.7B", "chains": ["Ethereum", "Arbitrum"]},
        {"name": "morpho", "displayName": "Morpho", "tvl": "5.7B", "chains": ["Ethereum", "Base"]},
        {"name": "sparklend", "displayName": "SparkLend", "tvl": "3.2B", "chains": ["Ethereum"]},
        {"name": "kamino", "displayName": "Kamino", "tvl": "2.1B", "chains": ["Solana"]},
        {"name": "justlend", "displayName": "JustLend", "tvl": "3.7B", "chains": ["Tron"]},
        {"name": "maple", "displayName": "Maple", "tvl": "2.5B", "chains": ["Ethereum"]},
        {"name": "venus", "displayName": "Venus", "tvl": "1.5B", "chains": ["Binance"]},
        {"name": "raydium", "displayName": "Raydium", "tvl": "1.4B", "chains": ["Solana"]},
        {"name": "convex", "displayName": "Convex", "tvl": "923M", "chains": ["Ethereum"]},
    ],
    "tier3": [  # Nowe protokoły z potencjałem airdrop
        {"name": "peapods", "displayName": "Peapods Finance", "tvl": "Unknown", "chains": ["Ethereum", "Base", "Arbitrum"], "airdrop_potential": "high"},
        {"name": "midas", "displayName": "Midas", "tvl": "Unknown", "chains": ["Multi-Chain"], "airdrop_potential": "high"},
        {"name": "infinifi", "displayName": "InfiniFi", "tvl": "Unknown", "chains": ["Ethereum"], "airdrop_potential": "high"},
        {"name": "scroll", "displayName": "Scroll Pools", "tvl": "500M", "chains": ["Scroll"], "airdrop_potential": "high"},
        {"name": "linea", "displayName": "Linea Pools", "tvl": "600M", "chains": ["Linea"], "airdrop_potential": "medium"},
        {"name": "zksync", "displayName": "zkSync Pools", "tvl": "400M", "chains": ["zkSync Era"], "airdrop_potential": "medium"},
    ]
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ScoutAgent")


class ScoutAgent:
    """
    The Scout - Data Collection Agent
    Runs continuously, fetching data from multiple sources
    """
    
    def __init__(self):
        self.apis = {
            "defillama_pools": "https://yields.llama.fi/pools",
            "defillama_protocols": "https://api.llama.fi/protocols",
            "beefy_vaults": "https://api.beefy.finance/vaults",
            "beefy_apy": "https://api.beefy.finance/apy",
        }
        
        # === MVP STABLECOIN-ONLY CONFIGURATION ===
        # Only "Big 3" trusted stablecoins (Base chain)
        self.allowed_stablecoins = {
            "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "USDT": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
            "DAI": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
        }
        
        # BANNED: Algorithmic/risky stables (high depeg risk)
        self.banned_assets = [
            "USDe", "USD+", "LUSD", "FRAX", "MIM", "UST", "USDD",
            "USTC", "agEUR", "FEI", "USDP", "GUSD"  # Add more if needed
        ]
        
        # Only battle-tested protocols for MVP
        self.trusted_protocols = [
            "aave", "aave-v3", "morpho", "compound", "compound-v3",
            "moonwell", "seamless", "sonne-finance", "radiant", "fluid-lending"
        ]
        
        # Allowed chains (EVM compatible)
        self.allowed_chains = [
            "ethereum", "base", "arbitrum", "optimism", "polygon", "avalanche"
        ]
        
        # Cache
        self.cache = {
            "pools": [],
            "protocols": [],
            "beefy_vaults": [],
            "last_update": None
        }
        
        # Whale wallets to monitor (Base chain examples)
        self.whale_wallets = [
            "0x...",  # Add whale addresses
        ]
        
        # Polling intervals (seconds)
        self.intervals = {
            "pools": 900,      # 15 minutes
            "protocols": 3600, # 1 hour
            "whales": 300      # 5 minutes
        }
        
        self.is_running = False
        self.subscribers = []  # Agents that want to receive updates
        
        logger.info("🔒 Scout in MVP Mode: Stablecoins ONLY (USDC, USDT, DAI)")
        
    async def start(self):
        """Start the continuous monitoring loop"""
        self.is_running = True
        logger.info("🔍 Scout Agent started - monitoring DeFi landscape...")
        
        await asyncio.gather(
            self._poll_pools(),
            self._poll_protocols(),
            # self._monitor_whales()  # Enable when whale addresses added
        )

    def stop(self):
        """Stop the monitoring loop"""
        self.is_running = False
        logger.info("Scout Agent stopped")
        
    def subscribe(self, callback):
        """Subscribe to receive data updates"""
        self.subscribers.append(callback)

    async def _fetch_beefy_vaults(self) -> List[Dict]:
        """Fetch vaults from Beefy Finance API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.apis["beefy_vaults"]) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Filter for Base chain and stablecoins
                        base_vaults = [
                            v for v in data 
                            if v.get('chain') == 'base' 
                            and v.get('status') == 'active'
                            and any(s in v.get('name', '') for s in ['USDC', 'USDT', 'DAI'])
                        ]
                        logger.info(f"🥩 Fetched {len(base_vaults)} Beefy vaults on Base")
                        return base_vaults
                    else:
                        logger.error(f"Beefy API error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Failed to fetch Beefy vaults: {str(e)}")
            return []

    async def _poll_pools(self):
        """Poll pool data from multiple sources"""
        while self.is_running:
            try:
                # 1. Fetch DeFiLlama Pools
                llama_pools = await self._fetch_defillama_pools()
                
                # 2. Fetch Beefy Vaults (New Source)
                beefy_vaults = await self._fetch_beefy_vaults()
                
                # Merge and Filter
                # Map Beefy format to our internal format
                mapped_beefy = []
                for vault in beefy_vaults:
                    mapped_beefy.append({
                        "chain": "base",
                        "project": "beefy", 
                        "symbol": vault.get("name", "Unknown"),
                        "tvlUsd": vault.get("tvl", 0),
                        "apy": (vault.get("apy", 0) or 0) * 100, # Beefy APY is decimal often
                        "pool": vault.get("id"),
                        "stablecoin": True,
                        "exposure": "single"
                    })

                # Combine lists
                all_pools = llama_pools + mapped_beefy
                
                # Update Cache
                self.cache["pools"] = all_pools
                self.cache["last_update"] = datetime.now()
                
                # Notify subscribers
                for callback in self.subscribers:
                    await callback(self.cache["pools"])
                    
                logger.info(f"✅ Updated pool data: {len(self.cache['pools'])} pools tracked (Llama: {len(llama_pools)}, Beefy: {len(mapped_beefy)})")
                
            except Exception as e:
                logger.error(f"Error polling pools: {str(e)}")
                
            await asyncio.sleep(self.intervals["pools"])
        
    async def _notify_subscribers(self, event_type: str, data: Any):
        """Notify all subscribers of new data"""
        for callback in self.subscribers:
            try:
                await callback(event_type, data)
            except Exception as e:
                logger.error(f"Failed to notify subscriber: {e}")
    
    # ===========================================
    # DEFILLAMA INTEGRATION
    # ===========================================
    
    def _get_whitelisted_projects(self) -> set:
        """Get set of all whitelisted project slugs/names"""
        allowed = set()
        for tier in ["tier1", "tier2", "tier3"]:
            for p in TOP_PROTOCOLS.get(tier, []):
                allowed.add(p["name"].lower())
        return allowed

    async def _fetch_defillama_pools(self, chain: str, min_tvl: float) -> List[Dict]:
        """Fetch pools from DefiLlama"""
        allowed_projects = self._get_whitelisted_projects()
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self.defillama_base}/pools")
            if response.status_code != 200:
                logger.error(f"DeFiLlama API error: {response.status_code}")
                return []
            
            data = response.json()
            pools = data.get('data', [])
            
            # Filter by chain and TVL
            filtered = []
            for pool in pools:
                if pool.get('chain', '').lower() != chain.lower():
                    continue
                if pool.get('tvlUsd', 0) < min_tvl:
                    continue
                
                # Strict Whitelist Check
                project_slug = (pool.get('project') or '').lower()
                is_whitelisted = False
                for allowed in allowed_projects:
                    if allowed in project_slug:
                        is_whitelisted = True
                        break
                
                if not is_whitelisted:
                    continue

                if self.mvp_mode:
                     # Check if symbol contains stablecoin
                    symbol = pool.get('symbol', '').upper()
                    if not any(s in symbol for s in self.stablecoins):
                        continue

                filtered.append({
                    "id": pool.get('pool'),
                    "chain": pool.get('chain'),
                    "project": pool.get('project'),
                    "symbol": pool.get('symbol'),
                    "apy": round(pool.get('apy', 0), 2),
                    "apyBase": round(pool.get('apyBase', 0) or 0, 2),
                    "apyReward": round(pool.get('apyReward', 0) or 0, 2),
                    "tvl": pool.get('tvlUsd', 0),
                    "tvl_formatted": self._format_tvl(pool.get('tvlUsd', 0)),
                    "stablecoin": pool.get('stablecoin', False),
                    "exposure": pool.get('exposure'),
                    "pool_link": self._generate_pool_link(pool.get('project'), pool.get('pool')),
                    "source": "defillama",
                    "source_name": "DefiLlama",
                    "source_badge": "📊",
                })
                
            return filtered[:50]  # Limit to top 50
    
    async def _poll_protocols(self):
        """Poll protocol TVL data"""
        while self.is_running:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.apis["defillama_protocols"]) as resp:
                        if resp.status == 200:
                            protocols = await resp.json()
                            
                            # Filter Base protocols
                            base_protocols = [
                                p for p in protocols 
                                if "Base" in p.get("chains", [])
                            ]
                            
                            self.cache["protocols"] = base_protocols
                            logger.info(f"Updated {len(base_protocols)} Base protocols")
                            
            except Exception as e:
                logger.error(f"Protocol polling failed: {e}")
            
            await asyncio.sleep(self.intervals["protocols"])
    
    # ===========================================
    # BEEFY INTEGRATION
    # ===========================================
    
    async def fetch_beefy_vaults(self, chain: str = "base") -> List[Dict]:
        """Fetch Beefy vaults with APY data"""
        try:
            async with aiohttp.ClientSession() as session:
                # Fetch vaults and APY in parallel
                vaults_resp, apy_resp = await asyncio.gather(
                    session.get(self.apis["beefy_vaults"]),
                    session.get(self.apis["beefy_apy"])
                )
                
                vaults = await vaults_resp.json()
                apys = await apy_resp.json()
                
                # Filter by chain and merge APY
                chain_vaults = []
                for vault in vaults:
                    if vault.get("chain") == chain and vault.get("status") == "active":
                        vault["apy"] = apys.get(vault["id"], 0) * 100
                        chain_vaults.append(vault)
                
                self.cache["beefy_vaults"] = chain_vaults
                logger.info(f"Fetched {len(chain_vaults)} Beefy vaults on {chain}")
                return chain_vaults
                
        except Exception as e:
            logger.error(f"Beefy fetch failed: {e}")
            return self.cache.get("beefy_vaults", [])
    
    # ===========================================
    # GECKOTERMINAL INTEGRATION
    # ===========================================

    async def _fetch_gecko_pools(self, chain: str, min_tvl: float) -> List[Dict]:
        """Fetch pools from GeckoTerminal"""
        allowed_projects = self._get_whitelisted_projects()
        chain_map = {
            "Base": "base",
            "Ethereum": "eth",
            "Arbitrum": "arbitrum",
            "Polygon": "polygon_pos",
            "Optimism": "optimism"
        }
        
        gecko_chain = chain_map.get(chain, chain.lower())
        
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    f"{self.gecko_base}/networks/{gecko_chain}/trending_pools",
                    headers={"Accept": "application/json"}
                )
            except Exception as e:
                logger.error(f"GeckoTerminal API request failed: {e}")
                return []

            if response.status_code != 200:
                logger.error(f"GeckoTerminal API error: {response.status_code}")
                return []
            
            data = response.json()
            pools = data.get('data', [])
            
            filtered = []
            for pool in pools:
                attrs = pool.get('attributes', {})
                reserve_usd = float(attrs.get('reserve_in_usd', '0') or '0')
                
                if reserve_usd < min_tvl:
                    continue
                
                # Strict Whitelist Check
                name_lower = (attrs.get('name', '')).lower()
                is_whitelisted = False
                for allowed in allowed_projects:
                    if allowed in name_lower:
                        is_whitelisted = True
                        break
                
                if not is_whitelisted:
                    continue

                if self.mvp_mode:
                    # Check if name contains stablecoin
                    if not any(s in name_lower.upper() for s in self.stablecoins):
                        continue

                # Estimate APY from volume (simplified)
                volume_24h = float(attrs.get('volume_usd', {}).get('h24', '0') or '0')
                fee_rate = 0.003  # Assume 0.3% fee
                estimated_apy = (volume_24h * fee_rate * 365 / max(reserve_usd, 1)) * 100
                
                filtered.append({
                    "id": pool.get('id'),
                    "chain": chain,
                    "project": attrs.get('name', '').split('/')[0] if '/' in attrs.get('name', '') else 'Unknown',
                    "symbol": attrs.get('name', ''),
                    "apy": round(estimated_apy, 2),
                    "tvl": reserve_usd,
                    "tvl_formatted": self._format_tvl(reserve_usd),
                    "stablecoin": False, # GeckoTerminal doesn't explicitly state stablecoin status
                    "pool_link": attrs.get('pool_url'),
                    "source": "geckoterminal",
                    "source_name": "GeckoTerminal",
                    "source_badge": "🦎",
                })
                
            return filtered[:20]  # Limit to top 20
    
    # ===========================================
    # WHALE MONITORING
    # ===========================================
    
    async def _monitor_whales(self):
        """Monitor whale wallet activity"""
        while self.is_running:
            try:
                for wallet in self.whale_wallets:
                    # Would use ethers/web3 to check recent transactions
                    # For MVP, this is a placeholder
                    pass
                    
            except Exception as e:
                logger.error(f"Whale monitoring failed: {e}")
            
            await asyncio.sleep(self.intervals["whales"])
    
    # ===========================================
    # DATA ANALYSIS HELPERS
    # ===========================================
    
    def _find_new_pools(self, new_pools: List[Dict]) -> List[Dict]:
        """Find pools that weren't in the previous cache"""
        if not self.cache["pools"]:
            return []
        
        cached_ids = {p.get("pool") for p in self.cache["pools"]}
        return [p for p in new_pools if p.get("pool") not in cached_ids]
    
    def _detect_apy_changes(self, new_pools: List[Dict]) -> List[Dict]:
        """Detect significant APY changes (>20%)"""
        changes = []
        
        if not self.cache["pools"]:
            return changes
        
        cached_map = {p.get("pool"): p for p in self.cache["pools"]}
        
        for pool in new_pools:
            pool_id = pool.get("pool")
            if pool_id in cached_map:
                old_apy = cached_map[pool_id].get("apy", 0)
                new_apy = pool.get("apy", 0)
                
                if old_apy > 0:
                    change_pct = ((new_apy - old_apy) / old_apy) * 100
                    if abs(change_pct) >= 20:
                        changes.append({
                            "pool": pool,
                            "old_apy": old_apy,
                            "new_apy": new_apy,
                            "change_pct": change_pct
                        })
        
        return changes
    
    def _is_single_sided_stable(self, pool: Dict) -> bool:
        """
        MVP Safety Filter: Only single-sided stablecoin pools
        
        Returns True if:
        - Pool is single-sided (supply/lending, not LP)
        - Asset is one of allowed stablecoins (USDC/USDT/DAI)
        - NOT an algorithmic stablecoin
        - Protocol is trusted
        """
        # 1. Must be single-sided (exposure = "single")
        exposure = pool.get("exposure", "").lower()
        if exposure != "single":
            return False
        
        # 2. Check symbol against whitelist
        symbol = pool.get("symbol", "").upper()
        if symbol not in self.allowed_stablecoins:
            return False
        
        # 3. Must NOT be algorithmic/risky stable
        for banned in self.banned_assets:
            if banned.upper() in symbol:
                logger.debug(f"Filtered out banned asset: {symbol}")
                return False
        
        # 4. Protocol must be trusted
        project = pool.get("project", "").lower()
        if project not in self.trusted_protocols:
            logger.debug(f"Filtered out untrusted protocol: {project}")
            return False
        
        # 5. Sanity check: TVL should exist
        if pool.get("tvlUsd", 0) < 10000:  # Min $10K TVL
            return False
        
        return True
    
    # ===========================================
    # API METHODS FOR OTHER AGENTS
    # ===========================================
    
    def get_pools(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Get cached pools with optional filtering"""
        pools = self.cache.get("pools", [])
        
        if not filters:
            return pools
        
        # Apply filters
        if filters.get("min_tvl"):
            pools = [p for p in pools if p.get("tvlUsd", 0) >= filters["min_tvl"]]
        if filters.get("min_apy"):
            pools = [p for p in pools if p.get("apy", 0) >= filters["min_apy"]]
        if filters.get("max_apy"):
            pools = [p for p in pools if p.get("apy", 0) <= filters["max_apy"]]
        if filters.get("stablecoin_only"):
            pools = [p for p in pools if p.get("stablecoin")]
        if filters.get("protocols"):
            pools = [p for p in pools if p.get("project") in filters["protocols"]]
        
        return pools
    
    def get_top_pools(self, limit: int = 20, sort_by: str = "apy") -> List[Dict]:
        """Get top pools sorted by metric"""
        pools = self.cache.get("pools", [])
        pools = [p for p in pools if p.get("apy", 0) > 0 and p.get("tvlUsd", 0) > 10000]
        
        pools.sort(key=lambda x: x.get(sort_by, 0), reverse=True)
        return pools[:limit]
    
    def get_cache_age(self) -> Optional[int]:
        """Get cache age in seconds"""
        if self.cache.get("last_update"):
            return int((datetime.now() - self.cache["last_update"]).total_seconds())
        return None


# Singleton instance
scout = ScoutAgent()
