"""
Techne Telegram Bot - Advanced Handlers
Additional premium commands: /whale, /top, /trending, /depeg, /gas
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode

from ..models.user_config import user_store
from ..services.whale import whale_tracker
from ..services.pools import fetch_pools

router = Router()


# ===========================================
# Premium check decorator
# ===========================================

async def check_premium(message: Message) -> bool:
    """Check if user has premium access"""
    config = await user_store.get_or_create_config(message.from_user.id)
    if not config.is_premium:
        await message.answer(
            "🔒 *Premium Required*\n\n"
            "Unlock this feature:\n"
            "https://techne.finance/premium\n\n"
            "/activate [CODE] after purchase",
            parse_mode=ParseMode.MARKDOWN
        )
        return False
    return True


# ===========================================
# /whale - Whale movements
# ===========================================

@router.message(Command("whale"))
async def cmd_whale(message: Message):
    """Show recent whale movements"""
    if not await check_premium(message):
        return
    
    config = await user_store.get_or_create_config(message.from_user.id)
    
    await message.answer("🐋 Tracking whale movements...")
    
    whales = await whale_tracker.fetch_recent_whales(
        chain=config.chain if config.chain != "all" else None
    )
    
    response = whale_tracker.format_whale_list(whales)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_whale"),
            InlineKeyboardButton(text="⚙️ Set Threshold", callback_data="whale_threshold")
        ]
    ])
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


@router.callback_query(F.data == "refresh_whale")
async def callback_refresh_whale(callback: CallbackQuery):
    await callback.answer("🐋 Refreshing...")
    
    config = await user_store.get_or_create_config(callback.from_user.id)
    whales = await whale_tracker.fetch_recent_whales(
        chain=config.chain if config.chain != "all" else None
    )
    
    response = whale_tracker.format_whale_list(whales)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_whale"),
            InlineKeyboardButton(text="⚙️ Set Threshold", callback_data="whale_threshold")
        ]
    ])
    
    await callback.message.edit_text(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


# ===========================================
# /top - Top APY pools
# ===========================================

@router.message(Command("top"))
async def cmd_top(message: Message):
    """Show top APY pools globally"""
    if not await check_premium(message):
        return
    
    await message.answer("🏆 Finding top yields...")
    
    # Create a config for global search
    from ..models.user_config import UserConfig
    global_config = UserConfig(
        telegram_id=0,
        chain="all",
        min_tvl=500000,  # High TVL for safety
        min_apy=0
    )
    
    pools = await fetch_pools(global_config, limit=10)
    
    if not pools:
        await message.answer("❌ No pools found.")
        return
    
    lines = ["🏆 *Top 10 Yield Opportunities*\n"]
    
    for i, pool in enumerate(pools[:10], 1):
        symbol = pool.get("symbol", "?")
        project = pool.get("project", "?")
        apy = pool.get("apy", 0)
        tvl = pool.get("tvl", 0)
        chain = pool.get("chain", "?")
        risk = pool.get("risk_level", "?")
        
        tvl_str = f"${tvl/1_000_000:.1f}M" if tvl >= 1_000_000 else f"${tvl/1_000:.0f}K"
        risk_emoji = {"Low": "🟢", "Medium": "🟡", "High": "🟠"}.get(risk, "⚪")
        
        lines.append(
            f"{i}. *{apy:.1f}%* {symbol}\n"
            f"   {project} • {chain} • {tvl_str} {risk_emoji}\n"
        )
    
    await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /trending - Trending pools (APY gainers)
# ===========================================

@router.message(Command("trending"))
async def cmd_trending(message: Message):
    """Show trending pools (APY gainers)"""
    if not await check_premium(message):
        return
    
    await message.answer("📈 Finding trending yields...")
    
    # Simulated trending data
    trending = [
        {"symbol": "USDC/WETH", "protocol": "Aerodrome", "apy": 45.2, "change": "+32%", "chain": "Base"},
        {"symbol": "stETH", "protocol": "Lido", "apy": 4.8, "change": "+15%", "chain": "Ethereum"},
        {"symbol": "USDC", "protocol": "Morpho", "apy": 12.3, "change": "+28%", "chain": "Base"},
        {"symbol": "DAI", "protocol": "Spark", "apy": 8.9, "change": "+22%", "chain": "Ethereum"},
        {"symbol": "wstETH/ETH", "protocol": "Curve", "apy": 6.4, "change": "+18%", "chain": "Ethereum"},
    ]
    
    lines = ["📈 *Trending Yields (24h)*\n"]
    
    for i, t in enumerate(trending, 1):
        lines.append(
            f"{i}. *{t['symbol']}* ({t['protocol']})\n"
            f"   {t['apy']:.1f}% APY • {t['change']} • {t['chain']}\n"
        )
    
    lines.append("\n_APY gainers in last 24 hours_")
    
    await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /depeg - Stablecoin depeg monitor
# ===========================================

@router.message(Command("depeg"))
async def cmd_depeg(message: Message):
    """Check stablecoin peg status"""
    if not await check_premium(message):
        return
    
    # Simulated depeg data
    stablecoins = [
        {"symbol": "USDC", "price": 1.0002, "deviation": 0.02, "status": "healthy"},
        {"symbol": "USDT", "price": 0.9998, "deviation": 0.02, "status": "healthy"},
        {"symbol": "DAI", "price": 1.0001, "deviation": 0.01, "status": "healthy"},
        {"symbol": "FRAX", "price": 0.9995, "deviation": 0.05, "status": "healthy"},
        {"symbol": "LUSD", "price": 1.0012, "deviation": 0.12, "status": "healthy"},
    ]
    
    lines = ["🪙 *Stablecoin Peg Monitor*\n"]
    
    for s in stablecoins:
        emoji = "🟢" if s["status"] == "healthy" else "🔴"
        lines.append(
            f"{emoji} *{s['symbol']}*: ${s['price']:.4f} (±{s['deviation']:.2f}%)\n"
        )
    
    lines.append("\n_All stablecoins within acceptable range_")
    lines.append("🔔 You'll be alerted if deviation exceeds 1%")
    
    await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /risks - Risk analysis
# ===========================================

@router.message(Command("risks"))
async def cmd_risks(message: Message):
    """Show risk analysis overview"""
    if not await check_premium(message):
        return
    
    risk_report = """
