"""
Rules Engine - Evaluate conditional rules against positions
Handles trailing stop loss, duration limits, take profit, and other exit conditions.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from .conditional_rules import ConditionalRule, RuleAction, PositionState


@dataclass
class RuleEvaluation:
    """Result of evaluating rules against a position"""
    matched_rule: Optional[ConditionalRule] = None
    should_exit: bool = False
    exit_reason: Optional[str] = None
    action: Optional[RuleAction] = None


class RulesEngine:
    """
    Evaluate conditional rules against positions.
    
    Checks:
    - Trailing stop loss (exit if drops X% from peak)
    - Stop loss (exit if drops X% from entry)
    - Take profit (exit if gains X%)
    - Max duration (exit after X hours)
    - APY threshold (exit if APY drops below X%)
    """
    
    def __init__(self):
        # Track peak values for trailing stop
        self.peak_values: Dict[str, float] = {}
        
    def find_matching_rule(self, position: PositionState, rules: List[ConditionalRule]) -> Optional[ConditionalRule]:
        """
        Find the first matching rule for a position.
        Rules are checked in priority order (highest first).
        """
        sorted_rules = sorted(rules, key=lambda r: -r.priority)
        
        for rule in sorted_rules:
            if self._matches_condition(position, rule.condition):
                return rule
        
        return None
    
    def _matches_condition(self, position: PositionState, condition) -> bool:
        """Check if position matches rule condition"""
        pool = position.pool_info
        
        # TVL check
        tvl = pool.get('tvl', 0)
        if condition.tvl_min and tvl < condition.tvl_min:
            return False
        if condition.tvl_max and tvl > condition.tvl_max:
            return False
        
        # Protocol check
        if condition.protocol:
            pool_protocol = pool.get('protocol', '').lower()
            if pool_protocol != condition.protocol.lower():
                return False
        
        # Pool type check
        if condition.pool_type:
            pool_type = pool.get('pool_type', '').lower()
            if pool_type != condition.pool_type.lower():
                return False
        
        # Asset check
        if condition.asset:
            assets = [a.upper() for a in pool.get('assets', [])]
            if condition.asset.upper() not in assets:
                return False
        
        # APY range check
        apy = pool.get('apy', 0)
        if condition.apy_min and apy < condition.apy_min:
            return False
        if condition.apy_max and apy > condition.apy_max:
            return False
        
        return True
    
    def evaluate(self, position: PositionState, rules: List[ConditionalRule]) -> RuleEvaluation:
        """
        Evaluate all rules against position and determine if exit is needed.
        
        Returns:
            RuleEvaluation with matched_rule, should_exit, and exit_reason
        """
        matched_rule = self.find_matching_rule(position, rules)
        
        if not matched_rule:
            return RuleEvaluation()
        
        action = matched_rule.action
        result = RuleEvaluation(matched_rule=matched_rule, action=action)
        
        # Update peak value for trailing stop
        pos_id = position.position_id
        current_peak = self.peak_values.get(pos_id, position.entry_value)
        if position.current_value > current_peak:
            self.peak_values[pos_id] = position.current_value
            current_peak = position.current_value
        
        # Check exit conditions
        
        # 1. Trailing Stop
        if action.trailing_stop_percent:
            drawdown = position.drawdown_from_peak()
            if drawdown >= action.trailing_stop_percent:
                result.should_exit = True
                result.exit_reason = f"TRAILING_STOP: {drawdown:.1f}% drop from peak (limit: {action.trailing_stop_percent}%)"
                return result
        
        # 2. Stop Loss
        if action.stop_loss_percent:
            loss = -position.profit_percent() if position.profit_percent() < 0 else 0
            if loss >= action.stop_loss_percent:
                result.should_exit = True
                result.exit_reason = f"STOP_LOSS: {loss:.1f}% loss (limit: {action.stop_loss_percent}%)"
                return result
        
        # 3. Take Profit
        if action.take_profit_percent:
            profit = position.profit_percent()
            if profit >= action.take_profit_percent:
                result.should_exit = True
                result.exit_reason = f"TAKE_PROFIT: {profit:.1f}% profit (target: {action.take_profit_percent}%)"
                return result
        
        # 4. Max Duration
        if action.max_duration_hours:
            hours_held = position.hours_held()
            if hours_held >= action.max_duration_hours:
                result.should_exit = True
                result.exit_reason = f"MAX_DURATION: Held {hours_held:.1f}h (limit: {action.max_duration_hours}h)"
                return result
        
        # 5. APY Threshold
        if action.exit_if_apy_below:
            current_apy = position.pool_info.get('apy', 0)
            if current_apy < action.exit_if_apy_below:
                result.should_exit = True
                result.exit_reason = f"APY_LOW: Current {current_apy:.1f}% < threshold {action.exit_if_apy_below}%"
                return result
        
        return result
    
    def clear_position_state(self, position_id: str):
        """Clear tracked state for a position (call after exit)"""
        self.peak_values.pop(position_id, None)
    
    def get_position_stats(self, position: PositionState) -> Dict[str, Any]:
        """Get current stats for a position"""
        pos_id = position.position_id
        peak = self.peak_values.get(pos_id, position.current_value)
        
        return {
            "position_id": pos_id,
            "entry_value": position.entry_value,
            "current_value": position.current_value,
            "peak_value": peak,
            "hours_held": position.hours_held(),
            "profit_percent": position.profit_percent(),
            "drawdown_from_peak": position.drawdown_from_peak() if peak > 0 else 0
        }


# Singleton
_engine = None

def get_rules_engine() -> RulesEngine:
    global _engine
    if _engine is None:
        _engine = RulesEngine()
    return _engine


# Test
if __name__ == "__main__":
    from .conditional_rules import ConditionalRule, RuleCondition, RuleAction, PositionState
    from datetime import datetime, timedelta
    
    print("=" * 60)
    print("Rules Engine Test")
    print("=" * 60)
    
    engine = RulesEngine()
    
    # Create test rules
    rules = [
        ConditionalRule(
            condition=RuleCondition(tvl_min=1_000_000, tvl_max=5_000_000, protocol="aerodrome", pool_type="dual"),
            action=RuleAction(max_duration_hours=1),
            priority=2,
            name="Small Aerodrome LP - 1h Max"
        ),
        ConditionalRule(
            condition=RuleCondition(tvl_min=5_000_000, tvl_max=20_000_000),
            action=RuleAction(trailing_stop_percent=15),
            priority=1,
            name="Medium TVL - 15% Trailing Stop"
        )
    ]
    
    # Test position matching rule 1
    print("\n--- Test 1: Aerodrome 2M TVL position held 2h ---")
    pos1 = PositionState(
        position_id="pos1",
        user_address="0x123",
        pool_address="0xaero",
        entry_time=datetime.utcnow() - timedelta(hours=2),
        entry_value=1000,
        peak_value=1050,
        current_value=1000,
        pool_info={"tvl": 2_000_000, "protocol": "aerodrome", "pool_type": "dual", "apy": 25}
    )
    
    result = engine.evaluate(pos1, rules)
    print(f"Matched: {result.matched_rule.name if result.matched_rule else 'None'}")
    print(f"Should Exit: {result.should_exit}")
    print(f"Reason: {result.exit_reason}")
    
    # Test position matching rule 2 with trailing stop hit
    print("\n--- Test 2: 10M TVL position with 20% drop from peak ---")
    pos2 = PositionState(
        position_id="pos2",
        user_address="0x123",
        pool_address="0xmorph",
        entry_time=datetime.utcnow() - timedelta(hours=0.5),
        entry_value=1000,
        peak_value=1200,  # Peak was $1200
        current_value=960,  # Now $960 = 20% drop from peak
        pool_info={"tvl": 10_000_000, "protocol": "morpho", "pool_type": "single", "apy": 12}
    )
    
    # Simulate peak tracking
    engine.peak_values["pos2"] = 1200
    
    result = engine.evaluate(pos2, rules)
    print(f"Matched: {result.matched_rule.name if result.matched_rule else 'None'}")
    print(f"Should Exit: {result.should_exit}")
    print(f"Reason: {result.exit_reason}")
    print(f"Stats: {engine.get_position_stats(pos2)}")
