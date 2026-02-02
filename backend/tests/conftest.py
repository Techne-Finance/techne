"""
Pytest Configuration for Techne Backend Tests

Run all tests: python -m pytest tests/ -v
Run unit tests only: python -m pytest tests/ -v -m "not integration"
Run integration tests: python -m pytest tests/ -v -m integration
"""

import pytest
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


# =============================================================================
# FIXTURES - Shared across all test files
# =============================================================================

@pytest.fixture
def test_addresses():
    """Standard test addresses for Base"""
    return {
        "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "WETH": "0x4200000000000000000000000000000000000006",
        "AERO": "0x940181a94A35A4569E4529A3CDfB74e38FD98631",
        "SOL": "0x9B8Df6E244526ab5F6e6400d331DB28C8fdDdb55",
        "cbBTC": "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf",
        "ROUTER": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
        "FACTORY_V4": "0x6f93C211695c2ea7D81c7A9139590835ef7A2364",
        "agent": "0xa30A689ec0F9D717C5bA1098455B031b868B720f",
        "smart_account": "0x5E047DeB5eb22F4E4A7f2207087369468575e3EF",
    }


@pytest.fixture
def mock_agent_config():
    """Standard agent configuration for testing"""
    from datetime import datetime, timedelta
    
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
        "duration": 30,
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
# MARKERS
# =============================================================================

def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (use real APIs)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


# =============================================================================
# ASYNC SUPPORT
# =============================================================================

@pytest.fixture
def event_loop():
    """Create an instance of the event loop for async tests"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
