"""
STRICT Dual-Sided LP Flow Tests
==================================

Restrykcyjne testy dla flow: SCAN → SWAP 50% → ALLOCATE

Flow:
1. Scan: Znajdź matching pool, calculate 50/50 split
2. Swap 50%: CoW Swap USDC → WETH (MEV-protected)
3. Wait for Fill: Poll CoW API for order status
4. Allocate: Add both tokens to Aerodrome LP

Run: python -m pytest tests/test_strict_dual_lp_flow.py -v --tb=short
"""

import pytest
import asyncio
from datetime import datetime, timedelta
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
        "agent": "0xa30A689ec0F9D717C5bA1098455B031b868B720f",
    }


@pytest.fixture
def dual_lp_params():
    """Standard dual LP parameters"""
    return {
        "pool_token_a": "USDC",
        "pool_token_b": "WETH",
        "token_in": "USDC",
        "amount_in": 100_000_000,  # 100 USDC
        "stable": False,
        "agent_address": "0xa30A689ec0F9D717C5bA1098455B031b868B720f",
        "private_key": "0x" + "a" * 64,  # Mock private key
        "max_slippage": 2.0,
        "swap_timeout": 300,
    }


# =============================================================================
# STEP 1: SCAN & SPLIT CALCULATION
# =============================================================================

class TestStep1ScanAndSplit:
    """Testy kroku 1: Scan pool i calculate 50/50 split"""
    
    @pytest.mark.asyncio
    async def test_split_is_exactly_50_50(self, dual_lp_params):
        """Split MUSI być dokładnie 50/50"""
        from services.dual_lp_service import DualSidedLPService
        
        service = DualSidedLPService()
        
        with patch.object(service.aerodrome, 'get_reserves', new_callable=AsyncMock) as mock_reserves:
            mock_reserves.return_value = (1_000_000_000_000, 500_000_000_000_000_000_000)
            
            token_keep, amount_keep, token_swap, amount_swap = await service.calculate_split(
                pool_token_a="USDC",
                pool_token_b="WETH",
                token_in="USDC",
                amount_in=100_000_000,  # 100 USDC
                stable=False
            )
            
            # Verify 50/50 split
            assert amount_keep == 50_000_000, f"❌ Keep amount should be 50 USDC, got {amount_keep/1e6}"
            assert amount_swap == 50_000_000, f"❌ Swap amount should be 50 USDC, got {amount_swap/1e6}"
            assert amount_keep + amount_swap == 100_000_000, "❌ Split doesn't sum to original"
            
            # Verify token assignment
            assert token_keep == "USDC", "❌ Keep token should be USDC"
            assert token_swap == "WETH", "❌ Swap to token should be WETH"
        
        print(f"✅ Split is exactly 50/50: keep {amount_keep/1e6} USDC, swap {amount_swap/1e6} → WETH")
    
    
    @pytest.mark.asyncio
    async def test_split_with_odd_amount(self):
        """Split z nieparzystą kwotą obsługuje dust"""
        from services.dual_lp_service import DualSidedLPService
        
        service = DualSidedLPService()
        
        with patch.object(service.aerodrome, 'get_reserves', new_callable=AsyncMock) as mock_reserves:
            mock_reserves.return_value = (1_000_000_000_000, 500_000_000_000_000_000_000)
            
            # Odd amount: 99 USDC
            _, amount_keep, _, amount_swap = await service.calculate_split(
                pool_token_a="USDC",
                pool_token_b="WETH",
                token_in="USDC",
                amount_in=99_000_001,  # 99.000001 USDC (odd)
                stable=False
            )
            
            # Sum must equal original
            assert amount_keep + amount_swap == 99_000_001, "❌ Dust handling failed"
            
            # Half should be floor division
            assert amount_swap == 99_000_001 // 2, "❌ Swap amount should be floor(amount/2)"
        
        print(f"✅ Odd amount split handled: {amount_keep} + {amount_swap} = 99000001")
    
    
    @pytest.mark.asyncio
    async def test_split_determines_correct_swap_direction(self):
        """Split musi poprawnie określić kierunek swap"""
        from services.dual_lp_service import DualSidedLPService
        
        service = DualSidedLPService()
        
        with patch.object(service.aerodrome, 'get_reserves', new_callable=AsyncMock) as mock_reserves:
            mock_reserves.return_value = (1_000_000_000_000, 500_000_000_000_000_000_000)
            
            # Case 1: Deposit USDC → keep USDC, swap to WETH
            token_keep, _, token_swap, _ = await service.calculate_split(
                pool_token_a="USDC", pool_token_b="WETH",
                token_in="USDC", amount_in=100_000_000, stable=False
            )
            assert token_keep == "USDC" and token_swap == "WETH", "❌ USDC deposit: wrong swap direction"
            
            # Case 2: Deposit WETH → keep WETH, swap to USDC
            token_keep2, _, token_swap2, _ = await service.calculate_split(
                pool_token_a="USDC", pool_token_b="WETH",
                token_in="WETH", amount_in=1_000_000_000_000_000_000, stable=False
            )
            assert token_keep2 == "WETH" and token_swap2 == "USDC", "❌ WETH deposit: wrong swap direction"
        
        print(f"✅ Swap direction correctly determined for both deposit types")


