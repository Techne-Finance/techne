"""
Techne Bot - Entry Point
Run this script to start the Telegram bot
"""

import asyncio
import logging
import os
import sys

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, use env vars directly

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram.bot import TechneBot
from telegram.scheduler import alert_scheduler, set_scheduler_bot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """
    Main entry point
    """
    # Check for token
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        logger.error(
            "\n" + "=" * 50 + "\n"
            "❌ TELEGRAM_BOT_TOKEN not set!\n\n"
            "To get a token:\n"
            "1. Open Telegram and message @BotFather\n"
            "2. Send /newbot\n"
            "3. Follow the prompts to create your bot\n"
            "4. Copy the token and set it:\n\n"
            "   Windows: set TELEGRAM_BOT_TOKEN=your_token\n"
            "   Linux/Mac: export TELEGRAM_BOT_TOKEN=your_token\n"
            "   Or add to .env file\n"
            + "=" * 50
        )
        return
    
    logger.info("🏛️ Starting Techne Telegram Bot...")
    
    # Initialize bot
    bot = TechneBot(token)
    
    # Set bot instance for scheduler jobs (prevents router re-attach error)
    set_scheduler_bot(bot.bot)
    
    # Start scheduler
    alert_scheduler.start()
    
    try:
        # Run bot
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        # Cleanup
        alert_scheduler.stop()
        await bot.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")
