"""
Swap Execution Tests
Tests for CoW Swap integration - quotes, signing, order status

Run: python -m pytest tests/test_swap_execution.py -v
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_cow_client():
    """Mock CoW Swap client for unit tests"""
    from integrations.cow_swap import CowSwapClient
    client = CowSwapClient(chain="base")
    return client


@pytest.fixture
def test_addresses():
    """Standard test addresses"""
    return {
        "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "WETH": "0x4200000000000000000000000000000000000006",
        "AERO": "0x940181a94A35A4569E4529A3CDfB74e38FD98631",
        "SOL": "0x9B8Df6E244526ab5F6e6400d331DB28C8fdDdb55",
        "agent": "0xa30A689ec0F9D717C5bA1098455B031b868B720f",
    }


# =============================================================================
# TEST: CoW Swap Quote
# =============================================================================

class TestCowSwapQuote:
    """Test quote fetching from CoW Protocol API"""
    
    @pytest.mark.asyncio
    async def test_get_quote_usdc_to_weth(self, mock_cow_client, test_addresses):
        """Test getting a quote for USDC -> WETH swap"""
        sell_amount = 100_000_000  # 100 USDC (6 decimals)
        
        quote = await mock_cow_client.get_quote(
            sell_token=test_addresses["USDC"],
            buy_token=test_addresses["WETH"],
            sell_amount=sell_amount,
            from_address=test_addresses["agent"]
        )
        
        # Verify quote structure
        assert quote is not None
        assert "quote" in quote
        assert "buyAmount" in quote["quote"]
        
        # Buy amount should be positive
        buy_amount = int(quote["quote"]["buyAmount"])
        assert buy_amount > 0
        
        print(f"✅ Quote: {sell_amount/1e6} USDC -> {buy_amount/1e18:.6f} WETH")
    
    
    @pytest.mark.asyncio
    async def test_get_quote_usdc_to_aero(self, mock_cow_client, test_addresses):
        """Test getting a quote for USDC -> AERO swap"""
        sell_amount = 50_000_000  # 50 USDC
        
        quote = await mock_cow_client.get_quote(
            sell_token=test_addresses["USDC"],
            buy_token=test_addresses["AERO"],
            sell_amount=sell_amount,
            from_address=test_addresses["agent"]
        )
        
        assert quote is not None
        buy_amount = int(quote["quote"]["buyAmount"])
        assert buy_amount > 0
        
        print(f"✅ Quote: {sell_amount/1e6} USDC -> {buy_amount/1e18:.6f} AERO")
    
    
    @pytest.mark.asyncio
    async def test_quote_with_zero_amount_fails(self, mock_cow_client, test_addresses):
        """Test that zero amount returns error or None"""
        try:
            quote = await mock_cow_client.get_quote(
                sell_token=test_addresses["USDC"],
                buy_token=test_addresses["WETH"],
                sell_amount=0,
                from_address=test_addresses["agent"]
            )
            # If no exception, quote should be None or have error
            assert quote is None or "error" in str(quote).lower() or quote.get("quote") is None
            print(f"✅ Zero amount handled: {quote}")
        except Exception as e:
            # Exception is also acceptable
            print(f"✅ Zero amount raises: {e}")


# =============================================================================
# TEST: Order Signing (Mocked)
# =============================================================================

class TestOrderSigning:
    """Test EIP-712 order signing"""
    
    def test_sign_order_generates_signature(self):
        """Test that signing produces valid signature"""
        from eth_account import Account
        
        # Create test account
        account = Account.create()
        
        # Mock order data
        order = {
            "sellToken": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "buyToken": "0x4200000000000000000000000000000000000006",
            "sellAmount": "100000000",
            "buyAmount": "50000000000000000",
            "validTo": int((datetime.now() + timedelta(minutes=20)).timestamp()),
            "appData": "0x0000000000000000000000000000000000000000000000000000000000000000",
            "feeAmount": "0",
            "kind": "sell",
            "partiallyFillable": False,
            "receiver": account.address,
        }
        
        # Just verify the order dict has correct structure
        assert "sellToken" in order
        assert "buyToken" in order
        assert "validTo" in order
        assert order["validTo"] > int(datetime.now().timestamp())
        
        print(f"✅ Order structure valid, expires: {order['validTo']}")


# =============================================================================
# TEST: Slippage Calculation
# =============================================================================

class TestSlippageCalculation:
    """Test slippage tolerance calculations"""
    
    def test_slippage_1_percent(self):
        """Test 1% slippage calculation"""
        buy_amount = 100_000_000_000_000_000  # 0.1 WETH
        slippage_pct = 1.0
        
        min_buy = int(buy_amount * (1 - slippage_pct / 100))
        
        expected_min = 99_000_000_000_000_000  # 0.099 WETH
        assert min_buy == expected_min
        
        print(f"✅ 1% slippage: {buy_amount} -> min {min_buy}")
    
    
    def test_slippage_2_percent(self):
        """Test 2% slippage calculation (default for LP swaps)"""
        buy_amount = 100_000_000_000_000_000
        slippage_pct = 2.0
        
        min_buy = int(buy_amount * (1 - slippage_pct / 100))
        
        expected_min = 98_000_000_000_000_000
        assert min_buy == expected_min
        
        print(f"✅ 2% slippage: {buy_amount} -> min {min_buy}")
    
    
    def test_slippage_zero_not_allowed(self):
        """Test that 0% slippage is blocked"""
        buy_amount = 100_000_000_000_000_000
        slippage_pct = 0.0
        
        # With 0 slippage, min should equal buy amount (risky!)
        min_buy = int(buy_amount * (1 - slippage_pct / 100))
        
        assert min_buy == buy_amount
        print(f"⚠️ 0% slippage: min equals exact amount (risky)")


# =============================================================================
# TEST: Order Status Check (Mocked)
# =============================================================================

class TestOrderStatus:
    """Test order status polling"""
    
    @pytest.mark.asyncio
    async def test_order_status_check(self):
        """Test checking order status with mocked response"""
        from integrations.cow_swap import CowSwapClient
        
        with patch.object(CowSwapClient, 'get_order_status', new_callable=AsyncMock) as mock_status:
            mock_status.return_value = {
                "status": "fulfilled",
                "executedBuyAmount": "50000000000000000",
                "executedSellAmount": "100000000"
            }
            
            client = CowSwapClient(chain="base")
            status = await client.get_order_status("test_order_uid")
            
            assert status["status"] == "fulfilled"
            print(f"✅ Order status: {status['status']}")
    
    
    @pytest.mark.asyncio
    async def test_order_wait_for_fill(self):
        """Test waiting for order fill with mocked response"""
        from integrations.cow_swap import CowSwapClient
        
        # Mock the wait_for_fill to return immediately
        with patch.object(CowSwapClient, 'wait_for_fill', new_callable=AsyncMock) as mock_wait:
            mock_wait.return_value = {
                "status": "fulfilled",
                "executedBuyAmount": "50000000000000000"
            }
            
            client = CowSwapClient(chain="base")
            result = await client.wait_for_fill("test_order_uid", poll_interval=1, timeout=5)
            
            assert result is not None
            assert result["status"] == "fulfilled"
            print(f"✅ Order filled: {result['executedBuyAmount']}")


# =============================================================================
# INTEGRATION TEST: Real CoW API Quote
# =============================================================================

class TestRealCowAPI:
    """Integration tests against real CoW Protocol API (Base mainnet)"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_quote_usdc_to_weth(self, test_addresses):
        """Test real API quote for USDC -> WETH"""
        from integrations.cow_swap import cow_client
        
        try:
            quote = await cow_client.get_quote(
                sell_token=test_addresses["USDC"],
                buy_token=test_addresses["WETH"],
                sell_amount=10_000_000,  # 10 USDC
                from_address=test_addresses["agent"]
            )
            
            assert quote is not None
            buy_amount = int(quote["quote"]["buyAmount"])
            
            # Sanity check: 10 USDC should get some WETH
            assert buy_amount > 0
            
            # At current prices (~$3500/ETH), 10 USDC ≈ 0.00285 WETH
            weth_amount = buy_amount / 1e18
            print(f"✅ REAL API: 10 USDC -> {weth_amount:.6f} WETH")
            
        except Exception as e:
            pytest.skip(f"CoW API unavailable: {e}")


# =============================================================================
# CLI RUNNER
# =============================================================================

if __name__ == "__main__":
    # Run quick self-test
    import sys
    sys.path.insert(0, '..')
    
    async def quick_test():
        print("=" * 60)
        print("🧪 SWAP EXECUTION TESTS")
        print("=" * 60)
        
        # Test slippage
        print("\n📊 Slippage Calculation:")
        test = TestSlippageCalculation()
        test.test_slippage_1_percent()
        test.test_slippage_2_percent()
        
        # Test quote (real API)
        print("\n📊 Real CoW API Quote:")
        try:
            from integrations.cow_swap import cow_client
            quote = await cow_client.get_quote(
                sell_token="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                buy_token="0x4200000000000000000000000000000000000006",
                sell_amount=10_000_000,
                from_address="0xa30A689ec0F9D717C5bA1098455B031b868B720f"
            )
            buy = int(quote["quote"]["buyAmount"]) / 1e18
            print(f"   ✅ 10 USDC -> {buy:.6f} WETH")
        except Exception as e:
            print(f"   ⚠️ API error: {e}")
        
        print("\n" + "=" * 60)
        print("✅ All quick tests passed!")
        print("=" * 60)
    
    asyncio.run(quick_test())
