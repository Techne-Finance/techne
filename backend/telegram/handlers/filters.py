"""
Techne Telegram Bot - Filter Handlers
Handles /setchain, /setmintvl, /setminapy, etc.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode

from ..models.user_config import user_store


router = Router()


# ===========================================
# /setchain - Set chain filter
# ===========================================

@router.message(Command("setchain"))
async def cmd_setchain(message: Message):
    """Set chain filter"""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🌐 All", callback_data="chain_all"),
                InlineKeyboardButton(text="🔵 Base", callback_data="chain_base"),
            ],
            [
                InlineKeyboardButton(text="⟠ Ethereum", callback_data="chain_ethereum"),
                InlineKeyboardButton(text="🟣 Solana", callback_data="chain_solana"),
            ],
            [
                InlineKeyboardButton(text="🔷 Arbitrum", callback_data="chain_arbitrum"),
            ]
        ])
        
        await message.answer(
            "🔗 *Select Chain*\n\nChoose which blockchain to filter pools:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        return
    
    chain = args[1].strip().lower()
    valid_chains = ["all", "base", "ethereum", "solana", "arbitrum"]
    
    if chain not in valid_chains:
        await message.answer(f"❌ Invalid chain. Valid: {', '.join(valid_chains)}")
        return
    
    telegram_id = message.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    config.chain = chain
    await user_store.save_config(config)
    
    chain_emoji = {"all": "🌐", "base": "🔵", "ethereum": "⟠", "solana": "🟣", "arbitrum": "🔷"}.get(chain, "🌐")
    
    await message.answer(
        f"✅ Chain filter set to: {chain_emoji} *{chain.capitalize()}*",
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data.startswith("chain_"))
async def callback_setchain(callback: CallbackQuery):
    await callback.answer()
    chain = callback.data.replace("chain_", "")
    
    telegram_id = callback.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    config.chain = chain
    await user_store.save_config(config)
    
    chain_emoji = {"all": "🌐", "base": "🔵", "ethereum": "⟠", "solana": "🟣", "arbitrum": "🔷"}.get(chain, "🌐")
    
    await callback.message.edit_text(
        f"✅ Chain filter set to: {chain_emoji} *{chain.capitalize()}*",
        parse_mode=ParseMode.MARKDOWN
    )


# ===========================================
# /setmintvl - Set minimum TVL
# ===========================================

@router.message(Command("setmintvl"))
async def cmd_setmintvl(message: Message):
    """Set minimum TVL filter"""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="$10K", callback_data="tvl_10000"),
                InlineKeyboardButton(text="$50K", callback_data="tvl_50000"),
                InlineKeyboardButton(text="$100K", callback_data="tvl_100000"),
            ],
            [
                InlineKeyboardButton(text="$500K", callback_data="tvl_500000"),
                InlineKeyboardButton(text="$1M", callback_data="tvl_1000000"),
                InlineKeyboardButton(text="$10M", callback_data="tvl_10000000"),
            ]
        ])
        
        await message.answer(
            "💰 *Set Minimum TVL*\n\n"
            "Filter pools by Total Value Locked.\n"
            "Higher TVL = more liquidity = safer.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        return
    
    try:
        # Parse value (support K, M suffixes)
        value_str = args[1].strip().upper().replace("$", "").replace(",", "")
        if value_str.endswith("K"):
            value = float(value_str[:-1]) * 1000
        elif value_str.endswith("M"):
            value = float(value_str[:-1]) * 1000000
        else:
            value = float(value_str)
        
        telegram_id = message.from_user.id
        config = await user_store.get_or_create_config(telegram_id)
        config.min_tvl = value
        await user_store.save_config(config)
        
        formatted = f"${value/1000000:.1f}M" if value >= 1000000 else f"${value/1000:.0f}K"
        await message.answer(f"✅ Minimum TVL set to: *{formatted}*", parse_mode=ParseMode.MARKDOWN)
        
    except ValueError:
        await message.answer("❌ Invalid value. Use numbers like: 100000, 500K, 1M")


@router.callback_query(F.data.startswith("tvl_"))
async def callback_settvl(callback: CallbackQuery):
    await callback.answer()
    value = int(callback.data.replace("tvl_", ""))
    
    telegram_id = callback.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    config.min_tvl = value
    await user_store.save_config(config)
    
    formatted = f"${value/1000000:.1f}M" if value >= 1000000 else f"${value/1000:.0f}K"
    await callback.message.edit_text(f"✅ Minimum TVL set to: *{formatted}*", parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /setminapy - Set minimum APY
# ===========================================

@router.message(Command("setminapy"))
async def cmd_setminapy(message: Message):
    """Set minimum APY filter"""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="0%", callback_data="apy_0"),
                InlineKeyboardButton(text="3%", callback_data="apy_3"),
                InlineKeyboardButton(text="5%", callback_data="apy_5"),
            ],
            [
                InlineKeyboardButton(text="10%", callback_data="apy_10"),
                InlineKeyboardButton(text="20%", callback_data="apy_20"),
                InlineKeyboardButton(text="50%", callback_data="apy_50"),
            ]
        ])
        
        await message.answer(
            "📈 *Set Minimum APY*\n\n"
            "Filter pools by minimum yield.\n"
            "Higher APY may indicate higher risk.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        return
    
    try:
        value = float(args[1].strip().replace("%", ""))
        
        telegram_id = message.from_user.id
        config = await user_store.get_or_create_config(telegram_id)
        config.min_apy = value
        await user_store.save_config(config)
        
        await message.answer(f"✅ Minimum APY set to: *{value}%*", parse_mode=ParseMode.MARKDOWN)
        
    except ValueError:
        await message.answer("❌ Invalid value. Use numbers like: 5, 10, 20")


@router.callback_query(F.data.startswith("apy_"))
async def callback_setapy(callback: CallbackQuery):
    await callback.answer()
    value = float(callback.data.replace("apy_", ""))
    
    telegram_id = callback.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    config.min_apy = value
    await user_store.save_config(config)
    
    await callback.message.edit_text(f"✅ Minimum APY set to: *{value}%*", parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /setrisk - Set risk tolerance
# ===========================================

@router.message(Command("setrisk"))
async def cmd_setrisk(message: Message):
    """Set risk level filter"""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Low Only", callback_data="risk_low"),
                InlineKeyboardButton(text="🟡 Medium", callback_data="risk_medium"),
            ],
            [
                InlineKeyboardButton(text="🟠 High", callback_data="risk_high"),
                InlineKeyboardButton(text="🌐 All", callback_data="risk_all"),
            ]
        ])
        
        await message.answer(
            "🛡️ *Set Risk Tolerance*\n\n"
            "🟢 Low - Blue-chip protocols, high TVL\n"
            "🟡 Medium - Established protocols\n"
            "🟠 High - Newer or riskier pools",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        return
    
    risk = args[1].strip().lower()
    valid = ["low", "medium", "high", "all"]
    
    if risk not in valid:
        await message.answer(f"❌ Invalid. Valid: {', '.join(valid)}")
        return
    
    telegram_id = message.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    config.risk_level = risk
    await user_store.save_config(config)
    
    emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "all": "🌐"}.get(risk, "🌐")
    await message.answer(f"✅ Risk filter set to: {emoji} *{risk.capitalize()}*", parse_mode=ParseMode.MARKDOWN)


@router.callback_query(F.data.startswith("risk_"))
async def callback_setrisk(callback: CallbackQuery):
    await callback.answer()
    risk = callback.data.replace("risk_", "")
    
    telegram_id = callback.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    config.risk_level = risk
    await user_store.save_config(config)
    
    emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "all": "🌐"}.get(risk, "🌐")
    await callback.message.edit_text(f"✅ Risk filter set to: {emoji} *{risk.capitalize()}*", parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /setprotocols - Set protocol whitelist
# ===========================================

@router.message(Command("setprotocols"))
async def cmd_setprotocols(message: Message):
    """Set protocol whitelist"""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer(
            "🏛️ *Set Protocol Filter*\n\n"
            "Usage: /setprotocols [protocol1, protocol2, ...]\n\n"
            "Examples:\n"
            "• /setprotocols aave, compound, lido\n"
            "• /setprotocols aerodrome\n"
            "• /setprotocols clear (to show all)\n\n"
            "Available protocols:\n"
            "aave, compound, lido, uniswap, curve, aerodrome, morpho, pendle, gmx, beefy, balancer, spark, moonwell",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    protocols_str = args[1].strip().lower()
    
    telegram_id = message.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    
    if protocols_str == "clear" or protocols_str == "all":
        config.protocols = []
        await user_store.save_config(config)
        await message.answer("✅ Protocol filter cleared. Showing all protocols.")
        return
    
    # Parse comma-separated list
    protocols = [p.strip() for p in protocols_str.split(",") if p.strip()]
    config.protocols = protocols
    await user_store.save_config(config)
    
    await message.answer(
        f"✅ Protocol filter set to:\n*{', '.join(protocols)}*",
        parse_mode=ParseMode.MARKDOWN
    )


# ===========================================
# /setstablecoin - Toggle stablecoin mode
# ===========================================

@router.message(Command("setstablecoin"))
async def cmd_setstablecoin(message: Message):
    """Toggle stablecoin-only mode"""
    args = message.text.split(maxsplit=1)
    
    telegram_id = message.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    
    if len(args) >= 2:
        value = args[1].strip().lower()
        config.stablecoin_only = value in ["on", "true", "yes", "1"]
    else:
        # Toggle
        config.stablecoin_only = not config.stablecoin_only
    
    await user_store.save_config(config)
    
    status = "✅ ON" if config.stablecoin_only else "❌ OFF"
    await message.answer(
        f"🪙 *Stablecoin Only Mode: {status}*\n\n"
        f"{'Only showing USDC, USDT, DAI pools.' if config.stablecoin_only else 'Showing all asset types.'}",
        parse_mode=ParseMode.MARKDOWN
    )


# ===========================================
# /setasset - Set asset type
# ===========================================

@router.message(Command("setasset"))
async def cmd_setasset(message: Message):
    """Set asset type filter"""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🌐 All", callback_data="asset_all"),
                InlineKeyboardButton(text="🪙 Stablecoins", callback_data="asset_stablecoin"),
            ],
            [
                InlineKeyboardButton(text="⟠ ETH", callback_data="asset_eth"),
                InlineKeyboardButton(text="🟣 SOL", callback_data="asset_sol"),
            ]
        ])
        
        await message.answer(
            "💎 *Set Asset Type*\n\n"
            "Filter by underlying asset:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        return
    
    asset = args[1].strip().lower()
    valid = ["all", "stablecoin", "eth", "sol"]
    
    if asset not in valid:
        await message.answer(f"❌ Invalid. Valid: {', '.join(valid)}")
        return
    
    telegram_id = message.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    config.asset_type = asset
    await user_store.save_config(config)
    
    await message.answer(f"✅ Asset type set to: *{asset.capitalize()}*", parse_mode=ParseMode.MARKDOWN)


@router.callback_query(F.data.startswith("asset_"))
async def callback_setasset(callback: CallbackQuery):
    await callback.answer()
    asset = callback.data.replace("asset_", "")
    
    telegram_id = callback.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    config.asset_type = asset
    await user_store.save_config(config)
    
    await callback.message.edit_text(f"✅ Asset type set to: *{asset.capitalize()}*", parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /setpooltype - Set pool type
# ===========================================

@router.message(Command("setpooltype"))
async def cmd_setpooltype(message: Message):
    """Set pool type filter"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌐 All", callback_data="pooltype_all"),
            InlineKeyboardButton(text="📥 Single (Lending)", callback_data="pooltype_single"),
        ],
        [
            InlineKeyboardButton(text="🔄 Dual (LP)", callback_data="pooltype_dual"),
        ]
    ])
    
    await message.answer(
        "🏊 *Set Pool Type*\n\n"
        "📥 Single - Deposit one asset (lending)\n"
        "🔄 Dual - Provide liquidity pairs (LP)",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("pooltype_"))
