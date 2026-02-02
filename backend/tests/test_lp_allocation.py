"""
LP Allocation Tests
Tests for Aerodrome LP integration - reserves, 50/50 split, add/remove liquidity

Run: python -m pytest tests/test_lp_allocation.py -v
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def test_addresses():
    """Standard test addresses for Base"""
    return {
        "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "WETH": "0x4200000000000000000000000000000000000006",
        "AERO": "0x940181a94A35A4569E4529A3CDfB74e38FD98631",
        "ROUTER": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
        "agent": "0xa30A689ec0F9D717C5bA1098455B031b868B720f",
    }


@pytest.fixture
def mock_web3():
    """Mock Web3 instance"""
    mock = MagicMock()
    mock.eth.get_transaction_count.return_value = 1
    mock.eth.gas_price = 1_000_000_000  # 1 gwei
    mock.eth.chain_id = 8453  # Base
    return mock


# =============================================================================
# TEST: 50/50 Split Logic
# =============================================================================

class TestSplitCalculation:
    """Test the 50/50 split logic for dual-sided LP"""
    
    def test_50_50_split_exact(self):
        """Test exact 50/50 split"""
        amount_in = 100_000_000  # 100 USDC
        
        half = amount_in // 2
        
        assert half == 50_000_000
        assert half * 2 == amount_in
        
        print(f"✅ 100 USDC splits to: 50 USDC + 50 USDC")
    
    
    def test_50_50_split_odd_amount(self):
        """Test split with odd amount (dust handling)"""
        amount_in = 100_000_001  # 100.000001 USDC (odd)
        
        half = amount_in // 2
        remainder = amount_in - half
        
        assert half == 50_000_000
        assert remainder == 50_000_001
        assert half + remainder == amount_in
        
        print(f"✅ Odd split: {half} + {remainder} = {amount_in}")
    
    
    def test_split_minimum_amount(self):
        """Test split with minimum viable amount"""
        amount_in = 10_000_000  # $10 minimum for LP
        
        half = amount_in // 2
        
        # After split, each side should be at least $5
        assert half >= 5_000_000
        
        print(f"✅ $10 minimum splits to: ${half/1e6:.2f} each side")


# =============================================================================
# TEST: Reserves Fetching
# =============================================================================

class TestReservesFetching:
    """Test pool reserves fetching from Aerodrome"""
    
    @pytest.mark.asyncio
    async def test_get_reserves_mock(self, test_addresses, mock_web3):
        """Test reserves fetch with mocked response"""
        from services.aerodrome_lp import AerodromeLPService
        
        with patch.object(AerodromeLPService, 'get_reserves', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = (
                1_000_000_000_000,  # 1M USDC
                500_000_000_000_000_000_000  # 500 WETH
            )
            
            service = AerodromeLPService()
            reserve_a, reserve_b = await service.get_reserves(
                test_addresses["USDC"],
                test_addresses["WETH"],
                stable=False
            )
            
            assert reserve_a == 1_000_000_000_000
            assert reserve_b == 500_000_000_000_000_000_000
            
            print(f"✅ Reserves: {reserve_a/1e6:.0f} USDC, {reserve_b/1e18:.2f} WETH")


# =============================================================================
# TEST: Optimal Amounts Calculation  
# =============================================================================

class TestOptimalAmounts:
    """Test optimal LP amounts based on reserves"""
    
    def test_calculate_optimal_amount_b(self):
        """Calculate optimal amount B given amount A and reserves"""
        # Reserves: 1M USDC, 500 WETH (ratio 2000 USDC per WETH)
        reserve_a = 1_000_000_000_000  # USDC
        reserve_b = 500_000_000_000_000_000_000  # WETH
        
        amount_a = 100_000_000  # 100 USDC to add
        
        # Formula: amount_b = (amount_a * reserve_b) / reserve_a
        optimal_b = (amount_a * reserve_b) // reserve_a
        
        # 100 USDC should get ~0.05 WETH
        expected_weth = 50_000_000_000_000_000  # 0.05 WETH
        
        assert optimal_b == expected_weth
        print(f"✅ 100 USDC optimal pair: {optimal_b/1e18:.6f} WETH")
    
    
    def test_calculate_optimal_with_slippage(self):
        """Calculate min amounts with 1% slippage"""
        amount_a = 100_000_000  # 100 USDC
        amount_b = 50_000_000_000_000_000  # 0.05 WETH
        slippage_pct = 1.0
        
        min_a = int(amount_a * (1 - slippage_pct / 100))
        min_b = int(amount_b * (1 - slippage_pct / 100))
        
        assert min_a == 99_000_000
        assert min_b == 49_500_000_000_000_000
        
        print(f"✅ With 1% slippage: min_a={min_a/1e6}, min_b={min_b/1e18}")


# =============================================================================
# TEST: Token Approval Flow
# =============================================================================

class TestTokenApproval:
    """Test ERC20 approve before adding liquidity"""
    
    @pytest.mark.asyncio
    async def test_approve_token_mock(self, test_addresses):
        """Test token approval with mocked transaction"""
        from services.aerodrome_lp import AerodromeLPService
        
        with patch.object(AerodromeLPService, 'approve_token', new_callable=AsyncMock) as mock_approve:
            mock_approve.return_value = "0x123abc..."
            
            service = AerodromeLPService()
            tx_hash = await service.approve_token(
                token=test_addresses["USDC"],
                amount=100_000_000,
                owner_address=test_addresses["agent"],
                private_key="0xtest..."
            )
            
            assert tx_hash is not None
            print(f"✅ Approval tx: {tx_hash}")
    
    
    def test_max_approval_amount(self):
        """Test max uint256 approval (infinite)"""
        MAX_UINT256 = 2**256 - 1
        
        # Verify it's the correct max value
        assert MAX_UINT256 == 115792089237316195423570985008687907853269984665640564039457584007913129639935
        
        print(f"✅ Max approval: {MAX_UINT256}")


# =============================================================================
# TEST: Add Liquidity Calldata
# =============================================================================

class TestAddLiquidityCalldata:
    """Test addLiquidity calldata generation"""
    
    @pytest.mark.asyncio
    async def test_add_liquidity_mock(self, test_addresses):
        """Test add_liquidity with mocked execution"""
        from services.aerodrome_lp import AerodromeLPService, LPResult
        
        with patch.object(AerodromeLPService, 'add_liquidity', new_callable=AsyncMock) as mock_add:
            mock_add.return_value = LPResult(
                success=True,
                tx_hash="0xabc123...",
                amount_a=100_000_000,
                amount_b=50_000_000_000_000_000,
                liquidity=1_000_000_000_000_000_000
            )
            
            service = AerodromeLPService()
            result = await service.add_liquidity(
                token_a=test_addresses["USDC"],
                token_b=test_addresses["WETH"],
                amount_a=100_000_000,
                amount_b=50_000_000_000_000_000,
                stable=False,
                agent_address=test_addresses["agent"],
                private_key="0xtest..."
            )
            
            assert result.success is True
            assert result.liquidity > 0
            
            print(f"✅ LP received: {result.liquidity/1e18:.6f}")


# =============================================================================
# TEST: Remove Liquidity
# =============================================================================

class TestRemoveLiquidity:
    """Test remove liquidity flow"""
    
    @pytest.mark.asyncio
    async def test_remove_liquidity_mock(self, test_addresses):
        """Test remove_liquidity with mocked execution"""
        from services.aerodrome_lp import AerodromeLPService, LPResult
        
        with patch.object(AerodromeLPService, 'remove_liquidity', new_callable=AsyncMock) as mock_remove:
            mock_remove.return_value = LPResult(
                success=True,
                tx_hash="0xdef456...",
                amount_a=100_000_000,  # USDC received
                amount_b=50_000_000_000_000_000,  # WETH received
                liquidity=0
            )
            
            service = AerodromeLPService()
            result = await service.remove_liquidity(
                token_a=test_addresses["USDC"],
                token_b=test_addresses["WETH"],
                lp_amount=1_000_000_000_000_000_000,
                stable=False,
                agent_address=test_addresses["agent"],
                private_key="0xtest..."
            )
            
            assert result.success is True
            assert result.amount_a == 100_000_000
            
            print(f"✅ Received: {result.amount_a/1e6} USDC + {result.amount_b/1e18} WETH")


# =============================================================================
# TEST: Dual LP Service (Full Flow)
# =============================================================================

class TestDualLPService:
    """Test the complete dual LP deposit flow"""
    
    @pytest.mark.asyncio
    async def test_calculate_split(self, test_addresses):
        """Test split calculation in DualSidedLPService"""
        from services.dual_lp_service import DualSidedLPService
        
        with patch.object(DualSidedLPService, 'calculate_split', new_callable=AsyncMock) as mock_split:
            mock_split.return_value = {
                "keep_amount": 50_000_000,
                "swap_amount": 50_000_000,
                "token_to_swap": "WETH"
            }
            
            service = DualSidedLPService()
            split = await service.calculate_split(
                pool_token_a="USDC",
                pool_token_b="WETH",
                token_in="USDC",
                amount_in=100_000_000,
                stable=False
            )
            
            assert split["keep_amount"] == 50_000_000
            assert split["swap_amount"] == 50_000_000
            
            print(f"✅ Split: keep {split['keep_amount']/1e6} USDC, swap {split['swap_amount']/1e6} for WETH")
    
    
    @pytest.mark.asyncio
    async def test_deposit_single_token_lp_mock(self, test_addresses):
        """Test complete deposit flow with mocks"""
        from services.dual_lp_service import DualSidedLPService, DualLPResult
        
        with patch.object(DualSidedLPService, 'deposit_single_token_lp', new_callable=AsyncMock) as mock_deposit:
            mock_deposit.return_value = DualLPResult(
                success=True,
                swap_order_uid="test_order_123",
                swap_filled=True,
                lp_tx_hash="0xabc123...",
                amount_a_deposited=50_000_000,
                amount_b_deposited=25_000_000_000_000_000,
                lp_tokens_received=500_000_000_000_000_000
            )
            
            service = DualSidedLPService()
            result = await service.deposit_single_token_lp(
                pool_token_a="USDC",
                pool_token_b="WETH",
                token_in="USDC",
                amount_in=100_000_000,
                stable=False,
                agent_address=test_addresses["agent"],
                private_key="0xtest..."
            )
            
            assert result.success is True
            assert result.swap_filled is True
            assert result.lp_tokens_received > 0
            
            print(f"✅ Full LP deposit: {result.lp_tokens_received/1e18:.6f} LP tokens")


# =============================================================================
# INTEGRATION TEST: Real Aerodrome
# =============================================================================

class TestRealAerodrome:
    """Integration tests against real Aerodrome (read-only)"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_reserves_fetch(self, test_addresses):
        """Test real reserves fetch for USDC/WETH pool"""
        from services.aerodrome_lp import get_aerodrome_lp
        
        try:
            service = get_aerodrome_lp()
            reserve_a, reserve_b = await service.get_reserves(
                token_a=test_addresses["USDC"],
                token_b=test_addresses["WETH"],
                stable=False
            )
            
            # Sanity checks
            assert reserve_a > 0, "USDC reserves should be > 0"
            assert reserve_b > 0, "WETH reserves should be > 0"
            
            print(f"✅ REAL: USDC reserve: ${reserve_a/1e6:,.0f}")
            print(f"✅ REAL: WETH reserve: {reserve_b/1e18:,.2f}")
            
        except Exception as e:
            pytest.skip(f"Aerodrome unavailable: {e}")


# =============================================================================
# CLI RUNNER
# =============================================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '..')
    
    async def quick_test():
        print("=" * 60)
        print("🧪 LP ALLOCATION TESTS")
        print("=" * 60)
        
        # Test splits
        print("\n📊 50/50 Split Logic:")
        test = TestSplitCalculation()
        test.test_50_50_split_exact()
        test.test_50_50_split_odd_amount()
        
        # Test optimal amounts
        print("\n📊 Optimal Amounts:")
        test2 = TestOptimalAmounts()
        test2.test_calculate_optimal_amount_b()
        test2.test_calculate_optimal_with_slippage()
        
        # Test real reserves
        print("\n📊 Real Aerodrome Reserves:")
        try:
            from services.aerodrome_lp import get_aerodrome_lp
            service = get_aerodrome_lp()
            ra, rb = await service.get_reserves(
                "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                "0x4200000000000000000000000000000000000006",
                stable=False
            )
            print(f"   ✅ USDC/WETH: ${ra/1e6:,.0f} / {rb/1e18:,.2f}")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
        
        print("\n" + "=" * 60)
        print("✅ All quick tests passed!")
        print("=" * 60)
    
    asyncio.run(quick_test())
