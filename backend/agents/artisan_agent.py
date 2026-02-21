"""
Artisan Agent - AI-Powered DeFi Portfolio Manager
Connects Kimi K2.5 with Techne's backend for autonomous yield optimization

This is the main agent class that:
1. Receives commands from Telegram bot
2. Uses Kimi K2.5 for reasoning
3. Executes actions via Techne backend
4. Respects autonomy mode limits
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from services.kimi_client import get_kimi_client, ARTISAN_TOOLS
from supabase import create_client

logger = logging.getLogger("ArtisanAgent")


class AutonomyMode(Enum):
    """Agent autonomy levels"""
    OBSERVER = "observer"      # View only
    ADVISOR = "advisor"        # Suggest + confirm
    COPILOT = "copilot"        # Auto < $1000
    FULL_AUTO = "full_auto"    # Full autonomy


@dataclass
class AgentContext:
    """Context for agent operations"""
    user_address: str
    autonomy_mode: AutonomyMode
    subscription_id: str
    telegram_chat_id: int
    portfolio_value: float = 0.0
    guidelines: Dict[str, Any] = None


class ArtisanAgent:
    """
    Artisan Agent - Personal AI DeFi Assistant
    
    Uses Kimi K2.5 for reasoning and decision making.
    Executes trades via session key within autonomy limits.
    """
    
    def __init__(self, context: AgentContext):
        self.context = context
        self.kimi = get_kimi_client()
        self.supabase = self._get_supabase()
        
        # Conversation history for this user
        self.conversation_history: List[Dict] = []
        
        # Pending actions requiring confirmation
        self.pending_actions: List[Dict] = []
    
    def _get_supabase(self):
        """Get Supabase client"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if url and key:
            return create_client(url, key)
        return None
    
    async def process_message(self, text: str) -> Dict[str, Any]:
        """
        Process a natural language message from the user.
        
        Args:
            text: User's message
            
        Returns:
            Response with content and any actions taken
        """
        # Add to history
        self.conversation_history.append({
            "role": "user",
            "content": text
        })
        
        # Build user context for Kimi
        user_context = {
            "wallet_address": self.context.user_address,
            "autonomy_mode": self.context.autonomy_mode.value,
            "portfolio_value": self.context.portfolio_value,
            "guidelines": self.context.guidelines or {}
        }
        
        # Get response from Kimi
        response = await self.kimi.process_command(
            user_message=text,
            conversation_history=self.conversation_history[-10:],
            tools=ARTISAN_TOOLS,
            user_context=user_context
        )
        
        actions_taken = []
        
        # Handle tool calls
        if response.get("tool_calls"):
            for call in response["tool_calls"]:
                func_name = call.get("function", {}).get("name")
                args = call.get("function", {}).get("arguments", "{}")
                
                try:
                    args = json.loads(args) if isinstance(args, str) else args
                except:
                    args = {}
                
                result = await self._execute_tool(func_name, args)
                actions_taken.append({
                    "tool": func_name,
                    "args": args,
                    "result": result
                })
        
        # Add assistant response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": response.get("content", "")
        })
        
        # Log to database
        await self._log_conversation(text, response.get("content", ""), actions_taken)
        
        return {
            "content": response.get("content", ""),
            "actions": actions_taken,
            "tool_calls": response.get("tool_calls", [])
        }
    
    async def _execute_tool(self, tool_name: str, args: Dict) -> Dict:
        """
        Execute a tool respecting autonomy mode.
        
        Args:
            tool_name: Name of the tool to execute
            args: Tool arguments
            
        Returns:
            Tool execution result
        """
        # Action tools that modify state
        action_tools = ["execute_trade", "exit_position", "emergency_exit_all"]
        
        if tool_name in action_tools:
            result = await self._execute_action_tool(tool_name, args)
        else:
            result = await self._execute_read_tool(tool_name, args)
        
        # Log action to database
        await self._log_action(tool_name, args, result)
        
        return result
    
    async def _execute_action_tool(self, tool_name: str, args: Dict) -> Dict:
        """
        Execute action tool with autonomy checks.
        """
        mode = self.context.autonomy_mode
        
        # Observer mode - no actions allowed
        if mode == AutonomyMode.OBSERVER:
            return {
                "blocked": True,
                "reason": "Observer mode - actions are disabled. Change to Advisor or higher to enable trades."
            }
        
        # Advisor mode - queue for confirmation
        if mode == AutonomyMode.ADVISOR:
            action = {
                "id": f"action_{datetime.now().timestamp()}",
                "tool": tool_name,
                "args": args,
                "status": "pending_confirmation",
                "created_at": datetime.now().isoformat()
            }
            self.pending_actions.append(action)
            
            return {
                "queued": True,
                "action_id": action["id"],
                "message": "Action queued for your confirmation. Reply 'confirm' or 'cancel'."
            }
        
        # Co-pilot mode - check amount threshold
        if mode == AutonomyMode.COPILOT:
            amount = args.get("amount_usd", 0)
            if amount > 1000:
                action = {
                    "id": f"action_{datetime.now().timestamp()}",
                    "tool": tool_name,
                    "args": args,
                    "status": "pending_confirmation",
                    "reason": f"Amount (${amount}) exceeds $1000 threshold",
                    "created_at": datetime.now().isoformat()
                }
                self.pending_actions.append(action)
                
                return {
                    "queued": True,
                    "action_id": action["id"],
                    "message": f"Trade of ${amount} exceeds $1000 limit. Reply 'confirm' to proceed."
                }
        
        # Full Auto mode - cap at $10K per transaction
        if mode == AutonomyMode.FULL_AUTO:
            amount = args.get("amount_usd", 0)
            if amount > 10000:
                return {
                    "blocked": True,
                    "reason": f"Full Auto cap: ${amount} exceeds $10,000 per-transaction limit."
                }
        
        # Execute immediately (Full Auto under cap, or Copilot under $1K)
        return await self._do_execute_action(tool_name, args)
    
    async def _do_execute_action(self, tool_name: str, args: Dict) -> Dict:
        """
        Actually execute the action (no checks - internal use).
        """
        try:
            if tool_name == "execute_trade":
                return await self._execute_trade(args)
            
            elif tool_name == "exit_position":
                return await self._exit_position(args)
            
            elif tool_name == "emergency_exit_all":
                return await self._emergency_exit_all(args)
            
            return {"error": f"Unknown action tool: {tool_name}"}
            
        except Exception as e:
            logger.error(f"Action execution error: {e}")
            return {"error": str(e)}
    
    async def _execute_trade(self, args: Dict) -> Dict:
        """Execute a trade via Artisan Execution bridge"""
        from agents.artisan_execution import execute_trade_for_user
        
        action = args.get("action")  # deposit, withdraw, swap
        pool_id = args.get("pool_id", "")
        amount = args.get("amount_usd", 0)
        
        # Extract protocol from pool_id (e.g., "aave-v3-usdc" -> "aave-v3")
        protocol_id = pool_id.split("-")[0] + "-" + pool_id.split("-")[1] if "-" in pool_id else pool_id
        
        logger.info(f"Executing trade: {action} ${amount} to {protocol_id}")
        
        result = await execute_trade_for_user(
            user_address=self.context.user_address,
            action=action,
            protocol_id=protocol_id,
            amount_usd=amount
        )
        
        return result
    
    async def _exit_position(self, args: Dict) -> Dict:
        """Exit a specific position via Artisan Execution bridge"""
        from agents.artisan_execution import create_executor
        
        position_id = args.get("position_id")
        
        logger.info(f"Exiting position: {position_id}")
        
        executor = create_executor(self.context.user_address)
        result = await executor.exit_position(position_id)
        
        return result
    
    async def _emergency_exit_all(self, args: Dict) -> Dict:
        """Emergency exit all positions via Artisan Execution bridge"""
        from agents.artisan_execution import emergency_exit_for_user
        
        reason = args.get("reason", "User requested")
        
        logger.warning(f"EMERGENCY EXIT ALL: {reason}")
        
        result = await emergency_exit_for_user(
            user_address=self.context.user_address,
            reason=reason
        )
        
        return result
    
    async def _execute_read_tool(self, tool_name: str, args: Dict) -> Dict:
        """Execute read-only tool (no autonomy check needed)"""
        try:
            if tool_name == "analyze_portfolio":
                return await self._analyze_portfolio()
            
            elif tool_name == "find_pools":
                return await self._find_pools(args)
            
            elif tool_name == "analyze_pool":
                return await self._analyze_pool(args)
            
            elif tool_name == "get_market_sentiment":
                return await self._get_market_sentiment()
            
            elif tool_name == "send_report":
                return await self._send_report(args)
            
            return {"error": f"Unknown read tool: {tool_name}"}
            
        except Exception as e:
            logger.error(f"Read tool error: {e}")
            return {"error": str(e)}
    
    async def _analyze_portfolio(self) -> Dict:
        """Get portfolio analysis"""
        # Get positions from Supabase
        if not self.supabase:
            return {"error": "Database not configured"}
        
        try:
            result = self.supabase.table("agent_positions").select("*").eq(
                "user_address", self.context.user_address.lower()
            ).execute()
            
            positions = result.data or []
            
            # Use Kimi for analysis
            analysis = await self.kimi.analyze_portfolio(positions)
            
            return {
                "positions": positions,
                "analysis": analysis
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _find_pools(self, args: Dict) -> Dict:
        """Find yield pools"""
        # Get pools from Scout Agent
        from artisan.scout_agent import get_scout_pools
        
        pools = await get_scout_pools(
            chain=args.get("chain", "Base"),
            min_apy=args.get("min_apy", 5),
            max_risk=args.get("max_risk", "all"),
            stablecoin_only=args.get("stablecoin_only", False)
        )
        
        # Use Kimi to rank by user preferences
        if self.context.guidelines:
            ranked = await self.kimi.find_opportunities(
                user_preferences=self.context.guidelines,
                available_pools=pools,
                current_positions=None
            )
            return ranked
        
        return {"pools": pools[:10]}
    
    async def _analyze_pool(self, args: Dict) -> Dict:
        """Analyze specific pool"""
        pool_id = args.get("pool_id")
        
        # Get pool details
        # TODO: Implement pool analysis
        
        return {
            "pool_id": pool_id,
            "analysis": "Pool analysis pending implementation"
        }
    
    async def _get_market_sentiment(self) -> Dict:
        """Get market sentiment"""
        return {
            "sentiment": "neutral",
            "btc_dominance": "52%",
            "fear_greed_index": 55,
            "eth_gas_gwei": 15,
            "base_recommended": True,
            "note": "Market conditions stable. Base remains optimal for DeFi."
        }
    
    async def _send_report(self, args: Dict) -> Dict:
        """Generate and send report"""
        report_type = args.get("report_type", "daily")
        
        # Get portfolio data
        portfolio = await self._analyze_portfolio()
        
        # Generate report with Kimi
        # TODO: Format and send via Telegram
        
        return {
            "report_type": report_type,
            "generated": True,
            "sent": False,  # TODO: Send to Telegram
            "summary": portfolio.get("analysis", {}).get("summary", "Report generated")
        }
    
    async def confirm_action(self, action_id: str) -> Dict:
        """Confirm a pending action"""
        for action in self.pending_actions:
            if action["id"] == action_id:
                self.pending_actions.remove(action)
                return await self._do_execute_action(action["tool"], action["args"])
        
        return {"error": "Action not found or expired"}
    
    async def cancel_action(self, action_id: str) -> Dict:
        """Cancel a pending action"""
        for action in self.pending_actions:
            if action["id"] == action_id:
                self.pending_actions.remove(action)
                return {"cancelled": True, "action_id": action_id}
        
        return {"error": "Action not found"}
    
    async def _log_conversation(
        self,
        user_message: str,
        assistant_response: str,
        actions: List[Dict]
    ):
        """Log conversation to database"""
        if not self.supabase:
            return
        
        try:
            self.supabase.table("artisan_conversations").insert({
                "subscription_id": self.context.subscription_id,
                "role": "user",
                "content": user_message
            }).execute()
            
            self.supabase.table("artisan_conversations").insert({
                "subscription_id": self.context.subscription_id,
                "role": "assistant",
                "content": assistant_response,
                "tool_calls": json.dumps(actions) if actions else None
            }).execute()
            
        except Exception as e:
            logger.error(f"Conversation logging error: {e}")
    
    async def _log_action(self, tool_name: str, args: Dict, result: Dict):
        """Log action to database"""
        if not self.supabase:
            return
        
        try:
            action_type = "analyze" if tool_name.startswith("analyze") or tool_name.startswith("find") or tool_name == "get_market_sentiment" else (
                "report" if tool_name == "send_report" else "trade"
            )
            
            self.supabase.table("artisan_actions").insert({
                "subscription_id": self.context.subscription_id,
                "action_type": action_type,
                "details": {
                    "tool": tool_name,
                    "args": args,
                    "result": result
                },
                "confirmation_required": result.get("queued", False),
                "confirmed": not result.get("queued", False),
                "executed": result.get("executed", False),
                "tx_hash": result.get("tx_hash")
            }).execute()
            
        except Exception as e:
            logger.error(f"Action logging error: {e}")


# Factory function
def create_artisan_agent(
    user_address: str,
    autonomy_mode: str,
    subscription_id: str,
    telegram_chat_id: int,
    guidelines: Dict = None
) -> ArtisanAgent:
    """Create an Artisan Agent instance"""
    
    context = AgentContext(
        user_address=user_address,
        autonomy_mode=AutonomyMode(autonomy_mode),
        subscription_id=subscription_id,
        telegram_chat_id=telegram_chat_id,
        guidelines=guidelines
    )
    
    return ArtisanAgent(context)