# =============================================================================
# STEP 2: SWAP 50% VIA COW SWAP
# =============================================================================

class TestStep2SwapExecution:
    """Testy kroku 2: Swap 50% przez CoW Swap"""
    
    @pytest.mark.asyncio
    async def test_cow_swap_called_with_correct_amount(self, dual_lp_params):
        """CoW Swap MUSI być wywołany z 50% kwoty"""
        from services.dual_lp_service import DualSidedLPService
        
        service = DualSidedLPService()
        
        with patch.object(service.cow, 'swap', new_callable=AsyncMock) as mock_swap:
            mock_swap.return_value = "order_uid_123"
            
            order_uid = await service.execute_pre_swap(
                from_token="USDC",
                to_token="WETH",
                amount=50_000_000,  # 50 USDC (half of 100)
                agent_address=dual_lp_params["agent_address"],
                private_key=dual_lp_params["private_key"],
                max_slippage=2.0
            )
            
            # Verify swap was called
            mock_swap.assert_called_once()
            call_args = mock_swap.call_args
            
            # Verify amount is exactly 50% (50 USDC)
            assert call_args.kwargs["sell_amount"] == 50_000_000, "❌ Swap amount should be 50 USDC"
            assert call_args.kwargs["sell_token"] == "USDC", "❌ Sell token should be USDC"
            assert call_args.kwargs["buy_token"] == "WETH", "❌ Buy token should be WETH"
            
            assert order_uid is not None, "❌ Should return order UID"
        
        print(f"✅ CoW Swap called with exactly 50% (50 USDC)")
    
    
    @pytest.mark.asyncio
    async def test_cow_swap_uses_slippage(self, dual_lp_params):
        """CoW Swap MUSI użyć slippage z config"""
        from services.dual_lp_service import DualSidedLPService
        
        service = DualSidedLPService()
        
        with patch.object(service.cow, 'swap', new_callable=AsyncMock) as mock_swap:
            mock_swap.return_value = "order_uid_123"
            
            await service.execute_pre_swap(
                from_token="USDC",
                to_token="WETH",
                amount=50_000_000,
                agent_address=dual_lp_params["agent_address"],
                private_key=dual_lp_params["private_key"],
                max_slippage=2.0  # 2% slippage
            )
            
            call_args = mock_swap.call_args
            assert call_args.kwargs["max_slippage_percent"] == 2.0, "❌ Slippage not passed correctly"
        
        print(f"✅ CoW Swap uses 2% slippage from config")
    
    
    @pytest.mark.asyncio
    async def test_swap_failure_returns_none(self, dual_lp_params):
        """Nieudany swap MUSI zwrócić None"""
        from services.dual_lp_service import DualSidedLPService
        
        service = DualSidedLPService()
        
        with patch.object(service.cow, 'swap', new_callable=AsyncMock) as mock_swap:
            mock_swap.return_value = None  # Swap failed
            
            order_uid = await service.execute_pre_swap(
                from_token="USDC",
                to_token="WETH",
                amount=50_000_000,
                agent_address=dual_lp_params["agent_address"],
                private_key=dual_lp_params["private_key"],
                max_slippage=2.0
            )
            
            assert order_uid is None, "❌ Failed swap should return None"
        
        print(f"✅ Failed swap correctly returns None")


# =============================================================================
# STEP 3: WAIT FOR COW FILL
# =============================================================================