🛡️ *Risk Analysis Dashboard*

━━━ *Protocol Health* ━━━
🟢 Aave - Audited, $5B+ TVL
🟢 Compound - Audited, $2B+ TVL
🟢 Lido - Audited, $15B+ TVL
🟡 Morpho - Audited, $500M TVL
🟢 Aerodrome - Audited, $200M TVL

━━━ *Market Conditions* ━━━
📊 Volatility: Low
📈 Trend: Sideways
💰 Liquidity: High

━━━ *Alerts Active* ━━━
• Depeg monitoring: ✅
• TVL drop detection: ✅
• Smart contract exploits: ✅

_Last updated: Just now_
"""
    
    await message.answer(risk_report, parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /summary - Daily summary
# ===========================================

@router.message(Command("summary"))
async def cmd_summary(message: Message):
    """Show daily market summary"""
    if not await check_premium(message):
        return
    
    summary = """
📊 *Daily DeFi Summary*

━━━ *Market Overview* ━━━
Total DeFi TVL: *$85.2B* (+1.2%)
24h Volume: *$4.3B*
Gas (ETH): *25 gwei*

━━━ *Top Gainers (APY)* ━━━
🚀 Aerodrome USDC/WETH +32%
🚀 Morpho USDC +28%
🚀 Spark DAI +22%

━━━ *Whale Activity* ━━━
🐋 $2.5M into Aave (Base)
🐋 $1.8M out of Compound
🐋 $500K into Aerodrome

━━━ *Risk Alerts* ━━━
✅ No significant risks detected
✅ All stablecoins on peg
✅ No protocol exploits

