"""
Liquidity Lock Checker
Checks if LP tokens are locked via Team Finance, Unicrypt, etc.
Provides rug-pull protection analysis.
"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from web3 import Web3

logger = logging.getLogger(__name__)

# Known locker contracts
LOCKER_CONTRACTS = {
    "base": {
        "team_finance": "0xE2fE530C047f2d85298b07D9333C05737f1435fB",
        "unicrypt": None,  # Not on Base yet
        "pinklock": None,
    },
    "ethereum": {
        "team_finance": "0xE2fE530C047f2d85298b07D9333C05737f1435fB",
        "unicrypt": "0x663A5C229c09b049E36dCc11a9B0d4a8Eb9db214",
        "pinklock": "0x71B5759d73262FBb223956913ecF4ecC51057641",
    },
    "bsc": {
        "team_finance": "0xE2fE530C047f2d85298b07D9333C05737f1435fB",
        "unicrypt": "0x407993575c91ce7643a4d4cCACc9A98c3d8d7689",
        "pinklock": "0x7ee058420e5937496F5a2096f04caA7721cF70cc",
    },
    "arbitrum": {
        "team_finance": "0xE2fE530C047f2d85298b07D9333C05737f1435fB",
        "unicrypt": None,
        "pinklock": None,
    }
}

# Team Finance API
TEAM_FINANCE_API = "https://api.team.finance/v1"


class LiquidityLockChecker:
    """Check if LP tokens are locked for anti-rug protection."""
    
    def __init__(self):
        self.cache = {}
    
    async def check_lp_lock(
        self,
        pool_address: str,
        chain: str = "base"
    ) -> Dict[str, Any]:
        """
        Check if LP tokens for a pool are locked.
        
        Returns:
            {
                "has_lock": bool,
                "locked_percent": float,
                "lock_platforms": ["Team Finance", "Unicrypt"],
                "locks": [
                    {
                        "platform": "Team Finance",
                        "amount": 1000000,
                        "percent": 80,
                        "unlock_date": "2025-12-31",
                        "owner": "0x..."
                    }
                ],
                "risk_level": "low" | "medium" | "high",
                "source": "api" | "rpc" | "unknown"
            }
        """
        pool_address = pool_address.lower()
        
        # Try Team Finance API first
        try:
            result = await self._check_team_finance(pool_address, chain)
            if result and result.get("has_lock"):
                return result
        except Exception as e:
            logger.warning(f"Team Finance check failed: {e}")
        
        # Try Unicrypt API
        try:
            result = await self._check_unicrypt(pool_address, chain)
            if result and result.get("has_lock"):
                return result
        except Exception as e:
            logger.warning(f"Unicrypt check failed: {e}")
        
        # Fallback: check on-chain (if we have RPC)
        try:
            result = await self._check_onchain(pool_address, chain)
            if result:
                return result
        except Exception as e:
            logger.debug(f"On-chain check skipped: {e}")
        
        # No lock found
        return {
            "has_lock": False,
            "locked_percent": 0,
            "lock_platforms": [],
            "locks": [],
            "risk_level": "high",
            "source": "unknown",
            "note": "No verified LP lock found. Higher rug-pull risk."
        }
    
    async def _check_team_finance(
        self,
        pool_address: str,
        chain: str
    ) -> Optional[Dict[str, Any]]:
        """Check Team Finance for LP locks."""
        chain_map = {
            "base": "8453",
            "ethereum": "1",
            "bsc": "56",
            "arbitrum": "42161",
            "polygon": "137"
        }
        
        chain_id = chain_map.get(chain.lower())
        if not chain_id:
            return None
        
        url = f"{TEAM_FINANCE_API}/locks"
        params = {
            "chainId": chain_id,
            "tokenAddress": pool_address
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                locks = data.get("locks", [])
                
                if locks:
                    total_locked = sum(lock.get("amount", 0) for lock in locks)
                    total_supply = data.get("totalSupply", total_locked) or total_locked
                    locked_percent = (total_locked / total_supply * 100) if total_supply > 0 else 0
                    
                    parsed_locks = []
                    for lock in locks:
                        unlock_timestamp = lock.get("unlockTime", 0)
                        unlock_date = datetime.fromtimestamp(unlock_timestamp, tz=timezone.utc).strftime("%Y-%m-%d") if unlock_timestamp else "Unknown"
                        
                        parsed_locks.append({
                            "platform": "Team Finance",
                            "amount": lock.get("amount", 0),
                            "percent": lock.get("amount", 0) / total_supply * 100 if total_supply > 0 else 0,
                            "unlock_date": unlock_date,
                            "owner": lock.get("owner", "Unknown"),
                            "days_remaining": self._days_until(unlock_timestamp)
                        })
                    
                    return {
                        "has_lock": True,
                        "locked_percent": round(locked_percent, 2),
                        "lock_platforms": ["Team Finance"],
                        "locks": parsed_locks,
                        "risk_level": self._assess_lock_risk(locked_percent, parsed_locks),
                        "source": "team_finance"
                    }
        
        return None
    
    async def _check_unicrypt(
        self,
        pool_address: str,
        chain: str
    ) -> Optional[Dict[str, Any]]:
        """Check Unicrypt for LP locks."""
        # Unicrypt API endpoint
        url = f"https://api.unicrypt.network/api/v1/locks"
        
        chain_map = {
            "ethereum": "ethereum",
            "bsc": "bsc",
            "polygon": "polygon"
        }
        
        network = chain_map.get(chain.lower())
        if not network:
            return None
        
        params = {
            "network": network,
            "token": pool_address
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    locks = data.get("data", [])
                    
                    if locks:
                        total_locked = sum(float(lock.get("amount", 0)) for lock in locks)
                        
                        parsed_locks = []
                        for lock in locks:
                            unlock_timestamp = int(lock.get("unlockDate", 0))
                            unlock_date = datetime.fromtimestamp(unlock_timestamp, tz=timezone.utc).strftime("%Y-%m-%d") if unlock_timestamp else "Unknown"
                            
                            parsed_locks.append({
                                "platform": "Unicrypt",
                                "amount": float(lock.get("amount", 0)),
                                "unlock_date": unlock_date,
                                "owner": lock.get("owner", "Unknown"),
                                "days_remaining": self._days_until(unlock_timestamp)
                            })
                        
                        return {
                            "has_lock": True,
                            "locked_percent": None,  # Unicrypt doesn't always provide %
                            "lock_platforms": ["Unicrypt"],
                            "locks": parsed_locks,
                            "risk_level": "medium",  # Can't assess without %
                            "source": "unicrypt"
                        }
            except Exception as e:
                logger.debug(f"Unicrypt API error: {e}")
        
        return None
    
    async def _check_onchain(
        self,
        pool_address: str,
        chain: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check on-chain for locks by examining LP token holders.
        Looks for known locker contracts in top holders.
        """
        # This would require RPC access and is slower
        # For now, return None to indicate we didn't check
        return None
    
    def _days_until(self, timestamp: int) -> int:
        """Calculate days until a timestamp."""
        if not timestamp:
            return 0
        
        now = datetime.now(tz=timezone.utc)
        unlock = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        delta = unlock - now
        return max(0, delta.days)
    
    def _assess_lock_risk(
        self,
        locked_percent: float,
        locks: List[Dict]
    ) -> str:
        """Assess risk level based on lock parameters."""
        if locked_percent >= 80:
            # Check if locks are long enough
            min_days = min((lock.get("days_remaining", 0) for lock in locks), default=0)
            if min_days >= 180:  # 6+ months
                return "low"
            elif min_days >= 30:  # 1+ month
                return "medium"
            else:
                return "high"  # Unlocking soon
        elif locked_percent >= 50:
            return "medium"
        else:
            return "high"
    
    def format_lock_info(self, lock_result: Dict[str, Any]) -> str:
        """Format lock info for display."""
        if not lock_result.get("has_lock"):
            return "❌ No LP lock detected"
        
        locked = lock_result.get("locked_percent", 0)
        platforms = ", ".join(lock_result.get("lock_platforms", []))
        
        if lock_result.get("locks"):
            nearest_unlock = min(
                (l.get("days_remaining", 999) for l in lock_result["locks"]),
                default=0
            )
            unlock_text = f"{nearest_unlock} days" if nearest_unlock > 0 else "Unlocked"
        else:
            unlock_text = "Unknown"
        
        return f"🔒 {locked:.0f}% locked via {platforms} (unlock: {unlock_text})"


# Singleton instance
liquidity_lock_checker = LiquidityLockChecker()
