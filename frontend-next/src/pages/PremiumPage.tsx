/**
 * Premium Page — Full subscription UI with activation flow
 * Ported from frontend/premium-ui.js + subscription-ui.js
 *
 * Features:
 * - Credit pack purchase ($0.10 USDC for 100 credits)
 * - Artisan Bot subscription ($99/mo)
 * - Post-payment activation code modal
 * - Upgrade modal when credits run out
 * - Artisan Bot settings panel
 * - Credit cost breakdown
 * - Search counter system
 */

import { useState, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    Crown, Zap, Bot, Shield, Brain, AlertTriangle,
    MessageSquare, CheckCircle2, XCircle, Loader2, Coins,
    Copy, Check, ExternalLink, Settings,
    ToggleLeft, ToggleRight, X, Lock, CreditCard, Flame,
    PartyPopper, Wallet, Activity, ChevronRight,
    Eye, BarChart3, Crosshair, Gift,
    Globe, Terminal
} from 'lucide-react'
import { useWalletStore } from '@/stores/walletStore'
import { useCreditsStore, CREDIT_COSTS } from '@/stores/creditsStore'
import { fetchPaymentRequirements, fetchPremiumRequirements, settlePayment, subscribePremium, updatePremiumSettings, fetchPremiumStatus, toggleAutoRenewal, fetchRenewalStatus } from '@/lib/api'
import { toast } from '@/components/Toast'
// ethers loaded via dynamic import() in async payment functions
import { SubscribeModal } from '@/components/modals/SubscribeModal'

// ============ Constants ============

const TELEGRAM_BOT = 'TechneArtisanBot'
const USDC_DECIMALS = 6
const CREDIT_PACK_PRICE = '0.10'
const ERC20_ABI = ['function transfer(address to, uint256 amount) returns (bool)']

const PAY_PER_USE_FEATURES = [
    { text: '100 Pool Search Credits', included: true },
    { text: 'Full APY & TVL History', included: true },
    { text: 'Basic Protocol Safety Score', included: true },
    { text: 'Real-Time Signals', included: false },
]

const ARTISAN_FEATURES = [
    { text: 'Personal AI Trading Agent', icon: Bot },
    { text: 'Autonomous Trade Execution', icon: Zap },
    { text: 'Telegram AI Assistant', icon: MessageSquare },
    { text: '$10K/trade Session Key Limits', icon: AlertTriangle },
    { text: 'AI Strategy Optimization', icon: Brain },
    { text: 'Emergency Exit Controls', icon: Shield },
]

const HOW_IT_WORKS_STEPS = [
    {
        step: '01',
        title: 'Connect Wallet',
        desc: 'Link your Web3 wallet — your address becomes your premium key. No email, no password.',
        icon: Wallet,
    },
    {
        step: '02',
        title: 'Activate Artisan Bot',
        desc: 'Subscribe for $99/mo. Open @TechneArtisanBot on Telegram and paste your activation code.',
        icon: Bot,
    },
    {
        step: '03',
        title: 'Start Managing DeFi',
        desc: 'Chat with your AI agent in natural language — it finds yields, executes trades, and guards your portfolio 24/7.',
        icon: Brain,
    },
]

const BOT_SKILLS = [
    {
        title: '18 DeFi Tools',
        desc: 'Swap tokens, provide liquidity, stake, bridge cross-chain, verify pools — all through one chat interface.',
        icon: Terminal,
    },
    {
        title: 'Portfolio Autopilot',
        desc: 'Auto-compounds yields, rebalances positions across protocols, and optimizes gas costs without you touching anything.',
        icon: BarChart3,
    },
    {
        title: 'Risk Engine',
        desc: 'Built-in stop-loss, max drawdown limits, volatility guard, and instant emergency exit. Protects your funds 24/7.',
        icon: Shield,
    },
    {
        title: 'Yield Scanner',
        desc: 'Scans 25+ protocols on Base in real-time. Finds the best APY for your risk profile and auto-rotates into top opportunities.',
        icon: Crosshair,
    },
]

const SUB_AGENTS = [
    {
        name: 'Scout',
        desc: 'Finds best yield opportunities across 25+ protocols on Base',
        icon: Crosshair,
        status: 'Active',
        color: 'var(--color-green)',
    },
    {
        name: 'Guardian',
        desc: 'Monitors positions for risk, drawdown, and emergency conditions',
        icon: Shield,
        status: 'Active',
        color: 'var(--color-gold)',
    },
    {
        name: 'Airdrop',
        desc: 'Tracks potential airdrop eligibility and farming opportunities',
        icon: Gift,
        status: 'Active',
        color: 'var(--color-accent)',
    },
]

const EXAMPLE_COMMANDS = [
    { cmd: '"Find pools with 15%+ APY on Base"', category: 'Discovery' },
    { cmd: '"Move 50% of my USDC to Aave"', category: 'Execution' },
    { cmd: '"Check my portfolio performance"', category: 'Analytics' },
    { cmd: '"Exit all positions to stablecoins"', category: 'Emergency' },
    { cmd: '"Set stop-loss at -5% for all positions"', category: 'Risk' },
    { cmd: '"Show me safest stablecoin yields above 8%"', category: 'Strategy' },
]

const SUPPORTED_SOURCES = [
    'Aerodrome', 'Uniswap V3', 'Aave V3', 'Compound V3', 'Moonwell',
    'Morpho Blue', 'Pendle', 'Beefy', 'Curve', 'Balancer V2',
    'Stargate', 'dHEDGE', 'PancakeSwap', 'Silo Finance', 'Overnight',
]

// ============ Main Component ============