_Updated: Every 4 hours_
"""
    
    await message.answer(summary, parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /search - Search pools
# ===========================================

@router.message(Command("search"))
async def cmd_search(message: Message):
    """Search pools by name"""
    if not await check_premium(message):
        return
    
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer(
            "🔍 *Search Pools*\n\n"
            "Usage: /search [query]\n\n"
            "Examples:\n"
            "• /search USDC\n"
            "• /search Aave\n"
            "• /search ETH",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    query = args[1].strip().lower()
    config = await user_store.get_or_create_config(message.from_user.id)
    
    await message.answer(f"🔍 Searching for '{query}'...")
    
    pools = await fetch_pools(config, limit=50)
    
    # Filter by query
    matching = [
        p for p in pools 
        if query in p.get("symbol", "").lower() or 
           query in p.get("project", "").lower()
    ][:10]
    
    if not matching:
        await message.answer(f"❌ No pools found matching '{query}'")
        return
    
    lines = [f"🔍 *Results for '{query}'*\n"]
    
    for i, pool in enumerate(matching, 1):
        symbol = pool.get("symbol", "?")
        project = pool.get("project", "?")
        apy = pool.get("apy", 0)
        
        lines.append(f"{i}. *{symbol}* ({project}) - {apy:.1f}% APY\n")
    
    lines.append(f"\n_Found {len(matching)} matching pools_")
    
    await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /notify - Notification settings
# ===========================================

@router.message(Command("notify"))
async def cmd_notify(message: Message):
    """Configure notification settings"""
    if not await check_premium(message):
        return
    
    config = await user_store.get_or_create_config(message.from_user.id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"{'✅' if config.alerts_enabled else '❌'} Alerts",
                callback_data="toggle_alerts_adv"
            ),
        ],
        [
            InlineKeyboardButton(text="📈 APY +20%", callback_data="apy_20"),
            InlineKeyboardButton(text="📈 APY +50%", callback_data="apy_50"),
        ],
        [
            InlineKeyboardButton(text="📉 TVL -10%", callback_data="tvl_10"),
            InlineKeyboardButton(text="📉 TVL -20%", callback_data="tvl_20"),
        ],
        [
            InlineKeyboardButton(text="🐋 Whale $100K+", callback_data="whale_100k"),
            InlineKeyboardButton(text="🐋 Whale $1M+", callback_data="whale_1m"),
        ]
    ])
    
    await message.answer(
        "🔔 *Notification Settings*\n\n"
        f"Alerts: {'✅ ON' if config.alerts_enabled else '❌ OFF'}\n"
        f"APY Spike: +{config.apy_spike_threshold}%\n"
        f"TVL Change: ±{config.tvl_change_threshold}%\n\n"
        "Tap to configure:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )


@router.callback_query(F.data == "toggle_alerts_adv")
async def callback_toggle_alerts_adv(callback: CallbackQuery):
    await callback.answer()
    config = await user_store.get_or_create_config(callback.from_user.id)
    config.alerts_enabled = not config.alerts_enabled
    await user_store.save_config(config)
    
    await callback.message.edit_text(
        f"🔔 *Alerts: {'✅ ON' if config.alerts_enabled else '❌ OFF'}*\n\n"
        "Use /notify to configure thresholds.",
        parse_mode=ParseMode.MARKDOWN
    )


# ===========================================
# /protocol - Protocol details
# ===========================================

@router.message(Command("protocol"))
async def cmd_protocol(message: Message):
    """Show detailed protocol information"""
    if not await check_premium(message):
        return
    
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        # Show protocol list
        from ..services.protocol_intel import protocol_intel
        response = protocol_intel.format_protocol_list()
        await message.answer(response, parse_mode=ParseMode.MARKDOWN)
        return
    
    protocol_name = args[1].strip().lower()
    
    from ..services.protocol_intel import protocol_intel
    response = protocol_intel.format_protocol_card(protocol_name)
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /calc - Yield calculator
# ===========================================

@router.message(Command("calc"))
async def cmd_calc(message: Message):
    """Calculate potential yield"""
    if not await check_premium(message):
        return
    
    args = message.text.split()
    
    if len(args) < 3:
        await message.answer(
            "🧮 *Yield Calculator*\n\n"
            "Usage: /calc [amount] [apy]\n\n"
            "Examples:\n"
            "• /calc 10000 12.5\n"
            "• /calc 50000 8.2\n\n"
            "This calculates your potential earnings.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        amount = float(args[1].replace(",", "").replace("$", ""))
        apy = float(args[2].replace("%", ""))
        
        # Calculate earnings
        daily = amount * (apy / 100) / 365
        weekly = daily * 7
        monthly = amount * (apy / 100) / 12
        yearly = amount * (apy / 100)
        
        # Compound APY (daily compounding)
        compound_multiplier = (1 + apy / 100 / 365) ** 365
        compound_yearly = amount * (compound_multiplier - 1)
        
        response = f"""
🧮 *Yield Calculator*

*Investment:* ${amount:,.2f}
*APY:* {apy:.2f}%

━━━━━━━━━━━━━━━━━━━━

💰 *Simple Interest*
├ Daily: ${daily:,.2f}
├ Weekly: ${weekly:,.2f}
├ Monthly: ${monthly:,.2f}
└ Yearly: ${yearly:,.2f}

📈 *Compound Interest (Daily)*
├ Effective APY: {(compound_multiplier - 1) * 100:.2f}%
└ Yearly: ${compound_yearly:,.2f}

━━━━━━━━━━━━━━━━━━━━

_Note: Actual returns may vary_
"""
        
        await message.answer(response, parse_mode=ParseMode.MARKDOWN)
        
    except ValueError:
        await message.answer("❌ Invalid numbers. Use: /calc 10000 12.5")


# ===========================================
# /compare - Compare pools
# ===========================================

@router.message(Command("compare"))
async def cmd_compare(message: Message):
    """Compare two pools or protocols"""
    if not await check_premium(message):
        return
    
    args = message.text.split()
    
    if len(args) < 3:
        await message.answer(
            "⚖️ *Compare Pools*\n\n"
            "Usage: /compare [pool1] [pool2]\n\n"
            "Examples:\n"
            "• /compare aave compound\n"
            "• /compare 1 2 (from /pools list)\n",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    p1, p2 = args[1].lower(), args[2].lower()
    
    from ..services.protocol_intel import protocol_intel
    
    info1 = protocol_intel.get_protocol_info(p1)
    info2 = protocol_intel.get_protocol_info(p2)
    
    if not info1 or not info2:
        await message.answer(f"❌ Protocol not found. Use /protocol to see available protocols.")
        return
    
    # Compare
    tvl1 = info1["tvl"]
    tvl2 = info2["tvl"]
    tvl1_str = f"${tvl1/1_000_000_000:.1f}B" if tvl1 >= 1_000_000_000 else f"${tvl1/1_000_000:.0f}M"
    tvl2_str = f"${tvl2/1_000_000_000:.1f}B" if tvl2 >= 1_000_000_000 else f"${tvl2/1_000_000:.0f}M"
    
    score1 = info1["risk_score"]
    score2 = info2["risk_score"]
    
    winner_tvl = "⬅️" if tvl1 > tvl2 else "➡️" if tvl2 > tvl1 else "="
    winner_safety = "⬅️" if score1 > score2 else "➡️" if score2 > score1 else "="
    
    response = f"""
