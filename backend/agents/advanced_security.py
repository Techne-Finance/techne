"""
Advanced Security Module - Multi-sig, Safe{Wallet}, 2FA
Enterprise-grade security for agent wallet operations

Features:
- Multi-sig for large withdrawals (>$10k)
- Safe{Wallet} smart contract wallet integration
- 2FA (TOTP) for critical actions
- Smart contract interaction auditing
"""

import logging
import hashlib
import hmac
import time
import struct
import base64
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AdvancedSecurity")


# ===========================================
# MULTI-SIG FOR LARGE WITHDRAWALS
# ===========================================

class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class MultiSigRequest:
    """Multi-signature approval request for large transactions"""
    request_id: str
    user_id: str
    action: str  # "withdraw", "drain", etc.
    amount_usd: float
    token: str
    destination: str
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=24))
    required_approvals: int = 2
    approvals: List[str] = field(default_factory=list)  # List of approver addresses
    rejections: List[str] = field(default_factory=list)
    status: ApprovalStatus = ApprovalStatus.PENDING
    
    def is_approved(self) -> bool:
        return len(self.approvals) >= self.required_approvals
    
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


class MultiSigManager:
    """
    Manages multi-signature approvals for large transactions
    
    Rules:
    - Withdrawals > $10,000 require 2+ approvals
    - User + authorized signer (could be backup device, trusted friend, etc.)
    """
    
    THRESHOLD_USD = 10000.0
    
    def __init__(self):
        self.pending_requests: Dict[str, MultiSigRequest] = {}
        self.authorized_signers: Dict[str, Set[str]] = {}  # user -> set of signer addresses
        self._request_counter = 0
    
    def requires_multisig(self, amount_usd: float) -> bool:
        """Check if transaction requires multi-sig"""
        return amount_usd > self.THRESHOLD_USD
    
    def add_authorized_signer(self, user_id: str, signer_address: str):
        """Add an authorized signer for a user"""
        if user_id not in self.authorized_signers:
            self.authorized_signers[user_id] = set()
        self.authorized_signers[user_id].add(signer_address.lower())
        logger.info(f"✅ Added authorized signer for {user_id[:10]}...")
    
    def remove_authorized_signer(self, user_id: str, signer_address: str):
        """Remove an authorized signer"""
        if user_id in self.authorized_signers:
            self.authorized_signers[user_id].discard(signer_address.lower())
    
    def create_request(
        self,
        user_id: str,
        action: str,
        amount_usd: float,
        token: str,
        destination: str
    ) -> MultiSigRequest:
        """Create a new multi-sig request"""
        self._request_counter += 1
        request_id = f"msig_{int(time.time())}_{self._request_counter}"
        
        request = MultiSigRequest(
            request_id=request_id,
            user_id=user_id,
            action=action,
            amount_usd=amount_usd,
            token=token,
            destination=destination,
            required_approvals=2
        )
        
        self.pending_requests[request_id] = request
        logger.info(f"🔐 Multi-sig request created: {request_id} for ${amount_usd:,.2f}")
        
        return request
    
    def approve(self, request_id: str, signer_address: str) -> Tuple[bool, str]:
        """Approve a multi-sig request"""
        request = self.pending_requests.get(request_id)
        
        if not request:
            return False, "Request not found"
        
        if request.is_expired():
            request.status = ApprovalStatus.EXPIRED
            return False, "Request expired"
        
        if request.status != ApprovalStatus.PENDING:
            return False, f"Request already {request.status.value}"
        
        signer_lower = signer_address.lower()
        
        # Check if signer is authorized
        is_user = signer_lower == request.user_id.lower()
        is_authorized = signer_lower in self.authorized_signers.get(request.user_id, set())
        
        if not is_user and not is_authorized:
            return False, "Not authorized to approve"
        
        if signer_lower in request.approvals:
            return False, "Already approved"
        
        request.approvals.append(signer_lower)
        
        if request.is_approved():
            request.status = ApprovalStatus.APPROVED
            logger.info(f"✅ Multi-sig request APPROVED: {request_id}")
        
        return True, f"Approved ({len(request.approvals)}/{request.required_approvals})"
    
    def reject(self, request_id: str, signer_address: str) -> Tuple[bool, str]:
        """Reject a multi-sig request"""
        request = self.pending_requests.get(request_id)
        
        if not request:
            return False, "Request not found"
        
        request.rejections.append(signer_address.lower())
        request.status = ApprovalStatus.REJECTED
        
        logger.info(f"❌ Multi-sig request REJECTED: {request_id}")
        return True, "Request rejected"
    
    def get_pending_requests(self, user_id: str) -> List[Dict]:
        """Get all pending requests for a user"""
        requests = []
        for req in self.pending_requests.values():
            if req.user_id == user_id and req.status == ApprovalStatus.PENDING:
                if not req.is_expired():
                    requests.append({
                        "request_id": req.request_id,
                        "action": req.action,
                        "amount_usd": req.amount_usd,
                        "token": req.token,
                        "destination": req.destination,
                        "approvals": len(req.approvals),
                        "required": req.required_approvals,
                        "expires_at": req.expires_at.isoformat()
                    })
        return requests


