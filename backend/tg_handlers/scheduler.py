"""
Techne Telegram Bot - Background Scheduler
Runs periodic jobs for alert checking
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .models.user_config import user_store, UserConfig
from .services.alerts import generate_alerts_for_user, fetch_all_pools_for_alerts
from .services.new_pool_alert import new_pool_detector
from .services.channel_poster import channel_poster

logger = logging.getLogger(__name__)

# Store previous pool states for comparison
_previous_pools: Dict[str, Dict[str, Any]] = {}

# Global bot reference - set by run_bot.py at startup
_scheduler_bot: Optional[Bot] = None

def set_scheduler_bot(bot: Bot):
    """Set the bot instance for scheduler to use."""
    global _scheduler_bot
    _scheduler_bot = bot
    logger.info("📅 Scheduler bot instance set")

def get_scheduler_bot() -> Optional[Bot]:
    """Get the bot instance for scheduler jobs."""
    global _scheduler_bot
    if _scheduler_bot is None:
        # Fallback to get_bot() but only get the Bot instance
        try:
            from .bot import get_bot
            techne_bot = get_bot()
            _scheduler_bot = techne_bot.bot
        except Exception as e:
            logger.error(f"Failed to get bot for scheduler: {e}")
            return None
    return _scheduler_bot


# =====================================================
# CHANNEL POSTING JOBS
# =====================================================

async def post_news_channel_summary():
    """
    Post daily summary to NEWS channel (9:00 UTC).
    News channel gets: breaking news, market updates, security alerts.
    """
    logger.info("📰 Posting daily summary to NEWS channel...")
    
    try:
        bot = get_scheduler_bot()
        if not bot:
            logger.error("No bot available for news summary")
            return
        await channel_poster.post_daily_summary(bot)
        logger.info("📰 News channel summary posted")
    except Exception as e:
        logger.error(f"❌ Failed to post news summary: {e}")


async def post_airdrop_daily_digest():
    """
    Post DAILY airdrop digest to AIRDROPS channel.
    Uses LIVE DATA from DefiLlama + curated farming guides.
    Posted at 10:00 UTC and PINNED.
    """
    logger.info("🎁 Posting daily airdrop digest with LIVE data...")
    
    try:
        bot = get_scheduler_bot()
        if not bot:
            logger.error("No bot available for airdrop digest")
            return
        
        # Use REAL scraper with live DefiLlama data
        from .services.airdrop_scraper import airdrop_scraper
        
        # Get formatted digest with real data
        message = await airdrop_scraper.format_daily_digest()
        
        # Post and PIN the message
        from .services.channel_poster import CHANNEL_AIRDROPS
        try:
            sent = await bot.send_message(
                chat_id=CHANNEL_AIRDROPS,
                text=message,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            # Pin it
            await bot.pin_chat_message(
                chat_id=CHANNEL_AIRDROPS,
                message_id=sent.message_id,
                disable_notification=True
            )
            logger.info("🎁 Daily airdrop digest posted and pinned with LIVE data!")
        except Exception as e:
            logger.error(f"Failed to post airdrop digest: {e}")
        
    except Exception as e:
        logger.error(f"❌ Failed to post airdrop digest: {e}")
        logger.error(f"❌ Failed to post airdrop digest: {e}")


async def check_new_pools():
    """
    Check for new pools matching user filters
    """
    logger.info("🆕 Checking for new pools...")
    
    try:
        bot = get_bot()
        alerts_sent = await new_pool_detector.check_all_users(bot.bot)
        
        if alerts_sent > 0:
            logger.info(f"🆕 Sent {alerts_sent} new pool alerts")
        else:
            logger.debug("No new pools matching user filters")
            
    except Exception as e:
        logger.error(f"❌ New pool check failed: {e}")


async def check_breaking_news():
    """
    Check for breaking news from X/Twitter via Nitter and post to News channel.
    Runs every 10 seconds for near-real-time updates.
    
    Sources (X accounts only):
    - @WalterBloomberg, @solidintel_x, @tree_news_feed
    - @LiveSquawk, @degeneratenews
    """
    logger.info("📰 Checking X for breaking news...")
    
    try:
        from .services.news_monitor import news_monitor, NewsItem
        from .services.twikit_scraper import twikit_scraper
        from .services.channel_poster import CHANNEL_NEWS
        
        bot = get_scheduler_bot()
        if not bot:
            logger.error("No bot available for news check")
            return
        
        # Fetch news from X accounts (via Twikit)
        x_posts = await twikit_scraper.fetch_category("news")
        
        if not x_posts:
            logger.debug("No new X posts")
            return
        
        # Convert X posts to NewsItem format for deduplication
        news_items = []
        for post in x_posts[:10]:  # Check top 10 most recent
            # Determine importance based on keywords
            importance = 3
            content_lower = post.content.lower()
            if any(kw in content_lower for kw in ["breaking", "🚨", "alert", "just in"]):
                importance = 5
            elif any(kw in content_lower for kw in ["fed", "fomc", "rate", "inflation", "cpi"]):
                importance = 4
            
            news_items.append(NewsItem(
                title=post.content[:150],
                summary=post.content,
                source=f"@{post.handle}",
                category="news",
                timestamp=post.timestamp,
                url=post.url,
                importance=importance
            ))
        
        if news_items:
            posted = await news_monitor.check_and_post_news(
                news_items, 
                bot, 
                CHANNEL_NEWS
            )
            if posted > 0:
                logger.info(f"📰 Posted {posted} REAL news items to channel")
        
    except Exception as e:
        logger.error(f"❌ Breaking news check failed: {e}")


async def check_and_send_alerts():
    """
    Check for alerts and send to users
    """
    global _previous_pools
    
    logger.info("🔔 Running alert check...")
    
    try:
        # Get all users with alerts enabled
        users = await user_store.get_all_with_alerts()
        
        if not users:
            logger.info("No users with alerts enabled")
            return
        
        # Fetch current pool states
        current_pools = await fetch_all_pools_for_alerts()
        current_pool_map = {p.get("pool", p.get("id", "")): p for p in current_pools if p.get("pool") or p.get("id")}
        
        alerts_sent = 0
        
        for user in users:
            try:
                # Check rate limiting
                recent = await user_store.get_recent_alerts(
                    user.telegram_id, 
                    user.alert_interval_minutes
                )
                
                # Generate alerts for this user
                alerts = await generate_alerts_for_user(user, _previous_pools)
                
                # Filter out already-sent alerts
                recent_pool_ids = {r["pool_id"] for r in recent}
                new_alerts = [a for a in alerts if a["pool_id"] not in recent_pool_ids]
                
                # Send alerts
                bot = get_bot()
                for alert in new_alerts[:3]:  # Max 3 alerts per check
                    await bot.send_alert(user.telegram_id, alert["message"])
                    await user_store.log_alert(
                        user.telegram_id,
                        alert["type"],
                        alert["pool_id"],
                        alert["message"][:200]
                    )
                    alerts_sent += 1
                    await asyncio.sleep(0.1)  # Rate limit
                    
            except Exception as e:
                logger.error(f"Error processing alerts for {user.telegram_id}: {e}")
        
        # Update previous pool states
        _previous_pools = current_pool_map
        
        logger.info(f"✅ Alert check complete. Sent {alerts_sent} alerts to {len(users)} users")
        
    except Exception as e:
        logger.error(f"❌ Alert check failed: {e}")


async def send_daily_digest():
    """
    Send daily digest to premium users
    """
    logger.info("📊 Sending daily digest...")
    
    try:
        premium_users = await user_store.get_premium_users()
        
        if not premium_users:
            return
        
        # Generate digest
        digest = """
