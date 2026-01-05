"""
Techne Telegram Bot - Channel Posting Service
Automatically posts alerts and news to premium channels
"""

import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.enums import ParseMode

logger = logging.getLogger(__name__)

# Premium Channel Configuration
CHANNEL_NEWS = "-1003570137448"      # Techne News Feed
CHANNEL_AIRDROPS = "-1003544179066"  # Techne Airdrops


class ChannelPoster:
    """
    Handles automatic posting to premium channels
    
    Channels:
    - News Feed: macro, security, whale, pools
    - Airdrops: airdrop opportunities, points programs
    """
    
    def __init__(self):
        self.channel_news = CHANNEL_NEWS
        self.channel_airdrops = CHANNEL_AIRDROPS
        self._last_posts: Dict[str, datetime] = {}  # Prevent spam
        self._min_interval_minutes = 5  # Min time between same-type posts
    
    def _can_post(self, post_type: str) -> bool:
        """Check if we can post (rate limiting)"""
        if post_type not in self._last_posts:
            return True
        
        elapsed = datetime.utcnow() - self._last_posts[post_type]
        return elapsed.total_seconds() >= self._min_interval_minutes * 60
    
    def _mark_posted(self, post_type: str):
        """Mark that we posted"""
        self._last_posts[post_type] = datetime.utcnow()
    
    async def post_to_channel(self, bot: Bot, channel_id: str, message: str, post_type: str = "general", pin: bool = False) -> bool:
        """
        Post message to specified channel
        Returns True if posted successfully
        """
        if not channel_id:
            logger.warning("Channel not configured, skipping post")
            return False
        
        if not self._can_post(post_type):
            logger.debug(f"Rate limited: {post_type}")
            return False
        
        try:
            sent_message = await bot.send_message(
                chat_id=channel_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            self._mark_posted(post_type)
            logger.info(f"Posted {post_type} to channel {channel_id}")
            
            # Pin the message if requested
            if pin:
                try:
                    await bot.pin_chat_message(
                        chat_id=channel_id,
                        message_id=sent_message.message_id,
                        disable_notification=True  # Don't spam users
                    )
                    logger.info(f"📌 Pinned {post_type} in channel")
                except Exception as pin_error:
                    logger.warning(f"Failed to pin message: {pin_error}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to post to channel: {e}")
            return False
    
    async def post_to_news(self, bot: Bot, message: str, post_type: str = "news") -> bool:
        """Post to news channel"""
        return await self.post_to_channel(bot, self.channel_news, message, post_type)
    
    async def post_to_airdrops(self, bot: Bot, message: str, post_type: str = "airdrop") -> bool:
        """Post to airdrops channel"""
        return await self.post_to_channel(bot, self.channel_airdrops, message, post_type)
    
    # ===========================================
    # Formatted alert posts
    # ===========================================
    
    async def post_airdrop_alert(self, bot: Bot, protocol: str, details: str, score: int = 0):
        """Post airdrop opportunity alert"""
        message = f"""
🎁 *AIRDROP ALERT*

*{protocol}*
{details}

{"⭐" * min(5, score // 20)} Score: {score}/100

_Check /airdrop for full details_
"""
        await self.post_to_airdrops(bot, message, "airdrop")
    
    async def post_news_alert(self, bot: Bot, title: str, summary: str, source: str, category: str = "news"):
        """Post breaking news alert"""
        emoji = {
            "macro": "🌍",
            "security": "🚨",
            "defi": "📊",
            "airdrop": "🎁"
        }.get(category, "📰")
        
        message = f"""
{emoji} *BREAKING*

*{title}*

{summary}

📍 Source: {source}
⏰ {datetime.utcnow().strftime('%H:%M UTC')}
"""
        await self.post_to_news(bot, message, f"news_{category}")
    
    async def post_whale_alert(self, bot: Bot, action: str, amount: str, protocol: str, tx_hash: str = ""):
        """Post whale movement alert"""
        message = f"""
🐋 *WHALE ALERT*

*{action}*

💰 Amount: {amount}
📍 Protocol: {protocol}
{"🔗 " + tx_hash[:16] + "..." if tx_hash else ""}

_Large wallet movement detected_
"""
        await self.post_to_news(bot, message, "whale")
    
    async def post_new_pool_alert(self, bot: Bot, pool: Dict):
        """Post new pool discovered alert"""
        symbol = pool.get("symbol", "?")
        project = pool.get("project", "?")
        chain = pool.get("chain", "?")
        apy = pool.get("apy", 0)
        tvl = pool.get("tvl", 0)
        
        tvl_str = f"${tvl/1_000_000:.1f}M" if tvl >= 1_000_000 else f"${tvl/1_000:.0f}K"
        
        message = f"""
🆕 *NEW POOL*

*{symbol}*
{project} • {chain}

📈 APY: {apy:.1f}%
💰 TVL: {tvl_str}

_Use /pools to explore_
"""
        await self.post_to_news(bot, message, "new_pool")
    
    async def post_security_alert(self, bot: Bot, title: str, details: str, severity: str = "warning"):
        """Post security alert"""
        emoji = "🔴" if severity == "critical" else "⚠️"
        
        message = f"""
{emoji} *SECURITY ALERT*

*{title}*

{details}

⚠️ _Always verify URLs before connecting wallet!_
"""
        await self.post_to_news(bot, message, "security")
    
    async def post_daily_summary(self, bot: Bot):
        """Post daily market summary (pinned to channel)"""
        message = f"""
📊 *DAILY SUMMARY*
{datetime.utcnow().strftime('%Y-%m-%d')}

━━━ *Market Overview* ━━━
• Total DeFi TVL: $85B
• Top gainers: AERO +15%, PENDLE +8%
• Gas: ETH 25 gwei, Base <0.01

━━━ *Airdrop Updates* ━━━
• Berachain mainnet approaching
• Scroll activity increasing
• Symbiotic deposits growing

━━━ *Top Yields Today* ━━━
• Aerodrome USDC/WETH: 45%
• Morpho USDC: 12%
• Pendle YT pools: 20%+

_Use /alpha for full alpha feed_
📌 _This summary is pinned daily_
"""
        # Post and pin the summary
        await self.post_to_channel(bot, self.channel_news, message, "daily_summary", pin=True)


# Global instance
channel_poster = ChannelPoster()
