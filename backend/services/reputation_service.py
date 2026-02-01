"""
ERC-8004 Reputation Service
Records execution outcomes to on-chain AgentReputationRegistry

Usage:
    from services.reputation_service import report_execution, get_agent_reputation
    
    # After executing a trade:
    await report_execution(
        token_id=agent_token_id,
        success=True,
        value_usd=1000.0,
        profit_usd=5.0,
        execution_type="deposit"
    )
"""

import os
import logging
from typing import Dict, Optional
from web3 import Web3
from eth_account import Account

logger = logging.getLogger("ReputationService")

# Contract addresses (set in .env)
REPUTATION_REGISTRY_ADDRESS = os.getenv("REPUTATION_REGISTRY_ADDRESS", "")
IDENTITY_REGISTRY_ADDRESS = os.getenv("IDENTITY_REGISTRY_ADDRESS", "")

# Reputation Registry ABI (minimal for reporting)
REPUTATION_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"name": "tokenId", "type": "uint256"},
                    {"name": "success", "type": "bool"},
                    {"name": "valueUSD", "type": "uint256"},
                    {"name": "profitUSD", "type": "int256"},
                    {"name": "executionType", "type": "string"}
                ],
                "name": "report",
                "type": "tuple"
            }
        ],
        "name": "recordExecution",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "getReputation",
        "outputs": [
            {"name": "totalExecutions", "type": "uint256"},
            {"name": "successfulExecutions", "type": "uint256"},
            {"name": "failedExecutions", "type": "uint256"},
            {"name": "totalValueManaged", "type": "uint256"},
            {"name": "currentValueManaged", "type": "uint256"},
            {"name": "totalProfitGenerated", "type": "uint256"},
            {"name": "trustScore", "type": "uint256"},
            {"name": "endorsementScore", "type": "uint256"},
            {"name": "uptimeDays", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "getTrustScore",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "getSuccessRate",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Identity Registry ABI (minimal)
IDENTITY_ABI = [
    {
        "inputs": [{"name": "smartAccount", "type": "address"}],
        "name": "getTokenId",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "smartAccount", "type": "address"}],
        "name": "isRegistered",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "smartAccount", "type": "address"}],
        "name": "getAgentByAccount",
        "outputs": [
            {
                "components": [
                    {"name": "smartAccount", "type": "address"},
                    {"name": "owner", "type": "address"},
                    {"name": "modelHash", "type": "bytes32"},
                    {"name": "agentType", "type": "string"},
                    {"name": "createdAt", "type": "uint256"},
                    {"name": "lastActiveAt", "type": "uint256"},
                    {"name": "active", "type": "bool"}
                ],
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]


class ReputationService:
    """Service for ERC-8004 reputation tracking"""
    
    def __init__(self):
        self.rpc_url = os.getenv("ALCHEMY_RPC_URL") or os.getenv("BASE_RPC_URL")
        self.reporter_key = os.getenv("REPUTATION_REPORTER_KEY") or os.getenv("AGENT_PRIVATE_KEY")
        
        if not self.rpc_url:
            logger.warning("No RPC URL configured - reputation tracking disabled")
            self.w3 = None
            return
            
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Initialize contracts
        if REPUTATION_REGISTRY_ADDRESS:
            self.reputation_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(REPUTATION_REGISTRY_ADDRESS),
                abi=REPUTATION_ABI
            )
        else:
            self.reputation_contract = None
            
        if IDENTITY_REGISTRY_ADDRESS:
            self.identity_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(IDENTITY_REGISTRY_ADDRESS),
                abi=IDENTITY_ABI
            )
        else:
            self.identity_contract = None
    
    async def get_token_id_for_account(self, smart_account: str) -> Optional[int]:
        """Get ERC-8004 token ID for a smart account"""
        if not self.identity_contract:
            return None
            
        try:
            token_id = self.identity_contract.functions.getTokenId(
                Web3.to_checksum_address(smart_account)
            ).call()
            return token_id
        except Exception as e:
            logger.debug(f"No identity found for {smart_account}: {e}")
            return None
    
    async def is_registered(self, smart_account: str) -> bool:
        """Check if smart account has ERC-8004 identity"""
        if not self.identity_contract:
            return False
            
        try:
            return self.identity_contract.functions.isRegistered(
                Web3.to_checksum_address(smart_account)
            ).call()
        except Exception:
            return False
    
    async def get_agent_identity(self, smart_account: str) -> Optional[Dict]:
        """Get agent identity struct"""
        if not self.identity_contract:
            return None
            
        try:
            identity = self.identity_contract.functions.getAgentByAccount(
                Web3.to_checksum_address(smart_account)
            ).call()
            
            return {
                "smart_account": identity[0],
                "owner": identity[1],
                "model_hash": identity[2].hex(),
                "agent_type": identity[3],
                "created_at": identity[4],
                "last_active_at": identity[5],
                "active": identity[6]
            }
        except Exception as e:
            logger.error(f"Failed to get identity: {e}")
            return None
    
    async def report_execution(
        self,
        token_id: int,
        success: bool,
        value_usd: float,
        profit_usd: float,
        execution_type: str
    ) -> Optional[str]:
        """
        Report execution outcome to on-chain reputation registry.
        
        Args:
            token_id: ERC-8004 identity token ID
            success: Whether execution succeeded
            value_usd: USD value of the transaction
            profit_usd: Profit/loss in USD (can be negative)
            execution_type: Type (deposit, withdraw, rebalance, etc.)
            
        Returns:
            Transaction hash if successful
        """
        if not self.reputation_contract or not self.reporter_key:
            logger.warning("Reputation registry not configured - skipping report")
            return None
            
        try:
            # Convert to 8 decimals (registry uses 8 decimals for USD)
            value_wei = int(value_usd * 10**8)
            profit_wei = int(profit_usd * 10**8)
            
            # Build report struct
            report = (
                token_id,
                success,
                value_wei,
                profit_wei,
                execution_type
            )
            
            # Build transaction
            account = Account.from_key(self.reporter_key)
            
            tx = self.reputation_contract.functions.recordExecution(report).build_transaction({
                "from": account.address,
                "gas": 200000,
                "gasPrice": self.w3.eth.gas_price,
                "nonce": self.w3.eth.get_transaction_count(account.address)
            })
            
            # Sign and send
            signed = self.w3.eth.account.sign_transaction(tx, self.reporter_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
            
            logger.info(f"[ERC-8004] Reported execution: token={token_id}, type={execution_type}, tx={tx_hash.hex()}")
            
            return tx_hash.hex()
            
        except Exception as e:
            logger.error(f"Failed to report execution: {e}")
            return None
    
    async def get_reputation(self, token_id: int) -> Optional[Dict]:
        """Get full reputation for an agent"""
        if not self.reputation_contract:
            return None
            
        try:
            rep = self.reputation_contract.functions.getReputation(token_id).call()
            
            return {
                "total_executions": rep[0],
                "successful_executions": rep[1],
                "failed_executions": rep[2],
                "total_value_managed_usd": rep[3] / 10**8,
                "current_value_managed_usd": rep[4] / 10**8,
                "total_profit_generated_usd": rep[5] / 10**8,
                "trust_score": rep[6] / 100,  # Convert to percentage
                "endorsement_score": rep[7],
                "uptime_days": rep[8]
            }
        except Exception as e:
            logger.error(f"Failed to get reputation: {e}")
            return None
    
    async def get_trust_score(self, token_id: int) -> float:
        """Get trust score as percentage (0-100)"""
        if not self.reputation_contract:
            return 0.0
            
        try:
            score = self.reputation_contract.functions.getTrustScore(token_id).call()
            return score / 100  # Convert from 0-10000 to 0-100
        except Exception:
            return 0.0
    
    async def get_success_rate(self, token_id: int) -> float:
        """Get success rate as percentage (0-100)"""
        if not self.reputation_contract:
            return 0.0
            
        try:
            rate = self.reputation_contract.functions.getSuccessRate(token_id).call()
            return rate / 100  # Convert from 0-10000 to 0-100
        except Exception:
            return 0.0


# Singleton
_service: Optional[ReputationService] = None

def get_reputation_service() -> ReputationService:
    """Get or create reputation service singleton"""
    global _service
    if _service is None:
        _service = ReputationService()
    return _service


# Convenience functions
async def report_execution(
    token_id: int,
    success: bool,
    value_usd: float,
    profit_usd: float = 0.0,
    execution_type: str = "trade"
) -> Optional[str]:
    """Report execution to on-chain reputation registry"""
    service = get_reputation_service()
    return await service.report_execution(token_id, success, value_usd, profit_usd, execution_type)


async def get_agent_reputation(smart_account: str) -> Optional[Dict]:
    """Get full reputation for a smart account"""
    service = get_reputation_service()
    token_id = await service.get_token_id_for_account(smart_account)
    if token_id is None:
        return None
    return await service.get_reputation(token_id)


async def get_agent_profile(smart_account: str) -> Optional[Dict]:
    """Get combined identity + reputation profile"""
    service = get_reputation_service()
    
    identity = await service.get_agent_identity(smart_account)
    if not identity:
        return None
    
    token_id = await service.get_token_id_for_account(smart_account)
    reputation = await service.get_reputation(token_id) if token_id else None
    
    return {
        "identity": identity,
        "reputation": reputation,
        "token_id": token_id
    }