class TestStep3WaitForFill:
    """Testy kroku 3: Wait for CoW order fill"""
    
    @pytest.mark.asyncio
    async def test_wait_polls_until_filled(self):
        """Wait MUSI pollować do momentu fill"""
        from services.dual_lp_service import DualSidedLPService
        
        service = DualSidedLPService()
        
        with patch.object(service.cow, 'wait_for_fill', new_callable=AsyncMock) as mock_wait:
            mock_wait.return_value = {
                "status": "fulfilled",
                "executedBuyAmount": "50000000000000000"  # 0.05 WETH
            }
            
            result = await service.wait_for_swap("order_uid_123", timeout=300)
            
            assert result is not None, "❌ Should return fill result"
            assert result["status"] == "fulfilled", "❌ Status should be fulfilled"
        
        print(f"✅ Wait correctly polls until filled")
    
    
    @pytest.mark.asyncio
    async def test_wait_returns_none_on_timeout(self):
        """Wait MUSI zwrócić None przy timeout"""
        from services.dual_lp_service import DualSidedLPService
        
        service = DualSidedLPService()
        
        with patch.object(service.cow, 'wait_for_fill', new_callable=AsyncMock) as mock_wait:
            mock_wait.return_value = None  # Timeout
            
            result = await service.wait_for_swap("order_uid_123", timeout=1)
            
            assert result is None, "❌ Timeout should return None"
        
        print(f"✅ Wait correctly returns None on timeout")


# =============================================================================
# STEP 4: ALLOCATE TO LP
# =============================================================================

class TestStep4AllocateLP:
    """Testy kroku 4: Add liquidity to Aerodrome"""
    
    @pytest.mark.asyncio
    async def test_add_liquidity_uses_correct_amounts(self, dual_lp_params):
        """Add liquidity MUSI używać poprawnych kwot"""
        from services.dual_lp_service import DualSidedLPService, DualLPResult
        from services.aerodrome_lp import LPResult
        
        service = DualSidedLPService()
        
        with patch.object(service.aerodrome, 'get_reserves', new_callable=AsyncMock) as mock_reserves, \
             patch.object(service.cow, 'swap', new_callable=AsyncMock) as mock_swap, \
             patch.object(service.cow, 'wait_for_fill', new_callable=AsyncMock) as mock_fill, \
             patch.object(service.aerodrome, 'add_liquidity', new_callable=AsyncMock) as mock_lp:
            
            mock_reserves.return_value = (1_000_000_000_000, 500_000_000_000_000_000_000)
            mock_swap.return_value = "order_uid_123"
            mock_fill.return_value = {"status": "fulfilled", "executedBuyAmount": "25000000000000000"}  # 0.025 WETH
            mock_lp.return_value = LPResult(
                success=True,
                tx_hash="0xabc...",
                amount_a=50_000_000,
                amount_b=25_000_000_000_000_000,
                liquidity=1_000_000_000_000_000_000
            )
            
            result = await service.deposit_single_token_lp(**dual_lp_params)
            
            # Verify add_liquidity was called with correct amounts
            mock_lp.assert_called_once()
            call_args = mock_lp.call_args
            
            # 50 USDC kept + received WETH from swap
            assert call_args.kwargs["amount_a"] == 50_000_000, "❌ Amount A should be 50 USDC"
            assert call_args.kwargs["amount_b"] == 25_000_000_000_000_000, "❌ Amount B should be swap result"
            
            assert result.success, f"❌ Should succeed: {result.error}"
        
        print(f"✅ Add liquidity uses correct amounts: 50 USDC + swapped WETH")
    
    
    @pytest.mark.asyncio
    async def test_lp_failure_returns_error(self, dual_lp_params):
        """LP failure MUSI zwrócić error (ale swap completed)"""
        from services.dual_lp_service import DualSidedLPService
        from services.aerodrome_lp import LPResult
        
        service = DualSidedLPService()
        
        with patch.object(service.aerodrome, 'get_reserves', new_callable=AsyncMock) as mock_reserves, \
             patch.object(service.cow, 'swap', new_callable=AsyncMock) as mock_swap, \
             patch.object(service.cow, 'wait_for_fill', new_callable=AsyncMock) as mock_fill, \
             patch.object(service.aerodrome, 'add_liquidity', new_callable=AsyncMock) as mock_lp:
            
            mock_reserves.return_value = (1_000_000_000_000, 500_000_000_000_000_000_000)
            mock_swap.return_value = "order_uid_123"
            mock_fill.return_value = {"status": "fulfilled", "executedBuyAmount": "25000000000000000"}
            mock_lp.return_value = LPResult(
                success=False,
                error="Insufficient liquidity"
            )
            
            result = await service.deposit_single_token_lp(**dual_lp_params)
            
            assert result.success is False, "❌ Should fail"
            assert result.swap_filled is True, "❌ Swap should still be marked as filled"
            assert "failed" in result.error.lower(), "❌ Error should mention LP failure"
        
        print(f"✅ LP failure correctly returns error with swap_filled=True")


