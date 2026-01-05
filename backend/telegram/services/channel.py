"""
Techne Telegram Bot - Premium Channel Access Service
Manages access to premium-only Telegram channel
"""

import logging
from typing import Optional, List
from datetime import datetime, timedelta
from aiogram import Bot

from ..models.user_config import user_store, UserConfig

logger = logging.getLogger(__name__)

# Premium Channel Configuration
CHANNEL_NEWS = "-1003570137448"      # Techne News Feed
CHANNEL_AIRDROPS = "-1003544179066"  # Techne Airdrops


class PremiumChannelManager:
    """
    Manages access to premium-only Telegram channels
    
    Features:
    - Generate one-time invite links for premium users
    - Verify premium status before granting access
    - Daily check to remove expired premium users
    """
    
    def __init__(self):
        self.channel_news = CHANNEL_NEWS
        self.channel_airdrops = CHANNEL_AIRDROPS
        self._invite_cache = {}  # telegram_id -> {news: link, airdrops: link}
    
    async def check_premium_status(self, telegram_id: int) -> dict:
        """
        Check if user has valid premium status
        Returns: {is_premium: bool, expires: str, days_left: int}
        """
        config = await user_store.get_or_create_config(telegram_id)
        
        if not config.is_premium:
            return {"is_premium": False, "expires": None, "days_left": 0}
        
        # Check expiration
        if config.premium_expires:
            try:
                expires = datetime.fromisoformat(config.premium_expires.replace('Z', '+00:00'))
                now = datetime.utcnow().replace(tzinfo=expires.tzinfo) if expires.tzinfo else datetime.utcnow()
                
                if expires < now:
                    # Premium expired
                    config.is_premium = False
                    await user_store.save_config(config)
                    return {"is_premium": False, "expires": config.premium_expires, "days_left": 0, "expired": True}
                
                days_left = (expires - now).days
                return {
                    "is_premium": True,
                    "expires": config.premium_expires,
                    "days_left": days_left
                }
            except Exception as e:
                logger.error(f"Error parsing expiration: {e}")
        
        # Premium without expiration (lifetime or error)
        return {"is_premium": True, "expires": None, "days_left": 999}
    
    async def generate_invite_links(self, bot: Bot, telegram_id: int) -> dict:
        """
        Generate invite links for both premium channels
        Returns: {success: bool, news_link: str, airdrops_link: str, error: str}
        """
        # Verify premium status
        status = await self.check_premium_status(telegram_id)
        
        if not status["is_premium"]:
            if status.get("expired"):
                return {
                    "success": False,
                    "error": "Your premium subscription has expired.\n\nRenew at: https://techne.finance/premium"
                }
            return {
                "success": False,
                "error": "Premium subscription required.\n\nSubscribe at: https://techne.finance/premium"
            }
        
        # Check cache
        if telegram_id in self._invite_cache:
            cached = self._invite_cache[telegram_id]
            return {
                "success": True,
                "news_link": cached.get("news"),
                "airdrops_link": cached.get("airdrops"),
                "cached": True,
                "premium_days_left": status["days_left"]
            }
        
        try:
            links = {}
            
            # Generate news channel invite
            news_invite = await bot.create_chat_invite_link(
                chat_id=self.channel_news,
                expire_date=datetime.utcnow() + timedelta(hours=24),
                member_limit=1,
                name=f"News_{telegram_id}"
            )
            links["news"] = news_invite.invite_link
            
            # Generate airdrops channel invite
            airdrops_invite = await bot.create_chat_invite_link(
                chat_id=self.channel_airdrops,
                expire_date=datetime.utcnow() + timedelta(hours=24),
                member_limit=1,
                name=f"Airdrops_{telegram_id}"
            )
            links["airdrops"] = airdrops_invite.invite_link
            
            self._invite_cache[telegram_id] = links
            logger.info(f"Generated invite links for user {telegram_id}")
            
            return {
                "success": True,
                "news_link": links["news"],
                "airdrops_link": links["airdrops"],
                "expires_hours": 24,
                "premium_days_left": status["days_left"]
            }
            
        except Exception as e:
            logger.error(f"Failed to create invite links: {e}")
            return {"success": False, "error": f"Failed to generate invites: {str(e)}"}
    
    def format_channel_info(self) -> str:
        """Format channel info message"""
        return """
📢 *Techne Premium Channels*

Exclusive real-time alerts for premium subscribers:

━━━ *📰 News Feed Channel* ━━━
• Breaking DeFi & macro news
• Whale movement alerts
• Security warnings
• New pool discoveries

━━━ *🎁 Airdrops Channel* ━━━
• Airdrop opportunity alerts
• Points program updates
• Snapshot announcements
• Farming strategies

━━━━━━━━━━━━━━━━━━━━

📋 *How to join:*
Use /joinchannel to get invite links

💎 *$10/month* - Cancel anytime
"""


# Global instance
channel_manager = PremiumChannelManager()

