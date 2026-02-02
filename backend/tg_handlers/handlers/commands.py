"""
Techne Telegram Bot - Command Handlers
Handles /start, /help, /pools, /agent, etc.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode

from ..models.user_config import user_store, UserConfig
from ..services.pools import fetch_pools, format_pool_list, format_pool_detail, format_filters_summary
from ..services.agent_status import (
    get_agent_status, 
    get_agent_positions, 
    format_agent_status, 
    format_agent_positions,
    format_agent_summary
)

router = Router()


# ===========================================
# /start - Welcome message
# ===========================================

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Welcome message for new users"""
    telegram_id = message.from_user.id
    username = message.from_user.first_name or "Anon"
    
    # Create or get user config
    config = await user_store.get_or_create_config(telegram_id)
    
    if config.is_premium:
        # Premium user - full access
        welcome_text = f"""
🏛️ *Welcome back, {username}!*

💎 Premium Access: *Active*

━━━━━━━━━━━━━━━━━━━━

🔥 *Quick Actions:*
• /pools - Top yield opportunities
• /myconfig - Your filter settings
• /alerts - Toggle notifications

📊 Real-time alerts are {'✅ ON' if config.alerts_enabled else '❌ OFF'}

_Powered by 9 specialized AI Agents_
"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 View Pools", callback_data="cmd_pools"),
                InlineKeyboardButton(text="⚙️ My Filters", callback_data="cmd_config")
            ],
            [
                InlineKeyboardButton(text="🔔 Toggle Alerts", callback_data="toggle_alerts"),
                InlineKeyboardButton(text="📚 Help", callback_data="show_help")
            ],
            [
                InlineKeyboardButton(text="🎁 Airdrops Channel", url="https://t.me/+zUrkLNO2M_9lODc0")
            ]
        ])
    else:
        # Non-premium user - prompt to upgrade
        welcome_text = f"""
🏛️ *Welcome to Techne, {username}!*

This bot is available for *Premium subscribers* only.

━━━━━━━━━━━━━━━━━━━━

💎 *Premium Features:*
• Real-time APY spike alerts
• TVL change notifications
• Whale movement tracking
• AI-powered yield discovery
• Risk level warnings

━━━━━━━━━━━━━━━━━━━━

*Price:* 10 USDC/month