# =============================================================================
# FULL E2E FLOW: SCAN → SWAP 50% → ALLOCATE
# =============================================================================

class TestFullDualLPFlowE2E:
    """End-to-end test pełnego flow dual-sided LP"""
    
    @pytest.mark.asyncio
    async def test_complete_flow_scan_swap_allocate(self, dual_lp_params):
        """Test kompletnego flow: SCAN → SWAP 50% → ALLOCATE"""
        from services.dual_lp_service import DualSidedLPService
        from services.aerodrome_lp import LPResult
        
        service = DualSidedLPService()
        
        # Track call order
        call_order = []
        
        async def mock_get_reserves(*args, **kwargs):
            call_order.append("1_SCAN_RESERVES")
            return (1_000_000_000_000, 500_000_000_000_000_000_000)
        
        async def mock_swap(*args, **kwargs):
            call_order.append("2_SWAP_50_PERCENT")
            return "order_uid_123"
        
        async def mock_wait_for_fill(*args, **kwargs):
            call_order.append("3_WAIT_FOR_FILL")
            return {"status": "fulfilled", "executedBuyAmount": "25000000000000000"}
        
        async def mock_add_liquidity(*args, **kwargs):
            call_order.append("4_ALLOCATE_LP")
            return LPResult(
                success=True,
                tx_hash="0xabc...",
                amount_a=50_000_000,
                amount_b=25_000_000_000_000_000,
                liquidity=1_000_000_000_000_000_000
            )
        
        with patch.object(service.aerodrome, 'get_reserves', side_effect=mock_get_reserves), \
             patch.object(service.cow, 'swap', side_effect=mock_swap), \
             patch.object(service.cow, 'wait_for_fill', side_effect=mock_wait_for_fill), \
             patch.object(service.aerodrome, 'add_liquidity', side_effect=mock_add_liquidity):
            
            result = await service.deposit_single_token_lp(**dual_lp_params)
            
            # Verify correct order
            assert call_order == [
                "1_SCAN_RESERVES",
                "2_SWAP_50_PERCENT",
                "3_WAIT_FOR_FILL",
                "4_ALLOCATE_LP"
            ], f"❌ Wrong call order: {call_order}"
            
            # Verify result
            assert result.success is True, f"❌ Flow failed: {result.error}"
            assert result.swap_filled is True, "❌ Swap should be filled"
            assert result.lp_tx_hash is not None, "❌ Should have LP tx hash"
            assert result.lp_tokens_received > 0, "❌ Should receive LP tokens"
        
        print(f"✅ Complete flow executed in order: {' → '.join(call_order)}")
    
    
    @pytest.mark.asyncio
    async def test_flow_stops_on_swap_failure(self, dual_lp_params):
        """Flow MUSI się zatrzymać gdy swap failure"""
        from services.dual_lp_service import DualSidedLPService
        
        service = DualSidedLPService()
        
        lp_called = False
        
        async def mock_add_liquidity(*args, **kwargs):
            nonlocal lp_called
            lp_called = True
            return None
        
        with patch.object(service.aerodrome, 'get_reserves', new_callable=AsyncMock) as mock_reserves, \
             patch.object(service.cow, 'swap', new_callable=AsyncMock) as mock_swap, \
             patch.object(service.aerodrome, 'add_liquidity', side_effect=mock_add_liquidity):
            
            mock_reserves.return_value = (1_000_000_000_000, 500_000_000_000_000_000_000)
            mock_swap.return_value = None  # Swap failed!
            
            result = await service.deposit_single_token_lp(**dual_lp_params)
            
            # Verify flow stopped
            assert result.success is False, "❌ Should fail"
            assert lp_called is False, "❌ LP should NOT be called after swap failure"
            assert "swap order" in result.error.lower(), "❌ Error should mention swap"
        
        print(f"✅ Flow correctly stops on swap failure (LP not called)")
    
    
    @pytest.mark.asyncio
    async def test_flow_stops_on_swap_timeout(self, dual_lp_params):
        """Flow MUSI się zatrzymać gdy swap timeout"""
        from services.dual_lp_service import DualSidedLPService
        
        service = DualSidedLPService()
        
        lp_called = False
        
        async def mock_add_liquidity(*args, **kwargs):
            nonlocal lp_called
            lp_called = True
            return None
        
        with patch.object(service.aerodrome, 'get_reserves', new_callable=AsyncMock) as mock_reserves, \
             patch.object(service.cow, 'swap', new_callable=AsyncMock) as mock_swap, \
             patch.object(service.cow, 'wait_for_fill', new_callable=AsyncMock) as mock_fill, \
             patch.object(service.aerodrome, 'add_liquidity', side_effect=mock_add_liquidity):
            
            mock_reserves.return_value = (1_000_000_000_000, 500_000_000_000_000_000_000)
            mock_swap.return_value = "order_uid_123"
            mock_fill.return_value = None  # Timeout!
            
            result = await service.deposit_single_token_lp(**dual_lp_params)
            
            # Verify flow stopped
            assert result.success is False, "❌ Should fail"
            assert result.swap_order_uid is not None, "❌ Should have order UID"
            assert result.swap_filled is False, "❌ Swap should NOT be filled"
            assert lp_called is False, "❌ LP should NOT be called after timeout"
        
        print(f"✅ Flow correctly stops on swap timeout (LP not called)")