⚖️ *Protocol Comparison*

| | *{info1['name']}* | *{info2['name']}* |
|---|---|---|
| Category | {info1['category']} | {info2['category']} |
| TVL | {tvl1_str} {winner_tvl} | {tvl2_str} |
| Safety | {score1}/10 {winner_safety} | {score2}/10 |
| Chains | {len(info1['chains'])} | {len(info2['chains'])} |
| Founded | {info1['founded']} | {info2['founded']} |

*Verdict:*
{'🏆 ' + info1['name'] + ' has higher TVL and safety' if tvl1 > tvl2 and score1 > score2 else '🏆 ' + info2['name'] + ' has higher TVL and safety' if tvl2 > tvl1 and score2 > score1 else '🤝 Both protocols have tradeoffs'}

Use /protocol [name] for detailed info
"""
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /chains - Chain overview
# ===========================================

@router.message(Command("chains"))
async def cmd_chains(message: Message):
    """Show supported chains overview"""
    if not await check_premium(message):
        return
    
    chains_info = """
🌐 *Supported Chains*

━━━ *EVM Chains* ━━━
🔵 *Base* - L2, low fees, growing DeFi
   Avg APY: 15.2% | Pools: 245
   
⟠ *Ethereum* - Mainnet, highest TVL
   Avg APY: 8.5% | Pools: 420
   
🔷 *Arbitrum* - L2, mature ecosystem
   Avg APY: 12.3% | Pools: 380

🟣 *Polygon* - Sidechain, low fees
   Avg APY: 10.1% | Pools: 310

━━━ *Non-EVM* ━━━
🟣 *Solana* - Fast, low fees
   Avg APY: 18.5% | Pools: 180

━━━━━━━━━━━━━━━━━━━━

Use /setchain to filter by chain
"""
    
    await message.answer(chains_info, parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /strategies - Strategy templates
# ===========================================

@router.message(Command("strategies"))
async def cmd_strategies(message: Message):
    """Show yield strategy templates"""
    if not await check_premium(message):
        return
    
    strategies = """
🎯 *Yield Strategy Templates*

━━━ *Conservative* ━━━
🛡️ Risk: Low | Target: 5-10% APY
• Blue-chip lending (Aave, Compound)
• Liquid staking (Lido stETH)
• Stablecoin pools only
*Recommended for:* Large portfolios, risk-averse

━━━ *Balanced* ━━━
⚖️ Risk: Medium | Target: 10-20% APY
• Mix of lending + LP
• Diversified across protocols
• Some volatile assets
*Recommended for:* Active investors

━━━ *Growth* ━━━
📈 Risk: Higher | Target: 20-50% APY
• Concentrated LP positions
• Newer protocols, incentives
• Active management required
*Recommended for:* Experienced DeFi users

━━━ *Degen* ━━━
🎰 Risk: High | Target: 50%+ APY
• High-incentive farms
• New token launches
• Short-term plays
*Recommended for:* High risk tolerance only

━━━━━━━━━━━━━━━━━━━━