📊 *Daily DeFi Digest*

*Market Overview*
• Total TVL: $2.5B (+2.3%)
• Avg APY: 13.7%
• Active Pools: 847

*Top Movers (24h)*
📈 +45% APY - Aerodrome USDC/WETH
📈 +32% APY - Morpho USDC
📉 -12% TVL - Compound USDT

*Whale Activity*
🐋 $2.5M deposit to Aave
🐋 $1.8M withdrawn from Curve

_Use /pools to explore opportunities_
"""
        
        bot = get_bot()
        for user in premium_users:
            try:
                await bot.send_alert(user.telegram_id, digest)
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning(f"Failed to send digest to {user.telegram_id}: {e}")
        
        logger.info(f"📊 Daily digest sent to {len(premium_users)} premium users")
        
    except Exception as e:
        logger.error(f"Daily digest failed: {e}")


class AlertScheduler:
    """
    Manages background jobs for alerts
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()
    
    def _setup_jobs(self):
        """
        Configure scheduled jobs
        """
        # Check alerts every 5 minutes
        self.scheduler.add_job(
            check_and_send_alerts,
            IntervalTrigger(minutes=5),
            id="alert_check",
            name="Check and send alerts",
            replace_existing=True
        )
        
        # Check for new pools every 5 minutes
        self.scheduler.add_job(
            check_new_pools,
            IntervalTrigger(minutes=5),
            id="new_pool_check",
            name="Check for new pools",
            replace_existing=True
        )
        
        # Daily digest at 8:00 UTC
        self.scheduler.add_job(
            send_daily_digest,
            "cron",
            hour=8,
            minute=0,
            id="daily_digest",
            name="Send daily digest",
            replace_existing=True
        )
        
        # Airdrop daily digest at 10:00 UTC (once per day, pinned)
        self.scheduler.add_job(
            post_airdrop_daily_digest,
            "cron",
            hour=10,
            minute=0,
            id="airdrop_daily",
            name="Post airdrop daily digest",
            replace_existing=True
        )
        
        # NOTE: News channel functionality removed - only Airdrops active
        
        logger.info("📅 Scheduler jobs configured")
    
    def start(self):
        """
        Start the scheduler
        """
        self.scheduler.start()
        logger.info("⏰ Alert scheduler started")
    
    def stop(self):
        """
        Stop the scheduler
        """
        self.scheduler.shutdown()
        logger.info("⏰ Alert scheduler stopped")


# Global scheduler instance
alert_scheduler = AlertScheduler()
