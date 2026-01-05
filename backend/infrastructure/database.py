"""
Database Layer for Techne Finance
Production-grade database abstraction supporting SQLite (dev) and PostgreSQL (prod)

Features:
- Async operations
- Connection pooling
- Automatic failover
- Query logging
- Migration support
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from contextlib import asynccontextmanager
from enum import Enum
import json

# Try to import async database libraries
try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

try:
    import aioredis
    AIOREDIS_AVAILABLE = True
except ImportError:
    AIOREDIS_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DatabaseLayer")


class DatabaseType(Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


@dataclass
class DatabaseConfig:
    """Database configuration"""
    db_type: DatabaseType = DatabaseType.SQLITE
    
    # SQLite settings
    sqlite_path: str = "techne.db"
    
    # PostgreSQL settings
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str = "techne"
    pg_user: str = "techne"
    pg_password: str = ""
    pg_pool_min: int = 5
    pg_pool_max: int = 20
    
    # General settings
    query_timeout: int = 30
    log_queries: bool = False
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create config from environment variables"""
        db_type = os.environ.get("DB_TYPE", "sqlite")
        
        return cls(
            db_type=DatabaseType.POSTGRESQL if db_type == "postgresql" else DatabaseType.SQLITE,
            sqlite_path=os.environ.get("SQLITE_PATH", "techne.db"),
            pg_host=os.environ.get("PG_HOST", "localhost"),
            pg_port=int(os.environ.get("PG_PORT", "5432")),
            pg_database=os.environ.get("PG_DATABASE", "techne"),
            pg_user=os.environ.get("PG_USER", "techne"),
            pg_password=os.environ.get("PG_PASSWORD", ""),
            pg_pool_min=int(os.environ.get("PG_POOL_MIN", "5")),
            pg_pool_max=int(os.environ.get("PG_POOL_MAX", "20")),
            query_timeout=int(os.environ.get("DB_QUERY_TIMEOUT", "30")),
            log_queries=os.environ.get("LOG_QUERIES", "false").lower() == "true",
        )


class QueryResult:
    """Wrapper for query results"""
    
    def __init__(self, rows: List[Dict], rowcount: int = 0):
        self.rows = rows
        self.rowcount = rowcount
    
    def __iter__(self):
        return iter(self.rows)
    
    def __len__(self):
        return len(self.rows)
    
    def first(self) -> Optional[Dict]:
        return self.rows[0] if self.rows else None
    
    def all(self) -> List[Dict]:
        return self.rows


