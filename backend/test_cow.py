import asyncio
from integrations.cow_swap import cow_client
from services.agent_keys import decrypt_private_key
from api.agent_config_router import DEPLOYED_AGENTS

async def test():
    USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
    CBBTC = '0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf'
    
    agent = DEPLOYED_AGENTS.get('0xba9d6947c0ad6ea2aaa99507355cf83b4d098058'.lower(), [])[0]
    encrypted_pk = agent.get('encrypted_private_key')
    pk = decrypt_private_key(encrypted_pk)
    
    # Use swap() which includes approve
    print('Testing swap (with approve)...')
    order_uid = await cow_client.swap(
        sell_token=USDC,
        buy_token=CBBTC,
        sell_amount=20000000,  # 20 USDC
        from_address=agent.get('agent_address'),
        private_key=pk,
        max_slippage_percent=5.0  # 5% for cbBTC
    )
    print(f'Order UID: {order_uid}')

asyncio.run(test())
