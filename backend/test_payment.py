"""Test script for payment flow"""
from agents import merchant

print("=== PAYMENT FLOW TEST ===\n")

# 1. Create micropayment request
print("1. Creating $0.10 micropayment request...")
payment = merchant.create_pool_access_request("user123", "pool_abc_123")
print(f"   Payment ID: {payment.id}")
print(f"   Amount USD: ${payment.amount_usd}")
print(f"   Amount USDC: {payment.amount_usdc} (6 decimals)")
print(f"   Recipient: {payment.recipient_address}")
print(f"   Expires: {payment.expires_at}")
print(f"   Status: {payment.status}")

# 2. Generate x402 header
print("\n2. Generated x402 Headers:")
headers = merchant.generate_x402_header(payment)
for k, v in headers.items():
    print(f"   {k}: {v}")

# 3. Check pending payments
print(f"\n3. Pending payments count: {len(merchant.pending_payments)}")

# 4. Simulate manual confirmation
print("\n4. Simulating payment confirmation...")
confirmed = merchant.manually_confirm_payment(payment.id, "tx_hash_0x123abc")
print(f"   Confirmed: {confirmed}")

# 5. Check access after payment
print("\n5. Access check after payment:")
print(f"   Pool access granted: {'pool_abc_123' in merchant.access_grants.get('user123', [])}")
print(f"   Confirmed payments: {len(merchant.confirmed_payments)}")

print("\n=== PAYMENT FLOW OK! ===")