# ===========================================
# SAFE{WALLET} INTEGRATION
# ===========================================

class SafeWalletIntegration:
    """
    Integration with Safe{Wallet} (formerly Gnosis Safe)
    Smart contract wallet with multi-sig capabilities
    
    Features:
    - Create Safe for user
    - Add owners/signers
    - Execute multi-sig transactions
    """
    
    # Safe contract addresses per chain
    SAFE_PROXY_FACTORY = {
        "ethereum": "0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2",
        "base": "0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2",
        "arbitrum": "0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2",
        "optimism": "0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2"
    }
    
    SAFE_SINGLETON = {
        "ethereum": "0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552",
        "base": "0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552",
        "arbitrum": "0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552",
        "optimism": "0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552"
    }
    
    def __init__(self):
        self.user_safes: Dict[str, Dict] = {}  # user_id -> safe info
    
    def get_safe_creation_params(
        self,
        owners: List[str],
        threshold: int = 2,
        chain: str = "base"
    ) -> Dict:
        """
        Get parameters for creating a Safe wallet
        Returns data to be used with ethers.js on frontend
        """
        return {
            "proxy_factory": self.SAFE_PROXY_FACTORY.get(chain),
            "singleton": self.SAFE_SINGLETON.get(chain),
            "owners": owners,
            "threshold": threshold,
            "fallback_handler": "0xf48f2B2d2a534e402487b3ee7C18c33Aec0Fe5e4",
            "payment_token": "0x0000000000000000000000000000000000000000",
            "payment": 0,
            "payment_receiver": "0x0000000000000000000000000000000000000000"
        }
    
    def register_safe(
        self,
        user_id: str,
        safe_address: str,
        owners: List[str],
        threshold: int,
        chain: str
    ):
        """Register a deployed Safe wallet"""
        self.user_safes[user_id.lower()] = {
            "address": safe_address,
            "owners": owners,
            "threshold": threshold,
            "chain": chain,
            "created_at": datetime.now().isoformat()
        }
        logger.info(f"🔐 Safe registered for {user_id[:10]}... at {safe_address[:10]}...")
    
    def get_user_safe(self, user_id: str) -> Optional[Dict]:
        """Get Safe info for a user"""
        return self.user_safes.get(user_id.lower())
    
    def prepare_safe_transaction(
        self,
        safe_address: str,
        to: str,
        value: int,
        data: str,
        operation: int = 0  # 0 = CALL, 1 = DELEGATECALL
    ) -> Dict:
        """
        Prepare a Safe transaction for signing
        Returns the transaction data structure
        """
        return {
            "to": to,
            "value": str(value),
            "data": data,
            "operation": operation,
            "safeTxGas": 0,
            "baseGas": 0,
            "gasPrice": 0,
            "gasToken": "0x0000000000000000000000000000000000000000",
            "refundReceiver": "0x0000000000000000000000000000000000000000",
            "nonce": 0  # Should be fetched from Safe contract
        }


# ===========================================
# 2FA (TOTP) FOR CRITICAL ACTIONS
# ===========================================

