"""
Portfolio Router - Aggregated Portfolio Data API
Returns all holdings, positions, and LP data in a single call for fast frontend loading.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from web3 import Web3
import asyncio
import os
from datetime import datetime

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

# Base RPC
RPC_URL = os.getenv("ALCHEMY_RPC_URL") or os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Token addresses on Base
USDC_ADDRESS = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
WETH_ADDRESS = Web3.to_checksum_address("0x4200000000000000000000000000000000000006")
CBBTC_ADDRESS = Web3.to_checksum_address("0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf")
AERO_ADDRESS = Web3.to_checksum_address("0x940181a94A35A4569E4529A3CDfB74e38FD98631")
WSOL_ADDRESS = Web3.to_checksum_address("0x1c61629598e4a901136a81bc138e5828dc150d67")  # wSOL on Base

# ERC20 ABI (just balanceOf)
ERC20_ABI = [{"constant": True, "inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}]

# Approximate prices (could be fetched from oracle later)
TOKEN_PRICES = {
    "USDC": 1.0,
    "USDT": 1.0,
    "DAI": 1.0,
    "ETH": 3300,
    "WETH": 3300,
    "cbBTC": 100000,
    "AERO": 1.5,
    "wSOL": 180,
    "VIRTUAL": 2.5,
    "DEGEN": 0.02,
    "BRETT": 0.15,
    "TOSHI": 0.0003,
    "HIGHER": 0.05,
}

# All tokens to check (address, symbol, decimals)
ALL_TOKENS = [
    ("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "USDC", 6),
    ("0x4200000000000000000000000000000000000006", "WETH", 18),
    ("0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf", "cbBTC", 8),
    ("0x940181a94A35A4569E4529A3CDfB74e38FD98631", "AERO", 18),
    ("0x1C61629598e4a901136a81BC138E5828dc150d67", "wSOL", 9),
    ("0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b", "VIRTUAL", 18),
    ("0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed", "DEGEN", 18),
    ("0x532f27101965dd16442E59d40670FaF5eBB142E4", "BRETT", 18),
    ("0xAC1Bd2486aAf3B5C0fc3Fd868558b082a531B2B4", "TOSHI", 18),
    ("0x0578d8A44db98B23BF096A382e016e29a5Ce0ffe", "HIGHER", 18),
]

# Minimum value threshold to show in portfolio
MIN_VALUE_USD = 0.10

class Holding(BaseModel):
    asset: str
    balance: float
    value_usd: float
    label: Optional[str] = None

class Position(BaseModel):
    id: str
    protocol: str
    pool_name: Optional[str] = None
    value_usd: float  # Current value
    apy: float = 0  # Real APY from DeFiLlama, 0 = unknown
    deposited: Optional[float] = None  # Entry value
    # Dual token amounts for LP positions
    token0_symbol: Optional[str] = None
    token0_amount: Optional[float] = None
    token1_symbol: Optional[str] = None
    token1_amount: Optional[float] = None
    # PnL
    pnl: Optional[float] = None
    entry_value: Optional[float] = None

class PortfolioResponse(BaseModel):
    success: bool
    holdings: List[Holding]
    positions: List[Position]
    total_value_usd: float
    agent_address: Optional[str] = None
    cached_at: str
    load_time_ms: float


def get_token_balance_sync(token_address: str, wallet_address: str, decimals: int = 18) -> float:
    """Get ERC20 token balance synchronously"""
    try:
        contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
        balance = contract.functions.balanceOf(Web3.to_checksum_address(wallet_address)).call()
        return balance / (10 ** decimals)
    except Exception as e:
        print(f"[Portfolio] Balance fetch error for {token_address}: {e}")
        return 0.0


def get_eth_balance_sync(wallet_address: str) -> float:
    """Get ETH balance synchronously"""
    try:
        balance = w3.eth.get_balance(Web3.to_checksum_address(wallet_address))
        return balance / 1e18
    except Exception as e:
        print(f"[Portfolio] ETH balance error: {e}")
        return 0.0


async def fetch_all_balances(agent_address: str) -> List[Holding]:
    """Fetch all token balances in parallel using thread pool"""
    loop = asyncio.get_event_loop()
    
    # Build tasks dynamically from ALL_TOKENS list + ETH
    tasks = []
    for token_addr, symbol, decimals in ALL_TOKENS:
        tasks.append(loop.run_in_executor(None, get_token_balance_sync, token_addr, agent_address, decimals))
    # Add native ETH at the end
    tasks.append(loop.run_in_executor(None, get_eth_balance_sync, agent_address))
    
    # Execute all in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    holdings = []
    
    # Process ERC20 tokens
    for i, (token_addr, symbol, decimals) in enumerate(ALL_TOKENS):
        balance = results[i] if not isinstance(results[i], Exception) else 0
        if balance > 0:
            price = TOKEN_PRICES.get(symbol, 0)  # Default to 0 if no price (skip unknown)
            if price > 0:
                value = balance * price
                if value >= MIN_VALUE_USD:  # Only show if worth >= $0.10
                    holdings.append(Holding(
                        asset=symbol,
                        balance=round(balance, 8),
                        value_usd=round(value, 2),
                        label=f"Agent {symbol} balance"
                    ))
    
    # Process native ETH
    eth_balance = results[-1] if not isinstance(results[-1], Exception) else 0
    if eth_balance > 0:
        eth_value = eth_balance * TOKEN_PRICES.get("ETH", 3300)
        if eth_value >= MIN_VALUE_USD:
            holdings.append(Holding(
                asset="ETH",
                balance=round(eth_balance, 8),
                value_usd=round(eth_value, 2),
                label="Agent ETH balance"
            ))
    
    return holdings


async def fetch_lp_positions(user_address: str, agent_address: str) -> List[Position]:
    """Fetch LP positions directly from known Aerodrome pools"""
    try:
        if not agent_address:
            return []
        
        # Known Aerodrome LP tokens on Base with pool addresses for APY lookup
        LP_TOKENS = [
            {"name": "cbBTC/USDC", "address": "0x9c38b55f9a9aba91bbcedeb12bf4428f47a6a0b8", "protocol": "Aerodrome", 
             "token0": "cbBTC", "token0_decimals": 8, "token0_price": 100000,
             "token1": "USDC", "token1_decimals": 6, "token1_price": 1.0},
            {"name": "WETH/USDC", "address": "0xb4cb800910B228ED3d0834cF79D697127BBB00e5", "protocol": "Aerodrome",
             "token0": "WETH", "token0_decimals": 18, "token0_price": 3300,
             "token1": "USDC", "token1_decimals": 6, "token1_price": 1.0},
            {"name": "AERO/USDC", "address": "0x6cDcb1C4A4D1C3C6d054b27AC5B77e89eAFb971d", "protocol": "Aerodrome",
             "token0": "AERO", "token0_decimals": 18, "token0_price": 1.5,
             "token1": "USDC", "token1_decimals": 6, "token1_price": 1.0},
        ]
        
        # Get real APY from The Graph or DeFiLlama
        pool_apy_cache = {}
        try:
            from data_sources.thegraph import TheGraphClient
            graph_client = TheGraphClient()
            
            for lp in LP_TOKENS:
                try:
                    apy = await graph_client.get_pool_apy(lp["address"])
                    if apy is not None and apy > 0:
                        pool_apy_cache[lp['address'].lower()] = round(apy, 2)
                        print(f"[Portfolio] Got APY for {lp['name']}: {apy:.2f}%")
                except Exception as e:
                    print(f"[Portfolio] APY fetch error for {lp['name']}: {e}")
        except Exception as e:
            print(f"[Portfolio] TheGraphClient init error: {e}")
        
        positions = []
        agent_checksummed = Web3.to_checksum_address(agent_address)
        
        for lp in LP_TOKENS:
            try:
                # balanceOf(agent)
                balance_call = w3.eth.call({
                    'to': Web3.to_checksum_address(lp["address"]),
                    'data': '0x70a08231' + agent_address[2:].lower().zfill(64)
                })
                balance = int(balance_call.hex(), 16)
                
                # Skip dust amounts (less than 0.000001 LP tokens)
                if balance > 1e12:  # At least 0.000001 LP tokens (1e12 of 1e18)
                    lp_tokens = balance / 1e18
                    
                    # Get reserves and calculate USD value + token amounts
                    token0_amount = 0
                    token1_amount = 0
                    try:
                        reserves_call = w3.eth.call({
                            'to': Web3.to_checksum_address(lp["address"]),
                            'data': '0x0902f1ac'  # getReserves()
                        })
                        reserve0 = int(reserves_call.hex()[2:66], 16)
                        reserve1 = int(reserves_call.hex()[66:130], 16)
                        
                        supply_call = w3.eth.call({
                            'to': Web3.to_checksum_address(lp["address"]),
                            'data': '0x18160ddd'  # totalSupply()
                        })
                        total_supply = int(supply_call.hex(), 16)
                        
                        if total_supply > 0:
                            share = balance / total_supply
                            # Original value calculation (proven to work)
                            # reserve1 is USDC side, multiply by 2 for both sides
                            estimated_value = (reserve1 / 1e6) * share * 2
                            
                            # Calculate token amounts for display only
                            token0_amount = (reserve0 / (10 ** lp["token0_decimals"])) * share
                            token1_amount = (reserve1 / (10 ** lp["token1_decimals"])) * share
                        else:
                            estimated_value = lp_tokens
                    except Exception as e:
                        print(f"[Portfolio] Reserve fetch error: {e}")
                        estimated_value = lp_tokens * 1.0
                    
                    # Get real APY from cache, fallback to 0 (unknown)
                    real_apy = pool_apy_cache.get(lp["address"].lower(), 0)
                    
                    # Entry value - for now use current value (no historical data)
                    # TODO: Get real entry_value from user_positions table
                    entry_value = estimated_value
                    pnl = estimated_value - entry_value  # Will be 0 until we track entry
                    
                    if estimated_value > 0.10:  # Only show if > $0.10
                        positions.append(Position(
                            id=f"lp_{len(positions)}",
                            protocol=lp["protocol"],
                            pool_name=lp["name"],
                            value_usd=round(estimated_value, 2),
                            apy=real_apy,
                            deposited=round(entry_value, 2),
                            entry_value=round(entry_value, 2),
                            pnl=round(pnl, 2),
                            token0_symbol=lp["token0"],
                            token0_amount=round(token0_amount, 8),
                            token1_symbol=lp["token1"],
                            token1_amount=round(token1_amount, 6)
                        ))
            except Exception as e:
                print(f"[Portfolio] LP check error for {lp['name']}: {e}")
                continue
        
        return positions
    except Exception as e:
        print(f"[Portfolio] LP positions error: {e}")
        return []


@router.get("/{user_address}", response_model=PortfolioResponse)
async def get_portfolio(user_address: str):
    """
    Get complete portfolio data in a single call.
    Fetches all balances and positions in parallel for fast loading.
    """
    import time
    start = time.time()
    
    # Get agent address from stored agents
    agent_address = None
    try:
        agents = []
        user_lower = user_address.lower()
        
        # Try agent_config_router DEPLOYED_AGENTS first (main source)
        try:
            from api.agent_config_router import DEPLOYED_AGENTS
            agents = DEPLOYED_AGENTS.get(user_lower, [])
            if agents:
                print(f"[Portfolio] Found {len(agents)} agents in DEPLOYED_AGENTS")
        except Exception as e:
            print(f"[Portfolio] DEPLOYED_AGENTS lookup error: {e}")
        
        # Fallback to Supabase
        if not agents:
            try:
                from infrastructure.supabase_client import SupabaseClient
                supabase = SupabaseClient()
                if supabase.is_available:
                    agents = await supabase.get_user_agents(user_address)
            except:
                pass
        
        # Fallback to agent_router deployed_agents
        if not agents:
            try:
                from api.agent_router import deployed_agents
                agents = deployed_agents.get(user_lower, [])
            except:
                pass
        
        if agents and len(agents) > 0:
            agent_address = agents[0].get("agent_address") or agents[0].get("address")
            print(f"[Portfolio] Using agent: {agent_address}")
    except Exception as e:
        print(f"[Portfolio] Agent lookup error: {e}")
    
    holdings = []
    positions = []
    
    if agent_address:
        # Fetch holdings and positions in parallel
        holdings_task = fetch_all_balances(agent_address)
        positions_task = fetch_lp_positions(user_address, agent_address)
        
        holdings, positions = await asyncio.gather(holdings_task, positions_task)
    
    # Calculate total
    total = sum(h.value_usd for h in holdings) + sum(p.value_usd for p in positions)
    
    load_time = (time.time() - start) * 1000
    print(f"[Portfolio] Loaded in {load_time:.0f}ms - {len(holdings)} holdings, {len(positions)} positions")
    
    return PortfolioResponse(
        success=True,
        holdings=holdings,
        positions=positions,
        total_value_usd=round(total, 2),
        agent_address=agent_address,
        cached_at=datetime.utcnow().isoformat() + "Z",
        load_time_ms=round(load_time, 1)
    )


class ClosePositionRequest(BaseModel):
    user_address: str
    position_id: str
    protocol: str
    percentage: int  # 25, 50, or 100
    amount: Optional[int] = None


@router.post("/position/close")
async def close_position(request: ClosePositionRequest):
    """
    Close a position (LP or single-sided).
    Executes on-chain withdrawal and swap to USDC.
    """
    from services.agent_keys import decrypt_private_key
    from api.agent_config_router import DEPLOYED_AGENTS
    from eth_account import Account
    import time
    
    print(f"[Position Close] Request: {request.user_address} closing {request.percentage}% of {request.protocol}")
    
    try:
        # Get agent config
        user_agents = DEPLOYED_AGENTS.get(request.user_address.lower(), [])
        if not user_agents:
            return {"success": False, "error": "No agent found for user"}
        
        agent = user_agents[0]
        agent_address = agent.get("agent_address")
        encrypted_pk = agent.get("encrypted_private_key")
        
        if not encrypted_pk:
            return {"success": False, "error": "Agent has no private key"}
        
        # Decrypt private key
        pk = decrypt_private_key(encrypted_pk)
        account = Account.from_key(pk)
        
        # LP position close (Aerodrome)
        if request.protocol.lower() == "aerodrome":
            from web3 import Web3
            
            w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))
            
            LP_TOKEN = '0x9c38b55f9a9aba91bbcedeb12bf4428f47a6a0b8'  # cbBTC/USDC
            ROUTER = '0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43'
            CBBTC = '0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf'
            USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
            FACTORY = '0x420DD381b31aEf6683db6B902084cB0FFECe40Da'
            
            ERC20_ABI = [{"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"type":"bool"}],"stateMutability":"nonpayable","type":"function"},
                        {"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"}]
            
            ROUTER_ABI = [
                {"inputs":[{"name":"tokenA","type":"address"},{"name":"tokenB","type":"address"},{"name":"stable","type":"bool"},{"name":"liquidity","type":"uint256"},{"name":"amountAMin","type":"uint256"},{"name":"amountBMin","type":"uint256"},{"name":"to","type":"address"},{"name":"deadline","type":"uint256"}],"name":"removeLiquidity","outputs":[{"name":"amountA","type":"uint256"},{"name":"amountB","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
                {"inputs":[{"name":"amountIn","type":"uint256"},{"name":"amountOutMin","type":"uint256"},{"components":[{"name":"from","type":"address"},{"name":"to","type":"address"},{"name":"stable","type":"bool"},{"name":"factory","type":"address"}],"name":"routes","type":"tuple[]"},{"name":"to","type":"address"},{"name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"}
            ]
            
            lp_contract = w3.eth.contract(address=Web3.to_checksum_address(LP_TOKEN), abi=ERC20_ABI)
            cbbtc_contract = w3.eth.contract(address=Web3.to_checksum_address(CBBTC), abi=ERC20_ABI)
            router = w3.eth.contract(address=Web3.to_checksum_address(ROUTER), abi=ROUTER_ABI)
            
            # Get LP balance
            lp_balance = lp_contract.functions.balanceOf(Web3.to_checksum_address(agent_address)).call()
            
            if lp_balance < 1e12:  # Dust check
                return {"success": True, "message": "Position already closed (dust only)", "lp_balance": lp_balance}
            
            # Calculate amount to close
            close_amount = int(lp_balance * request.percentage / 100)
            
            def send_tx(contract_call, gas=300000):
                tx = contract_call.build_transaction({
                    'from': account.address,
                    'nonce': w3.eth.get_transaction_count(account.address, 'latest'),
                    'gas': gas,
                    'gasPrice': int(w3.eth.gas_price * 3),
                    'chainId': 8453
                })
                signed = account.sign_transaction(tx)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                return receipt.status == 1, tx_hash.hex()
            
            # Step 1: Approve LP
            success, tx_hash = send_tx(lp_contract.functions.approve(Web3.to_checksum_address(ROUTER), close_amount))
            if not success:
                return {"success": False, "error": "LP approve failed", "tx": tx_hash}
            
            # Step 2: Remove liquidity
            deadline = int(time.time()) + 1200
            success, tx_hash = send_tx(router.functions.removeLiquidity(
                Web3.to_checksum_address(CBBTC),
                Web3.to_checksum_address(USDC),
                False, close_amount, 0, 0,
                account.address, deadline
            ))
            if not success:
                return {"success": False, "error": "Remove liquidity failed", "tx": tx_hash}
            
            # Step 3: Swap cbBTC to USDC
            time.sleep(2)
            cbbtc_balance = cbbtc_contract.functions.balanceOf(Web3.to_checksum_address(agent_address)).call()
            
            if cbbtc_balance > 0:
                send_tx(cbbtc_contract.functions.approve(Web3.to_checksum_address(ROUTER), cbbtc_balance))
                routes = [(Web3.to_checksum_address(CBBTC), Web3.to_checksum_address(USDC), False, Web3.to_checksum_address(FACTORY))]
                deadline = int(time.time()) + 1200
                success, tx_hash = send_tx(router.functions.swapExactTokensForTokens(
                    cbbtc_balance, 0, routes, account.address, deadline
                ))
            
            return {"success": True, "message": f"Closed {request.percentage}% of cbBTC/USDC", "tx": tx_hash}
        
        return {"success": False, "error": f"Protocol {request.protocol} close not implemented"}
        
    except Exception as e:
        print(f"[Position Close] Error: {e}")
        return {"success": False, "error": str(e)}
