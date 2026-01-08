"""
UniversalScanner - Auto-Detection Pool/Vault Analyzer
Fingerprints contracts to identify type (CLAMM, V2, ERC4626, Lending) via method calls.
Works with ANY pool on supported chains without hardcoding protocols.
"""
import logging
from enum import Enum
from typing import Optional, Dict, Any, List
from web3 import Web3
import httpx

logger = logging.getLogger("UniversalScanner")


class ContractType(Enum):
    """Detected contract types based on fingerprinting"""
    CLAMM = "clamm"                       # Uniswap V3 / Slipstream / Concentrated Liquidity
    V2_LP = "v2_lp"                       # Uniswap V2 / Aerodrome V2 / SushiSwap
    ERC4626 = "erc4626"                   # ERC-4626 Vaults (Yearn, Beefy, etc.)
    LENDING = "lending"                   # Compound/Aave style lending
    GENERIC_TOKEN_HOLDER = "generic"      # Unknown - just check ERC20 balances


# =============================================================================
# FINGERPRINT ABIS - Minimal ABIs for contract type detection
# =============================================================================

# CLAMM (V3-style) detection
SLOT0_ABI = [{
    "inputs": [],
    "name": "slot0",
    "outputs": [
        {"name": "sqrtPriceX96", "type": "uint160"},
        {"name": "tick", "type": "int24"},
        {"name": "observationIndex", "type": "uint16"},
        {"name": "observationCardinality", "type": "uint16"},
        {"name": "observationCardinalityNext", "type": "uint16"},
        {"name": "feeProtocol", "type": "uint8"},
        {"name": "unlocked", "type": "bool"}
    ],
    "stateMutability": "view",
    "type": "function"
}]

# V2 LP detection
GET_RESERVES_ABI = [{
    "constant": True,
    "inputs": [],
    "name": "getReserves",
    "outputs": [
        {"name": "reserve0", "type": "uint112"},
        {"name": "reserve1", "type": "uint112"},
        {"name": "blockTimestampLast", "type": "uint32"}
    ],
    "type": "function"
}]

# ERC-4626 Vault detection
ERC4626_ABI = [
    {"inputs": [], "name": "asset", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalAssets", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
]

# Lending protocol detection
LENDING_ABI = [
    {"inputs": [], "name": "underlying", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "exchangeRateStored", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
]

# Common token ABI
ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"type": "uint256"}], "type": "function"},
]

