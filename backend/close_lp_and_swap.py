"""
Close LP Position and Swap everything to USDC
1. Remove liquidity from Aerodrome cbBTC/USDC pool
2. Swap cbBTC to USDC
"""
from web3 import Web3
from eth_account import Account
from services.agent_keys import decrypt_private_key
from api.agent_config_router import DEPLOYED_AGENTS
import time

# Config
AGENT_ADDR = '0x8FE9c7b9a195D37C789D3529E6903394a52b5e82'
USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
CBBTC = '0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf'
ROUTER = '0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43'
FACTORY = '0x420DD381b31aEf6683db6B902084cB0FFECe40Da'
LP_TOKEN = '0x9c38b55f9a9aba91bbcedeb12bf4428f47a6a0b8'  # cbBTC/USDC LP

w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))

# ABIs
ERC20_ABI = [
    {"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"type":"bool"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"}
]

ROUTER_ABI = [
    # removeLiquidity
    {"inputs":[
        {"name":"tokenA","type":"address"},
        {"name":"tokenB","type":"address"},
        {"name":"stable","type":"bool"},
        {"name":"liquidity","type":"uint256"},
        {"name":"amountAMin","type":"uint256"},
        {"name":"amountBMin","type":"uint256"},
        {"name":"to","type":"address"},
        {"name":"deadline","type":"uint256"}
    ],"name":"removeLiquidity","outputs":[{"name":"amountA","type":"uint256"},{"name":"amountB","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
    # swapExactTokensForTokens
    {"inputs":[
        {"name":"amountIn","type":"uint256"},
        {"name":"amountOutMin","type":"uint256"},
        {"components":[{"name":"from","type":"address"},{"name":"to","type":"address"},{"name":"stable","type":"bool"},{"name":"factory","type":"address"}],"name":"routes","type":"tuple[]"},
        {"name":"to","type":"address"},
        {"name":"deadline","type":"uint256"}
    ],"name":"swapExactTokensForTokens","outputs":[{"name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"}
]

# Contracts
lp_contract = w3.eth.contract(address=Web3.to_checksum_address(LP_TOKEN), abi=ERC20_ABI)
cbbtc_contract = w3.eth.contract(address=Web3.to_checksum_address(CBBTC), abi=ERC20_ABI)
usdc_contract = w3.eth.contract(address=Web3.to_checksum_address(USDC), abi=ERC20_ABI)
router = w3.eth.contract(address=Web3.to_checksum_address(ROUTER), abi=ROUTER_ABI)

# Get current balances
lp_bal = lp_contract.functions.balanceOf(Web3.to_checksum_address(AGENT_ADDR)).call()
cbbtc_bal = cbbtc_contract.functions.balanceOf(Web3.to_checksum_address(AGENT_ADDR)).call()
usdc_bal = usdc_contract.functions.balanceOf(Web3.to_checksum_address(AGENT_ADDR)).call()

print('=' * 50)
print('Current Balances:')
print(f'  LP Tokens: {lp_bal / 1e18:.18f}')
print(f'  cbBTC: {cbbtc_bal / 1e8:.8f}')
print(f'  USDC: {usdc_bal / 1e6:.6f}')
print('=' * 50)

if lp_bal == 0:
    print('\n❌ No LP tokens to remove!')
    exit(0)

# Load private key
agent = DEPLOYED_AGENTS.get('0xba9d6947c0ad6ea2aaa99507355cf83b4d098058'.lower(), [])[0]
encrypted_pk = agent.get('encrypted_private_key')
pk = decrypt_private_key(encrypted_pk)
account = Account.from_key(pk)
print(f'\nAgent wallet: {account.address}')

def send_tx(contract_call, gas=200000):
    """Build and send transaction"""
    tx = contract_call.build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address, 'latest'),
        'gas': gas,
        'gasPrice': int(w3.eth.gas_price * 3),  # 3x for faster confirmation
        'chainId': 8453
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f'  TX: https://basescan.org/tx/{tx_hash.hex()}')
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    status = '✅ Success' if receipt.status == 1 else '❌ Failed'
    print(f'  Status: {status}')
    return receipt.status == 1

# Step 1: Approve LP tokens for Router
print('\n[1/4] Approving LP tokens for Router...')
if not send_tx(lp_contract.functions.approve(Web3.to_checksum_address(ROUTER), lp_bal)):
    print('Approve failed!')
    exit(1)

# Step 2: Remove Liquidity
print('\n[2/4] Removing Liquidity...')
deadline = int(time.time()) + 1200  # 20 min

# Min amounts with 5% slippage
min_cbbtc = 0  # Accept any amount
min_usdc = 0   # Accept any amount

if not send_tx(router.functions.removeLiquidity(
    Web3.to_checksum_address(CBBTC),
    Web3.to_checksum_address(USDC),
    False,  # not stable pool
    lp_bal,
    min_cbbtc,
    min_usdc,
    account.address,
    deadline
), gas=300000):
    print('Remove liquidity failed!')
    exit(1)

# Wait and refresh balances
time.sleep(3)
cbbtc_bal = cbbtc_contract.functions.balanceOf(Web3.to_checksum_address(AGENT_ADDR)).call()
usdc_bal = usdc_contract.functions.balanceOf(Web3.to_checksum_address(AGENT_ADDR)).call()
print(f'\n  After removal:')
print(f'    cbBTC: {cbbtc_bal / 1e8:.8f}')
print(f'    USDC: {usdc_bal / 1e6:.6f}')

if cbbtc_bal == 0:
    print('\n✅ Already all in USDC!')
    print(f'Final USDC balance: {usdc_bal / 1e6:.6f}')
    exit(0)

# Step 3: Approve cbBTC for swap
print('\n[3/4] Approving cbBTC for swap...')
if not send_tx(cbbtc_contract.functions.approve(Web3.to_checksum_address(ROUTER), cbbtc_bal)):
    print('Approve failed!')
    exit(1)

# Step 4: Swap cbBTC -> USDC
print(f'\n[4/4] Swapping {cbbtc_bal / 1e8:.8f} cbBTC -> USDC...')
deadline = int(time.time()) + 1200
routes = [(
    Web3.to_checksum_address(CBBTC),
    Web3.to_checksum_address(USDC),
    False,  # not stable
    Web3.to_checksum_address(FACTORY)
)]

if not send_tx(router.functions.swapExactTokensForTokens(
    cbbtc_bal,
    0,  # Accept any output (0 slippage protection for small amounts)
    routes,
    account.address,
    deadline
), gas=300000):
    print('Swap failed!')
    exit(1)

# Final balances
time.sleep(3)
final_cbbtc = cbbtc_contract.functions.balanceOf(Web3.to_checksum_address(AGENT_ADDR)).call()
final_usdc = usdc_contract.functions.balanceOf(Web3.to_checksum_address(AGENT_ADDR)).call()

print('\n' + '=' * 50)
print('🎉 COMPLETE! Final Balances:')
print(f'  cbBTC: {final_cbbtc / 1e8:.8f}')
print(f'  USDC: {final_usdc / 1e6:.6f}')
print('=' * 50)
