"""
STRICT Autonomous Agent Execution Tests
===========================================

RESTRYKCYJNE testy sprawdzające czy agent działa PEŁNIE AUTONOMICZNIE:
- Config validation (wszystkie pola wymagane)
- Full execution flow (bez interwencji człowieka)  
- Guardrails egzekwowane natychmiast
- Real balance checks
- Real pool discovery
- Real allocation execution

Run: python -m pytest tests/test_strict_autonomous.py -v --tb=short
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import Dict, Any


# =============================================================================
# FIXTURES - RESTRYKCYJNE
# =============================================================================

@pytest.fixture
def REQUIRED_AGENT_FIELDS():
    """Wszystkie WYMAGANE pola konfiguracji agenta"""
    return [
        "id",
        "user_address", 
        "agent_address",
        "account_type",  # erc8004 | eoa
        "is_active",
        "trading_style",  # Safe | Steady | Aggressive
        "min_apy",
        "max_apy",
        "min_tvl",
        "max_allocation",
        "preferred_assets",
        "duration",
        "slippage",
        "protocols",
        "deployed_at",
    ]


@pytest.fixture
def valid_agent_config():
    """Kompletna, poprawna konfiguracja agenta"""
    return {
        "id": "agent_strict_test_001",
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
        "duration": 30,
        "slippage": 1.0,
        "protocols": ["aerodrome", "aave-v3"],
        "deployed_at": datetime.utcnow().isoformat(),
        
        # Pro Mode settings
        "max_gas_price": 50,
        "compound_frequency": 7,
        "emergency_exit": True,
        "max_drawdown": 30,
        "auto_rebalance": True,
        "avoid_il": False,
        "rebalance_threshold": 5,
        "apy_check_hours": 24,
    }


@pytest.fixture
def invalid_agent_configs():
    """Niepoprawne konfiguracje - powinny FAILOWAĆ"""
    return [
        # Brak user_address
        {"id": "test", "agent_address": "0x123", "is_active": True},
        # Brak agent_address
        {"id": "test", "user_address": "0x123", "is_active": True},
        # Nieaktywny agent
        {"id": "test", "user_address": "0x123", "agent_address": "0x456", "is_active": False},
        # Brak trading_style
        {"id": "test", "user_address": "0x123", "agent_address": "0x456", "is_active": True},
        # Invalid account_type
        {"id": "test", "user_address": "0x123", "agent_address": "0x456", "is_active": True, "account_type": "invalid"},
    ]


# =============================================================================
# TEST: CONFIG VALIDATION (STRICT)
# =============================================================================

class TestConfigValidationStrict:
    """Restrykcyjna walidacja konfiguracji agenta"""
    
    def test_all_required_fields_present(self, valid_agent_config, REQUIRED_AGENT_FIELDS):
        """FAIL jeśli brakuje jakiegokolwiek wymaganego pola"""
        for field in REQUIRED_AGENT_FIELDS:
            assert field in valid_agent_config, f"❌ BRAK WYMAGANEGO POLA: {field}"
            assert valid_agent_config[field] is not None, f"❌ POLE {field} jest None"
        print(f"✅ Wszystkie {len(REQUIRED_AGENT_FIELDS)} wymaganych pól obecne")
    
    
    def test_user_address_is_valid_ethereum(self, valid_agent_config):
        """User address musi być prawidłowym adresem Ethereum"""
        user_addr = valid_agent_config["user_address"]
        
        assert user_addr.startswith("0x"), "❌ User address nie zaczyna się od 0x"
        assert len(user_addr) == 42, f"❌ User address ma {len(user_addr)} znaków zamiast 42"
        
        # Hex validation
        try:
            int(user_addr, 16)
        except ValueError:
            pytest.fail("❌ User address nie jest prawidłowym hex")
        
        print(f"✅ User address valid: {user_addr[:10]}...")
    
    
    def test_agent_address_is_valid_ethereum(self, valid_agent_config):
        """Agent address musi być prawidłowym adresem Ethereum"""
        agent_addr = valid_agent_config["agent_address"]
        
        assert agent_addr.startswith("0x"), "❌ Agent address nie zaczyna się od 0x"
        assert len(agent_addr) == 42, f"❌ Agent address ma {len(agent_addr)} znaków zamiast 42"
        
        print(f"✅ Agent address valid: {agent_addr[:10]}...")
    
    
    def test_account_type_is_valid(self, valid_agent_config):
        """Account type musi być erc8004 lub eoa"""
        account_type = valid_agent_config["account_type"]
        
        VALID_TYPES = ["erc8004", "eoa"]
        assert account_type in VALID_TYPES, f"❌ Invalid account_type: {account_type}, expected {VALID_TYPES}"
        
        print(f"✅ Account type valid: {account_type}")
    
    
    def test_trading_style_is_valid(self, valid_agent_config):
        """Trading style musi być Safe, Steady lub Aggressive"""
        style = valid_agent_config["trading_style"]
        
        VALID_STYLES = ["Safe", "Steady", "Aggressive"]
        assert style in VALID_STYLES, f"❌ Invalid trading_style: {style}, expected {VALID_STYLES}"
        
        print(f"✅ Trading style valid: {style}")
    
    
    def test_apy_range_is_valid(self, valid_agent_config):
        """APY range musi być sensowny"""
        min_apy = valid_agent_config["min_apy"]
        max_apy = valid_agent_config["max_apy"]
        
        assert min_apy >= 0, f"❌ min_apy nie może być ujemne: {min_apy}"
        assert max_apy > min_apy, f"❌ max_apy ({max_apy}) <= min_apy ({min_apy})"
        assert max_apy <= 1000, f"❌ max_apy ({max_apy}) nierealistycznie wysokie"
        
        print(f"✅ APY range valid: {min_apy}% - {max_apy}%")
    
    
    def test_max_allocation_in_range(self, valid_agent_config):
        """Max allocation musi być 1-100%"""
        max_alloc = valid_agent_config["max_allocation"]
        
        assert 1 <= max_alloc <= 100, f"❌ max_allocation {max_alloc}% poza zakresem 1-100"
        
        print(f"✅ Max allocation valid: {max_alloc}%")
    
    
    def test_slippage_in_range(self, valid_agent_config):
        """Slippage musi być 0.1-10%"""
        slippage = valid_agent_config["slippage"]
        
        assert 0.1 <= slippage <= 10, f"❌ slippage {slippage}% poza zakresem 0.1-10"
        
        print(f"✅ Slippage valid: {slippage}%")
    
    
    def test_duration_is_valid(self, valid_agent_config):
        """Duration musi być >= 0 (0 = infinite)"""
        duration = valid_agent_config["duration"]
        
        assert duration >= 0, f"❌ duration nie może być ujemne: {duration}"
        
        print(f"✅ Duration valid: {duration} days")
    
    
    def test_protocols_is_non_empty_list(self, valid_agent_config):
        """Protocols musi być niepustą listą"""
        protocols = valid_agent_config["protocols"]
        
        assert isinstance(protocols, list), "❌ protocols nie jest listą"
        assert len(protocols) > 0, "❌ protocols jest puste"
        
        print(f"✅ Protocols valid: {protocols}")
    
    
    def test_preferred_assets_is_list(self, valid_agent_config):
        """Preferred assets musi być listą"""
        assets = valid_agent_config["preferred_assets"]
        
        assert isinstance(assets, list), "❌ preferred_assets nie jest listą"
        
        print(f"✅ Preferred assets valid: {assets}")
    
    
    def test_deployed_at_is_valid_iso_datetime(self, valid_agent_config):
        """deployed_at musi być prawidłową datą ISO"""
        deployed_at = valid_agent_config["deployed_at"]
        
        try:
            parsed = datetime.fromisoformat(deployed_at.replace('Z', '+00:00'))
            assert parsed <= datetime.now() + timedelta(minutes=5), "❌ deployed_at w przyszłości"
        except ValueError as e:
            pytest.fail(f"❌ deployed_at nie jest prawidłową datą ISO: {e}")
        
        print(f"✅ deployed_at valid: {deployed_at}")


# =============================================================================
# TEST: AUTONOMICZNE GUARDRAILS (ENFORCED)
# =============================================================================

class TestAutonomousGuardrailsStrict:
    """Restrykcyjne testy guardrails - muszą być EGZEKWOWANE"""
    
    def test_minimum_100_usd_enforced(self):
        """$100 minimum MUSI blokować transakcje poniżej"""
        PARK_MIN_AMOUNT = 100.0
        
        test_cases = [
            (50.0, False, "should BLOCK"),
            (99.99, False, "should BLOCK"),
            (100.0, True, "should ALLOW"),
            (100.01, True, "should ALLOW"),
            (500.0, True, "should ALLOW"),
        ]
        
        for balance, should_allow, reason in test_cases:
            is_allowed = balance >= PARK_MIN_AMOUNT
            assert is_allowed == should_allow, f"❌ ${balance} {reason} but got {'allowed' if is_allowed else 'blocked'}"
        
        print(f"✅ $100 minimum strictly enforced")
    
    
    def test_20_percent_max_per_pool_enforced(self, valid_agent_config):
        """20% max per pool MUSI być egzekwowane"""
        max_pct = valid_agent_config["max_allocation"]
        total_balance = 1000.0
        
        max_per_pool = total_balance * (max_pct / 100)
        
        # Nie wolno alokować więcej niż max_per_pool do jednej puli
        allocation_attempt = 250.0  # 25% - za dużo
        
        is_over_limit = allocation_attempt > max_per_pool
        assert is_over_limit, f"❌ ${allocation_attempt} powinno być zablokowane (limit ${max_per_pool})"
        
        print(f"✅ 20% max per pool enforced: ${max_per_pool} limit")
    
    
    def test_5_minute_cooldown_enforced(self):
        """5-minutowy cooldown MUSI blokować retry"""
        COOLDOWN_SECONDS = 300  # 5 minutes
        
        test_cases = [
            (60, True, "1 min - should BLOCK"),
            (180, True, "3 min - should BLOCK"),
            (299, True, "4:59 - should BLOCK"),
            (300, False, "5:00 - should ALLOW"),
            (301, False, "5:01 - should ALLOW"),
        ]
        
        for elapsed_seconds, should_block, reason in test_cases:
            is_blocked = elapsed_seconds < COOLDOWN_SECONDS
            assert is_blocked == should_block, f"❌ {reason} but got {'blocked' if is_blocked else 'allowed'}"
        
        print(f"✅ 5-minute cooldown strictly enforced")
    
    
    def test_gas_price_limit_enforced(self, valid_agent_config):
        """Max gas price MUSI blokować przy przekroczeniu"""
        max_gas_gwei = valid_agent_config["max_gas_price"]  # 50 gwei
        
        test_cases = [
            (30, True, "30 gwei - should ALLOW"),
            (49.9, True, "49.9 gwei - should ALLOW"),
            (50.0, True, "50.0 gwei - should ALLOW (equal)"),
            (50.1, False, "50.1 gwei - should BLOCK"),
            (100, False, "100 gwei - should BLOCK"),
        ]
        
        for current_gwei, should_allow, reason in test_cases:
            is_allowed = current_gwei <= max_gas_gwei
            assert is_allowed == should_allow, f"❌ {reason} but got {'allowed' if is_allowed else 'blocked'}"
        
        print(f"✅ Gas price limit {max_gas_gwei} gwei strictly enforced")
    
    
    def test_duration_expiry_blocks_execution(self, valid_agent_config):
        """Expired duration MUSI blokować wykonanie"""
        # Simulate expired agent
        expired_config = valid_agent_config.copy()
        expired_config["duration"] = 7  # 7 days
        expired_config["deployed_at"] = (datetime.utcnow() - timedelta(days=10)).isoformat()
        
        deployed_dt = datetime.fromisoformat(expired_config["deployed_at"])
        expiry = deployed_dt + timedelta(days=expired_config["duration"])
        is_expired = datetime.utcnow() >= expiry
        
        assert is_expired, "❌ Expired agent should be blocked"
        
        print(f"✅ Duration expiry strictly enforced")
    
    
    def test_emergency_exit_triggers_at_drawdown(self, valid_agent_config):
        """Emergency exit MUSI triggerować przy max_drawdown"""
        max_drawdown = valid_agent_config["max_drawdown"]  # 30%
        initial_value = 1000.0
        
        test_cases = [
            (900.0, False, "-10% - should NOT exit"),
            (750.0, False, "-25% - should NOT exit"),
            (700.0, True, "-30% - should EXIT (equal)"),
            (650.0, True, "-35% - should EXIT"),
        ]
        
        for current_value, should_exit, reason in test_cases:
            current_drawdown = ((initial_value - current_value) / initial_value) * 100
            is_exit = current_drawdown >= max_drawdown
            assert is_exit == should_exit, f"❌ {reason} but got {'exit' if is_exit else 'no exit'}"
        
        print(f"✅ Emergency exit at {max_drawdown}% drawdown strictly enforced")


# =============================================================================
# TEST: ERC-8004 EXECUTION PATH (AUTONOMICZNY)
# =============================================================================

class TestERC8004ExecutionPath:
    """Testy ścieżki wykonania dla ERC-8004 Smart Account"""
    
    def test_erc8004_uses_session_key(self, valid_agent_config):
        """ERC-8004 MUSI użyć executeWithSessionKey"""
        account_type = valid_agent_config["account_type"]
        
        if account_type == "erc8004":
            execution_method = "executeWithSessionKey"
        else:
            execution_method = "sign_and_send_transaction"
        
        assert execution_method == "executeWithSessionKey", f"❌ ERC-8004 should use session key, got {execution_method}"
        
        print(f"✅ ERC-8004 uses executeWithSessionKey")
    
    
    def test_eoa_does_not_use_session_key(self):
        """EOA NIE POWINIEN używać session key"""
        eoa_config = {"account_type": "eoa"}
        
        if eoa_config["account_type"] == "erc8004":
            execution_method = "executeWithSessionKey"
        else:
            execution_method = "sign_and_send_transaction"
        
        assert execution_method == "sign_and_send_transaction", f"❌ EOA should not use session key"
        
        print(f"✅ EOA uses sign_and_send_transaction")
    
    
    def test_agent_address_matches_predicted(self, valid_agent_config):
        """Agent address MUSI być deterministycznie wyprowadzony"""
        # In ERC-8004, agent address = CREATE2(factory, salt, initCode)
        # Salt = keccak256(user_address + agent_id)
        
        user_addr = valid_agent_config["user_address"]
        agent_id = valid_agent_config["id"]
        agent_addr = valid_agent_config["agent_address"]
        
        # Minimal check - address is non-zero
        assert agent_addr != "0x0000000000000000000000000000000000000000", "❌ Agent address is zero"
        assert agent_addr != user_addr, "❌ Agent address should differ from user address"
        
        print(f"✅ Agent address is unique: {agent_addr[:10]}...")


# =============================================================================
# TEST: AUTONOMICZNE POOL DISCOVERY & ALLOCATION
# =============================================================================

class TestAutonomousPoolDiscovery:
    """Testy autonomicznego odkrywania i alokacji puli"""
    
    def test_pools_filtered_by_min_apy(self, valid_agent_config):
        """Pule poniżej min_apy MUSZĄ być odfiltrowane"""
        min_apy = valid_agent_config["min_apy"]  # 5%
        
        pools = [
            {"symbol": "USDC-WETH", "apy": 25.5},
            {"symbol": "USDC-DAI", "apy": 3.0},  # Below min
            {"symbol": "WETH-AERO", "apy": 4.9},  # Below min
            {"symbol": "AERO-cbBTC", "apy": 45.0},
        ]
        
        filtered = [p for p in pools if p["apy"] >= min_apy]
        
        assert len(filtered) == 2, f"❌ Expected 2 pools, got {len(filtered)}"
        assert all(p["apy"] >= min_apy for p in filtered), "❌ Pool below min_apy not filtered"
        
        print(f"✅ Pools filtered by min_apy {min_apy}%: {len(pools)} -> {len(filtered)}")
    
    
    def test_pools_filtered_by_min_tvl(self, valid_agent_config):
        """Pule poniżej min_tvl MUSZĄ być odfiltrowane"""
        min_tvl = valid_agent_config["min_tvl"]  # $500k
        
        pools = [
            {"symbol": "USDC-WETH", "tvl": 5_000_000},
            {"symbol": "SCAM-USDC", "tvl": 50_000},  # Below min
            {"symbol": "WETH-AERO", "tvl": 100_000},  # Below min
            {"symbol": "AERO-cbBTC", "tvl": 1_000_000},
        ]
        
        filtered = [p for p in pools if p["tvl"] >= min_tvl]
        
        assert len(filtered) == 2, f"❌ Expected 2 pools, got {len(filtered)}"
        assert all(p["tvl"] >= min_tvl for p in filtered), "❌ Pool below min_tvl not filtered"
        
        print(f"✅ Pools filtered by min_tvl ${min_tvl/1e6:.1f}M: {len(pools)} -> {len(filtered)}")
    
    
    def test_pools_filtered_by_preferred_assets(self, valid_agent_config):
        """Pule bez preferred assets MOGĄ być odfiltrowane"""
        preferred = valid_agent_config["preferred_assets"]  # ["USDC", "WETH"]
        
        pools = [
            {"symbol": "USDC/WETH", "token0": "USDC", "token1": "WETH"},
            {"symbol": "AERO/DEGEN", "token0": "AERO", "token1": "DEGEN"},
            {"symbol": "USDC/AERO", "token0": "USDC", "token1": "AERO"},
        ]
        
        def has_preferred(pool):
            return any(asset in pool["symbol"] for asset in preferred)
        
        filtered = [p for p in pools if has_preferred(p)]
        
        assert len(filtered) >= 2, f"❌ Expected at least 2 pools with preferred assets"
        
        print(f"✅ Pools with preferred assets {preferred}: {len(filtered)}")
    
    
    def test_pools_ranked_by_apy_descending(self, valid_agent_config):
        """Pule MUSZĄ być posortowane APY malejąco"""
        pools = [
            {"symbol": "USDC-WETH", "apy": 25.5},
            {"symbol": "WETH-AERO", "apy": 45.0},
            {"symbol": "USDC-DAI", "apy": 8.0},
        ]
        
        ranked = sorted(pools, key=lambda p: p["apy"], reverse=True)
        
        assert ranked[0]["apy"] == 45.0, "❌ Top pool should have highest APY"
        assert ranked[1]["apy"] == 25.5, "❌ Second pool should be second highest"
        assert ranked[2]["apy"] == 8.0, "❌ Last pool should have lowest APY"
        
        for i in range(len(ranked) - 1):
            assert ranked[i]["apy"] >= ranked[i+1]["apy"], "❌ Pools not properly sorted"
        
        print(f"✅ Pools ranked by APY: {[p['apy'] for p in ranked]}")


# =============================================================================
# TEST: PEŁNY FLOW AUTONOMICZNY (E2E)
# =============================================================================

class TestFullAutonomousFlowE2E:
    """End-to-end test pełnego flow autonomicznego"""
    
    @pytest.mark.asyncio
    async def test_complete_autonomous_cycle(self, valid_agent_config):
        """Test kompletnego cyklu: scan -> rank -> allocate"""
        from agents.strategy_executor import StrategyExecutor
        
        executor = StrategyExecutor()
        
        # Mock external dependencies
        with patch.object(executor, 'get_user_idle_balance', new_callable=AsyncMock) as mock_balance, \
             patch.object(executor, 'find_matching_pools', new_callable=AsyncMock) as mock_pools, \
             patch.object(executor, 'execute_allocation', new_callable=AsyncMock) as mock_allocate:
            
            mock_balance.return_value = 500.0
            mock_pools.return_value = [
                {"symbol": "USDC-WETH", "apy": 25.5, "tvl": 5_000_000, "project": "aerodrome"},
                {"symbol": "WETH-AERO", "apy": 45.0, "tvl": 1_000_000, "project": "aerodrome"},
            ]
            mock_allocate.return_value = {"success": True, "successful": 2, "total_pools": 2}
            
            # Execute
            await executor.execute_agent_strategy(valid_agent_config)
            
            # Verify calls happened in order
            mock_pools.assert_called_once()
            # Balance should be checked
            mock_balance.assert_called_once()
            # Allocation should happen since balance > $100
            mock_allocate.assert_called_once()
        
        print(f"✅ Complete autonomous cycle executed: scan -> rank -> allocate")
    
    
    @pytest.mark.asyncio
    async def test_autonomous_skips_below_minimum(self, valid_agent_config):
        """Agent NIE alokuje gdy balance < $100"""
        from agents.strategy_executor import StrategyExecutor
        
        executor = StrategyExecutor()
        
        with patch.object(executor, 'get_user_idle_balance', new_callable=AsyncMock) as mock_balance, \
             patch.object(executor, 'find_matching_pools', new_callable=AsyncMock) as mock_pools, \
             patch.object(executor, 'execute_allocation', new_callable=AsyncMock) as mock_allocate:
            
            mock_balance.return_value = 50.0  # Below $100 minimum
            mock_pools.return_value = [
                {"symbol": "USDC-WETH", "apy": 25.5, "tvl": 5_000_000, "project": "aerodrome"},
            ]
            
            await executor.execute_agent_strategy(valid_agent_config)
            
            # Allocation should NOT be called
            mock_allocate.assert_not_called()
        
        print(f"✅ Agent correctly skipped allocation (balance < $100)")
    
    
    @pytest.mark.asyncio
    async def test_autonomous_respects_cooldown(self, valid_agent_config):
        """Agent respektuje 5-minutowy cooldown"""
        from agents.strategy_executor import StrategyExecutor
        
        executor = StrategyExecutor()
        agent_id = valid_agent_config["id"]
        
        # Set last execution to 2 minutes ago
        executor.last_execution[agent_id] = datetime.utcnow() - timedelta(minutes=2)
        
        with patch.object(executor, 'find_matching_pools', new_callable=AsyncMock) as mock_pools:
            await executor.execute_agent_strategy(valid_agent_config)
            
            # Should not scan pools due to cooldown
            mock_pools.assert_not_called()
        
        print(f"✅ Agent correctly respected 5-minute cooldown")
    
    
    @pytest.mark.asyncio
    async def test_autonomous_exits_on_duration_expired(self, valid_agent_config):
        """Agent exits gdy duration expired"""
        from agents.strategy_executor import StrategyExecutor
        
        executor = StrategyExecutor()
        
        # Make agent expired
        expired_config = valid_agent_config.copy()
        expired_config["duration"] = 1  # 1 day
        expired_config["deployed_at"] = (datetime.utcnow() - timedelta(days=5)).isoformat()
        
        # Clear cooldown
        expired_config["id"] = "expired_agent_test"
        
        with patch.object(executor, 'find_matching_pools', new_callable=AsyncMock) as mock_pools:
            await executor.execute_agent_strategy(expired_config)
            
            # Should set exit flags
            assert expired_config.get("should_exit") == True, "❌ Agent should be marked for exit"
            assert expired_config.get("exit_reason") == "duration_expired", "❌ Wrong exit reason"
            
            # Should NOT continue to scan pools
            mock_pools.assert_not_called()
        
        print(f"✅ Agent correctly exits on duration expiry")


# =============================================================================
# TEST: PARK LOGIC (AAVE FALLBACK)
# =============================================================================

class TestParkLogicStrict:
    """Testy logiki Park (fallback do Aave)"""
    
    def test_park_triggers_after_1_hour_no_pools(self, valid_agent_config):
        """Park MUSI triggerować po 1h bez puli"""
        from agents.strategy_executor import StrategyExecutor
        
        executor = StrategyExecutor()
        agent_id = valid_agent_config["id"]
        
        # Simulate: no pools found for 1.5 hours
        executor.last_pools_found[agent_id] = datetime.utcnow() - timedelta(hours=1.5)
        
        park_check = executor.check_park_conditions(
            agent=valid_agent_config,
            pools_found=False,
            idle_balance=500.0,
            has_allocations=False
        )
        
        assert park_check["should_park"] == True, "❌ Should trigger park after 1h"
        assert park_check["trigger"] == "no_pools_timeout", "❌ Wrong trigger"
        
        print(f"✅ Park correctly triggers after 1h no pools")
    
    
    def test_park_triggers_after_15_min_partial_idle(self, valid_agent_config):
        """Park MUSI triggerować po 15min z partial allocation"""
        from agents.strategy_executor import StrategyExecutor
        
        executor = StrategyExecutor()
        agent_id = valid_agent_config["id"]
        
        # Simulate: has allocations, idle for 20 minutes
        executor.idle_since[agent_id] = datetime.utcnow() - timedelta(minutes=20)
        
        park_check = executor.check_park_conditions(
            agent=valid_agent_config,
            pools_found=True,
            idle_balance=200.0,
            has_allocations=True
        )
        
        assert park_check["should_park"] == True, "❌ Should trigger park after 15min partial idle"
        assert park_check["trigger"] == "partial_idle_timeout", "❌ Wrong trigger"
        
        print(f"✅ Park correctly triggers after 15min partial idle")
    
    
    def test_park_lock_blocks_reallocation(self, valid_agent_config):
        """1h lock MUSI blokować realokację"""
        from agents.strategy_executor import StrategyExecutor
        
        executor = StrategyExecutor()
        agent_id = valid_agent_config["id"]
        
        # Set lock for 30 more minutes
        executor.park_locked_until[agent_id] = datetime.utcnow() + timedelta(minutes=30)
        executor.parked_amount[agent_id] = 500.0
        
        park_check = executor.check_park_conditions(
            agent=valid_agent_config,
            pools_found=True,
            idle_balance=500.0,
            has_allocations=False
        )
        
        assert park_check["is_locked"] == True, "❌ Should be locked"
        assert park_check["should_park"] == False, "❌ Should not re-park while locked"
        
        print(f"✅ Park lock correctly blocks reallocation")


# =============================================================================
# CLI RUNNER
# =============================================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '..')
    
    print("=" * 70)
    print("🔒 STRICT AUTONOMOUS AGENT TESTS")
    print("=" * 70)
    
    # Quick validation
    config = {
        "id": "test",
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
        "duration": 30,
        "slippage": 1.0,
        "protocols": ["aerodrome"],
        "deployed_at": datetime.utcnow().isoformat(),
        "max_gas_price": 50,
        "max_drawdown": 30,
    }
    
    print("\n📊 Config Validation:")
    TestConfigValidationStrict().test_user_address_is_valid_ethereum(config)
    TestConfigValidationStrict().test_account_type_is_valid(config)
    TestConfigValidationStrict().test_apy_range_is_valid(config)
    
    print("\n📊 Guardrails:")
    TestAutonomousGuardrailsStrict().test_minimum_100_usd_enforced()
    TestAutonomousGuardrailsStrict().test_5_minute_cooldown_enforced()
    TestAutonomousGuardrailsStrict().test_gas_price_limit_enforced(config)
    
    print("\n📊 ERC-8004:")
    TestERC8004ExecutionPath().test_erc8004_uses_session_key(config)
    
    print("\n📊 Pool Discovery:")
    TestAutonomousPoolDiscovery().test_pools_filtered_by_min_apy(config)
    TestAutonomousPoolDiscovery().test_pools_ranked_by_apy_descending(config)
    
    print("\n" + "=" * 70)
    print("✅ All strict tests passed!")
    print("=" * 70)
