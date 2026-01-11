"""
Position Tracker - Track user DeFi positions and generate alerts
Monitors APY changes, TVL drops, epoch ends, and risk changes.
"""
import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import aiosqlite

logger = logging.getLogger("PositionTracker")


class AlertType(Enum):
    """Types of position alerts"""
    APY_DROP = "apy_drop"           # APY dropped significantly
    APY_INCREASE = "apy_increase"   # APY increased (good news)
    TVL_EXIT = "tvl_exit"           # Large TVL outflow
    EPOCH_END = "epoch_end"         # Epoch ending soon
    RISK_CHANGE = "risk_change"     # New risk flag detected
    HARVEST_READY = "harvest_ready" # Unclaimed rewards available
    POSITION_AT_RISK = "position_at_risk"  # Combined risk warning


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"       # Good news or FYI
    WARNING = "warning" # Should pay attention
    URGENT = "urgent"   # Action recommended
    CRITICAL = "critical"  # Immediate action needed


@dataclass
class Position:
    """User's DeFi position"""
    id: str
    user_id: str
    pool_address: str
    chain: str
    protocol: str
    symbol: str
    pool_type: str  # lp, vault, lending
    deposit_amount_usd: float
    deposit_timestamp: int
    
    # Snapshot at deposit time
    initial_apy: float
    initial_tvl: float
    
    # Current state (updated periodically)
    current_apy: float = 0.0
    current_tvl: float = 0.0
    unclaimed_rewards_usd: float = 0.0
    last_check_timestamp: int = 0
    
    # Alerts
    alerts_enabled: bool = True
    alert_thresholds: Dict = None
    
    def __post_init__(self):
        if self.alert_thresholds is None:
            self.alert_thresholds = {
                "apy_drop_pct": 20,      # Alert if APY drops >20%
                "tvl_drop_pct": 30,      # Alert if TVL drops >30%
                "epoch_hours": 6,         # Alert 6h before epoch end
                "harvest_usd": 10,        # Alert if rewards > $10
            }


@dataclass
class Alert:
    """Position alert"""
    id: str
    position_id: str
    user_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    data: Dict
    created_at: int
    read: bool = False
    delivered: bool = False
    delivery_channel: str = "in_app"  # in_app, telegram, email


