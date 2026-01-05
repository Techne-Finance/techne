"""
Guardian Agent - "The Protector" of Artisan System
User position monitoring, alerts, emergency exit management

Responsibilities:
- Monitor user positions for risks
- Trigger alerts on significant changes
- Execute emergency exits when configured
- Track position P&L
- Manage stop-loss and take-profit rules
- Record alerts in Memory Engine
- Trace operations via Observability
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

# Observability integration
try:
    from agents.observability_engine import observability, traced, SpanStatus
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False
    def traced(agent, op):
        def decorator(func): return func
        return decorator

# Memory integration
try:
    from agents.memory_engine import memory_engine, MemoryType
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GuardianAgent")


class AlertType(Enum):
    APY_DROP = "apy_drop"
    TVL_DROP = "tvl_drop"
    POSITION_LOSS = "position_loss"
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    SECURITY_WARNING = "security_warning"
    REBALANCE_NEEDED = "rebalance_needed"


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class UserPosition:
    user_id: str
    pool_id: str
    symbol: str
    deposited_amount: float
    deposited_at: datetime
    current_value: float = 0
    current_apy: float = 0
    pnl: float = 0
    pnl_percent: float = 0
    
    # Rules
    stop_loss_percent: Optional[float] = None  # e.g., -10 = exit if -10%
    take_profit_percent: Optional[float] = None
    apy_floor: Optional[float] = None  # Exit if APY drops below this


@dataclass
class Alert:
    id: str
    user_id: str
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    pool_id: Optional[str] = None
    data: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False


class GuardianAgent:
    """
    The Guardian - User Position Protection Agent
    Always watching, always protecting
    """
    
    def __init__(self):
        # User positions
        self.positions: Dict[str, List[UserPosition]] = {}  # user_id -> positions
        
        # Active alerts
        self.alerts: List[Alert] = []
        
        # Alert thresholds (defaults)
        self.default_rules = {
            "apy_drop_threshold": 30,       # Alert if APY drops 30%
            "tvl_drop_threshold": 25,       # Alert if TVL drops 25%
            "default_stop_loss": -15,       # Default stop loss -15%
            "check_interval_minutes": 15,
        }
        
        # Subscribers for alerts
        self.alert_subscribers: List[Callable] = []
        
        # Emergency exit queue
        self.emergency_queue: List[Dict] = []
        
        self._alert_counter = 0
        
    def subscribe_alerts(self, callback: Callable):
        """Subscribe to receive alerts"""
        self.alert_subscribers.append(callback)
    
    # ===========================================
    # POSITION MANAGEMENT
    # ===========================================
    
    def register_position(
        self,
        user_id: str,
        pool_id: str,
        symbol: str,
        amount: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        apy_floor: Optional[float] = None
    ) -> UserPosition:
        """Register a new user position to monitor"""
        
        position = UserPosition(
            user_id=user_id,
            pool_id=pool_id,
            symbol=symbol,
            deposited_amount=amount,
            deposited_at=datetime.now(),
            current_value=amount,
            stop_loss_percent=stop_loss or self.default_rules["default_stop_loss"],
            take_profit_percent=take_profit,
            apy_floor=apy_floor
        )
        
        if user_id not in self.positions:
            self.positions[user_id] = []
        
        self.positions[user_id].append(position)
        
        logger.info(f"🛡️ Guardian watching position: {user_id} in {symbol}")
        
        return position
    
    def update_position(
        self,
        user_id: str,
        pool_id: str,
        current_value: float,
        current_apy: float
    ) -> Optional[UserPosition]:
        """Update position with current values"""
        
        positions = self.positions.get(user_id, [])
        position = next((p for p in positions if p.pool_id == pool_id), None)
        
        if not position:
            return None
        
        # Update values
        position.current_value = current_value
        position.current_apy = current_apy
        position.pnl = current_value - position.deposited_amount
        position.pnl_percent = (position.pnl / position.deposited_amount * 100) if position.deposited_amount > 0 else 0
        
        return position
    
    def get_user_positions(self, user_id: str) -> List[UserPosition]:
        """Get all positions for a user"""
        return self.positions.get(user_id, [])
    
    def get_user_portfolio(self, user_id: str) -> Dict:
        """Get user's complete portfolio summary"""
        positions = self.get_user_positions(user_id)
        
        if not positions:
            return {"total_value": 0, "total_pnl": 0, "positions": []}
        
        total_value = sum(p.current_value for p in positions)
        total_deposited = sum(p.deposited_amount for p in positions)
        total_pnl = total_value - total_deposited
        
        return {
            "total_value": total_value,
            "total_deposited": total_deposited,
            "total_pnl": total_pnl,
            "total_pnl_percent": (total_pnl / total_deposited * 100) if total_deposited > 0 else 0,
            "position_count": len(positions),
            "avg_apy": sum(p.current_apy for p in positions) / len(positions) if positions else 0,
            "positions": [self._position_to_dict(p) for p in positions]
        }
    
    def _position_to_dict(self, position: UserPosition) -> Dict:
        return {
            "pool_id": position.pool_id,
            "symbol": position.symbol,
            "deposited": position.deposited_amount,
            "current_value": position.current_value,
            "pnl": position.pnl,
            "pnl_percent": position.pnl_percent,
            "current_apy": position.current_apy,
            "deposited_at": position.deposited_at.isoformat(),
            "stop_loss": position.stop_loss_percent,
            "take_profit": position.take_profit_percent,
        }
    
    # ===========================================
    # MONITORING & ALERTS
    # ===========================================
    
    def check_all_positions(self, pools: List[Dict]) -> List[Alert]:
        """Check all positions against current pool data"""
        new_alerts = []
        pool_map = {p.get("pool"): p for p in pools}
        
        for user_id, positions in self.positions.items():
            for position in positions:
                pool_data = pool_map.get(position.pool_id)
                
                if not pool_data:
                    continue
                
                # Update position with current data
                self.update_position(
                    user_id=user_id,
                    pool_id=position.pool_id,
                    current_value=position.current_value,  # Would calculate from blockchain
                    current_apy=pool_data.get("apy", 0)
                )
                
                # Check conditions
                alerts = self._check_position_rules(position, pool_data)
                new_alerts.extend(alerts)
        
        # Send alerts
        for alert in new_alerts:
            self._send_alert(alert)
        
        return new_alerts
    
    def _check_position_rules(self, position: UserPosition, pool_data: Dict) -> List[Alert]:
        """Check all rules for a position"""
        alerts = []
        
        # Check stop loss
        if position.stop_loss_percent and position.pnl_percent <= position.stop_loss_percent:
            alerts.append(self._create_alert(
                user_id=position.user_id,
                alert_type=AlertType.STOP_LOSS,
                severity=AlertSeverity.EMERGENCY,
                message=f"🚨 STOP LOSS triggered for {position.symbol}! Position down {position.pnl_percent:.1f}%",
                pool_id=position.pool_id,
                data={"pnl_percent": position.pnl_percent, "threshold": position.stop_loss_percent}
            ))
            
            # Add to emergency queue
            self.emergency_queue.append({
                "action": "exit",
                "user_id": position.user_id,
                "position": position,
                "reason": "stop_loss"
            })
        
        # Check take profit
        if position.take_profit_percent and position.pnl_percent >= position.take_profit_percent:
            alerts.append(self._create_alert(
                user_id=position.user_id,
                alert_type=AlertType.TAKE_PROFIT,
                severity=AlertSeverity.INFO,
                message=f"🎯 Take profit target reached for {position.symbol}! Position up {position.pnl_percent:.1f}%",
                pool_id=position.pool_id,
                data={"pnl_percent": position.pnl_percent, "threshold": position.take_profit_percent}
            ))
        
        # Check APY floor
        if position.apy_floor and position.current_apy < position.apy_floor:
            alerts.append(self._create_alert(
                user_id=position.user_id,
                alert_type=AlertType.APY_DROP,
                severity=AlertSeverity.WARNING,
                message=f"📉 APY dropped below floor for {position.symbol}. Current: {position.current_apy:.1f}%, Floor: {position.apy_floor}%",
                pool_id=position.pool_id,
                data={"current_apy": position.current_apy, "floor": position.apy_floor}
            ))
        
        return alerts
    
    def _create_alert(
        self,
        user_id: str,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        pool_id: Optional[str] = None,
        data: Optional[Dict] = None
    ) -> Alert:
        """Create a new alert"""
        self._alert_counter += 1
        
        alert = Alert(
            id=f"alert_{self._alert_counter}",
            user_id=user_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            pool_id=pool_id,
            data=data or {}
        )
        
        self.alerts.append(alert)
        
        return alert
    
    def _send_alert(self, alert: Alert):
        """Send alert to subscribers"""
        logger.info(f"🚨 Alert [{alert.severity.value}]: {alert.message}")
        
        for callback in self.alert_subscribers:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")
    
    # ===========================================
    # USER ALERT MANAGEMENT
    # ===========================================
    
    def get_user_alerts(self, user_id: str, unread_only: bool = False) -> List[Dict]:
        """Get alerts for a user"""
        user_alerts = [a for a in self.alerts if a.user_id == user_id]
        
        if unread_only:
            user_alerts = [a for a in user_alerts if not a.acknowledged]
        
        return [
            {
                "id": a.id,
                "type": a.alert_type.value,
                "severity": a.severity.value,
                "message": a.message,
                "pool_id": a.pool_id,
                "created_at": a.created_at.isoformat(),
                "acknowledged": a.acknowledged
            }
            for a in user_alerts
        ]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark alert as acknowledged"""
        alert = next((a for a in self.alerts if a.id == alert_id), None)
        if alert:
            alert.acknowledged = True
            return True
        return False
    
    # ===========================================
    # EMERGENCY ACTIONS
    # ===========================================
    
    def process_emergency_queue(self) -> List[Dict]:
        """Process pending emergency exit actions"""
        results = []
        
        while self.emergency_queue:
            action = self.emergency_queue.pop(0)
            
            if action["action"] == "exit":
                # In production: Execute exit transaction
                result = {
                    "action": "emergency_exit",
                    "user_id": action["user_id"],
                    "pool": action["position"].symbol,
                    "reason": action["reason"],
                    "status": "queued",  # Would be "executed" after tx
                    "timestamp": datetime.now().isoformat()
                }
                results.append(result)
                
                logger.warning(f"🆘 Emergency exit queued: {action['position'].symbol} for {action['user_id']}")
        
        return results
    
    def trigger_emergency_exit(self, user_id: str, pool_id: str, reason: str):
        """Manually trigger emergency exit"""
        positions = self.positions.get(user_id, [])
        position = next((p for p in positions if p.pool_id == pool_id), None)
        
        if position:
            self.emergency_queue.append({
                "action": "exit",
                "user_id": user_id,
                "position": position,
                "reason": reason
            })
            
            self._create_alert(
                user_id=user_id,
                alert_type=AlertType.SECURITY_WARNING,
                severity=AlertSeverity.EMERGENCY,
                message=f"🆘 Emergency exit initiated for {position.symbol}: {reason}",
                pool_id=pool_id
            )


# Singleton
guardian = GuardianAgent()
