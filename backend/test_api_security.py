"""Check raw API response"""
import httpx
import json

POOL = "0x56c11053159a24c0731b4b12356bc1f0578fb474"

r = httpx.get(f'http://localhost:8080/api/scout/verify-rpc?pool_address={POOL}&chain=base', timeout=60)

data = r.json()
pool = data.get('pool', {})

print("Security fields in response:")
print(f"  security_status: {pool.get('security_status')}")
print(f"  security_result present: {'security_result' in pool}")

sec = pool.get('security_result', {})
if sec:
    print(f"  security_result.status: {sec.get('status')}")
    print(f"  security_result.tokens present: {'tokens' in sec}")
    tokens = sec.get('tokens', {})
    for addr, info in tokens.items():
        print(f"\n  Token {addr[:15]}...:")
        if info:
            print(f"    token_name: {info.get('token_name')}")
        else:
            print(f"    NO DATA (empty object)")