async def callback_setpooltype(callback: CallbackQuery):
    await callback.answer()
    pool_type = callback.data.replace("pooltype_", "")
    
    telegram_id = callback.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    config.pool_type = pool_type
    await user_store.save_config(config)
    
    await callback.message.edit_text(f"✅ Pool type set to: *{pool_type.capitalize()}*", parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /setapyalert - Set APY alert threshold
# ===========================================

@router.message(Command("setapyalert"))
async def cmd_setapyalert(message: Message):
    """Set APY spike alert threshold"""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="10%", callback_data="apyalert_10"),
                InlineKeyboardButton(text="20%", callback_data="apyalert_20"),
                InlineKeyboardButton(text="50%", callback_data="apyalert_50"),
            ],
            [
                InlineKeyboardButton(text="100%", callback_data="apyalert_100"),
            ]
        ])
        
        await message.answer(
            "🚀 *APY Spike Alert Threshold*\n\n"
            "Get notified when a pool's APY increases by this percentage.\n\n"
            "Example: 20% means alert when APY jumps from 10% to 12%+",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        return
    
    try:
        value = float(args[1].strip().replace("%", ""))
        
        telegram_id = message.from_user.id
        config = await user_store.get_or_create_config(telegram_id)
        config.apy_spike_threshold = value
        await user_store.save_config(config)
        
        await message.answer(f"✅ APY spike alert set to: *+{value}%*", parse_mode=ParseMode.MARKDOWN)
        
    except ValueError:
        await message.answer("❌ Invalid value. Use a number like: 20")


@router.callback_query(F.data.startswith("apyalert_"))
async def callback_setapyalert(callback: CallbackQuery):
    await callback.answer()
    value = float(callback.data.replace("apyalert_", ""))
    
    telegram_id = callback.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    config.apy_spike_threshold = value
    await user_store.save_config(config)
    
    await callback.message.edit_text(f"✅ APY spike alert set to: *+{value}%*", parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /settvlalert - Set TVL alert threshold
# ===========================================

@router.message(Command("settvlalert"))
async def cmd_settvlalert(message: Message):
    """Set TVL change alert threshold"""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="5%", callback_data="tvlalert_5"),
                InlineKeyboardButton(text="10%", callback_data="tvlalert_10"),
                InlineKeyboardButton(text="20%", callback_data="tvlalert_20"),
            ]
        ])
        
        await message.answer(
            "🐋 *TVL Change Alert Threshold*\n\n"
            "Get notified when a pool's TVL changes by this percentage.\n"
            "Useful for detecting whale movements.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        return
    
    try:
        value = float(args[1].strip().replace("%", ""))
        
        telegram_id = message.from_user.id
        config = await user_store.get_or_create_config(telegram_id)
        config.tvl_change_threshold = value
        await user_store.save_config(config)
        
        await message.answer(f"✅ TVL change alert set to: *±{value}%*", parse_mode=ParseMode.MARKDOWN)
        
    except ValueError:
        await message.answer("❌ Invalid value. Use a number like: 10")


@router.callback_query(F.data.startswith("tvlalert_"))
async def callback_settvlalert(callback: CallbackQuery):
    await callback.answer()
    value = float(callback.data.replace("tvlalert_", ""))
    
    telegram_id = callback.from_user.id
    config = await user_store.get_or_create_config(telegram_id)
    config.tvl_change_threshold = value
    await user_store.save_config(config)
    
    await callback.message.edit_text(f"✅ TVL change alert set to: *±{value}%*", parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /reset - Reset all filters
# ===========================================

@router.message(Command("reset"))
async def cmd_reset(message: Message):
    """Reset all filters to defaults"""
    telegram_id = message.from_user.id
    
    # Create fresh config
    config = await user_store.get_or_create_config(telegram_id)
    
    # Reset to defaults
    config.chain = "all"
    config.min_tvl = 100000
    config.max_tvl = None
    config.min_apy = 3.0
    config.max_apy = 500.0
    config.risk_level = "all"
    config.protocols = []
    config.stablecoin_only = False
    config.asset_type = "all"
    config.pool_type = "all"
    
    await user_store.save_config(config)
    
    await message.answer(
        "🔄 *Filters Reset*\n\n"
        "All filters have been reset to defaults:\n"
        "• Chain: All\n"
        "• Min TVL: $100K\n"
        "• Min APY: 3%\n"
        "• Risk: All\n"
        "• Protocols: All\n\n"
        "Use /myconfig to view current settings.",
        parse_mode=ParseMode.MARKDOWN
    )
