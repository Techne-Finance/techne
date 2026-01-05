"""
Engineer API Router
Endpoints for autonomous DeFi execution

Routes:
- POST /api/engineer/deposit - Create deposit task
- POST /api/engineer/withdraw - Create withdrawal task
- GET /api/engineer/tasks/{task_id} - Get task status
- GET /api/engineer/tasks/user/{user_id} - Get user's tasks
- GET /api/engineer/gas-price - Current gas price
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Import Engineer Agent
import sys
sys.path.append('..')
from agents import engineer, TaskType, TaskStatus

router = APIRouter(prefix="/api/engineer", tags=["engineer"])


# ========================================
# REQUEST/RESPONSE MODELS
# ========================================

class DepositRequest(BaseModel):
    user_id: str = Field(..., description="User wallet address or ID")
    vault_address: str = Field(..., description="ERC-4626 vault contract address")
    amount_usdt: float = Field(..., gt=0, description="Amount of USDT to deposit")
    max_gas_usd: float = Field(2.0, description="Maximum gas cost in USD")

class WithdrawRequest(BaseModel):
    user_id: str
    vault_address: str
    shares_amount: float = Field(..., gt=0, description="Amount of vault shares to redeem")
    max_gas_usd: float = 2.0

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class TaskStatusResponse(BaseModel):
    id: str
    type: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    gas_cost_usd: Optional[float] = None
    tx_hashes: List[str] = []
    error_message: Optional[str] = None

class GasPriceResponse(BaseModel):
    current_gwei: float
    timestamp: str
    chain: str = "Base"


# ========================================
# ENDPOINTS
# ========================================

@router.post("/deposit", response_model=TaskResponse)
async def create_deposit(request: DepositRequest):
    """
    Create a USDT deposit task
    
    The Engineer will:
    1. Wait for optimal gas price
    2. Approve USDT to vault
    3. Execute deposit
    4. Return task ID for tracking
    """
    try:
        task = await engineer.create_deposit_task(
            user_id=request.user_id,
            vault_address=request.vault_address,
            amount_usdt=request.amount_usdt,
            max_gas_usd=request.max_gas_usd
        )
        
        return TaskResponse(
            task_id=task.id,
            status=task.status.value,
            message=f"Deposit task created for ${request.amount_usdt} USDT"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/withdraw", response_model=TaskResponse)
async def create_withdrawal(request: WithdrawRequest):
    """
    Create a withdrawal task
    
    Redeems vault shares for underlying USDT
    """
    try:
        task = await engineer.create_withdraw_task(
            user_id=request.user_id,
            vault_address=request.vault_address,
            shares_amount=request.shares_amount,
            max_gas_usd=request.max_gas_usd
        )
        
        return TaskResponse(
            task_id=task.id,
            status=task.status.value,
            message=f"Withdrawal task created for {request.shares_amount} shares"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get status of a specific task
    
    Returns:
    - QUEUED: Waiting to execute
    - WAITING_GAS: Waiting for cheaper gas
    - EXECUTING: Currently executing
    - COMPLETED: Successfully completed
    - FAILED_*: Various failure states
    """
    status = engineer.get_task_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskStatusResponse(**status)


@router.get("/tasks/user/{user_id}", response_model=List[TaskStatusResponse])
async def get_user_tasks(user_id: str, status_filter: Optional[str] = None):
    """
    Get all tasks for a user
    
    Optional status_filter: queued, executing, completed, failed
    """
    tasks = engineer.get_pending_tasks(user_id)
    
    if status_filter:
        tasks = [t for t in tasks if t['status'] == status_filter]
    
    return tasks


@router.get("/gas-price", response_model=GasPriceResponse)
async def get_gas_price():
    """
    Get current gas price on Base chain
    
    Used by UI to show users when tasks will execute
    """
    return GasPriceResponse(
        current_gwei=engineer.current_gas_gwei,
        timestamp=datetime.now().isoformat(),
        chain="Base"
    )


@router.get("/vaults/recommended")
async def get_recommended_vaults():
    """
    Get recommended USDT vaults for deposits
    
    Returns curated list of safe, high-APY vaults
    """
    # This would integrate with Scout + Appraiser
    # For MVP, return hardcoded safe vaults
    
    return {
        "primary_asset": "USDT",
        "vaults": [
            {
                "name": "Aave V3 USDT Supply",
                "protocol": "aave-v3",
                "address": "0x...",  # TODO: Get from Scout
                "current_apy": 8.5,
                "tvl_usd": 50_000_000,
                "risk_level": "safe",
                "utilization_rate": 0.75,
                "recommended": True
            },
            {
                "name": "Morpho USDT Vault",
                "protocol": "morpho",
                "address": "0x...",
                "current_apy": 12.3,
                "tvl_usd": 15_000_000,
                "risk_level": "low",
                "utilization_rate": 0.82,
                "recommended": True
            },
            {
                "name": "Compound V3 USDT",
                "protocol": "compound-v3",
                "address": "0x...",
                "current_apy": 9.7,
                "tvl_usd": 30_000_000,
                "risk_level": "safe",
                "utilization_rate": 0.68,
                "recommended": True
            }
        ]
    }


@router.post("/simulate-deposit")
async def simulate_deposit(request: DepositRequest):
    """
    Simulate a deposit without executing
    
    Returns:
    - Estimated gas cost
    - Expected output (shares)
    - Estimated time to execute
    - APY at current rate
    """
    # TODO: Integrate with actual vault contracts
    
    estimated_gas_gwei = engineer.current_gas_gwei
    estimated_gas_usd = estimated_gas_gwei * 200000 * 3000 / 1e9  # Rough estimate
    
    return {
        "amount_usdt": request.amount_usdt,
        "estimated_shares": request.amount_usdt * 0.998,  # Assume 0.2% slippage
        "estimated_gas_cost_usd": estimated_gas_usd,
        "estimated_time_seconds": 30,  # Base is fast
        "current_gas_gwei": estimated_gas_gwei,
        "will_execute_immediately": estimated_gas_gwei <= request.max_gas_usd,
        "simulation_timestamp": datetime.now().isoformat()
    }
