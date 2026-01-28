"""
Swap wSOL -> USDC via CoW Swap (retry)
"""
import asyncio
import json
from dotenv import load_dotenv

load_dotenv()

async def main():
    from integrations.cow_swap import cow_client
    from web3 import Web3
    from services.agent_keys import decrypt_private_key
    
    # Load agent
    with open('data/deployed_agents.json') as f:
        data = json.load(f)
    
    agent_data = list(data.values())[0][0]
    AGENT = agent_data['agent_address']
    enc_key = agent_data['encrypted_private_key']
    AGENT_KEY = decrypt_private_key(enc_key)
    
    from eth_account import Account
    acc = Account.from_key(AGENT_KEY)
    if acc.address.lower() != AGENT.lower():
        print(f"❌ Key mismatch!")
        return
    
    print(f"✅ Agent: {AGENT}")
    
    w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
    
    WSOL = "0x1c61629598e4a901136a81bc138e5828dc150d67"
    USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    
    ERC20_ABI = [{"constant": True, "inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}]
    wsol = w3.eth.contract(address=Web3.to_checksum_address(WSOL), abi=ERC20_ABI)
    usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC), abi=ERC20_ABI)
    
    wsol_balance = wsol.functions.balanceOf(AGENT).call()
    print(f"wSOL: {wsol_balance / 1e9:.6f} (~${wsol_balance / 1e9 * 180:.2f})")
    print(f"ETH: {w3.eth.get_balance(AGENT) / 1e18:.6f}")
    
    if wsol_balance == 0:
        print("❌ No wSOL!")
        return
    
    usdc_before = usdc.functions.balanceOf(AGENT).call() / 1e6
    print(f"USDC before: ${usdc_before:.2f}")
    
    print(f"\n=== CoW Swap: wSOL -> USDC ===")
    
    result = await cow_client.swap(
        sell_token=WSOL,
        buy_token=USDC,
        sell_amount=wsol_balance,
        from_address=AGENT,
        private_key=AGENT_KEY,
        max_slippage_percent=3.0  # Higher slippage for low liquidity
    )
    
    # Result can be string (order_uid) or dict with order_uid key
    if isinstance(result, str):
        order_uid = result
    elif isinstance(result, dict):
        order_uid = result.get("order_uid")
    else:
        print(f"❌ CoW Swap failed: {result}")
        return
    
    if not order_uid:
        print(f"❌ No order_uid in result: {result}")
        return
    
    print(f"✅ Order: {order_uid[:50]}...")
    print(f"Explorer: https://explorer.cow.fi/base/orders/{order_uid}")
    print(f"Waiting for fill...")
    
    max_wait = 180  # 3 minutes
    waited = 0
    
    while waited < max_wait:
        status = await cow_client.get_order_status(order_uid)
        order_status = status.get("status", "unknown")
        
        if order_status == "fulfilled":
            usdc_received = int(status.get("executedBuyAmount", 0)) / 1e6
            print(f"\n🎉 SUCCESS! Received: ${usdc_received:.2f} USDC")
            break
        elif order_status in ["cancelled", "expired"]:
            print(f"\n❌ Order {order_status}")
            break
        
        await asyncio.sleep(10)
        waited += 10
        print(f"  {waited}s - {order_status}")
    
    usdc_after = usdc.functions.balanceOf(AGENT).call() / 1e6
    print(f"\nFinal USDC: ${usdc_after:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
