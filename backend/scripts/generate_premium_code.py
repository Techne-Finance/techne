"""Generate premium activation code directly in Supabase (dev/admin tool)"""
import os
import sys
import secrets
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

def generate_code():
    part1 = secrets.token_hex(2).upper()
    part2 = secrets.token_hex(2).upper()
    return f"ARTISAN-{part1}-{part2}"

def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("ERROR: SUPABASE_URL or SUPABASE_KEY not set")
        return
    
    supabase = create_client(url, key)
    
    wallet = "0xba9d6947c0ad6ea2aaa99507355cf83b4d098058"
    code = generate_code()
    expires = (datetime.now() + timedelta(days=365)).isoformat()
    
    # Check existing
    existing = supabase.table("premium_subscriptions").select("*").eq(
        "user_address", wallet
    ).execute()
    
    if existing.data:
        sub = existing.data[0]
        print(f"Existing subscription found. Status: {sub['status']}")
        print(f"Old code: {sub.get('activation_code')}")
        
        # Update with new code
        supabase.table("premium_subscriptions").update({
            "status": "active",
            "activation_code": code,
            "code_used_at": None,
            "telegram_chat_id": None,
            "expires_at": expires,
        }).eq("user_address", wallet).execute()
        
        print(f"\n=== UPDATED ===")
    else:
        # Insert new
        supabase.table("premium_subscriptions").insert({
            "user_address": wallet,
            "status": "active",
            "autonomy_mode": "full_auto",
            "activation_code": code,
            "expires_at": expires,
            "x402_payment_id": "dev-admin-manual"
        }).execute()
        
        print(f"\n=== CREATED ===")
    
    print(f"Wallet:  {wallet}")
    print(f"Code:    {code}")
    print(f"Expires: {expires[:10]}")
    print(f"\nSend to bot: /start {code}")

if __name__ == "__main__":
    main()