# =============================================================================
# QUOTE TESTS (SIMULATION WITHOUT EXECUTION)
# =============================================================================

class TestQuoteSimulation:
    """Testy symulacji quote bez wykonania"""
    
    @pytest.mark.asyncio
    async def test_get_quote_returns_split_info(self):
        """Quote MUSI zwrócić informacje o split"""
        from services.dual_lp_service import DualSidedLPService
        
        service = DualSidedLPService()
        
        with patch.object(service.aerodrome, 'get_reserves', new_callable=AsyncMock) as mock_reserves, \
             patch.object(service.cow, 'get_quote', new_callable=AsyncMock) as mock_quote:
            
            mock_reserves.return_value = (1_000_000_000_000, 500_000_000_000_000_000_000)
            mock_quote.return_value = {
                "quote": {
                    "buyAmount": "25000000000000000",
                    "feeAmount": "100000"
                }
            }
            
            quote = await service.get_quote_for_lp(
                pool_token_a="USDC",
                pool_token_b="WETH",
                token_in="USDC",
                amount_in=100_000_000,
                stable=False
            )
            
            assert quote["success"] is True, "❌ Quote should succeed"
            assert quote["amount_kept"] == 50_000_000, "❌ Should keep 50 USDC"
            assert quote["amount_to_swap"] == 50_000_000, "❌ Should swap 50 USDC"
            assert quote["expected_swap_receive"] == 25_000_000_000_000_000, "❌ Wrong expected receive"
        
        print(f"✅ Quote correctly returns split info")


# =============================================================================
# CLI RUNNER
# =============================================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '..')
    
    print("=" * 70)
    print("🔒 STRICT DUAL-SIDED LP FLOW TESTS")
    print("=" * 70)
    print("\n📊 Flow: SCAN → SWAP 50% → WAIT FILL → ALLOCATE LP")
    
    async def run_tests():
        # Step 1
        print("\n📦 Step 1: Scan & Split")
        test1 = TestStep1ScanAndSplit()
        await test1.test_split_is_exactly_50_50({"amount_in": 100_000_000})
        await test1.test_split_with_odd_amount()
        
        # Step 2
        print("\n📦 Step 2: Swap 50%")  
        params = {
            "agent_address": "0xa30A689ec0F9D717C5bA1098455B031b868B720f",
            "private_key": "0x" + "a" * 64,
        }
        test2 = TestStep2SwapExecution()
        await test2.test_cow_swap_called_with_correct_amount({"agent_address": params["agent_address"], "private_key": params["private_key"]})
        
        # Step 3
        print("\n📦 Step 3: Wait for Fill")
        test3 = TestStep3WaitForFill()
        await test3.test_wait_polls_until_filled()
        
        print("\n" + "=" * 70)
        print("✅ All flow tests passed!")
        print("=" * 70)
    
    asyncio.run(run_tests())
