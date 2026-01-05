"""
Configuration Management for Techne Finance
Environment-based configuration with secrets handling and feature flags

Features:
- Environment-based config (dev/staging/prod)
- Secrets management
- Feature flags
- Dynamic reload
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from enum import Enum
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Config")


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DatabaseConfig:
    """Database configuration"""
    type: str = "sqlite"  # sqlite or postgresql
    
    # SQLite
    sqlite_path: str = "techne.db"
    
    # PostgreSQL
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str = "techne"
    pg_user: str = "techne"
    pg_password: str = ""
    pg_pool_min: int = 5
    pg_pool_max: int = 20


@dataclass
class CacheConfig:
    """Cache configuration"""
    enabled: bool = True
    redis_url: str = "redis://localhost:6379"
    default_ttl: int = 300
    pool_ttl: int = 60


@dataclass
class SecurityConfig:
    """Security configuration"""
    rate_limit_per_minute: int = 100
    rate_limit_per_hour: int = 2000
    rate_limit_per_day: int = 20000
    max_request_size_mb: int = 10
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    api_key_expiry_days: int = 365
    
    # Transaction limits
    max_tx_usd: float = 10000
    max_daily_usd: float = 50000


@dataclass
class BlockchainConfig:
    """Blockchain configuration"""
    default_chain: str = "base"
    
    # RPC endpoints
    rpc_urls: Dict[str, str] = field(default_factory=lambda: {
        "ethereum": "https://eth.llamarpc.com",
        "base": "https://mainnet.base.org",
        "arbitrum": "https://arb1.arbitrum.io/rpc",
        "optimism": "https://mainnet.optimism.io",
        "polygon": "https://polygon-rpc.com",
    })
    
    # Gas settings
    max_gas_gwei: int = 100
    gas_buffer_percent: int = 20


@dataclass
class APIConfig:
    """External API configuration"""
    defillama_url: str = "https://yields.llama.fi/pools"
    beefy_url: str = "https://api.beefy.finance"
    coingecko_url: str = "https://api.coingecko.com/api/v3"
    
    # Timeouts
    request_timeout: int = 30
    
    # Rate limits for external APIs
    defillama_requests_per_minute: int = 30
    coingecko_requests_per_minute: int = 10


@dataclass
class MonitoringConfig:
    """Monitoring configuration"""
    log_level: str = "INFO"
    log_queries: bool = False
    log_requests: bool = True
    metrics_enabled: bool = True
    
    # Alerting
    alert_webhook_url: Optional[str] = None
    alert_email: Optional[str] = None


@dataclass
class FeatureFlags:
    """Feature flags for gradual rollout"""
    enable_cross_chain: bool = False
    enable_auto_compound: bool = False
    enable_ai_predictions: bool = True
    enable_memory_engine: bool = True
    enable_observability: bool = True
    enable_x402_payments: bool = True
    
    # Experimental features
    enable_solana: bool = False
    enable_zap_deposits: bool = False
    
    def is_enabled(self, feature: str) -> bool:
        return getattr(self, f"enable_{feature}", False)


@dataclass
class TechneConfig:
    """Main application configuration"""
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True
    
    # Component configs
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    blockchain: BlockchainConfig = field(default_factory=BlockchainConfig)
    api: APIConfig = field(default_factory=APIConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    features: FeatureFlags = field(default_factory=FeatureFlags)
    
    @classmethod
    def from_env(cls) -> "TechneConfig":
        """Create configuration from environment variables"""
        env = os.environ.get("TECHNE_ENV", "development").lower()
        
        config = cls(
            environment=Environment(env) if env in [e.value for e in Environment] else Environment.DEVELOPMENT,
            debug=os.environ.get("DEBUG", "true").lower() == "true",
        )
        
        # Database config
        config.database = DatabaseConfig(
            type=os.environ.get("DB_TYPE", "sqlite"),
            sqlite_path=os.environ.get("SQLITE_PATH", "techne.db"),
            pg_host=os.environ.get("PG_HOST", "localhost"),
            pg_port=int(os.environ.get("PG_PORT", "5432")),
            pg_database=os.environ.get("PG_DATABASE", "techne"),
            pg_user=os.environ.get("PG_USER", "techne"),
            pg_password=os.environ.get("PG_PASSWORD", ""),
        )
        
        # Cache config
        config.cache = CacheConfig(
            enabled=os.environ.get("CACHE_ENABLED", "true").lower() == "true",
            redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379"),
        )
        
        # Security config - Production hardening
        if config.environment == Environment.PRODUCTION:
            config.debug = False
            config.security.cors_origins = [
                "https://techne.finance",
                "https://app.techne.finance",
            ]
            config.monitoring.log_level = "WARNING"
        
        return config
    
    def to_dict(self) -> Dict:
        """Convert to dictionary (hiding secrets)"""
        def sanitize(obj):
            if isinstance(obj, dict):
                return {k: sanitize(v) for k, v in obj.items() if "password" not in k.lower() and "secret" not in k.lower()}
            elif hasattr(obj, '__dataclass_fields__'):
                return sanitize({k: getattr(obj, k) for k in obj.__dataclass_fields__})
            elif isinstance(obj, Enum):
                return obj.value
            else:
                return obj
        
        return sanitize(self)


# ============================================
# SECRETS MANAGEMENT
# ============================================

class SecretsManager:
    """
    Manages secrets securely.
    In production, this would integrate with AWS Secrets Manager, HashiCorp Vault, etc.
    """
    
    def __init__(self):
        self._secrets: Dict[str, str] = {}
        self._load_from_env()
    
    def _load_from_env(self):
        """Load secrets from environment variables"""
        secret_keys = [
            "PG_PASSWORD",
            "REDIS_PASSWORD",
            "API_SECRET_KEY",
            "JWT_SECRET",
            "ENCRYPTION_KEY",
            "WALLET_PRIVATE_KEY",  # NEVER log this!
        ]
        
        for key in secret_keys:
            value = os.environ.get(key)
            if value:
                self._secrets[key] = value
    
    def get(self, key: str, default: str = None) -> Optional[str]:
        """Get a secret value"""
        return self._secrets.get(key, default)
    
    def set(self, key: str, value: str):
        """Set a secret value (runtime only)"""
        self._secrets[key] = value
    
    def has(self, key: str) -> bool:
        """Check if secret exists"""
        return key in self._secrets


# ============================================
# GLOBAL INSTANCES
# ============================================

# Load configuration on module import
config = TechneConfig.from_env()
secrets = SecretsManager()

logger.info(f"Configuration loaded for environment: {config.environment.value}")


def get_config() -> TechneConfig:
    """Get the global configuration"""
    return config


def get_secrets() -> SecretsManager:
    """Get the secrets manager"""
    return secrets


def reload_config():
    """Reload configuration from environment"""
    global config
    config = TechneConfig.from_env()
    logger.info("Configuration reloaded")
