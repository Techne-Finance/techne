"""
Verify ERC-8004 Contracts on BaseScan via Etherscan V2 API
Uses Standard JSON Input format from Hardhat build artifacts
"""
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASESCAN_API_KEY = os.getenv("BASESCAN_API_KEY")
# V2 API: https://api.etherscan.io/v2/api?chainid=8453
API_URL = "https://api.etherscan.io/v2/api"
CHAIN_ID = "8453"  # Base Mainnet

# Contracts to verify
CONTRACTS = [
    {
        "address": "0x8B3d7A48Ff5301F204E91C1aC2Ccc367a78d1c42",
        "name": "AgentIdentityRegistry",
        "path": "contracts/AgentIdentityRegistry.sol:AgentIdentityRegistry",
        "constructor_args": ""  # No constructor args
    },
    {
        "address": "0x68Aa2805A050A958c8CaaFE4fEC2830e9435d6d5",
        "name": "AgentReputationRegistry", 
        "path": "contracts/AgentReputationRegistry.sol:AgentReputationRegistry",
        "constructor_args": "0000000000000000000000008B3d7A48Ff5301F204E91C1aC2Ccc367a78d1c42"
    },
    {
        "address": "0x6f93C211695c2ea7D81c7A9139590835ef7A2364",
        "name": "TechneAgentFactoryV4",
        "path": "contracts/TechneAgentFactoryV4.sol:TechneAgentFactoryV4",
        # Constructor: implementation, sessionKey, identityRegistry (ABI encoded, no 0x prefix)
        "constructor_args": (
            "000000000000000000000000de70b3300f5fe05F4D698FEFe231cf8d874a6575"
            "000000000000000000000000a30A689ec0F9D717C5bA1098455B031b868B720f"
            "0000000000000000000000008B3d7A48Ff5301F204E91C1aC2Ccc367a78d1c42"
        )
    }
]

def get_build_info():
    """Load the Standard JSON Input from Hardhat build artifacts"""
    build_info_dir = Path(__file__).parent.parent / "artifacts" / "build-info"
    json_files = list(build_info_dir.glob("*.json"))
    
    if not json_files:
        print("❌ No build-info files found. Run: npx hardhat compile")
        return None
    
    latest = max(json_files, key=lambda p: p.stat().st_mtime)
    print(f"📄 Using build info: {latest.name}")
    
    with open(latest, 'r', encoding='utf-8') as f:
        return json.load(f)

def verify_contract(contract, build_info):
    """Submit contract for verification via V2 API"""
    print(f"\n🔍 Verifying {contract['name']} at {contract['address'][:10]}...")
    
    source_input = build_info.get("input", {})
    
    # V2 API uses chainid as query parameter
    url = f"{API_URL}?chainid={CHAIN_ID}"
    
    params = {
        "apikey": BASESCAN_API_KEY,
        "module": "contract",
        "action": "verifysourcecode",
        "contractaddress": contract["address"],
        "sourceCode": json.dumps(source_input),
        "codeformat": "solidity-standard-json-input",
        "contractname": contract["path"],
        "compilerversion": "v0.8.24+commit.e11b9ed9",
        "optimizationUsed": "1",
        "runs": "200",
        "evmversion": "paris",
        "constructorArguements": contract["constructor_args"]  # BaseScan typo
    }
    
    response = requests.post(url, data=params)
    result = response.json()
    
    if result.get("status") == "1":
        guid = result.get("result")
        print(f"✅ Submitted! GUID: {guid}")
        return guid
    else:
        print(f"❌ Failed: {result.get('result', result)}")
        return None

def main():
    if not BASESCAN_API_KEY:
        print("❌ BASESCAN_API_KEY not found in .env")
        return
    
    print("=" * 50)
    print("🔐 ERC-8004 Contract Verification (V2 API)")
    print("=" * 50)
    
    build_info = get_build_info()
    if not build_info:
        return
    
    guids = []
    for contract in CONTRACTS:
        guid = verify_contract(contract, build_info)
        if guid:
            guids.append((contract["name"], guid))
    
    if guids:
        print("\n" + "=" * 50)
        print("📋 Check status at:")
        for name, guid in guids:
            print(f"  {name}: https://basescan.org/address/{CONTRACTS[[c['name'] for c in CONTRACTS].index(name)]['address']}#code")

if __name__ == "__main__":
    main()
