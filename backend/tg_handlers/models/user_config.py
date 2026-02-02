"""
Techne Telegram Bot - User Configuration Model
Stores user preferences for alerts and filters
"""

import json
import os
import aiosqlite
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime


@dataclass
class UserConfig:
    """User configuration for Techne Bot"""
    telegram_id: int
    
    # Chain filter
    chain: str = "all"  # "base", "ethereum", "solana", "arbitrum", "all"
    
    # TVL filters
    min_tvl: float = 100000  # $100K default
    max_tvl: Optional[float] = None
    
    # APY filters
    min_apy: float = 3.0
    max_apy: float = 500.0
    
    # Risk filter
    risk_level: str = "all"  # "low", "medium", "high", "all"
    
    # Protocol whitelist (empty = all)
    protocols: List[str] = field(default_factory=list)
    
    # Asset type
    stablecoin_only: bool = False
    asset_type: str = "all"  # "stablecoin", "eth", "sol", "all"
    
    # Pool type
    pool_type: str = "all"  # "single", "dual", "all"
    
    # Alert preferences
    alerts_enabled: bool = True
    apy_spike_threshold: float = 20.0  # Alert if APY jumps 20%+
    tvl_change_threshold: float = 10.0  # Alert if TVL changes 10%+
    alert_interval_minutes: int = 60  # Min interval between alerts
    
    # Premium status
    is_premium: bool = False
    wallet_address: Optional[str] = None
    premium_expires: Optional[str] = None
    
    # Agent tracking
    agent_address: Optional[str] = None
    agent_notifications: bool = True
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class UserConfigStore:
    """SQLite-based storage for user configurations"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "telegram_users.db")
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    async def init_db(self):
        """Initialize database schema"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_configs (
                    telegram_id INTEGER PRIMARY KEY,
                    config_json TEXT NOT NULL,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER,
                    alert_type TEXT,
                    pool_id TEXT,
                    message TEXT,
                    sent_at TEXT,
                    FOREIGN KEY (telegram_id) REFERENCES user_configs(telegram_id)
                )
            """)
            await db.commit()
    
    async def get_config(self, telegram_id: int) -> Optional[UserConfig]:
        """Get user config by Telegram ID"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT config_json FROM user_configs WHERE telegram_id = ?",
                (telegram_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    data = json.loads(row[0])
                    return UserConfig.from_dict(data)
        return None
    
    async def save_config(self, config: UserConfig):
        """Save or update user config"""
        config.updated_at = datetime.utcnow().isoformat()
        config_json = json.dumps(config.to_dict())
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_configs (telegram_id, config_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    config_json = excluded.config_json,
                    updated_at = excluded.updated_at
            """, (config.telegram_id, config_json, config.created_at, config.updated_at))
            await db.commit()
    
    async def get_or_create_config(self, telegram_id: int) -> UserConfig:
        """Get existing config or create default"""
        config = await self.get_config(telegram_id)
        if not config:
            config = UserConfig(telegram_id=telegram_id)
            await self.save_config(config)
        return config
    
    async def get_all_with_alerts(self) -> List[UserConfig]:
        """Get all users with alerts enabled"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT config_json FROM user_configs") as cursor:
                configs = []
                async for row in cursor:
                    config = UserConfig.from_dict(json.loads(row[0]))
                    if config.alerts_enabled:
                        configs.append(config)
                return configs
    
    async def get_premium_users(self) -> List[UserConfig]:
        """Get all premium users"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT config_json FROM user_configs") as cursor:
                configs = []
                async for row in cursor:
                    config = UserConfig.from_dict(json.loads(row[0]))
                    if config.is_premium:
                        configs.append(config)
                return configs
    
    async def log_alert(self, telegram_id: int, alert_type: str, pool_id: str, message: str):
        """Log sent alert for rate limiting"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO alert_history (telegram_id, alert_type, pool_id, message, sent_at)
                VALUES (?, ?, ?, ?, ?)
            """, (telegram_id, alert_type, pool_id, message, datetime.utcnow().isoformat()))
            await db.commit()
    
    async def get_recent_alerts(self, telegram_id: int, minutes: int = 60) -> List[dict]:
        """Get recent alerts to prevent spam"""
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT alert_type, pool_id, sent_at FROM alert_history
                WHERE telegram_id = ? AND sent_at > ?
            """, (telegram_id, cutoff)) as cursor:
                return [{"type": r[0], "pool_id": r[1], "sent_at": r[2]} async for r in cursor]


# Global store instance
user_store = UserConfigStore()