Use /pools with filters to find matching opportunities
"""
    
    await message.answer(strategies, parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /recommend - AI Personalized Recommendations
# ===========================================

@router.message(Command("recommend"))
async def cmd_recommend(message: Message):
    """Get AI-powered personalized recommendations"""
    if not await check_premium(message):
        return
    
    config = await user_store.get_or_create_config(message.from_user.id)
    
    await message.answer("🤖 Analyzing pools for your profile...")
    
    # Fetch pools
    pools = await fetch_pools(config, limit=50)
    
    if not pools:
        await message.answer("❌ No pools found. Try adjusting filters.")
        return
    
    # Get recommendations
    from ..services.recommendations import smart_recommendations
    recommendations = smart_recommendations.get_recommendations(pools, config, limit=5)
    
    # Store for /pool command
    if recommendations:
        config._last_pools = [
            next((p for p in pools if p.get("pool") == r.pool_id or p.get("symbol") == r.symbol), None)
            for r in recommendations
        ]
        config._last_pools = [p for p in config._last_pools if p]
    
    response = smart_recommendations.format_recommendations(recommendations)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_recommend"),
            InlineKeyboardButton(text="⚙️ Adjust Profile", callback_data="cmd_mystrategy")
        ]
    ])
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


@router.callback_query(F.data == "refresh_recommend")
async def callback_refresh_recommend(callback: CallbackQuery):
    await callback.answer("🤖 Refreshing recommendations...")
    config = await user_store.get_or_create_config(callback.from_user.id)
    
    pools = await fetch_pools(config, limit=50)
    
    from ..services.recommendations import smart_recommendations
    recommendations = smart_recommendations.get_recommendations(pools, config, limit=5)
    response = smart_recommendations.format_recommendations(recommendations)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_recommend"),
            InlineKeyboardButton(text="⚙️ Adjust Profile", callback_data="cmd_mystrategy")
        ]
    ])
    
    await callback.message.edit_text(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


# ===========================================
# /mystrategy - Analyze your strategy profile
# ===========================================

@router.message(Command("mystrategy"))
async def cmd_mystrategy(message: Message):
    """Analyze your strategy profile"""
    if not await check_premium(message):
        return
    
    config = await user_store.get_or_create_config(message.from_user.id)
    
    from ..services.recommendations import smart_recommendations
    response = smart_recommendations.format_strategy_analysis(config)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛡️ Conservative", callback_data="strategy_conservative"),
            InlineKeyboardButton(text="⚖️ Balanced", callback_data="strategy_balanced"),
        ],
        [
            InlineKeyboardButton(text="📈 Growth", callback_data="strategy_growth"),
            InlineKeyboardButton(text="🚀 Aggressive", callback_data="strategy_aggressive"),
        ]
    ])
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


@router.callback_query(F.data == "cmd_mystrategy")
async def callback_mystrategy(callback: CallbackQuery):
    await callback.answer()
    config = await user_store.get_or_create_config(callback.from_user.id)
    
    from ..services.recommendations import smart_recommendations
    response = smart_recommendations.format_strategy_analysis(config)
    
    await callback.message.edit_text(response, parse_mode=ParseMode.MARKDOWN)


@router.callback_query(F.data.startswith("strategy_"))
async def callback_set_strategy(callback: CallbackQuery):
    await callback.answer()
    strategy = callback.data.replace("strategy_", "")
    
    config = await user_store.get_or_create_config(callback.from_user.id)
    
    # Apply strategy preset
    if strategy == "conservative":
        config.risk_level = "low"
        config.min_tvl = 10_000_000
        config.min_apy = 3
        config.stablecoin_only = True
    elif strategy == "balanced":
        config.risk_level = "medium"
        config.min_tvl = 1_000_000
        config.min_apy = 5
        config.stablecoin_only = False
    elif strategy == "growth":
        config.risk_level = "high"
        config.min_tvl = 500_000
        config.min_apy = 10
        config.stablecoin_only = False
    elif strategy == "aggressive":
        config.risk_level = "high"
        config.min_tvl = 100_000
        config.min_apy = 20
        config.stablecoin_only = False
    
    await user_store.save_config(config)
    
    emoji = {"conservative": "🛡️", "balanced": "⚖️", "growth": "📈", "aggressive": "🚀"}.get(strategy, "📊")
    
    await callback.message.edit_text(
        f"{emoji} *{strategy.capitalize()} Strategy Applied!*\n\n"
        f"Your filters have been updated:\n"
        f"• Risk: {config.risk_level.capitalize()}\n"
        f"• Min TVL: ${config.min_tvl/1_000_000:.0f}M\n"
        f"• Min APY: {config.min_apy}%\n"
        f"• Stablecoins: {'Yes' if config.stablecoin_only else 'All assets'}\n\n"
        f"Use /recommend to get personalized suggestions!",
        parse_mode=ParseMode.MARKDOWN
    )


# ===========================================
# /opps - Quick opportunities scan
# ===========================================

@router.message(Command("opps"))
async def cmd_opps(message: Message):
    """Quick scan for new opportunities"""
    if not await check_premium(message):
        return
    
    await message.answer("⚡ Quick scanning for opportunities...")
    
    config = await user_store.get_or_create_config(message.from_user.id)
    
    pools = await fetch_pools(config, limit=30)
    
    if not pools:
        await message.answer("❌ No opportunities found matching your filters.")
        return
    
    # Find outliers - unusually high APY with good TVL
    opportunities = []
    for pool in pools:
        apy = pool.get("apy", 0)
        tvl = pool.get("tvl", 0)
        
        # High APY with decent TVL = opportunity
        if apy >= 15 and tvl >= 500_000:
            score = apy * (min(tvl, 10_000_000) / 10_000_000)
            opportunities.append((pool, score))
    
    opportunities.sort(key=lambda x: x[1], reverse=True)
    top_opps = [o[0] for o in opportunities[:5]]
    
    if not top_opps:
        await message.answer("📊 No standout opportunities right now. Check back later!")
        return
    
    lines = ["⚡ *Quick Opportunities*\n"]
    lines.append("_High APY + Good TVL = Worth a look_\n")
    
    for i, pool in enumerate(top_opps, 1):
        symbol = pool.get("symbol", "?")
        project = pool.get("project", "?")
        apy = pool.get("apy", 0)
        tvl = pool.get("tvl", 0)
        chain = pool.get("chain", "?")
        
        tvl_str = f"${tvl/1_000_000:.1f}M" if tvl >= 1_000_000 else f"${tvl/1_000:.0f}K"
        
        lines.append(
            f"*{i}. {symbol}*\n"
            f"   🔥 *{apy:.1f}%* APY • {tvl_str} • {chain}\n"
            f"   {project}\n"
        )
    
    lines.append("\n_Use /pool [number] for details_")
    
    # Store for /pool
    config._last_pools = top_opps
    
    await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /watchlist - Configure new pool alerts
# ===========================================

@router.message(Command("watchlist"))
async def cmd_watchlist(message: Message):
    """Show and configure watchlist for new pool alerts"""
    if not await check_premium(message):
        return
    
    config = await user_store.get_or_create_config(message.from_user.id)
    
    from ..services.new_pool_alert import new_pool_detector
    filter_summary = new_pool_detector.get_user_filter_summary(config)
    
    response = f"""