export function PremiumPage() {
    const { isConnected, address, signer } = useWalletStore()
    const { credits, addCredits } = useCreditsStore()
    const [purchasing, setPurchasing] = useState(false)
    const [subscribing, setSubscribing] = useState(false)
    void subscribing // used only as setter in handleSubscribe

    // Activation modal state
    const [activationCode, setActivationCode] = useState<string | null>(null)
    const [codeCopied, setCodeCopied] = useState(false)

    // Upgrade modal (shown when credits run out)
    const [showUpgrade, setShowUpgrade] = useState(false)

    // Subscribe modal
    const [showSubscribeModal, setShowSubscribeModal] = useState(false)

    // Artisan settings panel
    const [showSettings, setShowSettings] = useState(false)
    const [artisanSettings, setArtisanSettings] = useState({
        maxTradeSize: 5000,
        riskLevel: 'medium' as 'low' | 'medium' | 'high',
        autoRebalance: true,
        telegramAlerts: true,
        emergencyExit: true,
    })
    const [savingSettings, setSavingSettings] = useState(false)

    // Auto-renewal state
    const [renewalStatus, setRenewalStatus] = useState<any>(null)
    const [togglingRenewal, setTogglingRenewal] = useState(false)

    // Subscription status
    const [subStatus, setSubStatus] = useState<any>(null)

    // Check subscription status on wallet connect
    useEffect(() => {
        if (!address) { setSubStatus(null); setRenewalStatus(null); return }
        fetchPremiumStatus(address)
            .then(data => setSubStatus(data))
            .catch(() => setSubStatus(null))
        fetchRenewalStatus(address)
            .then(data => setRenewalStatus(data))
            .catch(() => setRenewalStatus(null))
    }, [address])

    // ---- Toggle Auto-Renewal ----
    const handleToggleRenewal = async () => {
        if (!address) return
        setTogglingRenewal(true)
        try {
            const newEnabled = !renewalStatus?.auto_renewal_enabled
            const result = await toggleAutoRenewal(address, newEnabled)
            if (result.success) {
                setRenewalStatus((prev: any) => ({ ...prev, auto_renewal_enabled: newEnabled }))
                toast.success(result.message)
            }
        } catch (err: any) {
            toast.error(err.message || 'Failed to toggle auto-renewal')
        } finally {
            setTogglingRenewal(false)
        }
    }

    // ---- Buy Credits ----
    const handleBuyCredits = async () => {
        if (!isConnected || !signer) {
            toast.error('Connect your wallet first')
            return
        }

        setPurchasing(true)
        try {
            const requirements = await fetchPaymentRequirements()
            const { ethers } = await import('ethers')
            const usdcContract = new ethers.Contract(requirements.usdcAddress, ERC20_ABI, signer)
            const amount = ethers.parseUnits(CREDIT_PACK_PRICE, USDC_DECIMALS)

            toast.info('Approve USDC transfer...')
            const tx = await usdcContract.transfer(requirements.recipientAddress, amount)

            toast.info('Confirming transaction...')
            const receipt = await tx.wait()

            const result = await settlePayment({
                tx_hash: receipt.hash,
                chain_id: requirements.chainId,
                amount: CREDIT_PACK_PRICE,
                from: address,
            })

            if (result.success) {
                addCredits(result.credits || 100)
                toast.success(`${result.credits || 100} credits added!`)
            } else {
                throw new Error(result.error || 'Settlement failed')
            }
        } catch (err: any) {
            if (err.code === 'ACTION_REJECTED' || err.code === 4001) {
                toast.warning('Transaction cancelled')
            } else {
                toast.error(`Purchase failed: ${err.message || err}`)
            }
        } finally {
            setPurchasing(false)
        }
    }

    // ---- Subscribe ($99) ----
    const handleSubscribe = async () => {
        if (!isConnected || !signer) {
            toast.error('Connect your wallet first')
            return
        }

        setSubscribing(true)
        try {
            const requirements = await fetchPremiumRequirements()
            const { ethers } = await import('ethers')
            const usdcContract = new ethers.Contract(requirements.usdcAddress, ERC20_ABI, signer)
            const amount = ethers.parseUnits('99', USDC_DECIMALS)

            toast.info('Approve $99 USDC payment...')
            const tx = await usdcContract.transfer(requirements.recipientAddress, amount)

            toast.info('Confirming transaction...')
            const receipt = await tx.wait()

            const result = await subscribePremium({
                wallet_address: address!,
                paymentPayload: {
                    tx_hash: receipt.hash,
                    chain_id: 8453,
                    amount: '99000000',
                    tier: 'artisan',
                },
            })

            if (result.success || result.activation_code) {
                const code = result.activation_code || result.code || 'CHECK-TELEGRAM'
                setActivationCode(code)
                setSubStatus({ subscribed: true, status: 'active', expires_at: result.expires_at })
                toast.success('Artisan Access activated!')
            } else {
                throw new Error(result.error || 'Subscription failed')
            }
        } catch (err: any) {
            if (err.code === 'ACTION_REJECTED' || err.code === 4001) {
                toast.warning('Transaction cancelled')
            } else {
                toast.error(`Subscription failed: ${err.message || err}`)
            }
        } finally {
            setSubscribing(false)
        }
    }

    // ---- Copy activation code ----
    const copyCode = useCallback(() => {
        if (activationCode) {
            navigator.clipboard.writeText(activationCode)
            setCodeCopied(true)
            setTimeout(() => setCodeCopied(false), 2000)
        }
    }, [activationCode])

    // ---- Save Artisan Settings ----
    const handleSaveSettings = async () => {
        if (!address) return
        setSavingSettings(true)
        try {
            await updatePremiumSettings({
                user_address: address,
                settings: artisanSettings,
            })
            toast.success('Settings saved!')
        } catch (err: any) {
            toast.error(`Failed to save: ${err.message}`)
        } finally {
            setSavingSettings(false)
        }
    }

    return (
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
            {/* Header */}
            <div className="text-center mb-8">
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="inline-flex items-center gap-2 mb-3"
                >
                    <Crown className="w-8 h-8" style={{ color: 'var(--color-gold)' }} />
                    <h1 className="font-heading text-2xl sm:text-3xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
                        Artisan Access
                    </h1>
                </motion.div>
                <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                    Pay once with USDC. Your wallet is your key — premium is bound to the address that paid.
                </p>
                {/* Credits display */}
                <div className="inline-flex items-center gap-1.5 mt-2 px-3 py-1 rounded-full"
                    style={{ background: 'var(--color-gold-dim)', border: '1px solid var(--color-gold-border)' }}>
                    <Coins className="w-3.5 h-3.5" style={{ color: 'var(--color-gold)' }} />
                    <span className="text-xs font-medium" style={{ color: 'var(--color-gold)' }}>
                        {credits} credits remaining
                    </span>
                </div>
            </div>

            {/* Active Subscription Banner */}
            {subStatus?.subscribed && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="glass-card-gold p-4 sm:p-5 mb-6 flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:justify-between"
                >
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                            style={{ background: 'linear-gradient(135deg, var(--color-gold), var(--color-gold-bright))' }}>
                            <CheckCircle2 className="w-5 h-5" style={{ color: 'var(--color-bg-primary)' }} />
                        </div>
                        <div>
                            <h3 className="font-heading text-sm font-bold" style={{ color: 'var(--color-gold)' }}>
                                Artisan Access Active
                            </h3>
                            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                                Wallet-bound to {address?.slice(0, 6)}...{address?.slice(-4)}
                                {subStatus.expires_at && ` · Expires ${new Date(subStatus.expires_at).toLocaleDateString()}`}
                                {subStatus.telegram_connected && ' · Telegram ✓'}
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={() => setShowSettings(true)}
                        className="px-3 py-1.5 rounded-lg text-xs font-heading font-semibold cursor-pointer"
                        style={{ background: 'var(--color-glass)', border: '1px solid var(--color-gold-border)', color: 'var(--color-gold)' }}
                    >
                        <Settings className="w-3.5 h-3.5 inline mr-1" /> Settings
                    </button>
                </motion.div>
            )}

            {/* Pricing Cards */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-5 mb-8">
                {/* Pay-Per-Use */}
                <motion.div
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="glass-card p-4 sm:p-6 flex flex-col"
                >
                    <div className="text-center mb-5">
                        <p className="text-xs font-heading font-semibold tracking-widest mb-3" style={{ color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                            CREDIT PACK
                        </p>
                        <div className="flex items-baseline justify-center gap-1">
                            <span className="font-heading text-3xl sm:text-5xl font-bold" style={{ color: 'var(--color-text-primary)' }}>0.10</span>
                            <span className="text-lg" style={{ color: 'var(--color-text-muted)' }}>USDC</span>
                        </div>
                        <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
                            100 credits per pack
                        </p>
                    </div>

                    <div className="space-y-3 mb-6 flex-1">
                        {PAY_PER_USE_FEATURES.map((f, i) => (
                            <div key={i} className="flex items-center gap-2.5">
                                {f.included ? (
                                    <CheckCircle2 className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--color-green)' }} />
                                ) : (
                                    <XCircle className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--color-text-muted)' }} />
                                )}
                                <span className="text-sm" style={{ color: f.included ? 'var(--color-text-secondary)' : 'var(--color-text-muted)' }}>
                                    {f.text}
                                </span>
                            </div>
                        ))}
                    </div>

                    {/* Credit costs breakdown */}
                    <div className="p-3 rounded-xl mb-4"
                        style={{ background: 'var(--color-glass)', border: '1px solid var(--color-glass-border)' }}>
                        <p className="text-xs font-medium mb-2" style={{ color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            Credit Usage
                        </p>
                        <div className="space-y-1.5">
                            {[
                                { label: 'Pool Verification', cost: `${CREDIT_COSTS.VERIFY} cr`, color: 'var(--color-gold)' },
                                { label: 'Filter / Search', cost: `${CREDIT_COSTS.FILTER} cr`, color: 'var(--color-gold)' },
                                { label: 'Premium Daily Bonus', cost: `${CREDIT_COSTS.PREMIUM_DAILY} cr / day`, color: 'var(--color-green)' },
                                { label: 'Welcome Bonus', cost: `${CREDIT_COSTS.WELCOME_BONUS} cr`, color: 'var(--color-accent)' },
                            ].map((item, i) => (
                                <div key={i} className="flex items-center justify-between text-xs">
                                    <span style={{ color: 'var(--color-text-secondary)' }}>
                                        {item.label}
                                    </span>
                                    <span className="font-heading font-semibold" style={{ color: item.color }}>{item.cost}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.97 }}
                        onClick={handleBuyCredits}
                        disabled={purchasing || !isConnected}
                        className="w-full py-3 rounded-xl text-sm font-heading font-semibold cursor-pointer flex items-center justify-center gap-2"
                        style={{
                            background: 'var(--color-glass)',
                            border: '1px solid var(--color-glass-border)',
                            color: isConnected ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
                            opacity: purchasing ? 0.7 : 1,
                        }}
                    >
                        {purchasing ? (
                            <><Loader2 className="w-4 h-4 animate-spin" /> Processing...</>
                        ) : !isConnected ? (
                            'Connect Wallet to Buy'
                        ) : (
                            <><Coins className="w-4 h-4" style={{ color: 'var(--color-gold)' }} /> Buy 100 Credits</>
                        )}
                    </motion.button>
                </motion.div>

                {/* Artisan Bot */}
                <motion.div
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="glass-card-gold p-4 sm:p-6 flex flex-col relative overflow-hidden"
                >
                    {/* Badge */}
                    <div className="absolute top-3 right-3 sm:top-5 sm:right-5">
                        <span
                            className="px-3 py-1 rounded-full text-xs font-heading font-bold"
                            style={{
                                background: 'linear-gradient(135deg, var(--color-gold), var(--color-gold-bright))',
                                color: 'var(--color-bg-primary)',
                            }}
                        >
                            <Bot className="w-3.5 h-3.5 inline mr-1" /> AI TRADING AGENT
                        </span>
                    </div>

                    <div className="text-center mb-5">
                        <p className="text-xs font-heading font-semibold tracking-widest mb-3" style={{ color: 'var(--color-gold)', textTransform: 'uppercase' }}>
                            ARTISAN BOT
                        </p>
                        <div className="flex items-baseline justify-center gap-1">
                            <span className="font-heading text-3xl sm:text-5xl font-bold" style={{ color: 'var(--color-text-primary)' }}>99</span>
                            <span className="text-lg" style={{ color: 'var(--color-text-muted)' }}>USDC/mo</span>
                        </div>
                    </div>

                    <div className="space-y-3 mb-6 flex-1">
                        {ARTISAN_FEATURES.map((f, i) => (
                            <div key={i} className="flex items-center gap-2.5">
                                <f.icon className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--color-gold)' }} />
                                <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                                    {f.text}
                                </span>
                            </div>
                        ))}
                    </div>

                    <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.97 }}
                        onClick={() => setShowSubscribeModal(true)}
                        disabled={!isConnected}
                        className="w-full py-3 rounded-xl text-sm font-heading font-bold cursor-pointer flex items-center justify-center gap-2"
                        style={{
                            background: 'linear-gradient(135deg, var(--color-gold), var(--color-gold-bright))',
                            color: 'var(--color-bg-primary)',
                            opacity: !isConnected ? 0.7 : 1,
                        }}
                    >
                        {!isConnected ? (
                            'Connect Wallet to Subscribe'
                        ) : (
                            <><MessageSquare className="w-4 h-4" /> SUBSCRIBE WITH USDC</>
                        )}
                    </motion.button>

                    {/* Settings link */}
                    <button
                        onClick={() => setShowSettings(true)}
                        className="mt-3 flex items-center justify-center gap-1.5 text-xs cursor-pointer"
                        style={{ background: 'none', border: 'none', color: 'var(--color-gold)', opacity: 0.7 }}
                    >
                        <Settings className="w-3.5 h-3.5" /> Configure Artisan Settings
                    </button>

                    <p className="text-center mt-2 text-xs" style={{ color: 'var(--color-text-muted)' }}>
                        <Lock className="w-3 h-3 inline mr-1" style={{ color: 'var(--color-text-muted)' }} /> Secure Access: Payment generates activation code. Connect via{' '}
                        <a
                            href={`https://t.me/${TELEGRAM_BOT}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: 'var(--color-gold)' }}
                        >
                            @{TELEGRAM_BOT}
                        </a>
                        {' '}on Telegram.
                    </p>
                </motion.div>
            </div>

            {/* Telegram Section */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="glass-card p-4 sm:p-6"
            >
                <div className="flex items-center gap-3 mb-3">
                    <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
                        style={{ background: 'var(--color-gold-dim)', border: '1px solid var(--color-gold-border)' }}
                    >
                        <Bot className="w-5 h-5" style={{ color: 'var(--color-gold)' }} />
                    </div>
                    <div>
                        <h3 className="font-heading text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
                            Techne Artisan Bot
                        </h3>
                        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                            Your personal AI trading agent on Telegram. Powered by OpenClaw MCP with 18 specialized DeFi tools.
                        </p>
                    </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">
                    {[
                        { title: 'Setup in 60 Seconds', desc: 'Subscribe → get activation code → open @TechneArtisanBot on Telegram → paste code → done' },
                        { title: 'Natural Language AI', desc: 'No complex UIs. Just type "find best yields" or "move 50% to Aave" — the bot handles everything' },
                        { title: 'Always-On Agent', desc: 'Runs 24/7 on our VPS infrastructure. Monitors positions, auto-compounds, guards against risk — even while you sleep' },
                    ].map((item, i) => (
                        <div
                            key={i}
                            className="p-3 rounded-xl"
                            style={{ background: 'var(--color-glass)', border: '1px solid var(--color-glass-border)' }}
                        >
                            <h4 className="text-sm font-heading font-semibold mb-1" style={{ color: 'var(--color-gold)' }}>
                                {item.title}
                            </h4>
                            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{item.desc}</p>
                        </div>
                    ))}
                </div>
            </motion.div>

            {/* ========== HOW IT WORKS ========== */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
                className="glass-card p-4 sm:p-6 mt-6"
            >
                <h3 className="font-heading text-lg font-bold text-center mb-6" style={{ color: 'var(--color-text-primary)' }}>
                    How It Works
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {HOW_IT_WORKS_STEPS.map((step, i) => (
                        <div key={i} className="relative">
                            <div className="flex flex-col items-center text-center p-4">
                                <div
                                    className="w-14 h-14 rounded-2xl flex items-center justify-center mb-3"
                                    style={{ background: 'var(--color-gold-dim)', border: '1px solid var(--color-gold-border)' }}
                                >
                                    <step.icon className="w-6 h-6" style={{ color: 'var(--color-gold)' }} />
                                </div>
                                <span className="text-xs font-mono font-bold mb-1" style={{ color: 'var(--color-gold)', opacity: 0.6 }}>
                                    STEP {step.step}
                                </span>
                                <h4 className="font-heading text-sm font-bold mb-1" style={{ color: 'var(--color-text-primary)' }}>
                                    {step.title}
                                </h4>
                                <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                                    {step.desc}
                                </p>
                            </div>
                            {i < 2 && (
                                <div className="hidden md:flex absolute top-1/2 -right-2 -translate-y-1/2">
                                    <ChevronRight className="w-4 h-4" style={{ color: 'var(--color-text-muted)', opacity: 0.3 }} />
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </motion.div>

            {/* ========== BOT SKILLS & CAPABILITIES ========== */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="glass-card-gold p-4 sm:p-6 mt-6"
            >
                <div className="flex items-center justify-between mb-5">
                    <div className="flex items-center gap-2">
                        <Bot className="w-5 h-5" style={{ color: 'var(--color-gold)' }} />
                        <h3 className="font-heading text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
                            Artisan Bot Skills
                        </h3>
                    </div>
                    <div className="flex items-center gap-1.5 px-3 py-1 rounded-full"
                        style={{ background: 'var(--color-gold-dim)', border: '1px solid var(--color-gold-border)' }}>
                        <Activity className="w-3 h-3" style={{ color: 'var(--color-green)' }} />
                        <span className="text-xs font-heading font-bold" style={{ color: 'var(--color-green)' }}>Online 24/7</span>
                    </div>
                </div>
                <p className="text-sm mb-5" style={{ color: 'var(--color-text-muted)' }}>
                    Powered by OpenClaw MCP framework. Your Artisan Bot connects directly to on-chain smart contracts — no API middlemen, no centralized custody.
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {BOT_SKILLS.map((f, i) => (
                        <div
                            key={i}
                            className="p-4 rounded-xl flex gap-3"
                            style={{ background: 'var(--color-glass)', border: '1px solid var(--color-glass-border)' }}
                        >
                            <div
                                className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                                style={{ background: 'var(--color-gold-dim)' }}
                            >
                                <f.icon className="w-4 h-4" style={{ color: 'var(--color-gold)' }} />
                            </div>
                            <div>
                                <h4 className="text-sm font-heading font-semibold mb-0.5" style={{ color: 'var(--color-text-primary)' }}>
                                    {f.title}
                                </h4>
                                <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{f.desc}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </motion.div>

            {/* ========== BOT ACTIVATION MODES ========== */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.42 }}
                className="glass-card p-4 sm:p-6 mt-6"
            >
                <div className="flex items-center gap-2 mb-2">
                    <Settings className="w-5 h-5" style={{ color: 'var(--color-gold)' }} />
                    <h3 className="font-heading text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
                        4 Operating Modes
                    </h3>
                </div>
                <p className="text-sm mb-5" style={{ color: 'var(--color-text-muted)' }}>
                    After activating your code in Telegram, choose a mode with <code style={{ color: 'var(--color-gold)', background: 'var(--color-glass)', padding: '1px 5px', borderRadius: '4px', fontSize: '11px' }}>/mode</code>. Change anytime.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {([
                        {
                            label: 'Observer',
                            icon: Eye,
                            badge: 'Read Only',
                            color: 'var(--color-accent)',
                            colorDim: 'rgba(99,102,241,0.1)',
                            setup: 'Provide your Smart Account address',
                            desc: 'Analysis only — no execution. Portfolio tracking, yield discovery, risk alerts.',
                            bullets: ['Portfolio analysis & P&L tracking', 'Yield opportunity scanner', 'Risk monitoring & alerts'],
                        },
                        {
                            label: 'Advisor',
                            icon: MessageSquare,
                            badge: 'Confirm Each Trade',
                            color: 'var(--color-gold)',
                            colorDim: 'var(--color-gold-dim)',
                            setup: 'Smart Account + Session Key',
                            desc: 'Bot suggests optimal moves and trade parameters. Every transaction requires your explicit confirmation.',
                            bullets: ['AI-generated trade suggestions', 'Manual confirm: true per trade', 'Full visibility before execution'],
                        },
                        {
                            label: 'Copilot',
                            icon: Zap,
                            badge: 'Auto < $1K',
                            color: '#f59e0b',
                            colorDim: 'rgba(245,158,11,0.1)',
                            setup: 'Smart Account + Session Key',
                            desc: 'Auto-executes trades under $1,000. Anything above requires your confirmation in chat.',
                            bullets: ['Auto-execute under $1K', 'Confirmation for larger trades', 'Best for active DeFi users'],
                        },
                        {
                            label: 'Full Auto',
                            icon: Bot,
                            badge: 'Autonomous',
                            color: 'var(--color-green)',
                            colorDim: 'var(--color-green-dim)',
                            setup: 'Session Key from Portfolio → Agent panel',
                            desc: 'Fully autonomous — bot executes, rebalances, and manages risk 24/7. Capped at $10K per transaction.',
                            bullets: ['24/7 auto-execution & rebalancing', 'Built-in risk engine & stop-loss', '$10,000 per-transaction cap'],
                        },
                    ]).map((mode, idx) => (
                        <div
                            key={idx}
                            className="p-4 rounded-xl flex flex-col"
                            style={{
                                background: 'var(--color-glass)',
                                border: `1px solid var(--color-glass-border)`,
                            }}
                        >
                            <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center gap-2">
                                    <div
                                        className="w-8 h-8 rounded-lg flex items-center justify-center"
                                        style={{ background: mode.colorDim }}
                                    >
                                        <mode.icon className="w-4 h-4" style={{ color: mode.color }} />
                                    </div>
                                    <span className="font-heading text-sm font-bold" style={{ color: 'var(--color-text-primary)' }}>
                                        {mode.label}
                                    </span>
                                </div>
                                <span className="text-[10px] font-heading font-bold px-2 py-0.5 rounded-full"
                                    style={{ background: mode.colorDim, color: mode.color, border: `1px solid ${mode.color}40` }}>
                                    {mode.badge}
                                </span>
                            </div>
                            <p className="text-xs mb-3" style={{ color: 'var(--color-text-muted)' }}>
                                {mode.desc}
                            </p>
                            <div className="space-y-1.5 mb-3 flex-1">
                                {mode.bullets.map((b, i) => (
                                    <div key={i} className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                                        <Check className="w-3 h-3 flex-shrink-0" style={{ color: mode.color }} />
                                        {b}
                                    </div>
                                ))}
                            </div>
                            <div className="mt-auto pt-3" style={{ borderTop: '1px solid var(--color-glass-border)' }}>
                                <p className="text-[10px] font-heading font-medium" style={{ color: 'var(--color-text-muted)' }}>
                                    SETUP
                                </p>
                                <p className="text-xs font-heading font-semibold" style={{ color: mode.color }}>
                                    {mode.setup}
                                </p>
                            </div>
                        </div>
                    ))}
                </div>
            </motion.div>

            {/* ========== ARTISAN SUB-AGENTS ========== */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.45 }}
                className="glass-card-gold p-4 sm:p-6 mt-6"
            >
                <div className="flex items-center gap-2 mb-4">
                    <Brain className="w-5 h-5" style={{ color: 'var(--color-gold)' }} />
                    <h3 className="font-heading text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
                        Artisan Sub-Agents
                    </h3>
                </div>
                <p className="text-sm mb-5" style={{ color: 'var(--color-text-muted)' }}>
                    Your Artisan Bot runs three specialized sub-agents that work together to find, protect, and grow your DeFi positions.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {SUB_AGENTS.map((agent, i) => (
                        <div
                            key={i}
                            className="p-4 rounded-xl"
                            style={{ background: 'var(--color-glass)', border: '1px solid var(--color-glass-border)' }}
                        >
                            <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center gap-2">
                                    <div
                                        className="w-8 h-8 rounded-lg flex items-center justify-center"
                                        style={{ background: 'var(--color-gold-dim)' }}
                                    >
                                        <agent.icon className="w-4 h-4" style={{ color: 'var(--color-gold)' }} />
                                    </div>
                                    <span className="font-heading text-sm font-bold" style={{ color: 'var(--color-text-primary)' }}>
                                        {agent.name}
                                    </span>
                                </div>
                                <span
                                    className="flex items-center gap-1 text-xs font-heading font-semibold px-2 py-0.5 rounded-full"
                                    style={{ background: `${agent.color}15`, color: agent.color }}
                                >
                                    <Activity className="w-3 h-3" />
                                    {agent.status}
                                </span>
                            </div>
                            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{agent.desc}</p>
                        </div>
                    ))}
                </div>
            </motion.div>

            {/* ========== EXAMPLE AI COMMANDS ========== */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="glass-card p-4 sm:p-6 mt-6"
            >
                <div className="flex items-center gap-2 mb-4">
                    <Terminal className="w-5 h-5" style={{ color: 'var(--color-gold)' }} />
                    <h3 className="font-heading text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
                        Talk to Your Agent
                    </h3>
                </div>
                <p className="text-sm mb-5" style={{ color: 'var(--color-text-muted)' }}>
                    No complex interfaces. Just tell your AI agent what you want in plain language.
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {EXAMPLE_COMMANDS.map((cmd, i) => (
                        <div
                            key={i}
                            className="flex items-center gap-3 p-3 rounded-xl"
                            style={{ background: 'var(--color-glass)', border: '1px solid var(--color-glass-border)' }}
                        >
                            <span
                                className="text-[10px] font-heading font-bold px-2 py-0.5 rounded flex-shrink-0"
                                style={{ background: 'var(--color-gold-dim)', color: 'var(--color-gold)', border: '1px solid var(--color-gold-border)' }}
                            >
                                {cmd.category}
                            </span>
                            <span className="text-xs font-mono" style={{ color: 'var(--color-text-secondary)' }}>
                                {cmd.cmd}
                            </span>
                        </div>
                    ))}
                </div>
            </motion.div>

            {/* ========== SUPPORTED PROTOCOLS ========== */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.55 }}
                className="glass-card p-4 sm:p-6 mt-6 mb-8"
            >
                <div className="flex items-center gap-2 mb-4">
                    <Globe className="w-5 h-5" style={{ color: 'var(--color-gold)' }} />
                    <h3 className="font-heading text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
                        Supported Protocols
                    </h3>
                </div>
                <p className="text-sm mb-4" style={{ color: 'var(--color-text-muted)' }}>
                    Your Artisan Bot can trade, stake, and manage liquidity across all these protocols — directly from Telegram.
                </p>
                <div className="flex flex-wrap gap-2">
                    {SUPPORTED_SOURCES.map((name, i) => (
                        <span
                            key={i}
                            className="px-3 py-1.5 rounded-lg text-xs font-heading font-medium"
                            style={{ background: 'var(--color-glass)', border: '1px solid var(--color-glass-border)', color: 'var(--color-text-secondary)' }}
                        >
                            {name}
                        </span>
                    ))}
                </div>
            </motion.div>

            {/* ========== ACTIVATION CODE MODAL ========== */}
            <AnimatePresence>
                {activationCode && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[100] flex items-center justify-center"
                        style={{ background: 'rgba(0,0,0,0.85)' }}
                        onClick={() => setActivationCode(null)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, y: 20 }}
                            animate={{ scale: 1, y: 0 }}
                            exit={{ scale: 0.9, y: 20 }}
                            onClick={e => e.stopPropagation()}
                            className="glass-card-gold p-5 sm:p-8 max-w-md mx-4 text-center relative"
                        >
                            {/* Close */}
                            <button
                                onClick={() => setActivationCode(null)}
                                className="absolute top-4 right-4 cursor-pointer"
                                style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)' }}
                            >
                                <X className="w-5 h-5" />
                            </button>

                            <PartyPopper className="w-10 h-10 mx-auto mb-4" style={{ color: 'var(--color-gold)' }} />
                            <h2 className="font-heading text-2xl font-bold mb-2" style={{ color: 'var(--color-gold)' }}>
                                Artisan Bot Activated!
                            </h2>
                            <p className="text-sm mb-6" style={{ color: 'var(--color-text-muted)' }}>
                                Send this code to @{TELEGRAM_BOT} on Telegram:
                            </p>

                            {/* Code display */}
                            <div
                                className="p-4 rounded-xl mb-6"
                                style={{
                                    background: 'var(--color-bg-primary)',
                                    border: '2px dashed var(--color-gold)',
                                }}
                            >
                                <code
                                    className="font-mono text-lg sm:text-2xl font-bold tracking-widest"
                                    style={{ color: 'var(--color-text-primary)' }}
                                >
                                    {activationCode}
                                </code>
                            </div>

                            <div className="flex flex-col gap-3">
                                <motion.button
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.97 }}
                                    onClick={copyCode}
                                    className="w-full py-3 rounded-xl text-sm font-heading font-semibold cursor-pointer flex items-center justify-center gap-2"
                                    style={{
                                        background: 'var(--color-glass)',
                                        border: '1px solid var(--color-gold-border)',
                                        color: 'var(--color-text-primary)',
                                    }}
                                >
                                    {codeCopied ? (
                                        <><Check className="w-4 h-4" style={{ color: 'var(--color-green)' }} /> Copied!</>
                                    ) : (
                                        <><Copy className="w-4 h-4" /> Copy Code</>
                                    )}
                                </motion.button>

                                <a
                                    href={`https://t.me/${TELEGRAM_BOT}?start=${activationCode}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="w-full py-3 rounded-xl text-sm font-heading font-bold flex items-center justify-center gap-2 no-underline"
                                    style={{
                                        background: 'var(--color-blue)',
                                        color: '#fff',
                                    }}
                                >
                                    <ExternalLink className="w-4 h-4" /> Open Telegram
                                </a>
                            </div>

                            <p className="mt-4 text-xs" style={{ color: 'var(--color-text-muted)' }}>
                                After activation, choose your autonomy mode and start trading!
                            </p>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ========== UPGRADE MODAL (no credits) ========== */}
            <AnimatePresence>
                {showUpgrade && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[100] flex items-center justify-center"
                        style={{ background: 'rgba(0,0,0,0.85)' }}
                        onClick={() => setShowUpgrade(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, y: 20 }}
                            animate={{ scale: 1, y: 0 }}
                            exit={{ scale: 0.9, y: 20 }}
                            onClick={e => e.stopPropagation()}
                            className="glass-card p-6 max-w-sm mx-4 text-center"
                        >
                            <Lock className="w-8 h-8 mx-auto mb-3" style={{ color: 'var(--color-text-muted)' }} />
                            <h3 className="font-heading text-lg font-bold mb-2" style={{ color: 'var(--color-text-primary)' }}>
                                No Search Credits
                            </h3>
                            <p className="text-sm mb-5" style={{ color: 'var(--color-text-muted)' }}>
                                You need credits to search pools. Choose an option:
                            </p>

                            <div className="space-y-2">
                                <motion.button
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.97 }}
                                    onClick={() => { setShowUpgrade(false); handleBuyCredits() }}
                                    className="w-full p-3 rounded-xl cursor-pointer flex items-center justify-between"
                                    style={{
                                        background: 'var(--color-glass)',
                                        border: '1px solid var(--color-glass-border)',
                                        color: 'var(--color-text-primary)',
                                    }}
                                >
                                    <span className="text-sm font-medium flex items-center gap-1.5"><CreditCard className="w-3.5 h-3.5" /> Buy 100 Credits</span>
                                    <span className="text-sm font-heading font-bold" style={{ color: 'var(--color-gold)' }}>$0.10</span>
                                </motion.button>

                                <motion.button
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.97 }}
                                    onClick={() => { setShowUpgrade(false); handleSubscribe() }}
                                    className="w-full p-3 rounded-xl cursor-pointer flex items-center justify-between"
                                    style={{
                                        background: 'var(--color-gold-dim)',
                                        border: '1px solid var(--color-gold-border)',
                                        color: 'var(--color-text-primary)',
                                    }}
                                >
                                    <div className="text-left">
                                        <div className="text-sm font-medium flex items-center gap-1.5"><Bot className="w-3.5 h-3.5" /> Artisan Bot</div>
                                        <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>AI Trading Agent + TG</div>
                                    </div>
                                    <span className="text-sm font-heading font-bold" style={{ color: 'var(--color-gold)' }}>$99/mo</span>
                                </motion.button>

                                <button
                                    onClick={() => setShowUpgrade(false)}
                                    className="w-full py-2 text-sm cursor-pointer"
                                    style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)' }}
                                >
                                    Maybe later
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ========== ARTISAN SETTINGS MODAL ========== */}
            <AnimatePresence>
                {showSettings && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[100] flex items-center justify-center"
                        style={{ background: 'rgba(0,0,0,0.85)' }}
                        onClick={() => setShowSettings(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, y: 20 }}
                            animate={{ scale: 1, y: 0 }}
                            exit={{ scale: 0.9, y: 20 }}
                            onClick={e => e.stopPropagation()}
                            className="glass-card-gold p-6 max-w-md mx-4 w-full"
                        >
                            {/* Close */}
                            <button
                                onClick={() => setShowSettings(false)}
                                className="absolute top-4 right-4 cursor-pointer"
                                style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)' }}
                            >
                                <X className="w-5 h-5" />
                            </button>

                            <div className="flex items-center gap-2 mb-5">
                                <Settings className="w-5 h-5" style={{ color: 'var(--color-gold)' }} />
                                <h3 className="font-heading text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
                                    Artisan Bot Settings
                                </h3>
                            </div>

                            <div className="space-y-5">
                                {/* Max Trade Size */}
                                <div>
                                    <div className="flex items-center justify-between mb-2">
                                        <label className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                                            Max Trade Size
                                        </label>
                                        <span className="text-sm font-heading font-bold" style={{ color: 'var(--color-gold)' }}>
                                            ${artisanSettings.maxTradeSize.toLocaleString()}
                                        </span>
                                    </div>
                                    <input
                                        type="range"
                                        min={100}
                                        max={10000}
                                        step={100}
                                        value={artisanSettings.maxTradeSize}
                                        onChange={e => setArtisanSettings(prev => ({ ...prev, maxTradeSize: parseInt(e.target.value) }))}
                                        className="w-full accent-gold"
                                        style={{ accentColor: 'var(--color-gold)' }}
                                    />
                                    <div className="flex justify-between text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
                                        <span>$100</span>
                                        <span>$10,000</span>
                                    </div>
                                </div>

                                {/* Risk Level */}
                                <div>
                                    <label className="text-sm mb-2 block" style={{ color: 'var(--color-text-secondary)' }}>
                                        Risk Level
                                    </label>
                                    <div className="flex gap-2">
                                        {(['low', 'medium', 'high'] as const).map(level => (
                                            <button
                                                key={level}
                                                onClick={() => setArtisanSettings(prev => ({ ...prev, riskLevel: level }))}
                                                className="flex-1 py-2 rounded-lg text-xs font-heading font-semibold cursor-pointer transition-all capitalize"
                                                style={{
                                                    background: artisanSettings.riskLevel === level
                                                        ? 'var(--color-gold-dim)' : 'var(--color-glass)',
                                                    border: `1px solid ${artisanSettings.riskLevel === level
                                                        ? 'var(--color-gold-border)' : 'var(--color-glass-border)'}`,
                                                    color: artisanSettings.riskLevel === level
                                                        ? 'var(--color-gold)' : 'var(--color-text-muted)',
                                                }}
                                            >
                                                {level === 'low' ? <Shield className="w-3 h-3 inline" /> : level === 'medium' ? <Zap className="w-3 h-3 inline" /> : <Flame className="w-3 h-3 inline" />} {level}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* Toggles */}
                                {[
                                    { key: 'autoRebalance', label: 'Auto-Rebalance', desc: 'Automatically rebalance positions' },
                                    { key: 'telegramAlerts', label: 'Telegram Alerts', desc: 'Get real-time notifications' },
                                    { key: 'emergencyExit', label: 'Emergency Exit', desc: 'Auto-exit on high drawdown' },
                                ].map(toggle => (
                                    <div key={toggle.key} className="flex items-center justify-between">
                                        <div>
                                            <div className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
                                                {toggle.label}
                                            </div>
                                            <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                                                {toggle.desc}
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => setArtisanSettings(prev => ({
                                                ...prev,
                                                [toggle.key]: !(prev as any)[toggle.key]
                                            }))}
                                            className="cursor-pointer"
                                            style={{ background: 'none', border: 'none' }}
                                        >
                                            {(artisanSettings as any)[toggle.key] ? (
                                                <ToggleRight className="w-8 h-8" style={{ color: 'var(--color-gold)' }} />
                                            ) : (
                                                <ToggleLeft className="w-8 h-8" style={{ color: 'var(--color-text-muted)' }} />
                                            )}
                                        </button>
                                    </div>
                                ))}

                                {/* Auto-Renewal */}
                                <div
                                    className="p-4 rounded-xl mt-2"
                                    style={{
                                        background: renewalStatus?.auto_renewal_enabled
                                            ? 'rgba(255, 200, 55, 0.08)'
                                            : 'var(--color-glass)',
                                        border: `1px solid ${renewalStatus?.auto_renewal_enabled
                                            ? 'var(--color-gold-border)'
                                            : 'var(--color-glass-border)'}`
                                    }}
                                >
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <CreditCard className="w-4 h-4" style={{ color: 'var(--color-gold)' }} />
                                                <span className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
                                                    Auto-Renewal
                                                </span>
                                            </div>
                                            <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
                                                Bot auto-pays $99 USDC from agent wallet before expiry
                                            </p>
                                        </div>
                                        <button
                                            onClick={handleToggleRenewal}
                                            disabled={togglingRenewal || !renewalStatus?.can_enable}
                                            className="cursor-pointer"
                                            style={{
                                                background: 'none',
                                                border: 'none',
                                                opacity: (!renewalStatus?.can_enable || togglingRenewal) ? 0.4 : 1
                                            }}
                                            title={!renewalStatus?.can_enable
                                                ? `Missing: ${renewalStatus?.missing?.join(', ') || 'agent wallet'}`
                                                : renewalStatus?.auto_renewal_enabled ? 'Disable auto-renewal' : 'Enable auto-renewal'
                                            }
                                        >
                                            {togglingRenewal ? (
                                                <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'var(--color-gold)' }} />
                                            ) : renewalStatus?.auto_renewal_enabled ? (
                                                <ToggleRight className="w-8 h-8" style={{ color: 'var(--color-gold)' }} />
                                            ) : (
                                                <ToggleLeft className="w-8 h-8" style={{ color: 'var(--color-text-muted)' }} />
                                            )}
                                        </button>
                                    </div>
                                    {renewalStatus?.auto_renewal_enabled && renewalStatus?.expires_at && (
                                        <p className="text-xs mt-2" style={{ color: 'var(--color-gold)', opacity: 0.8 }}>
                                            Next renewal: {new Date(renewalStatus.expires_at).toLocaleDateString()}
                                            {renewalStatus.agent_address && ` · from ${renewalStatus.agent_address.slice(0, 6)}...${renewalStatus.agent_address.slice(-4)}`}
                                        </p>
                                    )}
                                    {renewalStatus?.last_failed && (
                                        <p className="text-xs mt-1 flex items-center gap-1" style={{ color: 'var(--color-red, #ef4444)' }}>
                                            <AlertTriangle className="w-3 h-3" />
                                            Last renewal failed. Ensure agent has sufficient USDC.
                                        </p>
                                    )}
                                    {!renewalStatus?.can_enable && (
                                        <p className="text-xs mt-2" style={{ color: 'var(--color-text-muted)' }}>
                                            <Lock className="w-3 h-3 inline mr-1" />
                                            Requires active agent wallet. Activate your code in Telegram first.
                                        </p>
                                    )}
                                </div>
                            </div>

                            {/* Save */}
                            <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.97 }}
                                onClick={handleSaveSettings}
                                disabled={savingSettings}
                                className="w-full py-3 mt-6 rounded-xl text-sm font-heading font-bold cursor-pointer flex items-center justify-center gap-2"
                                style={{
                                    background: 'linear-gradient(135deg, var(--color-gold), var(--color-gold-bright))',
                                    color: 'var(--color-bg-primary)',
                                    opacity: savingSettings ? 0.7 : 1,
                                }}
                            >
                                {savingSettings ? (
                                    <><Loader2 className="w-4 h-4 animate-spin" /> Saving...</>
                                ) : (
                                    <><CheckCircle2 className="w-4 h-4" /> Save Settings</>
                                )}
                            </motion.button>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Subscribe Modal */}
            <SubscribeModal
                isOpen={showSubscribeModal}
                onClose={() => setShowSubscribeModal(false)}
                onSuccess={(code) => {
                    setActivationCode(code)
                    setSubStatus({ subscribed: true, status: 'active' })
                }}
            />
        </div>
    )
}

// Export upgrade modal trigger for use by other pages
export function useUpgradeModal() {
    // This hook can be used by ExplorePage etc. to show upgrade modal
    // For now it triggers navigation to premium page
    return {
        showUpgrade: () => {
            toast.warning('No credits remaining. Visit Premium page to buy more.')
        }
    }
}