class DatabasePool:
    """
    Async database connection pool.
    Supports both SQLite (dev) and PostgreSQL (prod).
    """
    
    def __init__(self, config: DatabaseConfig = None):
        self.config = config or DatabaseConfig.from_env()
        self._pool = None
        self._sqlite_conn = None
        self._is_initialized = False
        
    async def initialize(self):
        """Initialize the database pool"""
        if self._is_initialized:
            return
        
        if self.config.db_type == DatabaseType.POSTGRESQL:
            if not ASYNCPG_AVAILABLE:
                raise RuntimeError("asyncpg is required for PostgreSQL. Install with: pip install asyncpg")
            
            self._pool = await asyncpg.create_pool(
                host=self.config.pg_host,
                port=self.config.pg_port,
                database=self.config.pg_database,
                user=self.config.pg_user,
                password=self.config.pg_password,
                min_size=self.config.pg_pool_min,
                max_size=self.config.pg_pool_max,
                command_timeout=self.config.query_timeout,
            )
            logger.info(f"PostgreSQL pool initialized: {self.config.pg_host}:{self.config.pg_port}/{self.config.pg_database}")
            
        else:
            if not AIOSQLITE_AVAILABLE:
                raise RuntimeError("aiosqlite is required for SQLite. Install with: pip install aiosqlite")
            
            self._sqlite_conn = await aiosqlite.connect(self.config.sqlite_path)
            self._sqlite_conn.row_factory = aiosqlite.Row
            logger.info(f"SQLite initialized: {self.config.sqlite_path}")
        
        self._is_initialized = True
    
    async def close(self):
        """Close the database pool"""
        if self.config.db_type == DatabaseType.POSTGRESQL and self._pool:
            await self._pool.close()
        elif self._sqlite_conn:
            await self._sqlite_conn.close()
        
        self._is_initialized = False
        logger.info("Database pool closed")
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire a database connection from the pool"""
        if not self._is_initialized:
            await self.initialize()
        
        if self.config.db_type == DatabaseType.POSTGRESQL:
            async with self._pool.acquire() as conn:
                yield conn
        else:
            yield self._sqlite_conn
    
    async def execute(self, query: str, params: tuple = None) -> QueryResult:
        """Execute a query and return results"""
        start_time = datetime.now()
        
        if self.config.log_queries:
            logger.debug(f"Query: {query[:100]}... Params: {params}")
        
        try:
            async with self.acquire() as conn:
                if self.config.db_type == DatabaseType.POSTGRESQL:
                    # PostgreSQL uses $1, $2, etc. for params
                    if params:
                        rows = await conn.fetch(query, *params)
                    else:
                        rows = await conn.fetch(query)
                    result = QueryResult([dict(row) for row in rows], len(rows))
                else:
                    # SQLite uses ? for params
                    cursor = await conn.execute(query, params or ())
                    rows = await cursor.fetchall()
                    result = QueryResult(
                        [dict(row) for row in rows],
                        cursor.rowcount
                    )
                    await conn.commit()
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            if self.config.log_queries:
                logger.debug(f"Query completed in {duration:.2f}ms, {len(result)} rows")
            
            return result
            
        except Exception as e:
            logger.error(f"Query failed: {query[:100]}... Error: {e}")
            raise
    
    async def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute a query multiple times with different params"""
        async with self.acquire() as conn:
            if self.config.db_type == DatabaseType.POSTGRESQL:
                await conn.executemany(query, params_list)
                return len(params_list)
            else:
                await conn.executemany(query, params_list)
                await conn.commit()
                return len(params_list)
    
    async def execute_script(self, script: str):
        """Execute a SQL script (for migrations)"""
        async with self.acquire() as conn:
            if self.config.db_type == DatabaseType.POSTGRESQL:
                await conn.execute(script)
            else:
                await conn.executescript(script)
                await conn.commit()


# ============================================
# CACHE LAYER (Redis)
# ============================================

@dataclass
class CacheConfig:
    """Cache configuration"""
    enabled: bool = True
    redis_url: str = "redis://localhost:6379"
    default_ttl: int = 300  # 5 minutes
    pool_data_ttl: int = 60  # 1 minute for pool data
    session_ttl: int = 3600  # 1 hour for sessions
    
    @classmethod
    def from_env(cls) -> "CacheConfig":
        return cls(
            enabled=os.environ.get("CACHE_ENABLED", "true").lower() == "true",
            redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379"),
            default_ttl=int(os.environ.get("CACHE_DEFAULT_TTL", "300")),
            pool_data_ttl=int(os.environ.get("CACHE_POOL_TTL", "60")),
            session_ttl=int(os.environ.get("CACHE_SESSION_TTL", "3600")),
        )