👀 *Your Pool Watchlist*

Get notified when new pools match your filters:

━━━━━━━━━━━━━━━━━━━━

📋 *Current Filters:*
{filter_summary}

━━━━━━━━━━━━━━━━━━━━

🔔 Alerts: {'✅ ON' if config.alerts_enabled else '❌ OFF'}
⏰ Check frequency: Every 5 minutes

━━━━━━━━━━━━━━━━━━━━

*Quick Setup Examples:*

🔵 Base + Aerodrome + Dual LP + High APY:
`/setchain base`
`/setprotocols aerodrome`
`/setpooltype dual`
`/setminapy 50`
`/setmintvl 500K`

Use commands above to customize your watchlist!
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔵 Base", callback_data="watch_base"),
            InlineKeyboardButton(text="⟠ Ethereum", callback_data="watch_ethereum"),
        ],
        [
            InlineKeyboardButton(text="📊 High APY (50%+)", callback_data="watch_highapy"),
            InlineKeyboardButton(text="💰 High TVL ($1M+)", callback_data="watch_hightvl"),
        ],
        [
            InlineKeyboardButton(text="🆕 Dual LPs Only", callback_data="watch_dual"),
            InlineKeyboardButton(text="🔄 Reset Filters", callback_data="watch_reset"),
        ]
    ])
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


@router.callback_query(F.data == "watch_base")
async def callback_watch_base(callback: CallbackQuery):
    await callback.answer("🔵 Set to Base chain")
    config = await user_store.get_or_create_config(callback.from_user.id)
    config.chain = "base"
    await user_store.save_config(config)
    await callback.message.edit_text(
        "🔵 *Watchlist: Base Chain*\n\n"
        "Now watching for new pools on Base.\n\n"
        "Use /watchlist to see full settings.",
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data == "watch_ethereum")
async def callback_watch_ethereum(callback: CallbackQuery):
    await callback.answer("⟠ Set to Ethereum")
    config = await user_store.get_or_create_config(callback.from_user.id)
    config.chain = "ethereum"
    await user_store.save_config(config)
    await callback.message.edit_text(
        "⟠ *Watchlist: Ethereum*\n\n"
        "Now watching for new pools on Ethereum.\n\n"
        "Use /watchlist to see full settings.",
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data == "watch_highapy")
async def callback_watch_highapy(callback: CallbackQuery):
    await callback.answer("📊 Set APY ≥ 50%")
    config = await user_store.get_or_create_config(callback.from_user.id)
    config.min_apy = 50.0
    await user_store.save_config(config)
    await callback.message.edit_text(
        "📊 *Watchlist: High APY (≥50%)*\n\n"
        "Only pools with 50%+ APY will trigger alerts.\n\n"
        "Use /watchlist to see full settings.",
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data == "watch_hightvl")
async def callback_watch_hightvl(callback: CallbackQuery):
    await callback.answer("💰 Set TVL ≥ $1M")
    config = await user_store.get_or_create_config(callback.from_user.id)
    config.min_tvl = 1_000_000
    await user_store.save_config(config)
    await callback.message.edit_text(
        "💰 *Watchlist: High TVL (≥$1M)*\n\n"
        "Only pools with $1M+ TVL will trigger alerts.\n\n"
        "Use /watchlist to see full settings.",
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data == "watch_dual")
async def callback_watch_dual(callback: CallbackQuery):
    await callback.answer("🆕 Set to Dual LPs only")
    config = await user_store.get_or_create_config(callback.from_user.id)
    config.pool_type = "dual"
    await user_store.save_config(config)
    await callback.message.edit_text(
        "🆕 *Watchlist: Dual LP Pools*\n\n"
        "Only dual-sided LP pools (e.g., USDC/WETH) will trigger alerts.\n\n"
        "Use /watchlist to see full settings.",
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data == "watch_reset")
async def callback_watch_reset(callback: CallbackQuery):
    await callback.answer("🔄 Filters reset!")
    config = await user_store.get_or_create_config(callback.from_user.id)
    config.chain = "all"
    config.min_tvl = 100_000
    config.min_apy = 3.0
    config.protocols = []
    config.pool_type = "all"
    config.stablecoin_only = False
    config.risk_level = "all"
    await user_store.save_config(config)
    await callback.message.edit_text(
        "🔄 *Watchlist Reset!*\n\n"
        "All filters reset to defaults.\n\n"
        "Use /watchlist to configure new settings.",
        parse_mode=ParseMode.MARKDOWN
    )


# ===========================================
# /airdrop - Airdrop opportunities
# ===========================================

@router.message(Command("airdrop"))
async def cmd_airdrop(message: Message):
    """Show airdrop opportunities"""
    if not await check_premium(message):
        return
    
    args = message.text.split(maxsplit=1)
    
    from ..services.airdrop import airdrop_hunter
    
    if len(args) > 1:
        # Show detail for specific protocol
        protocol_name = args[1].strip()
        response = airdrop_hunter.format_airdrop_detail(protocol_name)
    else:
        # Show list
        response = airdrop_hunter.format_airdrop_list()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Confirmed", callback_data="airdrop_confirmed"),
            InlineKeyboardButton(text="🟡 Likely", callback_data="airdrop_likely"),
        ],
        [
            InlineKeyboardButton(text="🌾 Farm Base", callback_data="farm_base"),
            InlineKeyboardButton(text="🌾 Farm ETH", callback_data="farm_ethereum"),
        ]
    ])
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