# Pool common ABI
POOL_COMMON_ABI = [
    {"constant": True, "inputs": [], "name": "token0", "outputs": [{"type": "address"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "token1", "outputs": [{"type": "address"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "fee", "outputs": [{"type": "uint24"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "liquidity", "outputs": [{"type": "uint128"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "stable", "outputs": [{"type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}], "type": "function"},
]

# RPC endpoints by chain
RPC_ENDPOINTS = {
    "base": ["https://mainnet.base.org", "https://base.llamarpc.com"],
    "ethereum": ["https://eth.llamarpc.com", "https://rpc.ankr.com/eth"],
    "arbitrum": ["https://arb1.arbitrum.io/rpc", "https://arbitrum.llamarpc.com"],
    "optimism": ["https://mainnet.optimism.io", "https://optimism.llamarpc.com"],
    "polygon": ["https://polygon.llamarpc.com", "https://polygon-rpc.com"],
}

# Known stablecoins by chain
STABLECOINS = {
    "base": {
        "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": ("USDC", 6),
        "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca": ("USDbC", 6),
        "0x50c5725949a6f0c72e6c4a641f24049a917db0cb": ("DAI", 18),
    },
    "ethereum": {
        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": ("USDC", 6),
        "0xdac17f958d2ee523a2206206994597c13d831ec7": ("USDT", 6),
        "0x6b175474e89094c44da98b954eedeac495271d0f": ("DAI", 18),
    }
}


class UniversalScanner:
    """
    Universal contract scanner that auto-detects pool/vault types.
    Uses "fingerprinting" by trying to call specific view functions.
    """
    
    def __init__(self):
        self.web3_cache: Dict[str, Web3] = {}
        logger.info("🔍 UniversalScanner initialized")
    
    def _get_web3(self, chain: str) -> Optional[Web3]:
        """Get Web3 instance for chain with caching"""
        chain = chain.lower()
        
        if chain in self.web3_cache:
            return self.web3_cache[chain]
        
        endpoints = RPC_ENDPOINTS.get(chain, [])
        for endpoint in endpoints:
            try:
                w3 = Web3(Web3.HTTPProvider(endpoint, request_kwargs={'timeout': 10}))
                if w3.is_connected():
                    self.web3_cache[chain] = w3
                    return w3
            except Exception as e:
                logger.debug(f"RPC {endpoint} failed: {e}")
        
        return None
    
    # =========================================================================
    # FINGERPRINTING - Contract Type Detection
    # =========================================================================
    
    async def identify_contract_type(self, address: str, chain: str = "base") -> ContractType:
        """
        Identify contract type by trying to call fingerprint methods.
        Returns the detected ContractType.
        """
        w3 = self._get_web3(chain)
        if not w3:
            logger.warning(f"No RPC for chain {chain}")
            return ContractType.GENERIC_TOKEN_HOLDER
        
        address = Web3.to_checksum_address(address)
        
        # Check 1: CLAMM (slot0)
        if self._try_call(w3, address, "slot0", SLOT0_ABI):
            logger.info(f"🔍 Detected CLAMM (V3-style): {address[:10]}...")
            return ContractType.CLAMM
        
        # Check 2: V2 LP (getReserves)
        if self._try_call(w3, address, "getReserves", GET_RESERVES_ABI):
            logger.info(f"🔍 Detected V2 LP: {address[:10]}...")
            return ContractType.V2_LP
        
        # Check 3: ERC-4626 (asset)
        if self._try_call(w3, address, "asset", ERC4626_ABI):
            logger.info(f"🔍 Detected ERC4626 Vault: {address[:10]}...")
            return ContractType.ERC4626
        
        # Check 4: Lending (underlying)
        if self._try_call(w3, address, "underlying", LENDING_ABI):
            logger.info(f"🔍 Detected Lending Protocol: {address[:10]}...")
            return ContractType.LENDING
        
        # Fallback: Generic token holder
        logger.info(f"🔍 Unknown contract type, treating as GENERIC: {address[:10]}...")
        return ContractType.GENERIC_TOKEN_HOLDER
    
    def _try_call(self, w3: Web3, address: str, method: str, abi: list) -> bool:
        """Try to call a method on a contract. Returns True if successful."""
        try:
            contract = w3.eth.contract(address=address, abi=abi)
            func = getattr(contract.functions, method)
            func().call()
            return True
        except Exception:
            return False
    
    # =========================================================================
    # MAIN SCAN METHOD
    # =========================================================================
    
    async def scan(self, address: str, chain: str = "base") -> Optional[Dict[str, Any]]:
        """
        Main entry point: Scan any contract address and return standardized pool data.
        
        Returns dict compatible with frontend modals:
        {
            "symbol": "TOKEN0/TOKEN1",
            "project": "Unknown Protocol",
            "chain": "Base",
            "tvl": 1234567.89,
            "apy": 0,
            "contract_type": "v2_lp",
            "pool_address": "0x...",
            ...
        }
        """
        try:
            contract_type = await self.identify_contract_type(address, chain)
            return await self.get_pool_details(address, chain, contract_type)
        except Exception as e:
            logger.error(f"Scan failed for {address}: {e}")
            return None
    
    async def get_pool_details(
        self, 
        address: str, 
        chain: str, 
        contract_type: ContractType
    ) -> Optional[Dict[str, Any]]:
        """Extract pool details based on detected contract type."""
        
        if contract_type == ContractType.CLAMM:
            return await self._extract_clamm(address, chain)
        elif contract_type == ContractType.V2_LP:
            return await self._extract_v2_lp(address, chain)
        elif contract_type == ContractType.ERC4626:
            return await self._extract_erc4626(address, chain)
        elif contract_type == ContractType.LENDING:
            return await self._extract_lending(address, chain)
        else:
            return await self._extract_generic(address, chain)
    
    # =========================================================================
    # EXTRACTION METHODS BY TYPE
    # =========================================================================
    
    async def _extract_clamm(self, address: str, chain: str) -> Optional[Dict[str, Any]]:
        """Extract data from CLAMM (V3-style) pool"""
        try:
            w3 = self._get_web3(chain)
            address = Web3.to_checksum_address(address)
            
            # Use separate contracts to avoid ABI conflicts
            slot0_contract = w3.eth.contract(address=address, abi=SLOT0_ABI)
            pool_contract = w3.eth.contract(address=address, abi=POOL_COMMON_ABI)
            
            # Get slot0 data
            slot0 = slot0_contract.functions.slot0().call()
            sqrt_price_x96 = slot0[0]
            tick = slot0[1]
            
            # Get tokens
            token0 = pool_contract.functions.token0().call()
            token1 = pool_contract.functions.token1().call()
            
            # Get fee (might fail on some pools)
            try:
                fee = pool_contract.functions.fee().call()
                fee_percent = fee / 10000
            except:
                fee_percent = 0.3  # Default
            
            # Get liquidity
            try:
                liquidity = pool_contract.functions.liquidity().call()
            except:
                liquidity = 0
            
            # Get token info
            token0_info = await self._get_token_info(w3, token0)
            token1_info = await self._get_token_info(w3, token1)
            
            # Calculate price from sqrtPriceX96
            price = (sqrt_price_x96 / (2 ** 96)) ** 2
            
            # Get token prices
            price0 = await self._get_token_price(token0, chain)
            price1 = await self._get_token_price(token1, chain)
            
            # Estimate TVL from liquidity (simplified)
            # Real TVL calculation for V3 is complex, this is an approximation
            tvl = (liquidity / 1e18) * ((price0 + price1) / 2) if liquidity > 0 else 0
            
            return {
                "symbol": f"{token0_info['symbol']}-{token1_info['symbol']} {fee_percent}%",
                "name": f"{token0_info['symbol']} / {token1_info['symbol']}",
                "project": "Unknown DEX (CLAMM)",
                "chain": chain.capitalize(),
                "tvl": tvl,
                "tvlUsd": tvl,
                "apy": 0,
                "pool_type": "concentrated",
                "contract_type": ContractType.CLAMM.value,
                "pool_address": address.lower(),
                "token0": token0.lower(),
                "token1": token1.lower(),
                "symbol0": token0_info['symbol'],
                "symbol1": token1_info['symbol'],
                "fee": fee_percent,
                "liquidity": liquidity,
                "sqrt_price_x96": sqrt_price_x96,
                "tick": tick,
                "source": "universal_scanner"
            }
            
        except Exception as e:
            logger.error(f"CLAMM extraction failed: {e}")
            return None
    
    async def _extract_v2_lp(self, address: str, chain: str) -> Optional[Dict[str, Any]]:
        """Extract data from V2-style LP pool"""
        try:
            w3 = self._get_web3(chain)
            address = Web3.to_checksum_address(address)
            
            # Use separate contracts to avoid ABI conflicts
            reserves_contract = w3.eth.contract(address=address, abi=GET_RESERVES_ABI)
            pool_contract = w3.eth.contract(address=address, abi=POOL_COMMON_ABI)
            
            # Get reserves
            reserves = reserves_contract.functions.getReserves().call()
            reserve0_raw = reserves[0]
            reserve1_raw = reserves[1]
            
            # Get tokens
            token0 = pool_contract.functions.token0().call()
            token1 = pool_contract.functions.token1().call()
            
            # Get token info
            token0_info = await self._get_token_info(w3, token0)
            token1_info = await self._get_token_info(w3, token1)
            
            # Convert reserves
            reserve0 = reserve0_raw / (10 ** token0_info['decimals'])
            reserve1 = reserve1_raw / (10 ** token1_info['decimals'])
            
            # Get pool type (stable/volatile)
            try:
                stable = pool_contract.functions.stable().call()
            except:
                stable = False
            
            # Get pool symbol
            try:
                pool_symbol = pool_contract.functions.symbol().call()
            except:
                pool_symbol = f"{token0_info['symbol']}-{token1_info['symbol']} LP"
            
            # Get token prices and calculate TVL
            price0 = await self._get_token_price(token0, chain)
            price1 = await self._get_token_price(token1, chain)
            tvl = (reserve0 * price0) + (reserve1 * price1)
            
            return {
                "symbol": f"{token0_info['symbol']}/{token1_info['symbol']}",
                "name": pool_symbol,
                "project": "Unknown DEX (V2)",
                "chain": chain.capitalize(),
                "tvl": tvl,
                "tvlUsd": tvl,
                "apy": 0,
                "pool_type": "stable" if stable else "volatile",
                "contract_type": ContractType.V2_LP.value,
                "pool_address": address.lower(),
                "token0": token0.lower(),
                "token1": token1.lower(),
                "symbol0": token0_info['symbol'],
                "symbol1": token1_info['symbol'],
                "decimals0": token0_info['decimals'],
                "decimals1": token1_info['decimals'],
                "reserve0": reserve0,
                "reserve1": reserve1,
                "stable": stable,
                "source": "universal_scanner"
            }
            
        except Exception as e:
            logger.error(f"V2 LP extraction failed: {e}")
            return None
    
    async def _extract_erc4626(self, address: str, chain: str) -> Optional[Dict[str, Any]]:
        """Extract data from ERC-4626 vault"""
        try:
            w3 = self._get_web3(chain)
            address = Web3.to_checksum_address(address)
            
            # Vault ABI
            abi = ERC4626_ABI + ERC20_ABI
            vault = w3.eth.contract(address=address, abi=abi)
            
            # Get underlying asset
            asset = vault.functions.asset().call()
            
            # Get total assets
            total_assets = vault.functions.totalAssets().call()
            
            # Get vault info
            try:
                vault_symbol = vault.functions.symbol().call()
            except:
                vault_symbol = "Vault"
            
            try:
                vault_name = vault.functions.name().call()
            except:
                vault_name = "Unknown Vault"
            
            # Get asset info
            asset_info = await self._get_token_info(w3, asset)
            
            # Convert total assets
            total_assets_human = total_assets / (10 ** asset_info['decimals'])
            
            # Get asset price and calculate TVL
            asset_price = await self._get_token_price(asset, chain)
            tvl = total_assets_human * asset_price
            
            return {
                "symbol": vault_symbol,
                "name": vault_name,
                "project": "Unknown Vault",
                "chain": chain.capitalize(),
                "tvl": tvl,
                "tvlUsd": tvl,
                "apy": 0,
                "pool_type": "vault",
                "contract_type": ContractType.ERC4626.value,
                "pool_address": address.lower(),
                "underlying_asset": asset.lower(),
                "underlying_symbol": asset_info['symbol'],
                "underlying_decimals": asset_info['decimals'],
                "total_assets": total_assets_human,
                "source": "universal_scanner"
            }
            
        except Exception as e:
            logger.error(f"ERC4626 extraction failed: {e}")
            return None
    
    async def _extract_lending(self, address: str, chain: str) -> Optional[Dict[str, Any]]:
        """Extract data from lending protocol (cToken style)"""
        try:
            w3 = self._get_web3(chain)
            address = Web3.to_checksum_address(address)
            
            # Lending ABI
            abi = LENDING_ABI + ERC20_ABI
            market = w3.eth.contract(address=address, abi=abi)
            
            # Get underlying
            underlying = market.functions.underlying().call()
            
            # Get supply info
            total_supply = market.functions.totalSupply().call()
            
            # Get exchange rate
            try:
                exchange_rate = market.functions.exchangeRateStored().call()
                exchange_rate_human = exchange_rate / 1e18
            except:
                exchange_rate_human = 1
            
            # Get market info
            try:
                market_symbol = market.functions.symbol().call()
            except:
                market_symbol = "cToken"
            
            try:
                market_name = market.functions.name().call()
            except:
                market_name = "Lending Market"
            
            # Get underlying info
            underlying_info = await self._get_token_info(w3, underlying)
            
            # Calculate TVL
            underlying_decimals = underlying_info['decimals']
            total_underlying = (total_supply / 1e8) * exchange_rate_human  # cTokens have 8 decimals
            
            underlying_price = await self._get_token_price(underlying, chain)
            tvl = total_underlying * underlying_price
            
            return {
                "symbol": market_symbol,
                "name": market_name,
                "project": "Unknown Lending",
                "chain": chain.capitalize(),
                "tvl": tvl,
                "tvlUsd": tvl,
                "apy": 0,
                "pool_type": "lending",
                "contract_type": ContractType.LENDING.value,
                "pool_address": address.lower(),
                "underlying_asset": underlying.lower(),
                "underlying_symbol": underlying_info['symbol'],
                "total_supply": total_supply,
                "exchange_rate": exchange_rate_human,
                "source": "universal_scanner"
            }
            
        except Exception as e:
            logger.error(f"Lending extraction failed: {e}")
            return None
    
    async def _extract_generic(self, address: str, chain: str) -> Optional[Dict[str, Any]]:
        """Fallback: Extract basic info as generic token holder"""
        try:
            w3 = self._get_web3(chain)
            address = Web3.to_checksum_address(address)
            
            contract = w3.eth.contract(address=address, abi=ERC20_ABI)
            
            # Try to get basic info
            try:
                symbol = contract.functions.symbol().call()
            except:
                symbol = "UNKNOWN"
            
            try:
                name = contract.functions.name().call()
            except:
                name = "Unknown Contract"
            
            try:
                total_supply = contract.functions.totalSupply().call()
            except:
                total_supply = 0
            
            return {
                "symbol": symbol,
                "name": name,
                "project": "Unknown",
                "chain": chain.capitalize(),
                "tvl": 0,
                "tvlUsd": 0,
                "apy": 0,
                "pool_type": "unknown",
                "contract_type": ContractType.GENERIC_TOKEN_HOLDER.value,
                "pool_address": address.lower(),
                "total_supply": total_supply,
                "source": "universal_scanner"
            }
            
        except Exception as e:
            logger.error(f"Generic extraction failed: {e}")
            return None
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    async def _get_token_info(self, w3: Web3, token_address: str) -> Dict[str, Any]:
        """Get token symbol and decimals"""
        try:
            token_address = Web3.to_checksum_address(token_address)
            contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)
            
            symbol = contract.functions.symbol().call()
            decimals = contract.functions.decimals().call()
            
            return {"symbol": symbol, "decimals": decimals}
        except Exception as e:
            logger.debug(f"Token info failed for {token_address[:10]}: {e}")
            return {"symbol": "???", "decimals": 18}
    
    async def _get_token_price(self, token_address: str, chain: str) -> float:
        """Get token price in USD"""
        token_address = token_address.lower()
        
        # Check stablecoins first
        chain_stables = STABLECOINS.get(chain.lower(), {})
        if token_address in chain_stables:
            return 1.0
        
        # Try CoinGecko
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"https://api.coingecko.com/api/v3/simple/token_price/{chain}",
                    params={"contract_addresses": token_address, "vs_currencies": "usd"}
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get(token_address, {}).get("usd", 0)
        except Exception as e:
            logger.debug(f"Price fetch failed: {e}")
        
        return 0


# Singleton instance
universal_scanner = UniversalScanner()