class TwoFactorAuth:
    """
    Time-based One-Time Password (TOTP) 2FA
    Compatible with Google Authenticator, Authy, etc.
    
    Required for:
    - Large withdrawals
    - Adding new signers
    - Exporting private keys
    - Emergency drain
    """
    
    def __init__(self):
        self.user_secrets: Dict[str, str] = {}  # user_id -> TOTP secret
        self.recovery_codes: Dict[str, List[str]] = {}
    
    def generate_secret(self) -> str:
        """Generate a new TOTP secret"""
        import secrets
        # Generate 20 random bytes, encode as base32
        random_bytes = secrets.token_bytes(20)
        return base64.b32encode(random_bytes).decode('utf-8')
    
    def setup_2fa(self, user_id: str) -> Dict:
        """
        Setup 2FA for a user
        Returns secret and provisioning URI for QR code
        """
        secret = self.generate_secret()
        self.user_secrets[user_id.lower()] = secret
        
        # Generate recovery codes
        recovery_codes = [
            hashlib.sha256(f"{user_id}{i}{time.time()}".encode()).hexdigest()[:8].upper()
            for i in range(8)
        ]
        self.recovery_codes[user_id.lower()] = recovery_codes
        
        # OTPAuth URI for QR code
        uri = f"otpauth://totp/Techne:{user_id[:10]}...?secret={secret}&issuer=Techne&algorithm=SHA1&digits=6&period=30"
        
        return {
            "secret": secret,
            "uri": uri,
            "recovery_codes": recovery_codes,
            "message": "Scan QR code with Google Authenticator or similar app"
        }
    
    def verify_totp(self, user_id: str, code: str) -> bool:
        """Verify a TOTP code"""
        secret = self.user_secrets.get(user_id.lower())
        if not secret:
            return False
        
        # Check code for current and adjacent time windows
        for offset in [-1, 0, 1]:
            expected = self._generate_totp(secret, offset)
            if hmac.compare_digest(code, expected):
                return True
        
        return False
    
    def verify_recovery_code(self, user_id: str, code: str) -> bool:
        """Verify and consume a recovery code"""
        codes = self.recovery_codes.get(user_id.lower(), [])
        code_upper = code.upper()
        
        if code_upper in codes:
            codes.remove(code_upper)
            return True
        
        return False
    
    def _generate_totp(self, secret: str, time_offset: int = 0) -> str:
        """Generate TOTP code"""
        try:
            # Decode base32 secret
            key = base64.b32decode(secret, casefold=True)
            
            # Get current time step (30 second windows)
            time_step = int(time.time() // 30) + time_offset
            
            # Pack time as 8-byte big-endian
            time_bytes = struct.pack('>Q', time_step)
            
            # HMAC-SHA1
            hmac_digest = hmac.new(key, time_bytes, hashlib.sha1).digest()
            
            # Dynamic truncation
            offset = hmac_digest[-1] & 0x0f
            code_bytes = hmac_digest[offset:offset + 4]
            code_int = struct.unpack('>I', code_bytes)[0] & 0x7fffffff
            
            # Get 6-digit code
            code = str(code_int % 1000000).zfill(6)
            
            return code
        except Exception:
            return "000000"
    
    def is_2fa_enabled(self, user_id: str) -> bool:
        """Check if 2FA is enabled for user"""
        return user_id.lower() in self.user_secrets
    
    def disable_2fa(self, user_id: str, recovery_code: str) -> bool:
        """Disable 2FA using recovery code"""
        if self.verify_recovery_code(user_id, recovery_code):
            self.user_secrets.pop(user_id.lower(), None)
            self.recovery_codes.pop(user_id.lower(), None)
            return True
        return False


# ===========================================
# SMART CONTRACT INTERACTION AUDIT
# ===========================================

class ContractAuditLog:
    """
    Audit logging for all smart contract interactions
    
    Logs:
    - Contract address
    - Function called
    - Parameters
    - Gas used
    - Result
    """
    
    def __init__(self):
        self.logs: List[Dict] = []
        self.known_contracts: Dict[str, Dict] = {
            # Known trusted contracts
            "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913": {"name": "USDC", "chain": "base", "verified": True},
            "0x4200000000000000000000000000000000000006": {"name": "WETH", "chain": "base", "verified": True},
        }
        self.suspicious_patterns: List[str] = [
            "0x095ea7b3ffffffffffffffffffffffffffffffffffffffffffffffffffffffff",  # Unlimited approval
            "selfdestruct",
            "delegatecall"
        ]
    
    def log_interaction(
        self,
        user_id: str,
        contract_address: str,
        function_name: str,
        parameters: Dict,
        tx_hash: Optional[str] = None,
        gas_used: Optional[int] = None,
        success: bool = True
    ) -> Dict:
        """Log a contract interaction"""
        
        contract_info = self.known_contracts.get(contract_address.lower(), {})
        
        log_entry = {
            "id": len(self.logs) + 1,
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "contract": {
                "address": contract_address,
                "name": contract_info.get("name", "Unknown"),
                "verified": contract_info.get("verified", False)
            },
            "function": function_name,
            "parameters": parameters,
            "tx_hash": tx_hash,
            "gas_used": gas_used,
            "success": success,
            "warnings": []
        }
        
        # Check for suspicious patterns
        param_str = str(parameters).lower()
        for pattern in self.suspicious_patterns:
            if pattern in param_str:
                log_entry["warnings"].append(f"Suspicious pattern: {pattern}")
        
        # Check for unknown contracts
        if not contract_info.get("verified"):
            log_entry["warnings"].append("Interacting with unverified contract")
        
        self.logs.append(log_entry)
        
        if log_entry["warnings"]:
            logger.warning(f"⚠️ Contract interaction warning: {log_entry['warnings']}")
        
        return log_entry
    
    def register_known_contract(
        self,
        address: str,
        name: str,
        chain: str,
        verified: bool = True
    ):
        """Register a known/trusted contract"""
        self.known_contracts[address.lower()] = {
            "name": name,
            "chain": chain,
            "verified": verified
        }
    
    def get_user_logs(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get audit logs for a user"""
        user_logs = [log for log in self.logs if log["user_id"] == user_id]
        return user_logs[-limit:][::-1]
    
    def get_suspicious_activity(self, user_id: Optional[str] = None) -> List[Dict]:
        """Get all suspicious activity"""
        suspicious = [log for log in self.logs if log["warnings"]]
        if user_id:
            suspicious = [log for log in suspicious if log["user_id"] == user_id]
        return suspicious


# ===========================================
# SINGLETONS
# ===========================================

multisig_manager = MultiSigManager()
safe_wallet = SafeWalletIntegration()
two_factor_auth = TwoFactorAuth()
contract_audit = ContractAuditLog()
