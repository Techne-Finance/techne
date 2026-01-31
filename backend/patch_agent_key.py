import json
from services.agent_keys import generate_agent_wallet, encrypt_private_key

# Generate new key for existing agent
pk, addr = generate_agent_wallet()
enc = encrypt_private_key(pk)

# Update deployed_agents.json
data = json.load(open('data/deployed_agents.json'))
user = list(data.keys())[0]
data[user][0]['encrypted_private_key'] = enc
json.dump(data, open('data/deployed_agents.json', 'w'), indent=2)

print(f"UPDATED: Added encrypted_private_key to agent {data[user][0]['agent_address'][:20]}...")