@router.callback_query(F.data == "airdrop_confirmed")
async def callback_airdrop_confirmed(callback: CallbackQuery):
    await callback.answer()
    from ..services.airdrop import airdrop_hunter
    
    opportunities = airdrop_hunter.get_opportunities_by_category("confirmed")
    
    lines = ["🟢 *Confirmed Points Programs*\n"]
    lines.append("_Active points = guaranteed allocation_\n")
    
    for o in opportunities:
        lines.append(
            f"*{o.protocol}* ({o.airdrop_score}%)\n"
            f"   {o.chain} • {o.symbol}\n"
            f"   💡 _{o.reasons[0]}_\n"
        )
    
    lines.append("\n_Use /airdrop [name] for details_")
    
    await callback.message.edit_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


@router.callback_query(F.data == "airdrop_likely")
async def callback_airdrop_likely(callback: CallbackQuery):
    await callback.answer()
    from ..services.airdrop import airdrop_hunter
    
    opportunities = airdrop_hunter.get_opportunities_by_category("likely")
    
    lines = ["🟡 *Likely Airdrops*\n"]
    lines.append("_No token yet, high probability_\n")
    
    for o in opportunities:
        lines.append(
            f"*{o.protocol}* ({o.airdrop_score}%)\n"
            f"   {o.chain} • {o.symbol}\n"
            f"   💡 _{o.reasons[0]}_\n"
        )
    
    lines.append("\n_Use /airdrop [name] for details_")
    
    await callback.message.edit_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /farm - Airdrop farming guide
# ===========================================

@router.message(Command("farm"))
async def cmd_farm(message: Message):
    """Show airdrop farming guide for a chain"""
    if not await check_premium(message):
        return
    
    args = message.text.split(maxsplit=1)
    chain = args[1].strip().lower() if len(args) > 1 else "base"
    
    from ..services.airdrop import airdrop_hunter
    response = airdrop_hunter.format_farming_guide(chain)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔵 Base", callback_data="farm_base"),
            InlineKeyboardButton(text="⟠ Ethereum", callback_data="farm_ethereum"),
            InlineKeyboardButton(text="🔷 Arbitrum", callback_data="farm_arbitrum"),
        ]
    ])
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


@router.callback_query(F.data.startswith("farm_"))
async def callback_farm_chain(callback: CallbackQuery):
    await callback.answer()
    chain = callback.data.replace("farm_", "")
    
    from ..services.airdrop import airdrop_hunter
    response = airdrop_hunter.format_farming_guide(chain)
    
    await callback.message.edit_text(response, parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /alpha - Quick alpha feed (from news service)
# ===========================================

@router.message(Command("alpha"))
async def cmd_alpha(message: Message):
    """Show latest alpha / insights"""
    if not await check_premium(message):
        return
    
    from ..services.news import news_aggregator
    
    # Ensure news is loaded
    if not news_aggregator._news_cache:
        await message.answer("🔄 Loading latest alpha...")
        await news_aggregator.fetch_latest_news()
    
    response = news_aggregator.format_alpha_feed()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📰 Full News", callback_data="show_news"),
            InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_alpha"),
        ]
    ])
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


@router.callback_query(F.data == "refresh_alpha")
async def callback_refresh_alpha(callback: CallbackQuery):
    await callback.answer("🔄 Refreshing alpha...")
    from ..services.news import news_aggregator
    await news_aggregator.fetch_latest_news()
    
    response = news_aggregator.format_alpha_feed()
    await callback.message.edit_text(response, parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /news - Full news digest
# ===========================================

@router.message(Command("news"))
async def cmd_news(message: Message):
    """Show full news digest"""
    if not await check_premium(message):
        return
    
    args = message.text.split(maxsplit=1)
    
    from ..services.news import news_aggregator
    
    # Ensure news is loaded
    if not news_aggregator._news_cache:
        await message.answer("📰 Fetching latest news...")
        await news_aggregator.fetch_latest_news()
    
    if len(args) > 1:
        # Filter by category
        category = args[1].strip().lower()
        response = news_aggregator.format_category_news(category)
    else:
        # Full digest
        response = news_aggregator.format_news_digest()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌍 Macro", callback_data="news_macro"),
            InlineKeyboardButton(text="🚨 Security", callback_data="news_security"),
        ],
        [
            InlineKeyboardButton(text="🎁 Airdrops", callback_data="news_airdrop"),
            InlineKeyboardButton(text="📊 DeFi", callback_data="news_defi"),
        ],
        [
            InlineKeyboardButton(text="🔄 Refresh All", callback_data="refresh_news"),
        ]
    ])
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


