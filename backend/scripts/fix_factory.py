"""
Fix Factory to allow deployments by zeroing defaultSessionKey
"""
from web3 import Web3
from eth_account import Account
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

RPC_URL = os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
FACTORY = "0x557049646BDe5B7C7eE2C08256Aea59A5A48B20f"

w3 = Web3(Web3.HTTPProvider(RPC_URL))
pk = PRIVATE_KEY if PRIVATE_KEY.startswith('0x') else f'0x{PRIVATE_KEY}'
signer = Account.from_key(pk)

print(f"Signer: {signer.address}")

# Factory ABI for setDefaultSessionKey
FACTORY_ABI = [
    {
        'inputs': [
            {'name': 'key', 'type': 'address'},
            {'name': 'validity', 'type': 'uint48'},
            {'name': 'dailyLimitUSD', 'type': 'uint256'}
        ],
        'name': 'setDefaultSessionKey',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function'
    },
    {'inputs': [], 'name': 'defaultSessionKey', 'outputs': [{'type': 'address'}], 'stateMutability': 'view', 'type': 'function'},
    {'inputs': [], 'name': 'owner', 'outputs': [{'type': 'address'}], 'stateMutability': 'view', 'type': 'function'}
]

factory = w3.eth.contract(address=FACTORY, abi=FACTORY_ABI)

# Check current state
current_sk = factory.functions.defaultSessionKey().call()
owner = factory.functions.owner().call()
print(f"Factory owner: {owner}")
print(f"Current defaultSessionKey: {current_sk}")

if signer.address.lower() != owner.lower():
    print(f"ERROR: Signer {signer.address} is not factory owner {owner}")
    exit(1)

if current_sk == "0x0000000000000000000000000000000000000000":
    print("Already set to zero address, no action needed")
    exit(0)

print("\nSetting defaultSessionKey to zero...")

# Build and send transaction
tx = factory.functions.setDefaultSessionKey(
    "0x0000000000000000000000000000000000000000",  # Zero address = no session key
    0,  # validity
    0   # dailyLimit
).build_transaction({
    "from": signer.address,
    "nonce": w3.eth.get_transaction_count(signer.address),
    "gas": 100000,
    "maxFeePerGas": w3.eth.gas_price * 2,
    "maxPriorityFeePerGas": w3.to_wei(0.01, 'gwei'),
    "chainId": 8453
})

signed = signer.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f"TX sent: {tx_hash.hex()}")

receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
print(f"Status: {'SUCCESS' if receipt.status == 1 else 'FAILED'}")

# Verify
new_sk = factory.functions.defaultSessionKey().call()
print(f"New defaultSessionKey: {new_sk}")
