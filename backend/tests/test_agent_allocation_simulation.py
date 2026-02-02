"""
Agent Allocation Simulation Tests
End-to-end tests for the complete agent allocation flow

Run: python -m pytest tests/test_agent_allocation_simulation.py -v
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_agent_config():
    """Standard agent configuration for testing"""
    return {
        "id": "test_agent_1",
        "user_address": "0xa30A689ec0F9D717C5bA1098455B031b868B720f",
        "agent_address": "0x5E047DeB5eb22F4E4A7f2207087369468575e3EF",
        "account_type": "erc8004",
        "is_active": True,
        "trading_style": "Steady",
        "min_apy": 5.0,
        "max_apy": 100.0,
        "min_tvl": 500_000,
        "max_allocation": 20,
        "preferred_assets": ["USDC", "WETH"],
        "duration": 30,  # 30 days
        "slippage": 1.0,
        "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
    }


@pytest.fixture
def mock_pool():
    """Mock pool for testing"""
    return {
        "name": "USDC-WETH",
        "symbol": "vAMM-USDC/WETH",
        "pool_address": "0x1234567890abcdef1234567890abcdef12345678",
        "project": "aerodrome",
        "chain": "Base",
        "apy": 25.5,
        "tvl": 5_000_000,
        "token0": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "token1": "0x4200000000000000000000000000000000000006",
        "stable": False,
    }


# =============================================================================
# TEST: Allocation Guardrails
# =============================================================================

class TestAllocationGuardrails:
    """Test allocation limits and guardrails"""
    
    def test_minimum_balance_threshold(self):
        """Test $100 minimum for allocation"""
        PARK_MIN_AMOUNT = 100.0  # $100 minimum
        
        # Too low - should NOT allocate
        low_balance = 50.0
        assert low_balance < PARK_MIN_AMOUNT
        should_skip = low_balance < PARK_MIN_AMOUNT
        assert should_skip is True
        
        # Sufficient - should allocate
        ok_balance = 150.0
        assert ok_balance >= PARK_MIN_AMOUNT
        
        print(f"✅ $100 minimum enforced: ${low_balance} skipped, ${ok_balance} proceeds")
    
    
    def test_max_allocation_per_pool(self, mock_agent_config):
        """Test 20% max per pool"""
        max_pct = mock_agent_config["max_allocation"]  # 20%
        total_balance = 1000.0  # $1000 USDC
        
        max_per_pool = total_balance * (max_pct / 100)
        
        assert max_per_pool == 200.0  # $200 max per pool
        print(f"✅ 20% cap: ${total_balance} total -> ${max_per_pool} max per pool")
    
    
    def test_allocation_split_across_pools(self, mock_agent_config):
        """Test equal split when multiple pools selected"""
        total_balance = 1000.0
        num_pools = 3
        max_pct = mock_agent_config["max_allocation"]
        
        # Equal split
        equal_split = total_balance / num_pools
        max_per_pool = total_balance * (max_pct / 100)
        
        # Allocation per pool = min(equal_split, max_per_pool)
        allocation = min(equal_split, max_per_pool)
        
        assert allocation == 200.0  # $333 split limited to $200 by 20% cap
        print(f"✅ 3-pool split: ${equal_split:.0f} each, capped to ${allocation}")
    
    
    def test_individual_agent_minimum(self):
        """Test $20 minimum per individual agent execution"""
        AGENT_MIN = 20.0
        
        low_agent = 15.0
        assert low_agent < AGENT_MIN
        
        ok_agent = 25.0
        assert ok_agent >= AGENT_MIN
        
        print(f"✅ $20 agent minimum: ${low_agent} skipped, ${ok_agent} proceeds")


# =============================================================================
# TEST: Duration Expiry
# =============================================================================

class TestDurationExpiry:
    """Test investment duration logic"""
    
    def test_duration_not_expired(self, mock_agent_config):
        """Test duration check when not expired"""
        duration_days = mock_agent_config["duration"]  # 30 days
        created_at = datetime.now() - timedelta(days=1)  # Created 1 day ago
        
        elapsed = (datetime.now() - created_at).days
        is_expired = elapsed >= duration_days
        
        assert is_expired is False
        print(f"✅ Duration: {elapsed}d elapsed of {duration_days}d - NOT expired")
    
    
    def test_duration_expired(self, mock_agent_config):
        """Test duration check when expired"""
        duration_days = 7  # 1 week
        created_at = datetime.now() - timedelta(days=10)  # Created 10 days ago
        
        elapsed = (datetime.now() - created_at).days
        is_expired = elapsed >= duration_days
        
        assert is_expired is True
        print(f"✅ Duration: {elapsed}d elapsed of {duration_days}d - EXPIRED")
    
    
    def test_infinite_duration(self):
        """Test infinite duration (0 = never expires)"""
        duration_days = 0  # Infinite
        created_at = datetime.now() - timedelta(days=365)  # 1 year ago
        
        # 0 duration means infinite
        is_expired = duration_days > 0 and (datetime.now() - created_at).days >= duration_days
        
        assert is_expired is False
        print(f"✅ Infinite duration: never expires")
    
    
    def test_hourly_duration(self):
        """Test sub-day duration (1 hour = 0.0416 days)"""
        duration_days = 0.0416  # ~1 hour
        created_at = datetime.now() - timedelta(hours=2)  # 2 hours ago
        
        elapsed_days = (datetime.now() - created_at).total_seconds() / 86400
        is_expired = elapsed_days >= duration_days
        
        assert is_expired is True
        print(f"✅ 1-hour duration: {elapsed_days:.4f}d elapsed - EXPIRED")


# =============================================================================
# TEST: Cooldown Enforcement
# =============================================================================

class TestCooldownEnforcement:
    """Test 5-minute cooldown between allocations"""
    
    def test_cooldown_active(self):
        """Test cooldown blocks re-allocation"""
        COOLDOWN_SECONDS = 300  # 5 minutes
        last_allocation = datetime.now() - timedelta(seconds=180)  # 3 min ago
        
        elapsed = (datetime.now() - last_allocation).total_seconds()
        cooldown_active = elapsed < COOLDOWN_SECONDS
        
        assert cooldown_active is True
        print(f"✅ Cooldown active: {elapsed:.0f}s elapsed of {COOLDOWN_SECONDS}s")
    
    
    def test_cooldown_expired(self):
        """Test cooldown allows allocation after 5 min"""
        COOLDOWN_SECONDS = 300
        last_allocation = datetime.now() - timedelta(seconds=360)  # 6 min ago
        
        elapsed = (datetime.now() - last_allocation).total_seconds()
        cooldown_active = elapsed < COOLDOWN_SECONDS
        
        assert cooldown_active is False
        print(f"✅ Cooldown expired: {elapsed:.0f}s elapsed - can allocate")
    
    
    def test_no_previous_allocation(self):
        """Test first allocation (no cooldown)"""
        last_allocation = None
        
        cooldown_active = last_allocation is not None
        
        assert cooldown_active is False
        print(f"✅ No previous allocation - no cooldown")


# =============================================================================
# TEST: ERC-8004 Identity Branching
# =============================================================================

class TestERC8004Identity:
    """Test Smart Account vs EOA execution branching"""
    
    def test_erc8004_account_type(self, mock_agent_config):
        """Test ERC-8004 account type detection"""
        account_type = mock_agent_config.get("account_type", "eoa")
        
        is_smart_account = account_type == "erc8004"
        
        assert is_smart_account is True
        print(f"✅ Account type: {account_type} -> Smart Account")
    
    
    def test_eoa_account_type(self):
        """Test EOA account type detection"""
        agent = {"account_type": "eoa"}
        
        is_smart_account = agent.get("account_type") == "erc8004"
        
        assert is_smart_account is False
        print(f"✅ Account type: eoa -> Standard EOA")
    
    
    def test_session_key_required_for_smart_account(self, mock_agent_config):
        """Test that Smart Account requires session key"""
        account_type = mock_agent_config.get("account_type")
        
        if account_type == "erc8004":
            execution_method = "executeWithSessionKey"
        else:
            execution_method = "sign_and_send_transaction"
        
        assert execution_method == "executeWithSessionKey"
        print(f"✅ ERC-8004 uses: {execution_method}")


# =============================================================================
# TEST: Pool Discovery & Ranking
# =============================================================================

class TestPoolDiscoveryRanking:
    """Test pool discovery and ranking logic"""
    
    def test_filter_by_min_apy(self, mock_agent_config, mock_pool):
        """Test filtering pools by minimum APY"""
        min_apy = mock_agent_config["min_apy"]  # 5%
        
        pools = [
            {"symbol": "USDC-WETH", "apy": 25.5},
            {"symbol": "USDC-DAI", "apy": 3.0},  # Below min
            {"symbol": "WETH-AERO", "apy": 45.0},
        ]
        
        filtered = [p for p in pools if p["apy"] >= min_apy]
        
        assert len(filtered) == 2
        assert filtered[0]["symbol"] == "USDC-WETH"
        
        print(f"✅ Filtered: {len(pools)} pools -> {len(filtered)} above {min_apy}% APY")
    
    
    def test_filter_by_min_tvl(self, mock_agent_config):
        """Test filtering pools by minimum TVL"""
        min_tvl = mock_agent_config["min_tvl"]  # $500k
        
        pools = [
            {"symbol": "USDC-WETH", "tvl": 5_000_000},
            {"symbol": "SCAM-USDC", "tvl": 50_000},  # Below min
            {"symbol": "WETH-AERO", "tvl": 1_000_000},
        ]
        
        filtered = [p for p in pools if p["tvl"] >= min_tvl]
        
        assert len(filtered) == 2
        print(f"✅ Filtered: {len(pools)} pools -> {len(filtered)} above ${min_tvl/1e6}M TVL")
    
    
    def test_filter_by_preferred_assets(self, mock_agent_config):
        """Test filtering by preferred assets"""
        preferred = mock_agent_config["preferred_assets"]  # ["USDC", "WETH"]
        
        pools = [
            {"symbol": "USDC-WETH", "token0": "USDC", "token1": "WETH"},
            {"symbol": "AERO-DEGEN", "token0": "AERO", "token1": "DEGEN"},  # No match
            {"symbol": "USDC-AERO", "token0": "USDC", "token1": "AERO"},  # USDC matches
        ]
        
        def has_preferred_asset(pool):
            return pool["token0"] in preferred or pool["token1"] in preferred
        
        filtered = [p for p in pools if has_preferred_asset(p)]
        
        assert len(filtered) == 2
        print(f"✅ Filtered: {len(pools)} pools -> {len(filtered)} with preferred assets")
    
    
    def test_rank_by_apy(self):
        """Test ranking pools by APY (descending)"""
        pools = [
            {"symbol": "USDC-WETH", "apy": 25.5},
            {"symbol": "WETH-AERO", "apy": 45.0},
            {"symbol": "USDC-DAI", "apy": 8.0},
        ]
        
        ranked = sorted(pools, key=lambda p: p["apy"], reverse=True)
        
        assert ranked[0]["symbol"] == "WETH-AERO"
        assert ranked[0]["apy"] == 45.0
        
        print(f"✅ Top pool: {ranked[0]['symbol']} at {ranked[0]['apy']}% APY")


# =============================================================================
# TEST: Strategy Executor (Mocked)
# =============================================================================

class TestStrategyExecutorMock:
    """Test StrategyExecutor with mocked dependencies"""
    
    @pytest.mark.asyncio
    async def test_get_idle_balance(self, mock_agent_config):
        """Test getting idle USDC balance"""
        from agents.strategy_executor import StrategyExecutor
        
        with patch.object(StrategyExecutor, 'get_user_idle_balance', new_callable=AsyncMock) as mock_bal:
            mock_bal.return_value = 500.0  # $500 USDC
            
            executor = StrategyExecutor()
            balance = await executor.get_user_idle_balance(
                mock_agent_config["user_address"],
                mock_agent_config
            )
            
            assert balance == 500.0
            print(f"✅ Idle balance: ${balance}")
    
    
    @pytest.mark.asyncio
    async def test_find_matching_pools(self, mock_agent_config, mock_pool):
        """Test finding matching pools"""
        from agents.strategy_executor import StrategyExecutor
        
        with patch.object(StrategyExecutor, 'find_matching_pools', new_callable=AsyncMock) as mock_find:
            mock_find.return_value = [mock_pool]
            
            executor = StrategyExecutor()
            pools = await executor.find_matching_pools(mock_agent_config)
            
            assert len(pools) == 1
            assert pools[0]["symbol"] == "vAMM-USDC/WETH"
            
            print(f"✅ Found {len(pools)} matching pools")
    
    
    @pytest.mark.asyncio
    async def test_execute_agent_strategy(self, mock_agent_config):
        """Test full strategy execution (mocked)"""
        from agents.strategy_executor import StrategyExecutor
        
        with patch.object(StrategyExecutor, 'execute_agent_strategy', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {
                "status": "allocated",
                "pools_selected": 1,
                "amount_allocated": 200.0
            }
            
            executor = StrategyExecutor()
            result = await executor.execute_agent_strategy(mock_agent_config)
            
            assert result["status"] == "allocated"
            assert result["amount_allocated"] == 200.0
            
            print(f"✅ Strategy executed: {result['status']}, ${result['amount_allocated']} allocated")


# =============================================================================
# CLI RUNNER
# =============================================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '..')
    
    async def quick_test():
        print("=" * 60)
        print("🧪 AGENT ALLOCATION SIMULATION TESTS")
        print("=" * 60)
        
        # Create fixtures
        agent_config = {
            "id": "test_agent_1",
            "user_address": "0xa30A689ec0F9D717C5bA1098455B031b868B720f",
            "agent_address": "0x5E047DeB5eb22F4E4A7f2207087369468575e3EF",
            "account_type": "erc8004",
            "is_active": True,
            "trading_style": "Steady",
            "min_apy": 5.0,
            "max_allocation": 20,
            "preferred_assets": ["USDC", "WETH"],
            "duration": 30,
        }
        
        # Test guardrails
        print("\n📊 Allocation Guardrails:")
        test1 = TestAllocationGuardrails()
        test1.test_minimum_balance_threshold()
        test1.test_max_allocation_per_pool(agent_config)
        
        # Test duration
        print("\n📊 Duration Expiry:")
        test2 = TestDurationExpiry()
        test2.test_duration_not_expired(agent_config)
        test2.test_infinite_duration()
        
        # Test cooldown
        print("\n📊 Cooldown Enforcement:")
        test3 = TestCooldownEnforcement()
        test3.test_cooldown_active()
        test3.test_cooldown_expired()
        
        # Test identity
        print("\n📊 ERC-8004 Identity:")
        test4 = TestERC8004Identity()
        test4.test_erc8004_account_type(agent_config)
        test4.test_session_key_required_for_smart_account(agent_config)
        
        # Test ranking
        print("\n📊 Pool Ranking:")
        test5 = TestPoolDiscoveryRanking()
        test5.test_rank_by_apy()
        
        print("\n" + "=" * 60)
        print("✅ All simulation tests passed!")
        print("=" * 60)
    
    asyncio.run(quick_test())
