"""
Pro Pack Bundle System for Techne.finance
- $1 = 5 pools for 24 hours
- Pools can be dismissed (no replacement)
- Session expires after 24h
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import secrets
import json


@dataclass
class ProPackSession:
    """Pro Pack subscription session"""
    session_id: str
    user_wallet: Optional[str]  # Wallet address if connected
    pools: List[Dict[str, Any]]  # 5 assigned pools
    dismissed_pool_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=24))
    paid: bool = False
    tx_hash: Optional[str] = None
    price_usd: float = 1.00
    
    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at
    
    @property
    def active_pools(self) -> List[Dict[str, Any]]:
        """Return pools that haven't been dismissed"""
        return [p for p in self.pools if p.get("id") not in self.dismissed_pool_ids]
    
    @property
    def remaining_count(self) -> int:
        return len(self.active_pools)
    
    def dismiss_pool(self, pool_id: str) -> bool:
        """Dismiss a pool (no replacement)"""
        if pool_id not in self.dismissed_pool_ids:
            self.dismissed_pool_ids.append(pool_id)
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_wallet": self.user_wallet,
            "pools_count": len(self.pools),
            "active_count": self.remaining_count,
            "dismissed_count": len(self.dismissed_pool_ids),
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_expired": self.is_expired,
            "paid": self.paid,
            "price_usd": self.price_usd
        }


# In-memory storage (use Redis in production)
_pro_sessions: Dict[str, ProPackSession] = {}

# Track user sessions by wallet
_user_sessions: Dict[str, str] = {}  # wallet -> session_id

# Track user subscriptions (Pro tier)
_user_subscriptions: Dict[str, Dict] = {}  # wallet -> subscription info


def get_user_subscription(user_wallet: str) -> Optional[Dict]:
    """Get user's active subscription status"""
    if not user_wallet:
        return None
    
    wallet = user_wallet.lower()
    subscription = _user_subscriptions.get(wallet)
    
    if subscription:
        # Check if expired
        from datetime import datetime
        expires_at = subscription.get("expires_at")
        if expires_at and datetime.now() < expires_at:
            return {
                "active": True,
                "tier": subscription.get("tier", "pro"),
                "expires_at": expires_at.isoformat(),
                "features": [
                    "Unlimited pool refresh",
                    "Telegram alerts",
                    "Airdrop agent access",
                    "Priority API access"
                ]
            }
    
    return {"active": False, "tier": "free"}


def activate_subscription(user_wallet: str, tier: str = "pro", duration_days: int = 30) -> Dict:
    """Activate a subscription for a user after payment"""
    from datetime import datetime, timedelta
    
    wallet = user_wallet.lower()
    expires_at = datetime.now() + timedelta(days=duration_days)
    
    _user_subscriptions[wallet] = {
        "tier": tier,
        "expires_at": expires_at,
        "activated_at": datetime.now()
    }
    
    return {
        "active": True,
        "tier": tier,
        "expires_at": expires_at.isoformat()
    }

def create_pro_pack_session(
    pools: List[Dict[str, Any]],
    user_wallet: Optional[str] = None,
    price_usd: float = 1.00
) -> ProPackSession:
    """
    Create a new Pro Pack session with 5 assigned pools
    """
    session_id = secrets.token_urlsafe(16)
    
    # Take only first 5 pools
    assigned_pools = pools[:5]
    
    session = ProPackSession(
        session_id=session_id,
        user_wallet=user_wallet,
        pools=assigned_pools,
        price_usd=price_usd
    )
    
    _pro_sessions[session_id] = session
    
    # Link to user wallet if provided
    if user_wallet:
        _user_sessions[user_wallet.lower()] = session_id
    
    print(f"[ProPack] Created session {session_id} with {len(assigned_pools)} pools")
    return session


def get_pro_session(session_id: str) -> Optional[ProPackSession]:
    """Get Pro Pack session by ID"""
    session = _pro_sessions.get(session_id)
    if session and session.is_expired:
        # Cleanup expired session
        del _pro_sessions[session_id]
        if session.user_wallet:
            _user_sessions.pop(session.user_wallet.lower(), None)
        return None
    return session


def get_user_active_session(user_wallet: str) -> Optional[ProPackSession]:
    """Get active Pro Pack session for user"""
    session_id = _user_sessions.get(user_wallet.lower())
    if session_id:
        return get_pro_session(session_id)
    return None


def mark_pro_session_paid(session_id: str, tx_hash: str) -> bool:
    """Mark Pro Pack session as paid"""
    session = get_pro_session(session_id)
    if session:
        session.paid = True
        session.tx_hash = tx_hash
        print(f"[ProPack] Session {session_id} marked as paid: {tx_hash}")
        return True
    return False


def dismiss_pool_from_session(session_id: str, pool_id: str) -> Dict[str, Any]:
    """Dismiss a pool from Pro Pack session"""
    session = get_pro_session(session_id)
    if not session:
        return {"success": False, "error": "Session not found or expired"}
    if not session.paid:
        return {"success": False, "error": "Session not paid"}
    
    if session.dismiss_pool(pool_id):
        return {
            "success": True,
            "remaining_count": session.remaining_count,
            "message": f"Pool dismissed. {session.remaining_count} pools remaining."
        }
    return {"success": False, "error": "Pool already dismissed or not found"}


def get_pro_pack_status(session_id: str) -> Dict[str, Any]:
    """Get status of Pro Pack session"""
    session = get_pro_session(session_id)
    if not session:
        return {"active": False, "error": "No active session"}
    
    return {
        "active": True,
        "session": session.to_dict(),
        "pools": session.active_pools if session.paid else []
    }


# ============================================
# CLI TEST
# ============================================

if __name__ == "__main__":
    # Test Pro Pack
    test_pools = [
        {"id": "pool1", "symbol": "ETH-USDC", "apy": 15.5},
        {"id": "pool2", "symbol": "WBTC-USDC", "apy": 12.3},
        {"id": "pool3", "symbol": "SOL-USDC", "apy": 25.1},
        {"id": "pool4", "symbol": "ARB-ETH", "apy": 18.7},
        {"id": "pool5", "symbol": "OP-ETH", "apy": 22.4},
    ]
    
    # Create session
    session = create_pro_pack_session(test_pools, "0x1234...5678")
    print(f"Created session: {session.session_id}")
    print(f"Active pools: {session.remaining_count}")
    
    # Dismiss a pool
    session.dismiss_pool("pool2")
    print(f"After dismiss: {session.remaining_count} pools")
    
    # Check status
    status = get_pro_pack_status(session.session_id)
    print(f"Status: {json.dumps(status, indent=2, default=str)}")