class PositionTracker:
    """
    Track and monitor user DeFi positions.
    Generates alerts based on configurable thresholds.
    """
    
    def __init__(self, db_path: str = "positions.db"):
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None
        self._monitoring = False
        self._check_interval = 300  # 5 minutes
        
    async def initialize(self):
        """Initialize database tables"""
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        
        # Create positions table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                pool_address TEXT NOT NULL,
                chain TEXT NOT NULL,
                protocol TEXT NOT NULL,
                symbol TEXT NOT NULL,
                pool_type TEXT NOT NULL,
                deposit_amount_usd REAL NOT NULL,
                deposit_timestamp INTEGER NOT NULL,
                initial_apy REAL NOT NULL,
                initial_tvl REAL NOT NULL,
                current_apy REAL DEFAULT 0,
                current_tvl REAL DEFAULT 0,
                unclaimed_rewards_usd REAL DEFAULT 0,
                last_check_timestamp INTEGER DEFAULT 0,
                alerts_enabled INTEGER DEFAULT 1,
                alert_thresholds TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                status TEXT DEFAULT 'active'
            )
        """)
        
        # Create alerts table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                position_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                data TEXT,
                created_at INTEGER NOT NULL,
                read INTEGER DEFAULT 0,
                delivered INTEGER DEFAULT 0,
                delivery_channel TEXT DEFAULT 'in_app',
                FOREIGN KEY (position_id) REFERENCES positions(id)
            )
        """)
        
        # Create indexes
        await self._db.execute("CREATE INDEX IF NOT EXISTS idx_positions_user ON positions(user_id)")
        await self._db.execute("CREATE INDEX IF NOT EXISTS idx_alerts_user ON alerts(user_id)")
        await self._db.execute("CREATE INDEX IF NOT EXISTS idx_alerts_unread ON alerts(user_id, read)")
        
        await self._db.commit()
        logger.info("PositionTracker initialized")
    
    async def close(self):
        """Close database connection"""
        if self._db:
            await self._db.close()
    
    # =========================================================================
    # POSITION MANAGEMENT
    # =========================================================================
    
    async def add_position(
        self,
        user_id: str,
        pool_address: str,
        chain: str,
        protocol: str,
        symbol: str,
        pool_type: str,
        deposit_amount_usd: float,
        current_apy: float,
        current_tvl: float,
        alert_thresholds: Dict = None
    ) -> Position:
        """Add a new position to track"""
        import uuid
        
        position = Position(
            id=str(uuid.uuid4()),
            user_id=user_id,
            pool_address=pool_address,
            chain=chain,
            protocol=protocol,
            symbol=symbol,
            pool_type=pool_type,
            deposit_amount_usd=deposit_amount_usd,
            deposit_timestamp=int(time.time()),
            initial_apy=current_apy,
            initial_tvl=current_tvl,
            current_apy=current_apy,
            current_tvl=current_tvl,
            alert_thresholds=alert_thresholds
        )
        
        now = int(time.time())
        await self._db.execute("""
            INSERT INTO positions (
                id, user_id, pool_address, chain, protocol, symbol, pool_type,
                deposit_amount_usd, deposit_timestamp, initial_apy, initial_tvl,
                current_apy, current_tvl, alert_thresholds, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            position.id, position.user_id, position.pool_address, position.chain,
            position.protocol, position.symbol, position.pool_type,
            position.deposit_amount_usd, position.deposit_timestamp,
            position.initial_apy, position.initial_tvl,
            position.current_apy, position.current_tvl,
            json.dumps(position.alert_thresholds),
            now, now
        ))
        await self._db.commit()
        
        logger.info(f"Added position {position.id}: {symbol} on {protocol}")
        return position
    
    async def get_user_positions(self, user_id: str, status: str = "active") -> List[Position]:
        """Get all positions for a user"""
        cursor = await self._db.execute(
            "SELECT * FROM positions WHERE user_id = ? AND status = ?",
            (user_id, status)
        )
        rows = await cursor.fetchall()
        
        positions = []
        for row in rows:
            positions.append(Position(
                id=row["id"],
                user_id=row["user_id"],
                pool_address=row["pool_address"],
                chain=row["chain"],
                protocol=row["protocol"],
                symbol=row["symbol"],
                pool_type=row["pool_type"],
                deposit_amount_usd=row["deposit_amount_usd"],
                deposit_timestamp=row["deposit_timestamp"],
                initial_apy=row["initial_apy"],
                initial_tvl=row["initial_tvl"],
                current_apy=row["current_apy"],
                current_tvl=row["current_tvl"],
                unclaimed_rewards_usd=row["unclaimed_rewards_usd"],
                last_check_timestamp=row["last_check_timestamp"],
                alerts_enabled=bool(row["alerts_enabled"]),
                alert_thresholds=json.loads(row["alert_thresholds"]) if row["alert_thresholds"] else None
            ))
        
        return positions
    
    async def close_position(self, position_id: str):
        """Mark position as closed (withdrawn)"""
        await self._db.execute(
            "UPDATE positions SET status = 'closed', updated_at = ? WHERE id = ?",
            (int(time.time()), position_id)
        )
        await self._db.commit()
    
    # =========================================================================
    # MONITORING & ALERTS
    # =========================================================================
    
    async def check_position(self, position: Position) -> List[Alert]:
        """Check a position and generate alerts if needed"""
        from api.smart_router import smart_router
        
        alerts = []
        
        # Fetch current pool data
        try:
            result = await smart_router.smart_route_pool_check(position.pool_address, position.chain)
            if not result.get("success"):
                return alerts
            
            pool_data = result.get("pool", {})
            new_apy = pool_data.get("apy", 0)
            new_tvl = pool_data.get("tvl", 0) or pool_data.get("tvlUsd", 0)
            
        except Exception as e:
            logger.warning(f"Failed to check position {position.id}: {e}")
            return alerts
        
        thresholds = position.alert_thresholds or {}
        
        # Check APY drop
        if position.current_apy > 0 and new_apy > 0:
            apy_change_pct = ((new_apy - position.current_apy) / position.current_apy) * 100
            threshold = thresholds.get("apy_drop_pct", 20)
            
            if apy_change_pct < -threshold:
                alerts.append(await self._create_alert(
                    position,
                    AlertType.APY_DROP,
                    AlertSeverity.WARNING if apy_change_pct > -50 else AlertSeverity.URGENT,
                    f"📉 APY Dropped {abs(apy_change_pct):.0f}%",
                    f"{position.symbol} APY dropped from {position.current_apy:.1f}% to {new_apy:.1f}%",
                    {"old_apy": position.current_apy, "new_apy": new_apy, "change_pct": apy_change_pct}
                ))
            elif apy_change_pct > threshold:
                alerts.append(await self._create_alert(
                    position,
                    AlertType.APY_INCREASE,
                    AlertSeverity.INFO,
                    f"📈 APY Increased {apy_change_pct:.0f}%",
                    f"{position.symbol} APY increased from {position.current_apy:.1f}% to {new_apy:.1f}%",
                    {"old_apy": position.current_apy, "new_apy": new_apy, "change_pct": apy_change_pct}
                ))
        
        # Check TVL exit
        if position.current_tvl > 0 and new_tvl > 0:
            tvl_change_pct = ((new_tvl - position.current_tvl) / position.current_tvl) * 100
            threshold = thresholds.get("tvl_drop_pct", 30)
            
            if tvl_change_pct < -threshold:
                severity = AlertSeverity.CRITICAL if tvl_change_pct < -50 else AlertSeverity.URGENT
                alerts.append(await self._create_alert(
                    position,
                    AlertType.TVL_EXIT,
                    severity,
                    f"💧 Large TVL Outflow",
                    f"{position.symbol} TVL dropped {abs(tvl_change_pct):.0f}% (${new_tvl:,.0f})",
                    {"old_tvl": position.current_tvl, "new_tvl": new_tvl, "change_pct": tvl_change_pct}
                ))
        
        # Check epoch end (for Aerodrome/Velodrome)
        epoch_end = pool_data.get("epoch_remaining")
        if epoch_end:
            hours_remaining = epoch_end / 3600
            threshold_hours = thresholds.get("epoch_hours", 6)
            
            if hours_remaining < threshold_hours:
                alerts.append(await self._create_alert(
                    position,
                    AlertType.EPOCH_END,
                    AlertSeverity.WARNING,
                    f"⏰ Epoch Ending Soon",
                    f"{position.symbol} epoch ends in {hours_remaining:.1f}h - rewards may change",
                    {"hours_remaining": hours_remaining}
                ))
        
        # Check risk flags
        risk_flags = pool_data.get("risk_flags", [])
        high_risk_flags = [f for f in risk_flags if f.get("severity") == "high"]
        if high_risk_flags:
            alerts.append(await self._create_alert(
                position,
                AlertType.RISK_CHANGE,
                AlertSeverity.URGENT,
                f"🚨 Risk Alert",
                f"{position.symbol} has {len(high_risk_flags)} high-risk flags: {', '.join(f.get('label', '') for f in high_risk_flags)}",
                {"risk_flags": high_risk_flags}
            ))
        
        # Update position with current data
        await self._db.execute("""
            UPDATE positions SET 
                current_apy = ?, current_tvl = ?, 
                last_check_timestamp = ?, updated_at = ?
            WHERE id = ?
        """, (new_apy, new_tvl, int(time.time()), int(time.time()), position.id))
        await self._db.commit()
        
        return alerts
    
    async def _create_alert(
        self,
        position: Position,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        data: Dict
    ) -> Alert:
        """Create and store an alert"""
        import uuid
        
        alert = Alert(
            id=str(uuid.uuid4()),
            position_id=position.id,
            user_id=position.user_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            data=data,
            created_at=int(time.time())
        )
        
        await self._db.execute("""
            INSERT INTO alerts (
                id, position_id, user_id, alert_type, severity,
                title, message, data, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert.id, alert.position_id, alert.user_id,
            alert.alert_type.value, alert.severity.value,
            alert.title, alert.message, json.dumps(data), alert.created_at
        ))
        await self._db.commit()
        
        logger.info(f"Created alert: {title} for position {position.id}")
        return alert
    
    async def get_user_alerts(
        self, 
        user_id: str, 
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Alert]:
        """Get alerts for a user"""
        query = "SELECT * FROM alerts WHERE user_id = ?"
        params = [user_id]
        
        if unread_only:
            query += " AND read = 0"
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = await self._db.execute(query, params)
        rows = await cursor.fetchall()
        
        alerts = []
        for row in rows:
            alerts.append(Alert(
                id=row["id"],
                position_id=row["position_id"],
                user_id=row["user_id"],
                alert_type=AlertType(row["alert_type"]),
                severity=AlertSeverity(row["severity"]),
                title=row["title"],
                message=row["message"],
                data=json.loads(row["data"]) if row["data"] else {},
                created_at=row["created_at"],
                read=bool(row["read"]),
                delivered=bool(row["delivered"]),
                delivery_channel=row["delivery_channel"]
            ))
        
        return alerts
    
    async def mark_alert_read(self, alert_id: str):
        """Mark an alert as read"""
        await self._db.execute(
            "UPDATE alerts SET read = 1 WHERE id = ?",
            (alert_id,)
        )
        await self._db.commit()
    
    # =========================================================================
    # BACKGROUND MONITORING
    # =========================================================================
    
    async def start_monitoring(self):
        """Start background monitoring loop"""
        self._monitoring = True
        logger.info("Position monitoring started")
        
        while self._monitoring:
            try:
                await self._monitoring_cycle()
            except Exception as e:
                logger.error(f"Monitoring cycle error: {e}")
            
            await asyncio.sleep(self._check_interval)
    
    async def stop_monitoring(self):
        """Stop background monitoring"""
        self._monitoring = False
        logger.info("Position monitoring stopped")
    
    async def _monitoring_cycle(self):
        """One cycle of position monitoring"""
        # Get all active positions that need checking
        cursor = await self._db.execute("""
            SELECT * FROM positions 
            WHERE status = 'active' 
            AND alerts_enabled = 1
            AND last_check_timestamp < ?
        """, (int(time.time()) - self._check_interval,))
        
        rows = await cursor.fetchall()
        logger.info(f"Checking {len(rows)} positions...")
        
        all_alerts = []
        for row in rows:
            position = Position(
                id=row["id"],
                user_id=row["user_id"],
                pool_address=row["pool_address"],
                chain=row["chain"],
                protocol=row["protocol"],
                symbol=row["symbol"],
                pool_type=row["pool_type"],
                deposit_amount_usd=row["deposit_amount_usd"],
                deposit_timestamp=row["deposit_timestamp"],
                initial_apy=row["initial_apy"],
                initial_tvl=row["initial_tvl"],
                current_apy=row["current_apy"],
                current_tvl=row["current_tvl"],
                alerts_enabled=bool(row["alerts_enabled"]),
                alert_thresholds=json.loads(row["alert_thresholds"]) if row["alert_thresholds"] else None
            )
            
            alerts = await self.check_position(position)
            all_alerts.extend(alerts)
        
        # Deliver alerts
        for alert in all_alerts:
            await self._deliver_alert(alert)
    
    async def _deliver_alert(self, alert: Alert):
        """Deliver alert to user via configured channel"""
        if alert.delivery_channel == "telegram":
            await self._send_telegram_alert(alert)
        elif alert.delivery_channel == "email":
            await self._send_email_alert(alert)
        
        # Mark as delivered
        await self._db.execute(
            "UPDATE alerts SET delivered = 1 WHERE id = ?",
            (alert.id,)
        )
        await self._db.commit()
    
    async def _send_telegram_alert(self, alert: Alert):
        """Send alert via Telegram"""
        # TODO: Integrate with Telegram bot
        # from telegram_alerts import send_alert
        severity_emoji = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.URGENT: "🚨",
            AlertSeverity.CRITICAL: "🔴"
        }
        emoji = severity_emoji.get(alert.severity, "📢")
        
        message = f"{emoji} {alert.title}\n\n{alert.message}"
        logger.info(f"Would send Telegram: {message}")
        # await send_alert(alert.user_id, message)
    
    async def _send_email_alert(self, alert: Alert):
        """Send alert via Email"""
        # TODO: Implement email delivery
        logger.info(f"Would send email: {alert.title}")


# Singleton instance
position_tracker = PositionTracker()
