"""
Deploy Smart Account for stuck funds recovery
"""
from web3 import Web3
from eth_account import Account
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

RPC_URL = os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")
FACTORY = "0x557049646BDe5B7C7eE2C08256Aea59A5A48B20f"
OWNER = "0xbA9D6947C0aD6eA2AaA99507355cf83B4D098058"
AGENT_ID = "agent_1_1769873174"

w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Calculate salt from agent_id
agent_bytes = AGENT_ID.encode('utf-8')
hash_bytes = w3.keccak(agent_bytes)
salt = int.from_bytes(hash_bytes[:32], 'big')

print(f"Owner: {OWNER}")
print(f"Agent ID: {AGENT_ID}")
print(f"Salt: {salt}")

# Factory ABI
FACTORY_ABI = [
    {
        "inputs": [{"name": "owner", "type": "address"}, {"name": "agentSalt", "type": "uint256"}],
        "name": "createAccount",
        "outputs": [{"name": "account", "type": "address"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "owner", "type": "address"}, {"name": "agentSalt", "type": "uint256"}],
        "name": "getAddress",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

factory = w3.eth.contract(address=FACTORY, abi=FACTORY_ABI)

# Verify predicted address
predicted = factory.functions.getAddress(OWNER, salt).call()
print(f"\nPredicted address: {predicted}")

# Check if already deployed
code = w3.eth.get_code(predicted)
if len(code) > 2:
    print(f"\n✓ Already deployed! Code length: {len(code)} bytes")
else:
    print(f"\n✗ NOT deployed yet. Building deploy transaction...")
    
    # Build transaction for MetaMask
    tx_data = factory.functions.createAccount(OWNER, salt).build_transaction({'from': OWNER, 'gas': 500000, 'value': 0, 'chainId': 8453})['data']
    
    print(f"\n=== TRANSACTION FOR METAMASK ===")
    print(f"To: {FACTORY}")
    print(f"Data: {tx_data}")
    print(f"Value: 0")
    print(f"\nCopy this and send via MetaMask or use the frontend to re-deploy!")
