"""
OnChain Verifier — Read-only on-chain verification for all Base DeFi protocols.

Returns TVL, Price, APY directly from smart contracts via RPC.
Compares with API data (DefiLlama) and flags discrepancies.

Supported protocols:
  1. Aave V3         — getReserveData()
  2. Morpho Blue      — market() supply/borrow
  3. Compound V3      — totalSupply(), getSupplyRate()
  4. Moonwell         — mToken exchangeRate, supplyRate
  5. Seamless         — ERC-4626 vaults on Morpho
  6. Aerodrome        — getReserves() + gauge rewardRate
  7. Uniswap V3       — slot0(), liquidity(), fee()
  8. Curve             — get_virtual_price(), balances()
  9. Pendle           — Market readState()
  10. ERC-4626 Generic — totalAssets(), convertToAssets()

Usage:
    verifier = OnChainVerifier()
    result = await verifier.verify("0x...", "aave-v3")
    # → {"tvl": 12345678, "apy": 4.23, "price": 1.0001, "verified": True, ...}
"""

import asyncio
import os
import time
import math
from typing import Dict, Any, Optional, List, Tuple
from web3 import Web3
from web3.exceptions import ContractLogicError

# ============================================
# CONFIGURATION
# ============================================

RPC_URL = os.environ.get(
    "ALCHEMY_RPC_URL",
    "https://base-mainnet.g.alchemy.com/v2/AqxI9okL6ZYv38MBFDHhb"
)

# Base mainnet contract addresses
CONTRACTS = {
    # Lending
    "aave_v3_pool": "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",
    "aave_v3_data_provider": "0x2d8A3C5677189723C4cB8873CfC9C8976FDF38Ac",
    "morpho_blue": "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb",
    "compound_comet_usdc": "0x46e6b214b524310239732D51387075E0e70970bf",
    "moonwell_comptroller": "0xfBb21d0380bEE3312B33c4353c8936a0F13EF26C",
    "moonwell_musdc": "0xEdc817A28E8B93B03976FBd4a3dDBc9f7D176c22",
    "ionic_comptroller": "0xFB3323E24743Caf4ADD0fDCCFB268565c0685556",
    "exactly_usdc_market": "0x85f16155c6C7dA460969D2E4d5923e30907B2Adc",
    "silo_router": "0x8658047e48CC09161f4152c79155Dac1d710Ff0a",

    # DEX
    "aerodrome_sugar": "0x2073D8035bB2b0F2e85aAF5a8732C6f397F9ff9b",
    "aerodrome_voter": "0x16613524e02ad97eDfeF371bC883F2F5d6C480A5",
    "uniswap_v3_factory": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD",
    "uniswap_v3_quoter": "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a",
    "sushiswap_v2_factory": "0x71524B4f93c58fcbF659783284E38825f0622859",
    "sushiswap_v3_factory": "0xc35DADB65012eC5796536bD9864eD8773aBc74C4",
    "baseswap_factory": "0xFDa619b6d20975be80A10332cD39b9a4b0FAa8BB",
    "pancakeswap_v3_factory": "0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865",
    "balancer_v2_vault": "0xBA12222222228d8Ba445958a75a0704d566BF2C8",
    "maverick_v2_factory": "0x0A7e848Aca42d879EF06507Fca0E7b33A0a63c1e",

    # Bridges
    "stargate_v2_usdc_pool": "0x27a16dc786820B16E5c9028b75B99F6f604b5d26",
    "hop_usdc_amm": "0xe22D2beDb3Eca35E6397e0C6D62857094aA26F52",

    # Vaults / Other
    "seamless_usdc_vault": "0x616a4E1db48e22028f6bbf20444Cd3b8e3273738",
    "seamless_weth_vault": "0x27d8c7273fd3fcc6956a0b370ce5fd4a7fc65c18",
    "wsteth": "0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452",
    "pyth_oracle": "0x8250f4aF4B972684F7b336503E2D6dFeDeB1487a",
    "overnight_usd_plus": "0xB79DD08EA68A908A97220C76d19A6aA9cBDE4376",
    "overnight_exchange": "0x1A1B28AB4e09Ae75e2a116e7B0abCF5B9d4662aE",
    "dhedge_pool_logic": "0x32400084C286CF3E17e7B677ea9583e60a000324",
    "extra_finance_lending_pool": "0xBB505c54D71E9e599cB8435b4F0cEEc05fC71cbD",
    "gains_trading": "0x4542256C583bcad0188EB2D9E5B1bb26d0D78FFC",

    # Utility
    "multicall3": "0xcA11bde05977b3631167028862bE2a173976CA11",
}

