"""
Conditional Rules Engine - Data Models
Defines schemas for parsing natural language instructions into executable trading rules.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List
from datetime import datetime
import json


@dataclass
class RuleCondition:
    """Condition that must be met for rule to apply"""
    tvl_min: Optional[float] = None        # Minimum TVL in USD (e.g., 1_000_000)
    tvl_max: Optional[float] = None        # Maximum TVL in USD (e.g., 5_000_000)
    protocol: Optional[str] = None         # Protocol name (e.g., "aerodrome")
    pool_type: Optional[str] = None        # "single" | "dual"
    asset: Optional[str] = None            # Asset symbol (e.g., "USDC")
    apy_min: Optional[float] = None        # Minimum APY %
    apy_max: Optional[float] = None        # Maximum APY %
    
    def matches(self, pool: dict) -> bool:
        """Check if pool matches this condition"""
        if self.tvl_min and pool.get('tvl', 0) < self.tvl_min:
            return False
        if self.tvl_max and pool.get('tvl', 0) > self.tvl_max:
            return False
        if self.protocol and pool.get('protocol', '').lower() != self.protocol.lower():
            return False
        if self.pool_type and pool.get('pool_type', '').lower() != self.pool_type.lower():
            return False
        if self.asset and self.asset.upper() not in [a.upper() for a in pool.get('assets', [])]:
            return False
        if self.apy_min and pool.get('apy', 0) < self.apy_min:
            return False
        if self.apy_max and pool.get('apy', 0) > self.apy_max:
            return False
        return True
    
    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class RuleAction:
    """Action to take when rule condition is met"""
    max_duration_hours: Optional[float] = None      # Max time to hold position
    trailing_stop_percent: Optional[float] = None   # Exit if drops X% from peak
    take_profit_percent: Optional[float] = None     # Exit if gains X%
    stop_loss_percent: Optional[float] = None       # Exit if loses X% from entry
    exit_if_apy_below: Optional[float] = None       # Exit if APY drops below X%
    auto_compound: Optional[bool] = None            # Auto-compound rewards
    rebalance_threshold: Optional[float] = None     # Rebalance if deviation > X%
    
    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ConditionalRule:
    """A complete conditional rule: IF condition THEN action"""
    condition: RuleCondition
    action: RuleAction
    priority: int = 0           # Higher priority rules evaluated first
    name: Optional[str] = None  # Human-readable rule name
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            'condition': self.condition.to_dict(),
            'action': self.action.to_dict(),
            'priority': self.priority,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ConditionalRule':
        return cls(
            condition=RuleCondition(**data.get('condition', {})),
            action=RuleAction(**data.get('action', {})),
            priority=data.get('priority', 0),
            name=data.get('name')
        )
    
    def __str__(self) -> str:
        cond_parts = []
        if self.condition.tvl_min or self.condition.tvl_max:
            tvl_str = f"TVL ${self.condition.tvl_min/1e6 if self.condition.tvl_min else 0}M-${self.condition.tvl_max/1e6 if self.condition.tvl_max else '∞'}M"
            cond_parts.append(tvl_str)
        if self.condition.protocol:
            cond_parts.append(f"protocol={self.condition.protocol}")
        if self.condition.pool_type:
            cond_parts.append(f"type={self.condition.pool_type}")
        
        action_parts = []
        if self.action.max_duration_hours:
            action_parts.append(f"max_hold={self.action.max_duration_hours}h")
        if self.action.trailing_stop_percent:
            action_parts.append(f"trailing_stop={self.action.trailing_stop_percent}%")
        if self.action.stop_loss_percent:
            action_parts.append(f"stop_loss={self.action.stop_loss_percent}%")
        if self.action.take_profit_percent:
            action_parts.append(f"take_profit={self.action.take_profit_percent}%")
        
        return f"IF [{', '.join(cond_parts)}] THEN [{', '.join(action_parts)}]"


@dataclass
class PositionState:
    """Tracks state of a position for rule evaluation"""
    position_id: str
    user_address: str
    pool_address: str
    entry_time: datetime
    entry_value: float
    peak_value: float           # For trailing stop
    current_value: float
    pool_info: dict             # TVL, APY, protocol, etc.
    
    def hours_held(self) -> float:
        return (datetime.utcnow() - self.entry_time).total_seconds() / 3600
    
    def profit_percent(self) -> float:
        if self.entry_value == 0:
            return 0
        return ((self.current_value - self.entry_value) / self.entry_value) * 100
    
    def drawdown_from_peak(self) -> float:
        if self.peak_value == 0:
            return 0
        return ((self.peak_value - self.current_value) / self.peak_value) * 100


# Example usage
if __name__ == "__main__":
    # Create rule: For pools 1M-5M TVL on Aerodrome dual, hold max 1h
    rule1 = ConditionalRule(
        condition=RuleCondition(tvl_min=1_000_000, tvl_max=5_000_000, 
                                protocol="aerodrome", pool_type="dual"),
        action=RuleAction(max_duration_hours=1),
        priority=1,
        name="Small Aerodrome LP - Quick Exit"
    )
    
    # Create rule: For pools 5M-20M TVL, trailing stop at 15%
    rule2 = ConditionalRule(
        condition=RuleCondition(tvl_min=5_000_000, tvl_max=20_000_000),
        action=RuleAction(trailing_stop_percent=15),
        priority=0,
        name="Medium TVL - Trailing Stop"
    )
    
    print("Rule 1:", rule1)
    print("Rule 2:", rule2)
    print("\nJSON:", json.dumps([rule1.to_dict(), rule2.to_dict()], indent=2, default=str))
