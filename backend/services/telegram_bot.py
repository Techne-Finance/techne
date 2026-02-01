"""
Techne Artisan Bot - Telegram Integration
AI-powered DeFi assistant using Kimi K2.5

Commands:
- /start - Activate with code or show welcome
- /mode - Change autonomy mode
- /status - Portfolio summary
- /disconnect - Cancel subscription
- Natural language → Kimi K2.5 processing
"""

import os
import logging
import asyncio
from typing import Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import httpx

from services.kimi_client import get_kimi_client, ARTISAN_TOOLS

logger = logging.getLogger("ArtisanBot")

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_ARTISAN_BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


class ArtisanBot:
    """Telegram bot for Artisan Agent"""
    
    def __init__(self):
        if not TELEGRAM_BOT_TOKEN:
            logger.warning("TELEGRAM_ARTISAN_BOT_TOKEN not set")
            self.app = None
            return
        
        self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.kimi = get_kimi_client()
        self.http = httpx.AsyncClient(base_url=BACKEND_URL, timeout=30.0)
        
        # Conversation history per chat
        self.conversations: dict = {}
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register command and message handlers"""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("mode", self.mode_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(CommandHandler("disconnect", self.disconnect_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command with optional activation code"""
        chat_id = update.effective_chat.id
        args = context.args
        
        # Check if already connected
        sub = await self._get_subscription(chat_id)
        if sub and sub.get("found"):
            await update.message.reply_text(
                f"✅ Already connected!\n\n"
                f"Wallet: `{sub['user_address'][:10]}...`\n"
                f"Mode: {sub['autonomy_mode'].upper()}\n"
                f"Expires: {sub['expires_at'][:10]}\n\n"
                f"Send me any message or use /help",
                parse_mode="Markdown"
            )
            return
        
        # Check for activation code in args
        if args:
            code = args[0].upper()
            success = await self._validate_code(code, chat_id, update.effective_user.username)
            
            if success.get("success"):
                # Show mode selection
                keyboard = [
                    [InlineKeyboardButton("👁️ Observer (View Only)", callback_data="mode_observer")],
                    [InlineKeyboardButton("💡 Advisor (Suggest + Confirm)", callback_data="mode_advisor")],
                    [InlineKeyboardButton("🤝 Co-pilot (Auto < $1000)", callback_data="mode_copilot")],
                    [InlineKeyboardButton("🤖 Full Auto (All Autonomous)", callback_data="mode_full_auto")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"🎉 *Welcome to Artisan Agent!*\n\n"
                    f"Your wallet: `{success['user_address'][:10]}...`\n\n"
                    f"Choose your autonomy mode:",
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    f"❌ Invalid code: {success.get('error', 'Unknown error')}\n\n"
                    f"Please check your code and try again:\n"
                    f"`/start YOUR-CODE-HERE`",
                    parse_mode="Markdown"
                )
            return
        
        # No code provided - show instructions
        await update.message.reply_text(
            "🤖 *Techne Artisan Agent*\n\n"
            "Your personal AI DeFi assistant.\n\n"
            "*To activate:*\n"
            "1. Subscribe at techne.finance/premium\n"
            "2. Copy your activation code\n"
            "3. Send: `/start ARTISAN-XXXX-XXXX`\n\n"
            "*Already have a code?*\n"
            "Just send it as a message!",
            parse_mode="Markdown"
        )
    
    async def mode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show mode selection menu"""
        chat_id = update.effective_chat.id
        
        sub = await self._get_subscription(chat_id)
        if not sub or not sub.get("found"):
            await update.message.reply_text("❌ Not connected. Use /start with your activation code.")
            return
        
        current_mode = sub.get("autonomy_mode", "advisor")
        
        keyboard = [
            [InlineKeyboardButton(
                f"{'✓ ' if current_mode == 'observer' else ''}👁️ Observer",
                callback_data="mode_observer"
            )],
            [InlineKeyboardButton(
                f"{'✓ ' if current_mode == 'advisor' else ''}💡 Advisor",
                callback_data="mode_advisor"
            )],
            [InlineKeyboardButton(
                f"{'✓ ' if current_mode == 'copilot' else ''}🤝 Co-pilot",
                callback_data="mode_copilot"
            )],
            [InlineKeyboardButton(
                f"{'✓ ' if current_mode == 'full_auto' else ''}🤖 Full Auto",
                callback_data="mode_full_auto"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        mode_descriptions = {
            "observer": "View & analyze only. All actions need your approval.",
            "advisor": "I suggest actions and wait for your OK before executing.",
            "copilot": "I auto-execute trades under $1000. Larger ones need your OK.",
            "full_auto": "Full autonomy within your guidelines. I handle everything."
        }
        
        await update.message.reply_text(
            f"*Current mode: {current_mode.upper()}*\n"
            f"_{mode_descriptions[current_mode]}_\n\n"
            f"Select a new mode:",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show portfolio status"""
        chat_id = update.effective_chat.id
        
        sub = await self._get_subscription(chat_id)
        if not sub or not sub.get("found"):
            await update.message.reply_text("❌ Not connected. Use /start with your activation code.")
            return
        
        await update.message.reply_text("📊 Fetching portfolio...")
        
        # Get portfolio from backend
        try:
            response = await self.http.get(
                f"/api/portfolio",
                params={"wallet_address": sub["user_address"]}
            )
            portfolio = response.json()
            
            # Use Kimi to summarize
            summary = await self.kimi.analyze_portfolio(
                positions=portfolio.get("positions", [])
            )
            
            await update.message.reply_text(
                f"*📈 Portfolio Summary*\n\n"
                f"Total Value: ${summary.get('total_value_usd', 0):,.2f}\n"
                f"Daily Yield: ${summary.get('total_daily_yield_usd', 0):,.2f}\n"
                f"Risk Score: {summary.get('risk_score', 'N/A')}/100\n\n"
                f"{summary.get('summary', 'Analysis complete.')}\n\n"
                f"_Mode: {sub['autonomy_mode'].upper()}_",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Status error: {e}")
            await update.message.reply_text(f"❌ Error fetching portfolio: {e}")
    
    async def disconnect_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Disconnect subscription"""
        chat_id = update.effective_chat.id
        
        sub = await self._get_subscription(chat_id)
        if not sub or not sub.get("found"):
            await update.message.reply_text("❌ Not connected.")
            return
        
        keyboard = [
            [InlineKeyboardButton("Yes, disconnect", callback_data="confirm_disconnect")],
            [InlineKeyboardButton("Cancel", callback_data="cancel_disconnect")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚠️ *Are you sure you want to disconnect?*\n\n"
            "This will cancel your subscription.\n"
            "You can resubscribe anytime at techne.finance/premium",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help"""
        await update.message.reply_text(
            "*🤖 Artisan Agent Help*\n\n"
            "*Commands:*\n"
            "/status - Portfolio summary\n"
            "/mode - Change autonomy mode\n"
            "/disconnect - Cancel subscription\n\n"
            "*Natural language:*\n"
            "Just type what you want!\n\n"
            "Examples:\n"
            "• \"Show me my positions\"\n"
            "• \"Find pools with 10%+ APY on Base\"\n"
            "• \"Analyze if I should exit Aerodrome\"\n"
            "• \"Move 50% to Aave USDC\"\n"
            "• \"Send me a daily report\"\n\n"
            "_Your mode determines what I can do automatically._",
            parse_mode="Markdown"
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button clicks"""
        query = update.callback_query
        await query.answer()
        
        chat_id = query.message.chat_id
        data = query.data
        
        if data.startswith("mode_"):
            mode = data.replace("mode_", "")
            sub = await self._get_subscription(chat_id)
            
            if sub and sub.get("found"):
                # Change mode
                await self._change_mode(sub["user_address"], mode)
                
                mode_emojis = {
                    "observer": "👁️",
                    "advisor": "💡",
                    "copilot": "🤝",
                    "full_auto": "🤖"
                }
                
                await query.edit_message_text(
                    f"{mode_emojis.get(mode, '🤖')} *Mode set to: {mode.upper()}*\n\n"
                    f"I'm ready! Send me a message or use /help",
                    parse_mode="Markdown"
                )
        
        elif data == "confirm_disconnect":
            sub = await self._get_subscription(chat_id)
            if sub and sub.get("found"):
                await self._disconnect(sub["user_address"])
                await query.edit_message_text(
                    "👋 Disconnected.\n\nResubscribe anytime at techne.finance/premium"
                )
        
        elif data == "cancel_disconnect":
            await query.edit_message_text("✅ Cancelled. Still connected!")
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle natural language messages"""
        chat_id = update.effective_chat.id
        text = update.message.text.strip()
        
        # Check for activation code pattern
        if text.upper().startswith("ARTISAN-"):
            await self.start_command(update, context)
            context.args = [text]
            return
        
        # Check subscription
        sub = await self._get_subscription(chat_id)
        if not sub or not sub.get("found"):
            # Try to validate as code
            if "-" in text and len(text) > 10:
                result = await self._validate_code(text.upper(), chat_id, update.effective_user.username)
                if result.get("success"):
                    await update.message.reply_text(
                        "✅ Code validated! Use /mode to select your autonomy level."
                    )
                    return
            
            await update.message.reply_text(
                "❌ Not connected. Send `/start ARTISAN-XXXX-XXXX` with your code.",
                parse_mode="Markdown"
            )
            return
        
        # Get/create conversation history
        if chat_id not in self.conversations:
            self.conversations[chat_id] = []
        
        # Add user message
        self.conversations[chat_id].append({
            "role": "user",
            "content": text
        })
        
        # Show typing indicator
        await update.message.chat.send_action("typing")
        
        # Process with Kimi
        try:
            user_context = {
                "wallet_address": sub["user_address"],
                "autonomy_mode": sub["autonomy_mode"],
                "portfolio_value": 0  # TODO: Get from portfolio API
            }
            
            response = await self.kimi.process_command(
                user_message=text,
                conversation_history=self.conversations[chat_id],
                tools=ARTISAN_TOOLS,
                user_context=user_context
            )
            
            # Handle tool calls
            if response.get("tool_calls"):
                # Execute tools and respond
                results = await self._execute_tools(
                    response["tool_calls"],
                    sub["user_address"],
                    sub["autonomy_mode"]
                )
                
                # Let Kimi summarize results
                self.conversations[chat_id].append({
                    "role": "assistant",
                    "content": response.get("content", ""),
                    "tool_calls": response["tool_calls"]
                })
                self.conversations[chat_id].append({
                    "role": "tool",
                    "content": str(results)
                })
                
                # Get final response
                final_response = await self.kimi.chat(
                    self.conversations[chat_id],
                    temperature=0.7
                )
                reply_text = final_response.get("content", "Done!")
            else:
                reply_text = response.get("content", "I'm not sure how to help with that.")
            
            # Add to history
            self.conversations[chat_id].append({
                "role": "assistant",
                "content": reply_text
            })
            
            # Keep history manageable
            if len(self.conversations[chat_id]) > 20:
                self.conversations[chat_id] = self.conversations[chat_id][-20:]
            
            await update.message.reply_text(reply_text)
            
        except Exception as e:
            logger.error(f"Message processing error: {e}")
            await update.message.reply_text(
                f"❌ Error processing request: {str(e)[:100]}"
            )
    
    async def _get_subscription(self, chat_id: int) -> Optional[dict]:
        """Get subscription by chat ID"""
        try:
            response = await self.http.get(
                "/api/premium/subscription-by-chat",
                params={"chat_id": chat_id}
            )
            return response.json()
        except Exception as e:
            logger.error(f"Get subscription error: {e}")
            return None
    
    async def _validate_code(self, code: str, chat_id: int, username: str) -> dict:
        """Validate activation code"""
        try:
            response = await self.http.post(
                "/api/premium/validate-code",
                json={
                    "activation_code": code,
                    "telegram_chat_id": chat_id,
                    "telegram_username": username
                }
            )
            return response.json()
        except Exception as e:
            logger.error(f"Validate code error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _change_mode(self, user_address: str, mode: str):
        """Change autonomy mode"""
        try:
            await self.http.post(
                "/api/premium/change-mode",
                json={"user_address": user_address, "mode": mode}
            )
        except Exception as e:
            logger.error(f"Change mode error: {e}")
    
    async def _disconnect(self, user_address: str):
        """Disconnect subscription"""
        try:
            await self.http.post(
                "/api/premium/disconnect",
                json={"user_address": user_address}
            )
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
    
    async def _execute_tools(
        self,
        tool_calls: list,
        user_address: str,
        autonomy_mode: str
    ) -> list:
        """Execute tool calls from Kimi"""
        results = []
        
        for call in tool_calls:
            func_name = call.get("function", {}).get("name")
            args = call.get("function", {}).get("arguments", "{}")
            
            try:
                import json
                args = json.loads(args) if isinstance(args, str) else args
            except:
                args = {}
            
            logger.info(f"Executing tool: {func_name} with args: {args}")
            
            # Check autonomy for action tools
            action_tools = ["execute_trade", "exit_position", "emergency_exit_all"]
            if func_name in action_tools:
                if autonomy_mode == "observer":
                    results.append({
                        "tool": func_name,
                        "result": "Action blocked - Observer mode. Switch to Advisor or higher to enable actions."
                    })
                    continue
                
                if autonomy_mode == "advisor":
                    results.append({
                        "tool": func_name,
                        "result": "Action requires confirmation in Advisor mode. (Not implemented yet)"
                    })
                    continue
                
                if autonomy_mode == "copilot" and func_name == "execute_trade":
                    amount = args.get("amount_usd", 0)
                    if amount > 1000:
                        results.append({
                            "tool": func_name,
                            "result": f"Trade of ${amount} requires confirmation in Co-pilot mode (>$1000 threshold)."
                        })
                        continue
            
            # Execute tool via backend API
            try:
                if func_name == "analyze_portfolio":
                    response = await self.http.get(
                        "/api/portfolio",
                        params={"wallet_address": user_address}
                    )
                    results.append({"tool": func_name, "result": response.json()})
                
                elif func_name == "find_pools":
                    response = await self.http.post(
                        "/api/artisan/scout",
                        params=args
                    )
                    results.append({"tool": func_name, "result": response.json()})
                
                elif func_name == "execute_trade":
                    # This would call the actual trading endpoint
                    results.append({
                        "tool": func_name,
                        "result": f"Trade execution: {args} - To be implemented"
                    })
                
                elif func_name == "get_market_sentiment":
                    results.append({
                        "tool": func_name,
                        "result": {
                            "sentiment": "neutral",
                            "btc_dominance": "52%",
                            "fear_greed_index": 55,
                            "note": "Market conditions are stable"
                        }
                    })
                
                else:
                    results.append({
                        "tool": func_name,
                        "result": f"Tool not yet implemented: {func_name}"
                    })
                    
            except Exception as e:
                results.append({
                    "tool": func_name,
                    "error": str(e)
                })
        
        return results
    
    async def start(self):
        """Start the bot"""
        if not self.app:
            logger.error("Bot not initialized - missing token")
            return
        
        logger.info("Starting Artisan Bot...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        logger.info("Artisan Bot started!")
    
    async def stop(self):
        """Stop the bot"""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            await self.http.aclose()


# Singleton
_artisan_bot: Optional[ArtisanBot] = None

def get_artisan_bot() -> ArtisanBot:
    """Get or create Artisan Bot singleton"""
    global _artisan_bot
    if _artisan_bot is None:
        _artisan_bot = ArtisanBot()
    return _artisan_bot


# Entry point for running standalone
if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    async def main():
        bot = get_artisan_bot()
        await bot.start()
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await bot.stop()
    
    asyncio.run(main())