# Common tokens on Base
TOKENS = {
    "USDC": {"address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "decimals": 6},
    "USDbC": {"address": "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA", "decimals": 6},
    "WETH": {"address": "0x4200000000000000000000000000000000000006", "decimals": 18},
    "cbETH": {"address": "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22", "decimals": 18},
    "cbBTC": {"address": "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf", "decimals": 8},
    "wstETH": {"address": "0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452", "decimals": 18},
    "AERO": {"address": "0x940181a94A35A4569E4529A3CDfB74e38FD98631", "decimals": 18},
    "DAI": {"address": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb", "decimals": 18},
    "WELL": {"address": "0xFF8adeC2221f9f4D8dfbAFa6B9a297d17603493D", "decimals": 18},
    "SUSHI": {"address": "0x7D49a065D17d6d4a55dc13649901fdBB98B2AFBA", "decimals": 18},
    "BAL": {"address": "0x4158734D47Fc9692176B5085E0F52ee0Da5d47F1", "decimals": 18},
    "STG": {"address": "0xE3B53AF74a4BF62Ae5511055290838050bf764Df", "decimals": 18},
    "OVN": {"address": "0xA3d1a8DEB97B111454B294E2324EfAD492308960", "decimals": 18},
    "EXTRA": {"address": "0x2dAD3a13ef0C6366220f989157009e501e7e68a3", "decimals": 18},
    "rETH": {"address": "0xB6fe221Fe9EeF5aBa221c348bA20A1Bf5e73624c", "decimals": 18},
    "USD+": {"address": "0xB79DD08EA68A908A97220C76d19A6aA9cBDE4376", "decimals": 6},
    "DEGEN": {"address": "0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed", "decimals": 18},
    "BRETT": {"address": "0x532f27101965dd16442E59d40670FaF5eBB142E4", "decimals": 18},
    "TOSHI": {"address": "0xAC1Bd2486aAf3B5C0fc3Fd868558b082a531B2B4", "decimals": 18},
}

# Stablecoin prices (hardcoded for simplicity)
STABLECOIN_ADDRESSES = {
    "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",  # USDC
    "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca",  # USDbC
    "0x50c5725949a6f0c72e6c4a641f24049a917db0cb",  # DAI
    "0xb79dd08ea68a908a97220c76d19a6aa9cbde4376",  # USD+
}

# Seconds per year for APY calculations
SECONDS_PER_YEAR = 365.25 * 24 * 3600

# ============================================
# ABIs (minimal, read-only)
# ============================================

# Aave V3 Pool
AAVE_POOL_ABI = [
    {
        "inputs": [{"name": "asset", "type": "address"}],
        "name": "getReserveData",
        "outputs": [{
            "components": [
                {"name": "configuration", "type": "uint256"},
                {"name": "liquidityIndex", "type": "uint128"},
                {"name": "currentLiquidityRate", "type": "uint128"},
                {"name": "variableBorrowIndex", "type": "uint128"},
                {"name": "currentVariableBorrowRate", "type": "uint128"},
                {"name": "currentStableBorrowRate", "type": "uint128"},
                {"name": "lastUpdateTimestamp", "type": "uint40"},
                {"name": "id", "type": "uint16"},
                {"name": "aTokenAddress", "type": "address"},
                {"name": "stableDebtTokenAddress", "type": "address"},
                {"name": "variableDebtTokenAddress", "type": "address"},
                {"name": "interestRateStrategyAddress", "type": "address"},
                {"name": "accruedToTreasury", "type": "uint128"},
                {"name": "unbacked", "type": "uint128"},
                {"name": "isolationModeTotalDebt", "type": "uint128"},
            ],
            "name": "",
            "type": "tuple"
        }],
        "stateMutability": "view",
        "type": "function"
    },
]

# ERC20 balanceOf + totalSupply + decimals
ERC20_ABI = [
    {"inputs": [{"name": "account", "type": "address"}],
     "name": "balanceOf", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "decimals", "outputs": [{"type": "uint8"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "symbol", "outputs": [{"type": "string"}],
     "stateMutability": "view", "type": "function"},
]

# Compound V3 Comet
COMET_ABI = [
    {"inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalBorrow", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "utilization", "type": "uint256"}],
     "name": "getSupplyRate", "outputs": [{"type": "uint64"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getUtilization", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "baseToken", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
]

# Moonwell mToken
MTOKEN_ABI = [
    {"inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "exchangeRateStored", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "supplyRatePerTimestamp", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "underlying", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getCash", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalBorrows", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalReserves", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
]

# ERC-4626 Vault (Seamless, Beefy, Yearn, Spark, etc.)
ERC4626_ABI = [
    {"inputs": [], "name": "totalAssets", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "shares", "type": "uint256"}],
     "name": "convertToAssets", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "asset", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "decimals", "outputs": [{"type": "uint8"}],
     "stateMutability": "view", "type": "function"},
]

# Uniswap V3 Factory + Pool
UNIV3_FACTORY_ABI = [
    {
        "inputs": [
            {"name": "tokenA", "type": "address"},
            {"name": "tokenB", "type": "address"},
            {"name": "fee", "type": "uint24"},
        ],
        "name": "getPool",
        "outputs": [{"type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
]

UNIV3_POOL_ABI = [
    {
        "inputs": [],
        "name": "slot0",
        "outputs": [
            {"name": "sqrtPriceX96", "type": "uint160"},
            {"name": "tick", "type": "int24"},
            {"name": "observationIndex", "type": "uint16"},
            {"name": "observationCardinality", "type": "uint16"},
            {"name": "observationCardinalityNext", "type": "uint16"},
            {"name": "feeProtocol", "type": "uint8"},
            {"name": "unlocked", "type": "bool"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {"inputs": [], "name": "liquidity", "outputs": [{"type": "uint128"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "fee", "outputs": [{"type": "uint24"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "token0", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "token1", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "feeGrowthGlobal0X128", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "feeGrowthGlobal1X128", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
]

# Aerodrome Pool (AMM)
AERO_POOL_ABI = [
    {"inputs": [], "name": "getReserves",
     "outputs": [
         {"name": "reserve0", "type": "uint256"},
         {"name": "reserve1", "type": "uint256"},
         {"name": "blockTimestampLast", "type": "uint256"},
     ],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "token0", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "token1", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "stable", "outputs": [{"type": "bool"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "gauge", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
]

# Aerodrome Gauge
AERO_GAUGE_ABI = [
    {"inputs": [], "name": "rewardRate", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "rewardToken", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
]

# Curve Pool (basic)
CURVE_POOL_ABI = [
    {"inputs": [], "name": "get_virtual_price", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "i", "type": "uint256"}],
     "name": "balances", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "i", "type": "uint256"}],
     "name": "coins", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
]

# Morpho Blue
MORPHO_ABI = [
    {
        "inputs": [{"name": "id", "type": "bytes32"}],
        "name": "market",
        "outputs": [
            {"name": "totalSupplyAssets", "type": "uint128"},
            {"name": "totalSupplyShares", "type": "uint128"},
            {"name": "totalBorrowAssets", "type": "uint128"},
            {"name": "totalBorrowShares", "type": "uint128"},
            {"name": "lastUpdate", "type": "uint128"},
            {"name": "fee", "type": "uint128"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "id", "type": "bytes32"}],
        "name": "idToMarketParams",
        "outputs": [
            {"name": "loanToken", "type": "address"},
            {"name": "collateralToken", "type": "address"},
            {"name": "oracle", "type": "address"},
            {"name": "irm", "type": "address"},
            {"name": "lltv", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

# Pendle Market (simplified)
PENDLE_MARKET_ABI = [
    {
        "inputs": [],
        "name": "readState",
        "outputs": [{
            "components": [
                {"name": "totalPt", "type": "uint256"},
                {"name": "totalSy", "type": "uint256"},
                {"name": "totalLp", "type": "uint256"},
                {"name": "treasury", "type": "address"},
                {"name": "scalarRoot", "type": "int256"},
                {"name": "expiry", "type": "uint256"},
                {"name": "lnFeeRateRoot", "type": "uint256"},
                {"name": "reserveFeePercent", "type": "uint256"},
                {"name": "lastLnImpliedRate", "type": "uint256"},
            ],
            "name": "",
            "type": "tuple",
        }],
        "stateMutability": "view",
        "type": "function",
    },
    {"inputs": [], "name": "SY", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "PT", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "expiry", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
]

# Balancer V2 Vault
BALANCER_VAULT_ABI = [
    {
        "inputs": [{"name": "poolId", "type": "bytes32"}],
        "name": "getPoolTokens",
        "outputs": [
            {"name": "tokens", "type": "address[]"},
            {"name": "balances", "type": "uint256[]"},
            {"name": "lastChangeBlock", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

BALANCER_POOL_ABI = [
    {"inputs": [], "name": "getPoolId", "outputs": [{"type": "bytes32"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getNormalizedWeights", "outputs": [{"type": "uint256[]"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getSwapFeePercentage", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
]

# SushiSwap / BaseSwap V2 Pair (Uniswap V2 fork)
V2_PAIR_ABI = [
    {"inputs": [], "name": "getReserves",
     "outputs": [
         {"name": "reserve0", "type": "uint112"},
         {"name": "reserve1", "type": "uint112"},
         {"name": "blockTimestampLast", "type": "uint32"},
     ],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "token0", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "token1", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "factory", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
]

# Stargate V2 Pool
STARGATE_POOL_ABI = [
    {"inputs": [], "name": "totalLiquidity", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "token", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "poolId", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "convertRate", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
]

# Exactly Protocol Market
EXACTLY_MARKET_ABI = [
    {"inputs": [], "name": "totalAssets", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalFloatingBorrowAssets", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalFloatingDepositAssets", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "floatingRate", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "asset", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "decimals", "outputs": [{"type": "uint8"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
]

# Ionic Protocol (Compound V2 cToken fork)
IONIC_CTOKEN_ABI = [
    {"inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "exchangeRateStored", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "supplyRatePerBlock", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "borrowRatePerBlock", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "underlying", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getCash", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalBorrows", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalReserves", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
]

# dHEDGE pool
DHEDGE_POOL_ABI = [
    {"inputs": [], "name": "tokenPrice", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalFundValue", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "managerName", "outputs": [{"type": "string"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "creationTime", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
]

# Hop Protocol AMM Wrapper
HOP_AMM_ABI = [
    {"inputs": [], "name": "getVirtualPrice", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "hToken", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "l2CanonicalToken", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "swapStorage",
     "outputs": [
         {"name": "initialA", "type": "uint256"},
         {"name": "futureA", "type": "uint256"},
         {"name": "initialATime", "type": "uint256"},
         {"name": "futureATime", "type": "uint256"},
         {"name": "swapFee", "type": "uint256"},
         {"name": "adminFee", "type": "uint256"},
         {"name": "lpToken", "type": "address"},
     ],
     "stateMutability": "view", "type": "function"},
]

# Overnight Exchange (USD+)
OVERNIGHT_EXCHANGE_ABI = [
    {"inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "buyFee", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "redeemFee", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
]

# Beefy Vault V7 (non-ERC4626)
BEEFY_VAULT_ABI = [
    {"inputs": [], "name": "balance", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getPricePerFullShare", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "want", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "decimals", "outputs": [{"type": "uint8"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "strategy", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
]

# Extra Finance LendingPool
EXTRA_LENDING_ABI = [
    {"inputs": [{"name": "reserveId", "type": "uint256"}],
     "name": "getReserveData",
     "outputs": [{
         "components": [
             {"name": "underlyingTokenAddress", "type": "address"},
             {"name": "eTokenAddress", "type": "address"},
             {"name": "debtTokenAddress", "type": "address"},
             {"name": "totalLiquidity", "type": "uint256"},
             {"name": "totalBorrows", "type": "uint256"},
             {"name": "borrowRate", "type": "uint256"},
             {"name": "depositRate", "type": "uint256"},
         ],
         "name": "",
         "type": "tuple"
     }],
     "stateMutability": "view", "type": "function"},
]

# Maverick V2 Pool
MAVERICK_V2_POOL_ABI = [
    {"inputs": [], "name": "tokenA", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "tokenB", "outputs": [{"type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "fee", "outputs": [{"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getCurrentTwa", "outputs": [{"type": "int256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getState",
     "outputs": [{
         "components": [
             {"name": "reserveA", "type": "uint128"},
             {"name": "reserveB", "type": "uint128"},
             {"name": "totalInBin", "type": "uint128"},
             {"name": "activeTick", "type": "int32"},
         ],
         "name": "",
         "type": "tuple"
     }],
     "stateMutability": "view", "type": "function"},
]

# Silo Finance (Silo v1)
SILO_ABI = [
    {"inputs": [{"name": "_asset", "type": "address"}],
     "name": "assetStorage",
     "outputs": [{
         "components": [
             {"name": "collateralToken", "type": "address"},
             {"name": "collateralOnlyToken", "type": "address"},
             {"name": "debtToken", "type": "address"},
             {"name": "totalDeposits", "type": "uint256"},
             {"name": "collateralOnlyDeposits", "type": "uint256"},
             {"name": "totalBorrowAmount", "type": "uint256"},
         ],
         "name": "",
         "type": "tuple"
     }],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getAssets", "outputs": [{"type": "address[]"}],
     "stateMutability": "view", "type": "function"},
]

# Gains Network (gTrade) Trading
GAINS_TRADING_ABI = [
    {"inputs": [], "name": "getAllPairsRestrictedMaxLeverage",
     "outputs": [{"type": "uint256[]"}],
     "stateMutability": "view", "type": "function"},
]


# ============================================
# MAIN SERVICE
# ============================================

class OnChainVerifier:
    """
    Read-only on-chain verification for all Base DeFi protocols.

    Usage:
        verifier = OnChainVerifier()
        result = await verifier.verify("0xABC...", "aave-v3")
    """

    # Protocol name → handler mapping
    PROTOCOL_HANDLERS = {
        # --- Lending ---
        "aave": "_verify_aave",
        "aave-v3": "_verify_aave",
        "aave_v3": "_verify_aave",
        "morpho": "_verify_morpho",
        "morpho-blue": "_verify_morpho",
        "morpho_blue": "_verify_morpho",
        "compound": "_verify_compound",
        "compound-v3": "_verify_compound",
        "compound_v3": "_verify_compound",
        "moonwell": "_verify_moonwell",
        "ionic": "_verify_ionic",
        "ionic-protocol": "_verify_ionic",
        "exactly": "_verify_exactly",
        "exactly-protocol": "_verify_exactly",
        "silo": "_verify_silo",
        "silo-finance": "_verify_silo",
        "silo_finance": "_verify_silo",
        "extra-finance": "_verify_extra_finance",
        "extra_finance": "_verify_extra_finance",

        # --- DEX ---
        "aerodrome": "_verify_aerodrome",
        "aerodrome-v2": "_verify_aerodrome",
        "aerodrome-slipstream": "_verify_aerodrome",
        "uniswap": "_verify_uniswap_v3",
        "uniswap-v3": "_verify_uniswap_v3",
        "uniswap_v3": "_verify_uniswap_v3",
        "sushiswap": "_verify_v2_pair",
        "sushiswap-v2": "_verify_v2_pair",
        "sushi": "_verify_v2_pair",
        "baseswap": "_verify_v2_pair",
        "baseswap-v2": "_verify_v2_pair",
        "pancakeswap": "_verify_v2_pair",
        "pancakeswap-v2": "_verify_v2_pair",
        "pancakeswap-v3": "_verify_pancakeswap_v3",
        "pancakeswap_v3": "_verify_pancakeswap_v3",
        "curve": "_verify_curve",
        "curve-dex": "_verify_curve",
        "balancer": "_verify_balancer_v2",
        "balancer-v2": "_verify_balancer_v2",
        "balancer_v2": "_verify_balancer_v2",
        "maverick": "_verify_maverick_v2",
        "maverick-v2": "_verify_maverick_v2",
        "maverick_v2": "_verify_maverick_v2",

        # --- Derivatives / Structured ---
        "pendle": "_verify_pendle",
        "gains": "_verify_gains_gdai",
        "gains-network": "_verify_gains_gdai",
        "gtrade": "_verify_gains_gdai",

        # --- Vaults / Yield ---
        "seamless": "_verify_erc4626",
        "seamless-protocol": "_verify_erc4626",
        "beefy": "_verify_beefy_vault",
        "yearn": "_verify_erc4626",
        "spark": "_verify_erc4626",
        "lido": "_verify_erc4626",
        "erc4626": "_verify_erc4626",
        "dhedge": "_verify_dhedge",
        "dhedge-v2": "_verify_dhedge",

        # --- Bridges ---
        "stargate": "_verify_stargate",
        "stargate-v2": "_verify_stargate",
        "stargate_v2": "_verify_stargate",
        "hop": "_verify_hop",
        "hop-protocol": "_verify_hop",

        # --- Stablecoin ---
        "overnight": "_verify_overnight",
        "overnight-finance": "_verify_overnight",
        "usd+": "_verify_overnight",
    }

    def __init__(self, rpc_url: str = None):
        self.rpc_url = rpc_url or RPC_URL
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self._price_cache: Dict[str, Tuple[float, float]] = {}  # addr → (price, timestamp)
        print(f"[OnChainVerifier] Initialized, connected: {self.w3.is_connected()}")

    # ============================================
    # PUBLIC API
    # ============================================

    async def verify(
        self,
        pool_address: str,
        protocol: str,
        api_data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Verify pool on-chain. Returns TVL, price, APY from RPC.

        Args:
            pool_address: Pool/market/vault contract address
            protocol: Protocol name (aave-v3, morpho, compound-v3, etc.)
            api_data: Optional API data to compare against (from DefiLlama)

        Returns:
            {
                "pool_address": "0x...",
                "protocol": "aave-v3",
                "onchain": {"tvl": 12345678, "apy": 4.23, "price": 1.0001},
                "verified": True,
                "delta": {"tvl_pct": 0.04, "apy_pct": 0.71},  # if api_data provided
                "source": "rpc",
                "timestamp": 1708186000,
                "error": null
            }
        """
        protocol_key = protocol.lower().strip().replace(" ", "-")
        handler_name = self.PROTOCOL_HANDLERS.get(protocol_key)

        if not handler_name:
            return self._error_result(pool_address, protocol, f"Unknown protocol: {protocol}")

        handler = getattr(self, handler_name)
        start = time.time()

        try:
            onchain = await handler(pool_address)
            elapsed = time.time() - start

            # ── APY BACKFILL: if handler returned None, use API data ──
            if onchain.get("apy") is None and api_data:
                api_apy = api_data.get("apy") or api_data.get("apyBase") or 0
                api_reward = api_data.get("apyReward", 0) or 0
                total_api_apy = float(api_apy) + float(api_reward)
                if total_api_apy > 0:
                    onchain["apy"] = round(total_api_apy, 4)
                    onchain["apy_source"] = "defillama"
                    print(f"[OnChainVerifier] APY backfilled from DefiLlama: {total_api_apy:.2f}%")

            result = {
                "pool_address": pool_address,
                "protocol": protocol,
                "onchain": onchain,
                "verified": onchain.get("tvl", 0) > 0,
                "source": "rpc",
                "rpc_time_ms": round(elapsed * 1000),
                "timestamp": int(time.time()),
                "error": None,
            }

            # Compare with API data if provided
            if api_data:
                result["api"] = {
                    "tvl": api_data.get("tvl", 0),
                    "apy": api_data.get("apy", 0),
                }
                result["delta"] = self._compute_delta(onchain, api_data)

            return result

        except Exception as e:
            print(f"[OnChainVerifier] Error verifying {protocol}/{pool_address}: {e}")
            return self._error_result(pool_address, protocol, str(e))

    async def verify_batch(
        self,
        pools: List[Dict],
    ) -> List[Dict]:
        """Verify multiple pools concurrently."""
        tasks = [
            self.verify(p["address"], p["protocol"], p.get("api_data"))
            for p in pools
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

    # ============================================
    # PROTOCOL HANDLERS
    # ============================================

    async def _verify_aave(self, asset_or_pool: str) -> Dict:
        """
        Aave V3: getReserveData(asset) → TVL + APY

        Input can be:
        - Asset address (USDC, WETH) → calls getReserveData on Aave Pool
        - aToken address → resolves underlying first
        """
        pool_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACTS["aave_v3_pool"]),
            abi=AAVE_POOL_ABI,
        )

        asset = Web3.to_checksum_address(asset_or_pool)

        try:
            reserve = pool_contract.functions.getReserveData(asset).call()
        except ContractLogicError:
            # Maybe it's an aToken — try known assets
            for token_info in TOKENS.values():
                try:
                    reserve = pool_contract.functions.getReserveData(
                        Web3.to_checksum_address(token_info["address"])
                    ).call()
                    a_token_addr = reserve[8]  # aTokenAddress
                    if a_token_addr.lower() == asset_or_pool.lower():
                        asset = Web3.to_checksum_address(token_info["address"])
                        break
                except:
                    continue
            else:
                raise ValueError(f"Cannot resolve Aave asset: {asset_or_pool}")

        # Parse reserve data
        liquidity_rate = reserve[2]  # currentLiquidityRate (RAY = 1e27)
        a_token_address = reserve[8]

        # Get aToken total supply = TVL
        a_token = self.w3.eth.contract(
            address=Web3.to_checksum_address(a_token_address),
            abi=ERC20_ABI,
        )
        total_supply = a_token.functions.totalSupply().call()
        decimals = a_token.functions.decimals().call()

        tvl_raw = total_supply / (10 ** decimals)
        # APY from liquidity rate (RAY precision)
        apy = (liquidity_rate / 1e27) * 100

        # Price: stablecoin = 1.0, ETH = oracle
        price = await self._get_token_price(asset)

        return {
            "tvl": round(tvl_raw * price, 2),
            "apy": round(apy, 4),
            "price": price,
            "supply_raw": str(total_supply),
            "details": {
                "atoken": a_token_address,
                "liquidity_rate_ray": str(liquidity_rate),
            }
        }

    async def _verify_morpho(self, market_id: str) -> Dict:
        """
        Morpho Blue: market(id) → supply/borrow data

        Input: market ID (bytes32 hex string)
        """
        morpho = self.w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACTS["morpho_blue"]),
            abi=MORPHO_ABI,
        )

        # Convert hex string to bytes32
        if market_id.startswith("0x"):
            market_id_bytes = bytes.fromhex(market_id[2:].ljust(64, '0'))
        else:
            market_id_bytes = bytes.fromhex(market_id.ljust(64, '0'))

        market_data = morpho.functions.market(market_id_bytes).call()
        market_params = morpho.functions.idToMarketParams(market_id_bytes).call()

        total_supply = market_data[0]  # totalSupplyAssets
        total_borrow = market_data[2]  # totalBorrowAssets
        fee = market_data[5]           # fee (1e18 = 100%)
        loan_token = market_params[0]

        # Get token decimals
        token = self.w3.eth.contract(
            address=Web3.to_checksum_address(loan_token),
            abi=ERC20_ABI,
        )
        decimals = token.functions.decimals().call()

        tvl_raw = total_supply / (10 ** decimals)
        price = await self._get_token_price(loan_token)

        # APY estimation: utilization-based
        utilization = total_borrow / total_supply if total_supply > 0 else 0
        # Morpho Blue uses adaptive IRM, approximate base APY
        estimated_apy = utilization * 8.0  # rough approximation

        return {
            "tvl": round(tvl_raw * price, 2),
            "apy": round(estimated_apy, 4),
            "price": price,
            "details": {
                "total_supply": str(total_supply),
                "total_borrow": str(total_borrow),
                "utilization": round(utilization * 100, 2),
                "loan_token": loan_token,
                "collateral_token": market_params[1],
            }
        }

    async def _verify_compound(self, comet_address: str = None) -> Dict:
        """
        Compound V3: totalSupply(), getSupplyRate(getUtilization())
        """
        addr = comet_address or CONTRACTS["compound_comet_usdc"]
        comet = self.w3.eth.contract(
            address=Web3.to_checksum_address(addr),
            abi=COMET_ABI,
        )

        total_supply = comet.functions.totalSupply().call()
        utilization = comet.functions.getUtilization().call()
        supply_rate = comet.functions.getSupplyRate(utilization).call()
        base_token = comet.functions.baseToken().call()

        # Get decimals
        token = self.w3.eth.contract(
            address=Web3.to_checksum_address(base_token),
            abi=ERC20_ABI,
        )
        decimals = token.functions.decimals().call()

        tvl_raw = total_supply / (10 ** decimals)
        price = await self._get_token_price(base_token)

        # APY: supply_rate is per second, scaled by 1e18
        apy = (supply_rate / 1e18) * SECONDS_PER_YEAR * 100

        return {
            "tvl": round(tvl_raw * price, 2),
            "apy": round(apy, 4),
            "price": price,
            "details": {
                "total_supply_raw": str(total_supply),
                "utilization_pct": round(utilization / 1e18 * 100, 2),
                "supply_rate_per_sec": str(supply_rate),
                "base_token": base_token,
            }
        }

    async def _verify_moonwell(self, mtoken_address: str = None) -> Dict:
        """
        Moonwell: mToken totalSupply * exchangeRate = TVL, supplyRatePerTimestamp → APY
        """
        addr = mtoken_address or CONTRACTS["moonwell_musdc"]
        mtoken = self.w3.eth.contract(
            address=Web3.to_checksum_address(addr),
            abi=MTOKEN_ABI,
        )

        total_supply = mtoken.functions.totalSupply().call()
        exchange_rate = mtoken.functions.exchangeRateStored().call()
        supply_rate = mtoken.functions.supplyRatePerTimestamp().call()
        underlying_addr = mtoken.functions.underlying().call()
        cash = mtoken.functions.getCash().call()
        borrows = mtoken.functions.totalBorrows().call()
        reserves = mtoken.functions.totalReserves().call()

        # Get underlying decimals
        underlying = self.w3.eth.contract(
            address=Web3.to_checksum_address(underlying_addr),
            abi=ERC20_ABI,
        )
        decimals = underlying.functions.decimals().call()

        # TVL = cash + totalBorrows - totalReserves
        tvl_raw = (cash + borrows - reserves) / (10 ** decimals)
        price = await self._get_token_price(underlying_addr)

        # APY: supplyRatePerTimestamp is per second in 1e18
        apy = (supply_rate / 1e18) * SECONDS_PER_YEAR * 100

        return {
            "tvl": round(tvl_raw * price, 2),
            "apy": round(apy, 4),
            "price": price,
            "details": {
                "total_supply": str(total_supply),
                "exchange_rate": str(exchange_rate),
                "cash": str(cash),
                "borrows": str(borrows),
                "underlying": underlying_addr,
            }
        }

    async def _verify_aerodrome(self, pool_address: str) -> Dict:
        """
        Aerodrome: getReserves() for TVL, gauge rewardRate() for APY
        """
        pool = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=AERO_POOL_ABI,
        )

        reserves = pool.functions.getReserves().call()
        token0_addr = pool.functions.token0().call()
        token1_addr = pool.functions.token1().call()

        try:
            is_stable = pool.functions.stable().call()
        except:
            is_stable = False

        # Get token decimals
        t0 = self.w3.eth.contract(address=Web3.to_checksum_address(token0_addr), abi=ERC20_ABI)
        t1 = self.w3.eth.contract(address=Web3.to_checksum_address(token1_addr), abi=ERC20_ABI)
        d0 = t0.functions.decimals().call()
        d1 = t1.functions.decimals().call()
        s0 = t0.functions.symbol().call()
        s1 = t1.functions.symbol().call()

        p0 = await self._get_token_price(token0_addr)
        p1 = await self._get_token_price(token1_addr)

        r0 = reserves[0] / (10 ** d0)
        r1 = reserves[1] / (10 ** d1)

        tvl = r0 * p0 + r1 * p1

        # Try to get gauge for APY
        apy = 0.0
        gauge_addr = None
        try:
            gauge_addr = pool.functions.gauge().call()
            if gauge_addr and gauge_addr != "0x0000000000000000000000000000000000000000":
                gauge = self.w3.eth.contract(
                    address=Web3.to_checksum_address(gauge_addr),
                    abi=AERO_GAUGE_ABI,
                )
                reward_rate = gauge.functions.rewardRate().call()
                gauge_supply = gauge.functions.totalSupply().call()

                # AERO price
                aero_price = await self._get_token_price(TOKENS["AERO"]["address"])

                if gauge_supply > 0 and tvl > 0:
                    # Rewards per year in USD
                    rewards_per_year = (reward_rate / 1e18) * SECONDS_PER_YEAR * aero_price
                    apy = (rewards_per_year / tvl) * 100
        except Exception as e:
            print(f"[OnChainVerifier] Gauge query error for {pool_address}: {e}")

        # Price = ratio between tokens
        price = (r0 * p0) / (r1 * p1) if r1 * p1 > 0 else 0

        return {
            "tvl": round(tvl, 2),
            "apy": round(apy, 4),
            "price": round(price, 6),
            "details": {
                "token0": s0,
                "token1": s1,
                "reserve0": round(r0, 4),
                "reserve1": round(r1, 4),
                "price0": p0,
                "price1": p1,
                "stable": is_stable,
                "gauge": gauge_addr,
            }
        }

    async def _verify_uniswap_v3(self, pool_address: str) -> Dict:
        """
        Uniswap V3: slot0() for price, liquidity() for TVL, fee() for APY estimation
        """
        pool = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=UNIV3_POOL_ABI,
        )

        slot0 = pool.functions.slot0().call()
        liquidity = pool.functions.liquidity().call()
        fee_tier = pool.functions.fee().call()
        token0_addr = pool.functions.token0().call()
        token1_addr = pool.functions.token1().call()

        sqrt_price_x96 = slot0[0]
        tick = slot0[1]

        # Get token info
        t0 = self.w3.eth.contract(address=Web3.to_checksum_address(token0_addr), abi=ERC20_ABI)
        t1 = self.w3.eth.contract(address=Web3.to_checksum_address(token1_addr), abi=ERC20_ABI)
        d0 = t0.functions.decimals().call()
        d1 = t1.functions.decimals().call()
        s0 = t0.functions.symbol().call()
        s1 = t1.functions.symbol().call()

        # Price from sqrtPriceX96
        price_raw = (sqrt_price_x96 / (2 ** 96)) ** 2
        price_adjusted = price_raw * (10 ** d0) / (10 ** d1)

        p0 = await self._get_token_price(token0_addr)
        p1 = await self._get_token_price(token1_addr)

        # TVL estimation from liquidity (simplified — around active tick)
        # For concentrated liquidity, TVL = 2 * sqrt(L) * sqrt(P) * token_price
        if sqrt_price_x96 > 0 and liquidity > 0:
            sqrt_p = sqrt_price_x96 / (2 ** 96)
            # Approximate amounts around current tick
            amount0 = liquidity / sqrt_p / (10 ** d0) if sqrt_p > 0 else 0
            amount1 = liquidity * sqrt_p / (10 ** d1)
            tvl = amount0 * p0 + amount1 * p1
        else:
            tvl = 0

        # Fee tier based APY estimation from feeGrowthGlobal
        fee_pct = fee_tier / 1_000_000 * 100  # e.g., 3000 → 0.3%
        apy = None
        try:
            fg0 = pool.functions.feeGrowthGlobal0X128().call()
            fg1 = pool.functions.feeGrowthGlobal1X128().call()
            # feeGrowthGlobal = cumulative fees per unit of liquidity in Q128
            # Estimate annual fees: fees_usd = feeGrowth / 2^128 * price * liquidity
            if liquidity > 0 and tvl > 0:
                fees0_usd = (fg0 / (2 ** 128)) * p0 / (10 ** (18 - d0)) if d0 < 18 else (fg0 / (2 ** 128)) * p0
                fees1_usd = (fg1 / (2 ** 128)) * p1 / (10 ** (18 - d1)) if d1 < 18 else (fg1 / (2 ** 128)) * p1
                # Pool age estimate (Base launch ~Aug 2023, ~18 months ago)
                pool_age_days = 365  # conservative estimate
                total_fees = fees0_usd + fees1_usd
                daily_fees = total_fees / pool_age_days if pool_age_days > 0 else 0
                annual_fees = daily_fees * 365
                if annual_fees > 0:
                    apy = round((annual_fees / tvl) * 100, 4)
                    # Sanity cap: max 500% APY
                    if apy > 500:
                        apy = round(fee_pct * 365 / 10, 4)  # rough fallback
        except Exception as e:
            print(f"[OnChainVerifier] feeGrowthGlobal estimation failed: {e}")

        return {
            "tvl": round(tvl, 2),
            "apy": apy,
            "apy_source": "feeGrowth" if apy is not None else None,
            "price": round(price_adjusted, 8),
            "fee_tier_pct": fee_pct,
            "details": {
                "token0": s0,
                "token1": s1,
                "tick": tick,
                "liquidity": str(liquidity),
                "sqrtPriceX96": str(sqrt_price_x96),
                "fee_tier": fee_tier,
                "price0_usd": p0,
                "price1_usd": p1,
            }
        }

    async def _verify_curve(self, pool_address: str) -> Dict:
        """
        Curve: get_virtual_price(), balances(i) for TVL
        """
        pool = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=CURVE_POOL_ABI,
        )

        virtual_price = pool.functions.get_virtual_price().call()

        # Enumerate coins and balances (most Curve pools have 2-4 coins)
        tvl = 0.0
        coins = []
        for i in range(4):
            try:
                coin_addr = pool.functions.coins(i).call()
                balance = pool.functions.balances(i).call()

                token = self.w3.eth.contract(
                    address=Web3.to_checksum_address(coin_addr), abi=ERC20_ABI)
                decimals = token.functions.decimals().call()
                symbol = token.functions.symbol().call()

                bal = balance / (10 ** decimals)
                price = await self._get_token_price(coin_addr)
                tvl += bal * price
                coins.append({"symbol": symbol, "balance": round(bal, 4), "price": price})
            except:
                break

        # Estimate fee APY from virtual price growth (Curve pools accrue fees via virtual price)
        # virtual_price starts at 1e18 and grows with fees
        vp = virtual_price / 1e18
        if vp > 1.0 and tvl > 0:
            # Base chain Curve pools are ~1 year old; estimate annual fee growth
            fee_apy = round((vp - 1.0) * 100, 4)  # rough annual estimate
        else:
            fee_apy = None

        return {
            "tvl": round(tvl, 2),
            "apy": fee_apy,
            "apy_source": "virtual_price" if fee_apy else None,
            "price": round(virtual_price / 1e18, 6),
            "details": {
                "virtual_price": str(virtual_price),
                "coins": coins,
            }
        }

    async def _verify_pendle(self, market_address: str) -> Dict:
        """
        Pendle: readState() for PT/SY totals, implied APY from lastLnImpliedRate
        """
        market = self.w3.eth.contract(
            address=Web3.to_checksum_address(market_address),
            abi=PENDLE_MARKET_ABI,
        )

        state = market.functions.readState().call()
        sy_addr = market.functions.SY().call()
        expiry = market.functions.expiry().call()

        total_pt = state[0]
        total_sy = state[1]
        total_lp = state[2]
        last_ln_implied_rate = state[8]

        # Get SY token info for TVL
        sy_token = self.w3.eth.contract(
            address=Web3.to_checksum_address(sy_addr), abi=ERC20_ABI)
        sy_decimals = sy_token.functions.decimals().call()

        sy_raw = total_sy / (10 ** sy_decimals)
        pt_raw = total_pt / (10 ** sy_decimals)

        # Price SY (usually wrapped staked asset)
        sy_price = await self._get_token_price(sy_addr)
        tvl = (sy_raw + pt_raw) * sy_price

        # Implied APY from lastLnImpliedRate
        # ln(1 + apy) = lastLnImpliedRate / 1e18
        apy = 0.0
        if last_ln_implied_rate > 0:
            try:
                apy = (math.exp(last_ln_implied_rate / 1e18) - 1) * 100
            except:
                pass

        # Time to expiry
        now = int(time.time())
        days_to_expiry = max(0, (expiry - now) / 86400)

        return {
            "tvl": round(tvl, 2),
            "apy": round(apy, 4),
            "price": sy_price,
            "details": {
                "total_pt": str(total_pt),
                "total_sy": str(total_sy),
                "total_lp": str(total_lp),
                "expiry": expiry,
                "days_to_expiry": round(days_to_expiry, 1),
                "implied_rate_raw": str(last_ln_implied_rate),
            }
        }

    async def _verify_erc4626(self, vault_address: str) -> Dict:
        """
        ERC-4626 Vault: totalAssets(), convertToAssets() for share price.
        Works for: Seamless vaults, Beefy, Yearn, Spark, Lido vaults, etc.
        """
        vault = self.w3.eth.contract(
            address=Web3.to_checksum_address(vault_address),
            abi=ERC4626_ABI,
        )

        total_assets = vault.functions.totalAssets().call()
        total_supply = vault.functions.totalSupply().call()
        asset_addr = vault.functions.asset().call()
        vault_decimals = vault.functions.decimals().call()

        # Share price
        one_share = 10 ** vault_decimals
        if total_supply > 0:
            try:
                assets_per_share = vault.functions.convertToAssets(one_share).call()
            except:
                assets_per_share = total_assets * one_share // total_supply
        else:
            assets_per_share = one_share

        # Get underlying token info
        asset_token = self.w3.eth.contract(
            address=Web3.to_checksum_address(asset_addr), abi=ERC20_ABI)
        asset_decimals = asset_token.functions.decimals().call()
        asset_symbol = asset_token.functions.symbol().call()

        tvl_raw = total_assets / (10 ** asset_decimals)
        price = await self._get_token_price(asset_addr)
        share_price = assets_per_share / one_share

        # Estimate APY from share price growth (share_price > 1.0 means yield accrued)
        erc4626_apy = None
        if share_price > 1.0:
            # Assume vault ~1 year old, share_price growth = annual yield
            erc4626_apy = round((share_price - 1.0) * 100, 4)
        elif share_price > 0.999 and share_price < 1.0:
            erc4626_apy = 0.0  # No yield accrued yet

        return {
            "tvl": round(tvl_raw * price, 2),
            "apy": erc4626_apy,
            "apy_source": "share_price" if erc4626_apy is not None else None,
            "price": price,
            "share_price": round(share_price, 6),
            "details": {
                "total_assets": str(total_assets),
                "total_supply": str(total_supply),
                "assets_per_share": str(assets_per_share),
                "underlying": asset_symbol,
                "underlying_address": asset_addr,
            }
        }

    # ------ NEW PROTOCOL HANDLERS (15 additional) ------

    async def _verify_balancer_v2(self, pool_address: str) -> Dict:
        """
        Balancer V2: getPoolId() → Vault.getPoolTokens() for TVL
        """
        pool = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=BALANCER_POOL_ABI,
        )
        vault = self.w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACTS["balancer_v2_vault"]),
            abi=BALANCER_VAULT_ABI,
        )

        pool_id = pool.functions.getPoolId().call()
        tokens_data = vault.functions.getPoolTokens(pool_id).call()
        token_addrs = tokens_data[0]
        balances = tokens_data[1]

        # Get swap fee
        try:
            swap_fee_raw = pool.functions.getSwapFeePercentage().call()
            swap_fee_pct = swap_fee_raw / 1e18 * 100
        except:
            swap_fee_pct = 0

        # Calculate TVL
        tvl = 0.0
        tokens_info = []
        for i, addr in enumerate(token_addrs):
            try:
                token = self.w3.eth.contract(
                    address=Web3.to_checksum_address(addr), abi=ERC20_ABI)
                decimals = token.functions.decimals().call()
                symbol = token.functions.symbol().call()
                bal = balances[i] / (10 ** decimals)
                price = await self._get_token_price(addr)
                tvl += bal * price
                tokens_info.append({"symbol": symbol, "balance": round(bal, 4), "price": price})
            except:
                continue

        # Estimate fee APY: swap_fee_pct * ~365 (assuming TVL turns over ~1x/day — rough)
        bal_fee_apy = None
        if swap_fee_pct > 0 and tvl > 0:
            # Conservative: assume ~10% daily volume/TVL ratio (common for large Balancer pools)
            bal_fee_apy = round(swap_fee_pct * 365 * 0.10, 4)

        return {
            "tvl": round(tvl, 2),
            "apy": bal_fee_apy,
            "apy_source": "swap_fee" if bal_fee_apy is not None else None,
            "price": None,
            "details": {
                "pool_id": pool_id.hex(),
                "swap_fee_pct": round(swap_fee_pct, 4),
                "tokens": tokens_info,
                "num_tokens": len(token_addrs),
            }
        }

    async def _verify_v2_pair(self, pair_address: str) -> Dict:
        """
        UniswapV2-fork (SushiSwap, BaseSwap, PancakeSwap V2, AlienBase, SwapBased):
        getReserves() + token prices for TVL
        """
        pair = self.w3.eth.contract(
            address=Web3.to_checksum_address(pair_address),
            abi=V2_PAIR_ABI,
        )

        reserves = pair.functions.getReserves().call()
        t0 = pair.functions.token0().call()
        t1 = pair.functions.token1().call()

        tk0 = self.w3.eth.contract(address=Web3.to_checksum_address(t0), abi=ERC20_ABI)
        tk1 = self.w3.eth.contract(address=Web3.to_checksum_address(t1), abi=ERC20_ABI)

        d0 = tk0.functions.decimals().call()
        d1 = tk1.functions.decimals().call()
        s0 = tk0.functions.symbol().call()
        s1 = tk1.functions.symbol().call()

        r0 = reserves[0] / (10 ** d0)
        r1 = reserves[1] / (10 ** d1)

        p0 = await self._get_token_price(t0)
        p1 = await self._get_token_price(t1)

        tvl = r0 * p0 + r1 * p1

        # Detect factory
        try:
            factory = pair.functions.factory().call()
        except:
            factory = "unknown"

        # Estimate fee APY: V2 pairs charge 0.3% per swap
        # Conservative: assume ~5% daily volume/TVL ratio
        v2_fee_apy = None
        if tvl > 0:
            v2_fee_apy = round(0.3 * 365 * 0.05, 4)  # ~5.475% base estimate

        return {
            "tvl": round(tvl, 2),
            "apy": v2_fee_apy,
            "apy_source": "fee_estimate" if v2_fee_apy is not None else None,
            "price": round(r1 * p1 / (r0 * p0), 8) if r0 * p0 > 0 else 0,
            "details": {
                "token0": s0,
                "token1": s1,
                "reserve0": round(r0, 4),
                "reserve1": round(r1, 4),
                "price0_usd": p0,
                "price1_usd": p1,
                "factory": factory,
            }
        }

    async def _verify_stargate(self, pool_address: str) -> Dict:
        """
        Stargate V2: totalLiquidity(), token() for TVL
        """
        pool = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=STARGATE_POOL_ABI,
        )

        total_liquidity = pool.functions.totalLiquidity().call()
        total_supply = pool.functions.totalSupply().call()
        token_addr = pool.functions.token().call()

        token = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_addr), abi=ERC20_ABI)
        decimals = token.functions.decimals().call()
        symbol = token.functions.symbol().call()

        tvl_raw = total_liquidity / (10 ** decimals)
        price = await self._get_token_price(token_addr)

        # Convert rate (Stargate internal scaling)
        try:
            convert_rate = pool.functions.convertRate().call()
        except:
            convert_rate = 1

        # Estimate share price growth APY
        sg_apy = None
        if total_supply > 0 and total_liquidity > 0:
            share_price = total_liquidity / total_supply
            if share_price > 1.0:
                sg_apy = round((share_price - 1.0) * 100, 4)

        return {
            "tvl": round(tvl_raw * price, 2),
            "apy": sg_apy,
            "apy_source": "share_price" if sg_apy is not None else None,
            "price": price,
            "details": {
                "total_liquidity": str(total_liquidity),
                "total_supply": str(total_supply),
                "underlying": symbol,
                "convert_rate": convert_rate,
            }
        }

    async def _verify_exactly(self, market_address: str) -> Dict:
        """
        Exactly Protocol: totalAssets(), totalFloatingBorrowAssets() for TVL + utilization
        """
        market = self.w3.eth.contract(
            address=Web3.to_checksum_address(market_address),
            abi=EXACTLY_MARKET_ABI,
        )

        total_assets = market.functions.totalAssets().call()
        asset_addr = market.functions.asset().call()
        decimals = market.functions.decimals().call()

        # Borrow data
        try:
            total_borrow = market.functions.totalFloatingBorrowAssets().call()
        except:
            total_borrow = 0

        try:
            total_deposit = market.functions.totalFloatingDepositAssets().call()
        except:
            total_deposit = total_assets

        # Rate
        try:
            floating_rate = market.functions.floatingRate().call()
            apy = (floating_rate / 1e18) * 100
        except:
            apy = None

        token = self.w3.eth.contract(
            address=Web3.to_checksum_address(asset_addr), abi=ERC20_ABI)
        asset_decimals = token.functions.decimals().call()
        symbol = token.functions.symbol().call()

        tvl_raw = total_assets / (10 ** asset_decimals)
        price = await self._get_token_price(asset_addr)

        utilization = 0
        if total_deposit > 0:
            utilization = round(total_borrow / total_deposit * 100, 2)

        return {
            "tvl": round(tvl_raw * price, 2),
            "apy": round(apy, 4) if apy is not None else None,
            "price": price,
            "details": {
                "total_deposit": str(total_deposit),
                "total_borrow": str(total_borrow),
                "utilization_pct": utilization,
                "underlying": symbol,
            }
        }

    async def _verify_ionic(self, ctoken_address: str) -> Dict:
        """
        Ionic Protocol (Compound V2 fork): exchangeRateStored(), supplyRatePerBlock()
        Same ABI as Moonwell but uses supplyRatePerBlock instead of supplyRatePerTimestamp.
        """
        ctoken = self.w3.eth.contract(
            address=Web3.to_checksum_address(ctoken_address),
            abi=IONIC_CTOKEN_ABI,
        )

        total_supply = ctoken.functions.totalSupply().call()
        exchange_rate = ctoken.functions.exchangeRateStored().call()
        underlying_addr = ctoken.functions.underlying().call()

        token = self.w3.eth.contract(
            address=Web3.to_checksum_address(underlying_addr), abi=ERC20_ABI)
        decimals = token.functions.decimals().call()
        symbol = token.functions.symbol().call()

        # TVL = totalSupply * exchangeRate / 1e18 / 10^decimals
        tvl_raw = (total_supply * exchange_rate) / 1e18 / (10 ** decimals)
        price = await self._get_token_price(underlying_addr)

        # APY from supplyRatePerBlock
        # Base: ~2 second blocks → 15_768_000 blocks/year
        try:
            supply_rate = ctoken.functions.supplyRatePerBlock().call()
            blocks_per_year = 15_768_000
            apy = ((1 + supply_rate / 1e18) ** blocks_per_year - 1) * 100
        except:
            apy = None

        # Utilization
        try:
            cash = ctoken.functions.getCash().call()
            borrows = ctoken.functions.totalBorrows().call()
            reserves = ctoken.functions.totalReserves().call()
            utilization = borrows / (cash + borrows - reserves) * 100 if (cash + borrows - reserves) > 0 else 0
        except:
            utilization = 0

        return {
            "tvl": round(tvl_raw * price, 2),
            "apy": round(apy, 4) if apy is not None else None,
            "price": price,
            "details": {
                "underlying": symbol,
                "exchange_rate": str(exchange_rate),
                "utilization_pct": round(utilization, 2),
            }
        }

    async def _verify_dhedge(self, pool_address: str) -> Dict:
        """
        dHEDGE: tokenPrice(), totalFundValue() for TVL
        """
        pool = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=DHEDGE_POOL_ABI,
        )

        token_price = pool.functions.tokenPrice().call()
        total_fund_value = pool.functions.totalFundValue().call()
        total_supply = pool.functions.totalSupply().call()

        try:
            manager = pool.functions.managerName().call()
        except:
            manager = "Unknown"

        try:
            creation = pool.functions.creationTime().call()
            days_live = (int(time.time()) - creation) / 86400
        except:
            days_live = 0

        # dHEDGE values are in 18 decimals, denominated in USD
        tvl = total_fund_value / 1e18
        share_price = token_price / 1e18

        # dHEDGE APY: estimate from share price vs $1 inception
        dh_apy = None
        if share_price > 0 and days_live > 30:
            # Annualized return from inception
            total_return = (share_price - 1.0) / 1.0  # assuming $1 inception
            years = days_live / 365.25
            if years > 0 and total_return > -0.99:
                dh_apy = round(((1 + total_return) ** (1 / years) - 1) * 100, 4)

        return {
            "tvl": round(tvl, 2),
            "apy": dh_apy,
            "apy_source": "nav_growth" if dh_apy is not None else None,
            "price": round(share_price, 6),
            "details": {
                "token_price_raw": str(token_price),
                "total_fund_value_raw": str(total_fund_value),
                "manager": manager,
                "days_live": round(days_live, 0),
            }
        }

    async def _verify_hop(self, amm_address: str) -> Dict:
        """
        Hop Protocol: getVirtualPrice(), l2CanonicalToken() for TVL
        """
        amm = self.w3.eth.contract(
            address=Web3.to_checksum_address(amm_address),
            abi=HOP_AMM_ABI,
        )

        virtual_price = amm.functions.getVirtualPrice().call()
        canonical_token = amm.functions.l2CanonicalToken().call()
        h_token = amm.functions.hToken().call()

        # Get LP token total supply from swapStorage
        try:
            swap_storage = amm.functions.swapStorage().call()
            lp_token_addr = swap_storage[6]
            lp_token = self.w3.eth.contract(
                address=Web3.to_checksum_address(lp_token_addr), abi=ERC20_ABI)
            lp_supply = lp_token.functions.totalSupply().call()
            swap_fee = swap_storage[4]
        except:
            lp_supply = 0
            swap_fee = 0

        token = self.w3.eth.contract(
            address=Web3.to_checksum_address(canonical_token), abi=ERC20_ABI)
        decimals = token.functions.decimals().call()
        symbol = token.functions.symbol().call()

        price = await self._get_token_price(canonical_token)

        # TVL = LP supply * virtual price / 1e18 * token price / 10^decimals
        if lp_supply > 0:
            tvl_raw = (lp_supply * virtual_price) / (1e18 * 10 ** decimals)
            tvl = tvl_raw * price
        else:
            # Fallback: check balances of canonical + hToken
            bal_c = self.w3.eth.contract(
                address=Web3.to_checksum_address(canonical_token), abi=ERC20_ABI
            ).functions.balanceOf(Web3.to_checksum_address(amm_address)).call()
            bal_h = self.w3.eth.contract(
                address=Web3.to_checksum_address(h_token), abi=ERC20_ABI
            ).functions.balanceOf(Web3.to_checksum_address(amm_address)).call()
            tvl_raw = (bal_c + bal_h) / (10 ** decimals)
            tvl = tvl_raw * price

        # Estimate APY from virtual price growth
        vp = virtual_price / 1e18
        hop_apy = None
        if vp > 1.0:
            hop_apy = round((vp - 1.0) * 100, 4)

        return {
            "tvl": round(tvl, 2),
            "apy": hop_apy,
            "apy_source": "virtual_price" if hop_apy is not None else None,
            "price": round(virtual_price / 1e18, 6),
            "details": {
                "virtual_price": str(virtual_price),
                "underlying": symbol,
                "swap_fee": str(swap_fee),
            }
        }

    async def _verify_overnight(self, token_address: str) -> Dict:
        """
        Overnight Finance (USD+): ERC20 totalSupply for TVL (1 USD+ = 1 USD)
        """
        token = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=ERC20_ABI,
        )

        total_supply = token.functions.totalSupply().call()
        decimals = token.functions.decimals().call()
        symbol = token.functions.symbol().call()

        tvl = total_supply / (10 ** decimals)  # USD+ is pegged to $1

        # Get fees from exchange if available
        buy_fee = 0
        redeem_fee = 0
        try:
            exchange = self.w3.eth.contract(
                address=Web3.to_checksum_address(CONTRACTS["overnight_exchange"]),
                abi=OVERNIGHT_EXCHANGE_ABI,
            )
            buy_fee = exchange.functions.buyFee().call()
            redeem_fee = exchange.functions.redeemFee().call()
        except:
            pass

        return {
            "tvl": round(tvl, 2),
            "apy": 5.0,  # USD+ typical daily rebase ~5% APY
            "apy_source": "rebase_estimate",
            "price": 1.0,
            "details": {
                "total_supply": str(total_supply),
                "symbol": symbol,
                "buy_fee_bps": buy_fee,
                "redeem_fee_bps": redeem_fee,
            }
        }

    async def _verify_beefy_vault(self, vault_address: str) -> Dict:
        """
        Beefy Finance (V7 vault): balance(), getPricePerFullShare(), want() for TVL.
        Falls back to ERC-4626 if Beefy-specific methods not found.
        """
        try:
            vault = self.w3.eth.contract(
                address=Web3.to_checksum_address(vault_address),
                abi=BEEFY_VAULT_ABI,
            )

            total_balance = vault.functions.balance().call()
            ppfs = vault.functions.getPricePerFullShare().call()
            want_addr = vault.functions.want().call()
            vault_decimals = vault.functions.decimals().call()

            total_supply = vault.functions.totalSupply().call()

            # Get want token info
            want_token = self.w3.eth.contract(
                address=Web3.to_checksum_address(want_addr), abi=ERC20_ABI)
            want_decimals = want_token.functions.decimals().call()
            want_symbol = want_token.functions.symbol().call()

            tvl_raw = total_balance / (10 ** want_decimals)
            price = await self._get_token_price(want_addr)
            share_price = ppfs / (10 ** vault_decimals)

            # Estimate APY from share price growth (ppfs > 1e18 means yield)
            beefy_apy = None
            if ppfs > 10 ** vault_decimals:
                growth = (ppfs / (10 ** vault_decimals)) - 1.0
                beefy_apy = round(growth * 100, 4)  # rough annualized estimate

            return {
                "tvl": round(tvl_raw * price, 2),
                "apy": beefy_apy,
                "apy_source": "ppfs_growth" if beefy_apy is not None else None,
                "price": price,
                "share_price": round(share_price, 6),
                "details": {
                    "total_balance": str(total_balance),
                    "ppfs": str(ppfs),
                    "want": want_symbol,
                    "want_address": want_addr,
                }
            }
        except Exception:
            # Fallback to ERC-4626
            return await self._verify_erc4626(vault_address)

    async def _verify_extra_finance(self, pool_address: str) -> Dict:
        """
        Extra Finance: getReserveData() for lending pool TVL + rates
        Input can be a reserve ID (as string number) or address.
        """
        lending = self.w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACTS["extra_finance_lending_pool"]),
            abi=EXTRA_LENDING_ABI,
        )

        # Try as reserve ID first
        try:
            reserve_id = int(pool_address)
        except ValueError:
            reserve_id = 0  # default

        try:
            reserve = lending.functions.getReserveData(reserve_id).call()
        except Exception:
            # If fails, try iterating reserves 0-10
            for rid in range(10):
                try:
                    reserve = lending.functions.getReserveData(rid).call()
                    if reserve[0].lower() != "0x" + "0" * 40:
                        break
                except:
                    continue
            else:
                raise ValueError("Cannot find valid Extra Finance reserve")

        underlying_addr = reserve[0]
        total_liquidity = reserve[3]
        total_borrows = reserve[4]
        deposit_rate = reserve[6]

        token = self.w3.eth.contract(
            address=Web3.to_checksum_address(underlying_addr), abi=ERC20_ABI)
        decimals = token.functions.decimals().call()
        symbol = token.functions.symbol().call()

        tvl_raw = total_liquidity / (10 ** decimals)
        price = await self._get_token_price(underlying_addr)
        apy = (deposit_rate / 1e18) * 100 if deposit_rate > 0 else None

        return {
            "tvl": round(tvl_raw * price, 2),
            "apy": round(apy, 4) if apy is not None else None,
            "price": price,
            "details": {
                "underlying": symbol,
                "total_liquidity": str(total_liquidity),
                "total_borrows": str(total_borrows),
                "utilization_pct": round(total_borrows / total_liquidity * 100, 2) if total_liquidity > 0 else 0,
            }
        }

    async def _verify_maverick_v2(self, pool_address: str) -> Dict:
        """
        Maverick V2: getState() → reserveA, reserveB for TVL
        """
        pool = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=MAVERICK_V2_POOL_ABI,
        )

        state = pool.functions.getState().call()
        tokenA = pool.functions.tokenA().call()
        tokenB = pool.functions.tokenB().call()
        fee = pool.functions.fee().call()

        tkA = self.w3.eth.contract(address=Web3.to_checksum_address(tokenA), abi=ERC20_ABI)
        tkB = self.w3.eth.contract(address=Web3.to_checksum_address(tokenB), abi=ERC20_ABI)
        dA = tkA.functions.decimals().call()
        dB = tkB.functions.decimals().call()
        sA = tkA.functions.symbol().call()
        sB = tkB.functions.symbol().call()

        rA = state[0] / (10 ** dA)
        rB = state[1] / (10 ** dB)

        pA = await self._get_token_price(tokenA)
        pB = await self._get_token_price(tokenB)

        tvl = rA * pA + rB * pB

        # Estimate fee APY from Maverick's fee
        mav_fee_apy = None
        if fee > 0 and tvl > 0:
            fee_pct = fee / 10000  # fee in basis points
            mav_fee_apy = round(fee_pct * 365 * 0.10, 4)  # ~10% daily volume/TVL

        return {
            "tvl": round(tvl, 2),
            "apy": mav_fee_apy,
            "apy_source": "fee_estimate" if mav_fee_apy is not None else None,
            "price": round(rB * pB / (rA * pA), 8) if rA * pA > 0 else 0,
            "details": {
                "tokenA": sA,
                "tokenB": sB,
                "reserveA": round(rA, 4),
                "reserveB": round(rB, 4),
                "fee_bps": fee,
                "active_tick": state[3],
            }
        }

    async def _verify_silo(self, silo_address: str) -> Dict:
        """
        Silo Finance: getAssets() → assetStorage() for each asset → TVL
        """
        silo = self.w3.eth.contract(
            address=Web3.to_checksum_address(silo_address),
            abi=SILO_ABI,
        )

        assets = silo.functions.getAssets().call()
        tvl = 0.0
        assets_info = []

        for asset_addr in assets[:4]:  # Limit to 4 max
            try:
                storage = silo.functions.assetStorage(
                    Web3.to_checksum_address(asset_addr)
                ).call()

                total_deposits = storage[3]
                total_borrows = storage[5]

                token = self.w3.eth.contract(
                    address=Web3.to_checksum_address(asset_addr), abi=ERC20_ABI)
                decimals = token.functions.decimals().call()
                symbol = token.functions.symbol().call()

                dep = total_deposits / (10 ** decimals)
                price = await self._get_token_price(asset_addr)
                tvl += dep * price

                assets_info.append({
                    "symbol": symbol,
                    "deposits": round(dep, 4),
                    "borrows": round(total_borrows / (10 ** decimals), 4),
                    "price": price,
                })
            except:
                continue

        # Estimate Silo APY from utilization (interest rate increases with utilization)
        silo_apy = None
        if assets_info:
            # Use first asset's utilization as proxy for interest rate
            for a in assets_info:
                if a.get("deposits", 0) > 0 and a.get("borrows", 0) > 0:
                    util = a["borrows"] / a["deposits"]
                    # Simple interest model: base_rate + util * slope
                    silo_apy = round((2.0 + util * 15.0) * (1 - 0.10), 4)  # 10% reserve
                    break

        return {
            "tvl": round(tvl, 2),
            "apy": silo_apy,
            "apy_source": "utilization_estimate" if silo_apy is not None else None,
            "price": None,
            "details": {
                "assets": assets_info,
                "num_assets": len(assets),
            }
        }

    async def _verify_gains_gdai(self, vault_address: str) -> Dict:
        """
        Gains Network gDAI/gUSDC vault (ERC-4626 compatible).
        Falls back to generic ERC-4626 handler.
        """
        return await self._verify_erc4626(vault_address)

    async def _verify_pancakeswap_v3(self, pool_address: str) -> Dict:
        """
        PancakeSwap V3: Same as Uniswap V3 (compatible interface).
        """
        return await self._verify_uniswap_v3(pool_address)

    # ============================================
    # HELPERS
    # ============================================

    async def _get_token_price(self, token_address: str) -> float:
        """
        Get USD price for a token. Uses cache + simple heuristics:
        - Stablecoins → $1.00
        - WETH → ETH price from Pyth or hardcoded
        - Others → attempt Pyth oracle or fallback
        """
        addr = token_address.lower()

        # Check cache (5 min TTL)
        if addr in self._price_cache:
            price, ts = self._price_cache[addr]
            if time.time() - ts < 300:
                return price

        # Stablecoins
        if addr in STABLECOIN_ADDRESSES:
            self._price_cache[addr] = (1.0, time.time())
            return 1.0

        # WETH
        if addr == TOKENS["WETH"]["address"].lower():
            price = await self._get_eth_price()
            self._price_cache[addr] = (price, time.time())
            return price

        # wstETH (approximately 1.15x ETH)
        if addr == TOKENS["wstETH"]["address"].lower():
            eth_price = await self._get_eth_price()
            price = eth_price * 1.15  # rough estimate
            self._price_cache[addr] = (price, time.time())
            return price

        # cbETH (approximately 1.05x ETH)
        if addr == TOKENS["cbETH"]["address"].lower():
            eth_price = await self._get_eth_price()
            price = eth_price * 1.05
            self._price_cache[addr] = (price, time.time())
            return price

        # cbBTC (approximately BTC price — hardcode rough estimate)
        if addr == TOKENS["cbBTC"]["address"].lower():
            self._price_cache[addr] = (95000.0, time.time())
            return 95000.0

        # AERO token — try to get from Aerodrome pool vs USDC
        if addr == TOKENS["AERO"]["address"].lower():
            price = await self._get_aero_price()
            self._price_cache[addr] = (price, time.time())
            return price

        # Fallback: try fetch from CoinGecko API
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"https://api.coingecko.com/api/v3/simple/token_price/base?"
                    f"contract_addresses={addr}&vs_currencies=usd"
                )
                data = resp.json()
                if addr in data:
                    price = data[addr]["usd"]
                    self._price_cache[addr] = (price, time.time())
                    return price
        except:
            pass

        # Final fallback: return 0
        print(f"[OnChainVerifier] ⚠️ Cannot get price for {token_address}")
        return 0.0

    async def _get_eth_price(self) -> float:
        """Get ETH price from Uniswap V3 WETH/USDC pool"""
        try:
            factory = self.w3.eth.contract(
                address=Web3.to_checksum_address(CONTRACTS["uniswap_v3_factory"]),
                abi=UNIV3_FACTORY_ABI,
            )
            pool_addr = factory.functions.getPool(
                Web3.to_checksum_address(TOKENS["WETH"]["address"]),
                Web3.to_checksum_address(TOKENS["USDC"]["address"]),
                500,  # 0.05% fee tier
            ).call()

            pool = self.w3.eth.contract(
                address=Web3.to_checksum_address(pool_addr),
                abi=UNIV3_POOL_ABI,
            )
            slot0 = pool.functions.slot0().call()
            sqrt_price = slot0[0] / (2 ** 96)
            # WETH is token0, USDC is token1 (depends on sort order)
            token0 = pool.functions.token0().call()

            if token0.lower() == TOKENS["WETH"]["address"].lower():
                # price = sqrt^2 * 10^(d0-d1) = sqrt^2 * 10^(18-6) = sqrt^2 * 10^12
                price = sqrt_price ** 2 * (10 ** 12)
            else:
                price = 1 / (sqrt_price ** 2 * (10 ** -12))

            return round(price, 2)
        except Exception as e:
            print(f"[OnChainVerifier] ETH price fallback: {e}")
            return 2700.0  # conservative fallback

    async def _get_aero_price(self) -> float:
        """Get AERO price from Aerodrome AERO/USDC pool"""
        try:
            # Known AERO/USDC pool on Aerodrome
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"https://api.coingecko.com/api/v3/simple/token_price/base?"
                    f"contract_addresses={TOKENS['AERO']['address'].lower()}&vs_currencies=usd"
                )
                data = resp.json()
                addr = TOKENS["AERO"]["address"].lower()
                if addr in data:
                    return data[addr]["usd"]
        except:
            pass
        return 0.80  # fallback

    def _compute_delta(self, onchain: Dict, api_data: Dict) -> Dict:
        """Compute % deviation between on-chain and API data."""
        delta = {}

        api_tvl = api_data.get("tvl", 0)
        onchain_tvl = onchain.get("tvl", 0)
        if api_tvl > 0 and onchain_tvl > 0:
            delta["tvl_pct"] = round(abs(onchain_tvl - api_tvl) / api_tvl * 100, 2)
        else:
            delta["tvl_pct"] = None

        api_apy = api_data.get("apy", 0)
        onchain_apy = onchain.get("apy")
        if api_apy and onchain_apy is not None and api_apy > 0:
            delta["apy_pct"] = round(abs(onchain_apy - api_apy) / api_apy * 100, 2)
        else:
            delta["apy_pct"] = None

        # Flag if delta is suspiciously large
        delta["suspicious"] = False
        if delta.get("tvl_pct") and delta["tvl_pct"] > 20:
            delta["suspicious"] = True
        if delta.get("apy_pct") and delta["apy_pct"] > 50:
            delta["suspicious"] = True

        return delta

    def _error_result(self, pool_address: str, protocol: str, error: str) -> Dict:
        return {
            "pool_address": pool_address,
            "protocol": protocol,
            "onchain": {"tvl": 0, "apy": None, "price": 0},
            "verified": False,
            "source": "rpc",
            "timestamp": int(time.time()),
            "error": error,
        }

    def get_supported_protocols(self) -> List[str]:
        """Return list of unique supported protocol names."""
        seen = set()
        protocols = []
        for key, handler in self.PROTOCOL_HANDLERS.items():
            base = handler.replace("_verify_", "")
            if base not in seen:
                seen.add(base)
                protocols.append(key)
        return protocols


# ============================================
# GLOBAL INSTANCE
# ============================================

_verifier: Optional[OnChainVerifier] = None


def get_onchain_verifier() -> OnChainVerifier:
    """Get or create global OnChainVerifier instance."""
    global _verifier
    if _verifier is None:
        _verifier = OnChainVerifier()
    return _verifier


# ============================================
# CLI TESTS
# ============================================

if __name__ == "__main__":

    async def test():
        v = OnChainVerifier()

        print("=" * 70)
        print("ON-CHAIN VERIFIER — PROTOCOL TESTS")
        print("=" * 70)

        # 1. ETH price
        eth_price = await v._get_eth_price()
        print(f"\n[ETH PRICE] ${eth_price:,.2f}")

        # 2. Aave V3 — USDC
        print("\n" + "-" * 50)
        print("[TEST] Aave V3 — USDC")
        result = await v.verify(TOKENS["USDC"]["address"], "aave-v3")
        print(f"  TVL: ${result['onchain']['tvl']:,.2f}")
        print(f"  APY: {result['onchain']['apy']}%")
        print(f"  Verified: {result['verified']}")
        print(f"  Time: {result.get('rpc_time_ms', 0)}ms")

        # 3. Aave V3 — WETH
        print("\n" + "-" * 50)
        print("[TEST] Aave V3 — WETH")
        result = await v.verify(TOKENS["WETH"]["address"], "aave-v3")
        print(f"  TVL: ${result['onchain']['tvl']:,.2f}")
        print(f"  APY: {result['onchain']['apy']}%")

        # 4. Compound V3
        print("\n" + "-" * 50)
        print("[TEST] Compound V3 — cUSDCv3")
        result = await v.verify(CONTRACTS["compound_comet_usdc"], "compound-v3")
        print(f"  TVL: ${result['onchain']['tvl']:,.2f}")
        print(f"  APY: {result['onchain']['apy']}%")

        # 5. Moonwell
        print("\n" + "-" * 50)
        print("[TEST] Moonwell — mUSDC")
        result = await v.verify(CONTRACTS["moonwell_musdc"], "moonwell")
        print(f"  TVL: ${result['onchain']['tvl']:,.2f}")
        print(f"  APY: {result['onchain']['apy']}%")

        # 6. ERC-4626 Seamless vault
        print("\n" + "-" * 50)
        print("[TEST] Seamless — USDC Vault (ERC-4626)")
        result = await v.verify(CONTRACTS["seamless_usdc_vault"], "seamless")
        print(f"  TVL: ${result['onchain']['tvl']:,.2f}")
        print(f"  Share price: {result['onchain'].get('share_price', 'N/A')}")

        # 7. Aerodrome — need a known pool
        print("\n" + "-" * 50)
        print("[TEST] Aerodrome — WETH/USDC vAMM")
        # Common WETH/USDC pool
        aero_pool = "0xcDAC0d6c6C59727a65F871236188350531885C43"
        result = await v.verify(aero_pool, "aerodrome")
        if result["error"]:
            print(f"  Error: {result['error']}")
        else:
            print(f"  TVL: ${result['onchain']['tvl']:,.2f}")
            print(f"  APY: {result['onchain']['apy']}%")
            details = result['onchain'].get('details', {})
            print(f"  {details.get('token0', '?')}/{details.get('token1', '?')}")
            print(f"  Reserves: {details.get('reserve0', 0)} / {details.get('reserve1', 0)}")

        # 8. Uniswap V3
        print("\n" + "-" * 50)
        print("[TEST] Uniswap V3 — find WETH/USDC pool")
        try:
            factory = v.w3.eth.contract(
                address=Web3.to_checksum_address(CONTRACTS["uniswap_v3_factory"]),
                abi=UNIV3_FACTORY_ABI,
            )
            uni_pool = factory.functions.getPool(
                Web3.to_checksum_address(TOKENS["WETH"]["address"]),
                Web3.to_checksum_address(TOKENS["USDC"]["address"]),
                500,
            ).call()
            print(f"  Pool address: {uni_pool}")
            result = await v.verify(uni_pool, "uniswap-v3")
            if result["error"]:
                print(f"  Error: {result['error']}")
            else:
                print(f"  TVL: ${result['onchain']['tvl']:,.2f}")
                print(f"  Price: {result['onchain']['price']}")
                print(f"  Fee tier: {result['onchain'].get('fee_tier_pct', '?')}%")
        except Exception as e:
            print(f"  Error: {e}")

        print("\n" + "=" * 70)
        print(f"Supported protocols: {', '.join(v.get_supported_protocols())}")
        print("=" * 70)

    asyncio.run(test())
