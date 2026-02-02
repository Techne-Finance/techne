"""
Techne Telegram Bot - Main Bot Module
Initializes and runs the bot with all handlers
"""

import os
import asyncio
import logging
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from .handlers import commands, filters
from .models.user_config import user_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TechneBot:
    """
    Main Techne Telegram Bot class
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the bot with token from env or parameter
        """
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        
        if not self.token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN not set. "
                "Create a bot via @BotFather and set the token."
            )
        
        # Initialize bot with markdown parsing by default
        self.bot = Bot(
            token=self.token,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
        )
        
        self.dp = Dispatcher()
        self._setup_handlers()
        
        logger.info("🤖 Techne Bot initialized")
    
    def _setup_handlers(self):
        """
        Register all command and callback handlers.
        Only attach once to prevent 'Router already attached' error.
        """
        # Check if already set up (prevent duplicate attachment)
        if hasattr(self, '_handlers_setup') and self._handlers_setup:
            return
        
        try:
            # Include command handlers
            self.dp.include_router(commands.router)
            
            # Include filter configuration handlers
            self.dp.include_router(filters.router)
            
            # Include advanced premium handlers
            try:
                from .handlers import advanced
                self.dp.include_router(advanced.router)
                logger.info("📋 Advanced handlers registered")
            except ImportError as e:
                logger.warning(f"Advanced handlers not available: {e}")
            
            self._handlers_setup = True
            logger.info("📋 Handlers registered")
        except RuntimeError as e:
            # Router already attached - this is okay, just log and continue
            if "already attached" in str(e):
                self._handlers_setup = True
                logger.debug("Handlers already attached, skipping")
            else:
                raise
    
    async def _init_database(self):
        """
        Initialize database for user configs
        """
        await user_store.init_db()
        logger.info("🗄️ Database initialized")
    
    async def start(self):
        """
        Start the bot (polling mode)
        """
        await self._init_database()
        
        logger.info("🚀 Starting Techne Bot...")
        
        # Delete webhook if any (for clean polling)
        await self.bot.delete_webhook(drop_pending_updates=True)
        
        # Start polling
        await self.dp.start_polling(self.bot)
    
    async def stop(self):
        """
        Stop the bot gracefully
        """
        logger.info("🛑 Stopping Techne Bot...")
        await self.bot.session.close()
    
    async def send_alert(self, telegram_id: int, message: str):
        """
        Send an alert message to a user
        """
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"📤 Alert sent to {telegram_id}")
        except Exception as e:
            logger.error(f"Failed to send alert to {telegram_id}: {e}")
    
    async def broadcast(self, message: str, premium_only: bool = False):
        """
        Broadcast message to all users
        """
        if premium_only:
            users = await user_store.get_premium_users()
        else:
            users = await user_store.get_all_with_alerts()
        
        sent = 0
        for user in users:
            try:
                await self.bot.send_message(
                    chat_id=user.telegram_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
                sent += 1
                # Rate limit
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.warning(f"Failed to send to {user.telegram_id}: {e}")
        
        logger.info(f"📢 Broadcast sent to {sent}/{len(users)} users")
        return sent


# Global bot instance (lazy initialized)
_bot_instance: Optional[TechneBot] = None


def get_bot() -> TechneBot:
    """
    Get or create the global bot instance
    """
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = TechneBot()
    return _bot_instance


async def run_bot():
    """
    Run the bot (entry point)
    """
    bot = get_bot()
    try:
        await bot.start()
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(run_bot())