class CacheLayer:
    """
    Redis-based caching layer.
    Falls back to in-memory cache if Redis unavailable.
    """
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig.from_env()
        self._redis = None
        self._memory_cache: Dict[str, tuple] = {}  # key -> (value, expiry)
        self._is_redis_available = False
    
    async def initialize(self):
        """Initialize Redis connection"""
        if not self.config.enabled:
            logger.info("Cache disabled")
            return
        
        if AIOREDIS_AVAILABLE:
            try:
                self._redis = await aioredis.from_url(
                    self.config.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self._redis.ping()
                self._is_redis_available = True
                logger.info(f"Redis connected: {self.config.redis_url}")
            except Exception as e:
                logger.warning(f"Redis unavailable, using memory cache: {e}")
                self._is_redis_available = False
        else:
            logger.info("aioredis not installed, using memory cache")
    
    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.config.enabled:
            return None
        
        if self._is_redis_available:
            value = await self._redis.get(key)
            if value:
                return json.loads(value)
        else:
            if key in self._memory_cache:
                value, expiry = self._memory_cache[key]
                if datetime.now().timestamp() < expiry:
                    return value
                else:
                    del self._memory_cache[key]
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None):
        """Set value in cache"""
        if not self.config.enabled:
            return
        
        ttl = ttl or self.config.default_ttl
        
        if self._is_redis_available:
            await self._redis.setex(key, ttl, json.dumps(value))
        else:
            expiry = datetime.now().timestamp() + ttl
            self._memory_cache[key] = (value, expiry)
    
    async def delete(self, key: str):
        """Delete value from cache"""
        if self._is_redis_available:
            await self._redis.delete(key)
        elif key in self._memory_cache:
            del self._memory_cache[key]
    
    async def delete_pattern(self, pattern: str):
        """Delete all keys matching pattern"""
        if self._is_redis_available:
            keys = await self._redis.keys(pattern)
            if keys:
                await self._redis.delete(*keys)
        else:
            # Simple pattern matching for memory cache
            to_delete = [k for k in self._memory_cache.keys() if pattern.replace("*", "") in k]
            for k in to_delete:
                del self._memory_cache[k]
    
    async def invalidate_pools(self):
        """Invalidate all pool cache"""
        await self.delete_pattern("pools:*")
    
    async def get_or_set(self, key: str, factory, ttl: int = None) -> Any:
        """Get from cache or compute and cache"""
        value = await self.get(key)
        if value is None:
            value = await factory() if asyncio.iscoroutinefunction(factory) else factory()
            await self.set(key, value, ttl)
        return value


# ============================================
# HEALTH CHECKS
# ============================================

class HealthChecker:
    """Health check system for all infrastructure components"""
    
    def __init__(self, db: DatabasePool, cache: CacheLayer):
        self.db = db
        self.cache = cache
    
    async def check_database(self) -> Dict:
        """Check database health"""
        try:
            start = datetime.now()
            await self.db.execute("SELECT 1")
            latency = (datetime.now() - start).total_seconds() * 1000
            
            return {
                "status": "healthy",
                "type": self.db.config.db_type.value,
                "latency_ms": round(latency, 2)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_cache(self) -> Dict:
        """Check cache health"""
        if not self.cache.config.enabled:
            return {"status": "disabled"}
        
        try:
            start = datetime.now()
            test_key = "_health_check_"
            await self.cache.set(test_key, "ok", ttl=10)
            value = await self.cache.get(test_key)
            await self.cache.delete(test_key)
            latency = (datetime.now() - start).total_seconds() * 1000
            
            return {
                "status": "healthy" if value == "ok" else "degraded",
                "type": "redis" if self.cache._is_redis_available else "memory",
                "latency_ms": round(latency, 2)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_all(self) -> Dict:
        """Check all components"""
        return {
            "database": await self.check_database(),
            "cache": await self.check_cache(),
            "timestamp": datetime.now().isoformat()
        }


# ============================================
# GLOBAL INSTANCES
# ============================================

# Create global instances (initialized on startup)
db_config = DatabaseConfig.from_env()
cache_config = CacheConfig.from_env()

database = DatabasePool(db_config)
cache = CacheLayer(cache_config)
health_checker = HealthChecker(database, cache)


async def init_infrastructure():
    """Initialize all infrastructure components"""
    await database.initialize()
    await cache.initialize()
    logger.info("Infrastructure initialized")


async def close_infrastructure():
    """Close all infrastructure components"""
    await database.close()
    await cache.close()
    logger.info("Infrastructure closed")
