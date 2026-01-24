"""Add test data to audit_trail for Reasoning Terminal demo"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')

headers = {
    'apikey': key,
    'Authorization': f'Bearer {key}',
    'Content-Type': 'application/json',
    'Prefer': 'return=minimal'
}

test_logs = [
    {'action': 'PROFITABILITY_GATE', 'gas_cost': 12.50, 'profit_usd': 8.20, 'reason': 'Gas exceeds profit margin'},
    {'action': 'SCAM_DETECTED', 'risk_score': 87, 'protocol': 'ShadyVault', 'reason': 'AI flagged honeypot pattern'},
    {'action': 'PARKING_ENGAGED', 'apy': 3.8, 'amount_usd': 5000, 'protocol': 'aave-v3'},
    {'action': 'ROTATION_BLOCKED', 'reason': 'TVL dropped 15%', 'protocol': 'morpho'},
    {'action': 'GAS_TOO_HIGH', 'gas_cost': 45.00, 'reason': 'Waiting for cheaper gas conditions'}
]

print("Adding test data to audit_trail...")
for log in test_logs:
    resp = requests.post(f'{url}/rest/v1/audit_trail', headers=headers, json=log)
    action = log['action']
    status = 'OK' if resp.status_code in [200, 201] else f'ERR {resp.status_code}'
    print(f"  {action}: {status}")

print("\nDone! Refresh Portfolio to see Reasoning Terminal")