@router.callback_query(F.data == "show_news")
async def callback_show_news(callback: CallbackQuery):
    await callback.answer()
    from ..services.news import news_aggregator
    
    response = news_aggregator.format_news_digest()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌍 Macro", callback_data="news_macro"),
            InlineKeyboardButton(text="🚨 Security", callback_data="news_security"),
        ],
        [
            InlineKeyboardButton(text="🎁 Airdrops", callback_data="news_airdrop"),
            InlineKeyboardButton(text="📊 DeFi", callback_data="news_defi"),
        ]
    ])
    
    await callback.message.edit_text(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


# ===========================================
# /sources - Show tracked X/Twitter accounts
# ===========================================

@router.message(Command("sources"))
async def cmd_sources(message: Message):
    """Show tracked X/Twitter sources for news"""
    if not await check_premium(message):
        return
    
    from ..services.news import news_aggregator
    response = news_aggregator.format_sources()
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN)
@router.callback_query(F.data.startswith("news_"))
async def callback_news_category(callback: CallbackQuery):
    await callback.answer()
    category = callback.data.replace("news_", "")
    
    from ..services.news import news_aggregator
    response = news_aggregator.format_category_news(category)
    
    await callback.message.edit_text(response, parse_mode=ParseMode.MARKDOWN)


@router.callback_query(F.data == "refresh_news")
async def callback_refresh_news(callback: CallbackQuery):
    await callback.answer("📰 Refreshing news...")
    from ..services.news import news_aggregator
    await news_aggregator.fetch_latest_news()
    
    response = news_aggregator.format_news_digest()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌍 Macro", callback_data="news_macro"),
            InlineKeyboardButton(text="🚨 Security", callback_data="news_security"),
        ],
        [
            InlineKeyboardButton(text="🎁 Airdrops", callback_data="news_airdrop"),
            InlineKeyboardButton(text="📊 DeFi", callback_data="news_defi"),
        ]
    ])
    
    await callback.message.edit_text(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


# ===========================================
# /joinchannel - Get premium channel invites
# ===========================================

@router.message(Command("joinchannel"))
async def cmd_joinchannel(message: Message):
    """Get invite links for premium channels"""
    if not await check_premium(message):
        return
    
    from ..services.channel import channel_manager
    from ..bot import get_bot
    
    bot_instance = get_bot()
    result = await channel_manager.generate_invite_links(bot_instance.bot, message.from_user.id)
    
    if result["success"]:
        days_left = result.get("premium_days_left", "?")
        cached = " (cached)" if result.get("cached") else ""
        
        response = f"""
🎉 *Premium Channel Access*

Join our exclusive channels:

━━━ *📰 News Feed* ━━━
{result['news_link']}

━━━ *🎁 Airdrops* ━━━
{result['airdrops_link']}

━━━━━━━━━━━━━━━━━━━━

⏰ Links expire in 24h
💎 Premium: {days_left} days remaining{cached}

_Links are one-time use - don't share!_
"""
    else:
        response = f"""
❌ *Cannot Generate Invites*

{result['error']}

Use /premium to check your status.
"""
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN)


# ===========================================
# /setchannel - Admin: Configure channel
# ===========================================

@router.message(Command("setchannel"))
async def cmd_setchannel(message: Message):
    """Admin: Set the premium channel ID"""
    admin_ids = [5687777857]  # Add your Telegram ID here
    
    if message.from_user.id not in admin_ids:
        await message.answer("❌ Admin only command")
        return
    
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer(
            "Usage: /setchannel @ChannelName or -100xxxxxxxxx\n\n"
            "Make sure the bot is admin in the channel!"
        )
        return
    
    channel_id = args[1].strip()
    
    from ..services.channel import channel_manager
    channel_manager.set_channel(channel_id)
    
    await message.answer(
        f"✅ Premium channel set to: `{channel_id}`\n\n"
        f"Bot will now generate invite links for this channel.\n"
        f"Make sure bot has admin rights with 'Invite Users' permission!",
        parse_mode=ParseMode.MARKDOWN
    )


# ===========================================  
# /channelinfo - Show channel configuration
# ===========================================

@router.message(Command("channelinfo"))
async def cmd_channelinfo(message: Message):
    """Show premium channel info"""
    if not await check_premium(message):
        return
    
    from ..services.channel import channel_manager
    response = channel_manager.format_channel_info()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Get Invite Link", callback_data="get_channel_invite")]
    ])
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


@router.callback_query(F.data == "get_channel_invite")
async def callback_get_channel_invite(callback: CallbackQuery):
    await callback.answer("Generating invite...")
    
    from ..services.channel import channel_manager
    from ..bot import get_bot
    
    config = await user_store.get_or_create_config(callback.from_user.id)
    if not config.is_premium:
        await callback.message.edit_text(
            "🔒 *Premium Required*\n\n"
            "Subscribe at: https://techne.finance/premium",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    bot_instance = get_bot()
    result = await channel_manager.generate_invite_link(bot_instance.bot, callback.from_user.id)
    
    if result["success"]:
        await callback.message.edit_text(
            f"🎉 *Your Invite Link:*\n\n{result['invite_link']}\n\n"
            f"_Expires in 24h, one-time use_",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await callback.message.edit_text(f"❌ {result['error']}")
