"""
Portfolio Balance Refresh Job
Background task that refreshes all agent balances every 10 minutes.
Saves to Supabase to reduce RPC calls on frontend requests.
"""
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Refresh interval: 10 minutes
REFRESH_INTERVAL_SECONDS = 600

# Flag to control the refresh loop
_refresh_running = False


async def refresh_agent_balances():
    """
    Refresh balances for all active agents.
    Called every 10 minutes by background loop.
    """
    from infrastructure.supabase_client import supabase
    from api.agent_config_router import DEPLOYED_AGENTS
    from api.portfolio_router import fetch_all_balances, fetch_lp_positions
    
    logger.info("[BalanceRefresh] Starting balance refresh cycle...")
    start = datetime.now()
    
    refreshed = 0
    errors = 0
    
    # Get all users with deployed agents
    for user_address, agents in DEPLOYED_AGENTS.items():
        for agent in agents:
            agent_address = agent.get("agent_address") or agent.get("address")
            if not agent_address:
                continue
            
            try:
                # Fetch fresh balances from RPC (parallel)
                holdings_task = fetch_all_balances(agent_address)
                positions_task = fetch_lp_positions(user_address, agent_address)
                
                holdings, positions = await asyncio.gather(holdings_task, positions_task)
                
                # Calculate total
                total = sum(h.value_usd for h in holdings) + sum(p.value_usd for p in positions)
                
                # Only save to Supabase if we have actual data (not empty results)
                has_data = len(holdings) > 0 or len(positions) > 0 or total > 0
                if has_data:
                    await supabase.save_agent_balances(
                        agent_address=agent_address,
                        user_address=user_address,
                        holdings=[h.model_dump() for h in holdings],
                        positions=[p.model_dump() for p in positions],
                        total_value_usd=total
                    )
                    refreshed += 1
                    logger.info(f"[BalanceRefresh] Refreshed {agent_address[:10]}... (${total:.2f})")
                else:
                    logger.warning(f"[BalanceRefresh] Skipping empty data for {agent_address[:10]}...")
                
            except Exception as e:
                errors += 1
                logger.error(f"[BalanceRefresh] Error refreshing {agent_address[:10]}...: {e}")
    
    elapsed = (datetime.now() - start).total_seconds()
    logger.info(f"[BalanceRefresh] Cycle complete: {refreshed} agents, {errors} errors, {elapsed:.1f}s")


async def balance_refresh_loop():
    """
    Background loop that runs every 10 minutes.
    Started by FastAPI lifespan.
    """
    global _refresh_running
    _refresh_running = True
    
    logger.info("[BalanceRefresh] Background loop started (interval: 10 min)")
    
    # Initial delay to let app start up
    await asyncio.sleep(30)
    
    while _refresh_running:
        try:
            await refresh_agent_balances()
        except Exception as e:
            logger.error(f"[BalanceRefresh] Loop error: {e}")
        
        # Wait for next cycle
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)


def start_balance_refresh():
    """Start the background refresh loop (call from main.py lifespan)"""
    asyncio.create_task(balance_refresh_loop())
    logger.info("[BalanceRefresh] Background task scheduled")


def stop_balance_refresh():
    """Stop the background refresh loop"""
    global _refresh_running
    _refresh_running = False
    logger.info("[BalanceRefresh] Background task stopped")
