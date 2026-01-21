"""
Aerodrome Sugar Contract Client
Uses LpSugar.byAddress() for fast single-call pool data including emissions.
Replaces 10+ slow RPC calls with 1 fast call.

Sugar Address (Base): 0x68c19e13618C41158fE4bAba1B8fb3A9c74bDb0A
"""

import logging
from typing import Dict, Any, Optional
from web3 import Web3

logger = logging.getLogger("AerodromeSugar")

# Sugar contract addresses by chain
SUGAR_ADDRESSES = {
    "base": "0x68c19e13618C41158fE4bAba1B8fb3A9c74bDb0A",
    "optimism": "0x28DcC3d6Fe59F0f8678f0e5EE3288D4d1D5c5102",  # Velodrome Sugar
}

# AERO token for price lookup
AERO_TOKEN = "0x940181a94A35A4569E4529A3CDfB74e38FD98631"

# LpSugar ABI - only byAddress function we need
LP_SUGAR_ABI = [
    {
        "inputs": [{"name": "_pool", "type": "address"}],
        "name": "byAddress",
        "outputs": [
            {
                "components": [
                    {"name": "lp", "type": "address"},
                    {"name": "symbol", "type": "string"},
                    {"name": "decimals", "type": "uint8"},
                    {"name": "liquidity", "type": "uint256"},
                    {"name": "type", "type": "int24"},
                    {"name": "tick", "type": "int24"},
                    {"name": "sqrt_ratio", "type": "uint160"},
                    {"name": "token0", "type": "address"},
                    {"name": "reserve0", "type": "uint256"},
                    {"name": "staked0", "type": "uint256"},
                    {"name": "token1", "type": "address"},
                    {"name": "reserve1", "type": "uint256"},
                    {"name": "staked1", "type": "uint256"},
                    {"name": "gauge", "type": "address"},
                    {"name": "gauge_liquidity", "type": "uint256"},
                    {"name": "gauge_alive", "type": "bool"},
                    {"name": "fee", "type": "address"},
                    {"name": "bribe", "type": "address"},
                    {"name": "factory", "type": "address"},
                    {"name": "emissions", "type": "uint256"},
                    {"name": "emissions_token", "type": "address"},
                    {"name": "emissions_cap", "type": "uint256"},
                    {"name": "pool_fee", "type": "uint256"},
                    {"name": "unstaked_fee", "type": "uint256"},
                    {"name": "token0_fees", "type": "uint256"},
                    {"name": "token1_fees", "type": "uint256"},
                    {"name": "locked", "type": "uint256"},
                    {"name": "emerging", "type": "bool"},
                    {"name": "created_at", "type": "uint256"},
                    {"name": "nfpm", "type": "address"},
                    {"name": "alm", "type": "address"},
                    {"name": "root", "type": "address"},
                ],
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# RPC endpoints
RPC_ENDPOINTS = {
    "base": "https://mainnet.base.org",
    "optimism": "https://mainnet.optimism.io",
}


class AerodromeSugar:
    """
    Fast APY data using Aerodrome Sugar contract.
    ONE RPC call instead of 10+.
    """
    
    def __init__(self):
        self._web3_cache: Dict[str, Web3] = {}
        self._aero_price_cache: Optional[float] = None
        self._aero_price_timestamp: float = 0
        logger.info("🍬 Aerodrome Sugar client initialized")
    
    def _get_web3(self, chain: str) -> Optional[Web3]:
        """Get cached Web3 instance"""
        if chain in self._web3_cache:
            return self._web3_cache[chain]
        
        rpc = RPC_ENDPOINTS.get(chain.lower())
        if not rpc:
            return None
            
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 10}))
            if w3.is_connected():
                self._web3_cache[chain] = w3
                return w3
        except Exception as e:
            logger.warning(f"RPC connection failed: {e}")
        
        return None
    
    async def get_pool_data_fast(self, pool_address: str, chain: str = "base") -> Optional[Dict[str, Any]]:
        """
        Get pool data via Sugar in ONE RPC call.
        Returns emissions, gauge info, staked amounts - everything needed for APY.
        """
        sugar_address = SUGAR_ADDRESSES.get(chain.lower())
        if not sugar_address:
            logger.warning(f"No Sugar contract for chain: {chain}")
            return None
        
        w3 = self._get_web3(chain)
        if not w3:
            return None
        
        try:
            pool_address = Web3.to_checksum_address(pool_address)
            sugar = w3.eth.contract(
                address=Web3.to_checksum_address(sugar_address),
                abi=LP_SUGAR_ABI
            )
            
            # ONE CALL for all data!
            lp_data = sugar.functions.byAddress(pool_address).call()
            
            # Parse tuple into dict
            result = {
                "lp": lp_data[0],
                "symbol": lp_data[1],
                "decimals": lp_data[2],
                "liquidity": lp_data[3],
                "pool_type": lp_data[4],  # tick spacing for CL, 0/-1 for V2
                "tick": lp_data[5],
                "token0": lp_data[7],
                "reserve0": lp_data[8],
                "staked0": lp_data[9],
                "token1": lp_data[10],
                "reserve1": lp_data[11],
                "staked1": lp_data[12],
                "gauge": lp_data[13],
                "gauge_liquidity": lp_data[14],
                "gauge_alive": lp_data[15],
                "factory": lp_data[18],
                "emissions": lp_data[19],  # Per second!
                "emissions_token": lp_data[20],
                "pool_fee": lp_data[22],
                "created_at": lp_data[28],
            }
            
            # Check if gauge exists and is alive
            has_gauge = result["gauge"] != "0x0000000000000000000000000000000000000000" and result["gauge_alive"]
            result["has_gauge"] = has_gauge
            
            # Determine pool type
            if result["pool_type"] >= 1:
                result["pool_type_name"] = "cl"  # Concentrated Liquidity
            elif result["pool_type"] == 0:
                result["pool_type_name"] = "stable"
            else:
                result["pool_type_name"] = "volatile"
            
            logger.info(f"🍬 Sugar data: {result['symbol']}, emissions={result['emissions']}/s, gauge_alive={has_gauge}")
            
            return result
            
        except Exception as e:
            logger.warning(f"Sugar call failed: {e}")
            return None
    
    async def calculate_apy_from_sugar(
        self, 
        pool_address: str, 
        chain: str = "base",
        tvl_usd: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate APY using Sugar data.
        
        Args:
            pool_address: Pool contract address
            chain: Chain name
            tvl_usd: Optional TVL from GeckoTerminal (more accurate)
        
        Returns:
            APY data with emissions info
        """
        sugar_data = await self.get_pool_data_fast(pool_address, chain)
        
        if not sugar_data:
            return {"apy_status": "error", "reason": "SUGAR_CALL_FAILED"}
        
        if not sugar_data["has_gauge"]:
            return {
                "apy_status": "unsupported",
                "reason": "NO_ACTIVE_GAUGE",
                "pool_type": sugar_data.get("pool_type_name"),
                "symbol": sugar_data.get("symbol"),
            }
        
        emissions_per_second = sugar_data["emissions"]
        if emissions_per_second == 0:
            return {
                "apy_status": "unavailable",
                "reason": "ZERO_EMISSIONS",
                "pool_type": sugar_data.get("pool_type_name"),
                "has_gauge": True,
            }
        
        # Get AERO price for APY calculation
        aero_price = await self._get_aero_price()
        if not aero_price:
            return {
                "apy_status": "requires_external_tvl",
                "reason": "AERO_PRICE_UNAVAILABLE",
                "emissions_per_second": emissions_per_second,
                "pool_type": sugar_data.get("pool_type_name"),
                "has_gauge": True,
            }
        
        # Calculate yearly emissions USD
        yearly_emissions = emissions_per_second * 86400 * 365 / 1e18  # AERO has 18 decimals
        yearly_rewards_usd = yearly_emissions * aero_price
        
        # Use provided TVL or need external source
        if not tvl_usd or tvl_usd <= 0:
            return {
                "apy_status": "requires_external_tvl",
                "reason": "NEED_TVL_FROM_GECKO",
                "yearly_rewards_usd": yearly_rewards_usd,
                "emissions_per_second": emissions_per_second,
                "aero_price": aero_price,
                "pool_type": sugar_data.get("pool_type_name"),
                "has_gauge": True,
                "gauge_address": sugar_data.get("gauge"),
            }
        
        # Calculate APY
        apy = (yearly_rewards_usd / tvl_usd) * 100 if tvl_usd > 0 else 0
        
        return {
            "apy_status": "ok",
            "apy": apy,
            "apy_reward": apy,
            "yearly_rewards_usd": yearly_rewards_usd,
            "tvl_usd": tvl_usd,
            "emissions_per_second": emissions_per_second,
            "aero_price": aero_price,
            "pool_type": sugar_data.get("pool_type_name"),
            "has_gauge": True,
            "gauge_address": sugar_data.get("gauge"),
            "symbol": sugar_data.get("symbol"),
            "source": "aerodrome_sugar",
        }
    
    async def _get_aero_price(self) -> Optional[float]:
        """Get AERO token price (cached 60s)"""
        import time
        
        # Check cache
        if self._aero_price_cache and (time.time() - self._aero_price_timestamp) < 60:
            return self._aero_price_cache
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                # Use GeckoTerminal for AERO price
                r = await client.get(
                    f"https://api.geckoterminal.com/api/v2/simple/networks/base/token_price/{AERO_TOKEN}"
                )
                if r.status_code == 200:
                    data = r.json()
                    price = float(data.get("data", {}).get("attributes", {}).get("token_prices", {}).get(AERO_TOKEN.lower(), 0))
                    if price > 0:
                        self._aero_price_cache = price
                        self._aero_price_timestamp = time.time()
                        logger.info(f"AERO price: ${price:.4f}")
                        return price
        except Exception as e:
            logger.debug(f"AERO price fetch failed: {e}")
        
        return self._aero_price_cache  # Return stale cache if available


# Global instance
sugar_client = AerodromeSugar()