Subscribe at techne.finance, then use your code here:
/activate [YOUR_CODE]
"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💎 Get Premium", url="https://techne.finance/premium")
            ],
            [
                InlineKeyboardButton(text="🔑 I have a code", callback_data="enter_code")
            ]
        ])
    
    await message.answer(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


# ===========================================
# /help - Command reference
# ===========================================

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Show all available commands"""
    help_text = """
📚 *Techne Bot Commands*

━━━━ *Discovery* ━━━━
/pools - View top pools matching your filters
/pool [id] - Detailed pool analysis
/search [query] - Search pools by name

━━━━ *Filters* ━━━━
/myconfig - View current filters
/setchain [chain] - Set chain filter
/setmintvl [amount] - Min TVL ($)
/setminapy [percent] - Min APY (%)
/setrisk [level] - Risk tolerance
/setprotocols [list] - Protocol whitelist
/reset - Reset all filters

━━━━ *Alerts* ━━━━
/alerts - Toggle alerts on/off
/setapyalert [%] - APY spike threshold
/settvlalert [%] - TVL change threshold

━━━━ *Agent* ━━━━
/agent - View agent status
/positions - Current positions
/history - Recent transactions

━━━━ *Premium* ━━━━
/premium - Check subscription
/whale - Whale movements (Premium)

━━━━ *Other* ━━━━
/gas - Current gas prices
/stats - Market statistics
"""
    await message.answer(help_text, parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /pools - View top pools
# ===========================================

@router.message(Command("pools"))
async def cmd_pools(message: Message):
    """Get top pools based on user filters"""
    telegram_id = message.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    
    # Premium check
    if not config.is_premium:
        await message.answer(
            "🔒 *Premium Required*\n\n"
            "Pool discovery requires Premium access.\n\n"
            "Subscribe at: https://techne.finance/premium\n"
            "Then: /activate [CODE]",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    await message.answer("🔍 Scanning protocols...")
    
    pools = await fetch_pools(config, limit=10)
    
    # Store pools in context for /pool command
    if pools:
        # Save to user session (simplified - in production use Redis)
        config._last_pools = pools
        await user_store.save_config(config)
    
    response = format_pool_list(pools, "🔥 Top Yield Opportunities")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_pools"),
            InlineKeyboardButton(text="⚙️ Filters", callback_data="cmd_config")
        ]
    ])
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


@router.callback_query(F.data == "cmd_pools")
async def callback_pools(callback: CallbackQuery):
    await callback.answer()
    telegram_id = callback.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    
    pools = await fetch_pools(config, limit=10)
    response = format_pool_list(pools, "🔥 Top Yield Opportunities")
    
    await callback.message.edit_text(response, parse_mode=ParseMode.MARKDOWN)


@router.callback_query(F.data == "refresh_pools")
async def callback_refresh_pools(callback: CallbackQuery):
    await callback.answer("🔄 Refreshing...")
    telegram_id = callback.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    
    pools = await fetch_pools(config, limit=10)
    response = format_pool_list(pools, "🔥 Top Yield Opportunities")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_pools"),
            InlineKeyboardButton(text="⚙️ Filters", callback_data="cmd_config")
        ]
    ])
    
    await callback.message.edit_text(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


# ===========================================
# /pool [id] - Pool details
# ===========================================

@router.message(Command("pool"))
async def cmd_pool_detail(message: Message):
    """Get detailed pool info"""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer(
            "Usage: /pool [pool_id or number]\n\n"
            "Example: /pool 1 (for first pool from /pools)"
        )
        return
    
    pool_ref = args[1].strip()
    
    # Try to get from last pools list by number
    telegram_id = message.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    
    pool = None
    
    # If it's a number, get from last search
    if pool_ref.isdigit():
        idx = int(pool_ref) - 1
        last_pools = getattr(config, '_last_pools', None)
        if last_pools and 0 <= idx < len(last_pools):
            pool = last_pools[idx]
    
    if not pool:
        await message.answer("❌ Pool not found. Run /pools first.")
        return
    
    response = format_pool_detail(pool)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📥 Deposit via Agent", callback_data=f"deposit_{pool.get('pool', '')[:20]}"),
            InlineKeyboardButton(text="🔙 Back to List", callback_data="cmd_pools")
        ]
    ])
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


# ===========================================
# /myconfig - View current filters
# ===========================================

@router.message(Command("myconfig"))
async def cmd_myconfig(message: Message):
    """Show current user configuration"""
    telegram_id = message.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    
    response = format_filters_summary(config)
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN)


@router.callback_query(F.data == "cmd_config")
async def callback_config(callback: CallbackQuery):
    await callback.answer()
    telegram_id = callback.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    
    response = format_filters_summary(config)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔙 Back", callback_data="cmd_pools")
        ]
    ])
    
    await callback.message.edit_text(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


# ===========================================
# /agent - Agent status
# ===========================================

@router.message(Command("agent"))
async def cmd_agent(message: Message):
    """Show AI Agent status"""
    telegram_id = message.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    
    if not config.wallet_address:
        await message.answer(
            "🔗 *Connect Your Wallet*\n\n"
            "To view your AI Agent status, first connect your wallet:\n"
            "1. Go to https://techne.finance\n"
            "2. Connect wallet\n"
            "3. Use /connect [wallet_address] here",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    status = await get_agent_status(config.wallet_address)
    response = format_agent_status(status, config.wallet_address)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Positions", callback_data="agent_positions"),
            InlineKeyboardButton(text="📜 History", callback_data="agent_history")
        ],
        [
            InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_agent")
        ]
    ])
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


@router.callback_query(F.data == "cmd_agent")
async def callback_agent(callback: CallbackQuery):
    await callback.answer()
    telegram_id = callback.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    
    if not config.wallet_address:
        await callback.message.edit_text(
            "🔗 Connect your wallet first via /connect [address]",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    status = await get_agent_status(config.wallet_address)
    response = format_agent_status(status, config.wallet_address)
    
    await callback.message.edit_text(response, parse_mode=ParseMode.MARKDOWN)


@router.callback_query(F.data == "agent_positions")
async def callback_agent_positions(callback: CallbackQuery):
    await callback.answer()
    telegram_id = callback.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    
    if not config.wallet_address:
        return
    
    positions = await get_agent_positions(config.wallet_address)
    response = format_agent_positions(positions)
    
    await callback.message.edit_text(response, parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /positions - Agent positions
# ===========================================

@router.message(Command("positions"))
async def cmd_positions(message: Message):
    """Show agent positions"""
    telegram_id = message.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    
    if not config.wallet_address:
        await message.answer("Connect wallet first: /connect [address]")
        return
    
    positions = await get_agent_positions(config.wallet_address)
    response = format_agent_positions(positions)
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /connect - Connect wallet
# ===========================================

@router.message(Command("connect"))
async def cmd_connect(message: Message):
    """Connect wallet address"""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer(
            "Usage: /connect [wallet_address]\n\n"
            "Example: /connect 0x1234...abcd"
        )
        return
    
    wallet = args[1].strip()
    
    # Basic validation
    if not wallet.startswith("0x") or len(wallet) != 42:
        await message.answer("❌ Invalid wallet address. Must be 0x... (42 chars)")
        return
    
    telegram_id = message.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    config.wallet_address = wallet
    await user_store.save_config(config)
    
    await message.answer(
        f"✅ *Wallet Connected!*\n\n"
        f"`{wallet[:10]}...{wallet[-6:]}`\n\n"
        f"You can now:\n"
        f"• /agent - View agent status\n"
        f"• /positions - See positions\n"
        f"• Receive agent notifications",
        parse_mode=ParseMode.MARKDOWN
    )


# ===========================================
# /alerts - Toggle alerts
# ===========================================

@router.message(Command("alerts"))
async def cmd_alerts(message: Message):
    """Toggle alerts on/off"""
    telegram_id = message.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    
    # Toggle
    config.alerts_enabled = not config.alerts_enabled
    await user_store.save_config(config)
    
    status = "✅ Enabled" if config.alerts_enabled else "❌ Disabled"
    
    await message.answer(
        f"🔔 *Alerts: {status}*\n\n"
        f"APY Spike Threshold: +{config.apy_spike_threshold}%\n"
        f"TVL Change Threshold: ±{config.tvl_change_threshold}%\n\n"
        f"Use /setapyalert and /settvlalert to customize.",
        parse_mode=ParseMode.MARKDOWN
    )


# ===========================================
# /premium - Premium status
# ===========================================

@router.message(Command("premium"))
async def cmd_premium(message: Message):
    """Check premium status"""
    telegram_id = message.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    
    if config.is_premium:
        await message.answer(
            "💎 *Premium Active*\n\n"
            f"Wallet: `{config.wallet_address[:10]}...`\n"
            f"Expires: {config.premium_expires or 'Never'}\n\n"
            "Premium features:\n"
            "• 🐋 Whale alerts\n"
            "• 📊 Advanced analytics\n"
            "• ⚡ Priority notifications\n"
            "• 🎯 Smart strategy suggestions",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Upgrade to Premium", url="https://techne.finance/premium")]
        ])
        
        await message.answer(
            "💎 *Premium Access*\n\n"
            "Unlock advanced features:\n"
            "• 🐋 Real-time whale alerts\n"
            "• 📊 Advanced AI analytics\n"
            "• ⚡ Priority notifications\n"
            "• 🎯 Smart strategy suggestions\n\n"
            "*Price:* 10 USDC/month\n\n"
            "Subscribe via the Techne web app.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )


@router.callback_query(F.data == "cmd_premium")
async def callback_premium(callback: CallbackQuery):
    await callback.answer()
    telegram_id = callback.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    
    if config.is_premium:
        text = "💎 *Premium Active*\n\nEnjoy all premium features!"
    else:
        text = "💎 Upgrade at https://techne.finance/premium"
    
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /gas - Gas prices
# ===========================================

@router.message(Command("gas"))
async def cmd_gas(message: Message):
    """Show current gas prices"""
    # In production, fetch real gas prices
    await message.answer(
        "⛽ *Gas Prices*\n\n"
        "🔵 *Base*: ~0.001 gwei (very cheap)\n"
        "⟠ *Ethereum*: ~25 gwei\n"
        "🔷 *Arbitrum*: ~0.1 gwei\n"
        "🟣 *Solana*: 0.000005 SOL\n\n"
        "_Prices update every minute_",
        parse_mode=ParseMode.MARKDOWN
    )


# ===========================================
# /stats - Market statistics
# ===========================================

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Show market statistics"""
    await message.answer(
        "📊 *Techne Market Stats*\n\n"
        "Total TVL Tracked: *$2.5B*\n"
        "Active Pools: *847*\n"
        "24h Volume: *$143M*\n"
        "Avg APY: *13.7%*\n"
        "Active Users: *12.4K*\n\n"
        "_Updated in real-time_",
        parse_mode=ParseMode.MARKDOWN
    )


# ===========================================
# /activate - Activate premium with code
# ===========================================

@router.message(Command("activate"))
async def cmd_activate(message: Message):
    """Activate premium subscription with code"""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer(
            "🔑 *Activate Premium*\n\n"
            "Usage: /activate [CODE]\n\n"
            "Get your code after subscribing at:\n"
            "https://techne.finance/premium",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    code = args[1].strip().upper()
    telegram_id = message.from_user.id
    
    # Validate code (in production, check against database)
    # For MVP, accept any 8+ char alphanumeric code
    if len(code) >= 8 and code.isalnum():
        config = await user_store.get_or_create_config(telegram_id)
        config.is_premium = True
        config.premium_expires = None  # Set expiry in production
        await user_store.save_config(config)
        
        await message.answer(
            "✅ *Premium Activated!*\n\n"
            "You now have full access to:\n"
            "• 🔍 /pools - Yield discovery\n"
            "• 🚨 Real-time alerts\n"
            "• 🐋 Whale tracking\n"
            "• ⚙️ Custom filters\n\n"
            "Type /help for all commands.",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.answer(
            "❌ *Invalid Code*\n\n"
            "Please check your code and try again.\n"
            "Codes are 8+ characters, letters and numbers only.",
            parse_mode=ParseMode.MARKDOWN
        )


@router.callback_query(F.data == "enter_code")
async def callback_enter_code(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "🔑 *Enter Activation Code*\n\n"
        "Send your code using:\n"
        "/activate [YOUR_CODE]\n\n"
        "Example: /activate TECHNE2024ABC",
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data == "toggle_alerts")
async def callback_toggle_alerts(callback: CallbackQuery):
    await callback.answer()
    telegram_id = callback.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    
    config.alerts_enabled = not config.alerts_enabled
    await user_store.save_config(config)
    
    status = "✅ ON" if config.alerts_enabled else "❌ OFF"
    await callback.message.edit_text(
        f"🔔 *Alerts: {status}*\n\n"
        f"APY Spike: +{config.apy_spike_threshold}%\n"
        f"TVL Change: ±{config.tvl_change_threshold}%\n\n"
        "Use /setapyalert and /settvlalert to customize.",
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data == "show_help")
async def callback_show_help(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "📚 *Commands*\n\n"
        "/pools - View top pools\n"
        "/myconfig - Your filters\n"
        "/alerts - Toggle alerts\n"
        "/setchain - Chain filter\n"
        "/setmintvl - Min TVL\n"
        "/setminapy - Min APY\n"
        "/setrisk - Risk level\n"
        "/setprotocols - Protocol filter\n"
        "/gas - Gas prices\n"
        "/stats - Market stats",
        parse_mode=ParseMode.MARKDOWN
    )


# ===========================================
# Premium check helper
# ===========================================

async def require_premium(message: Message) -> bool:
    """Check if user has premium access"""
    telegram_id = message.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    
    if not config.is_premium:
        await message.answer(
            "🔒 *Premium Required*\n\n"
            "This feature requires Premium access.\n"
            "Subscribe at: https://techne.finance/premium\n\n"
            "/activate [CODE] after purchase",
            parse_mode=ParseMode.MARKDOWN
        )
        return False
    return True
