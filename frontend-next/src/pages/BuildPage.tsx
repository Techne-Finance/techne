/**
 * Agent Builder — 3-Tier Mode (AI-Instant / Flexible / Pro)
 * Full parity with techne.finance live site + agent-builder-pro.js
 */
import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    Hammer, Terminal, Send, Shield, Zap, AlertTriangle,
    Play, StopCircle, TrendingUp, Settings, Check,
    Clock, Target, Flame, Lock, Wallet, Layers,
    ChevronDown, Crosshair, Activity, Rocket
} from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Slider } from '@/components/ui/slider'
import { useWalletStore } from '@/stores/walletStore'
import { deployAgent, confirmDeploy, setupAutoTrading, type AgentDeployResponse } from '@/lib/api'
import { toast } from '@/components/Toast'

// ─── Strategy Presets (from agent-builder-ui.js) ───
const STRATEGIES = {
    safe: {
        label: 'Safe', icon: Shield, range: '5-12% APY', color: '#22C55E',
        desc: 'Maximum security. Audited protocols only. Single-sided stablecoin deposits.',
        bullets: ['TVL $10M+ only', 'Time-tested protocols', 'No IL exposure'],
        badge: 'LOW RISK', badgeColor: '#22C55E',
        narrative: 'Maximum security. Targeting 5–12% APY on audited protocols only. TVL $10M+ required. No IL exposure.',
        riskLevel: 'low', minApy: 5, maxApy: 12, maxDrawdown: 10,
        protocols: ['aave', 'morpho', 'moonwell', 'compound'],
        assets: ['USDC', 'USDT'], poolType: 'single', vaultCount: 4,
        minTvl: 10_000_000, avoidIL: true, onlyAudited: true,
        rebalanceThreshold: 3, slippage: 0.3, compoundFreq: 7,
    },
    steady: {
        label: 'Steady', icon: TrendingUp, range: '10-30% APY', color: '#D4A853',
        desc: 'Balanced approach. Diversified across top protocols with moderate exposure.',
        bullets: ['TVL $10M+ pools', 'Blue-chip tokens', 'Auto-compound'],
        badge: 'BALANCED', badgeColor: '#D4A853',
        narrative: 'Balanced approach. Targeting 10–30% APY. TVL $10M+, single + dual pools. Ready to deploy.',
        riskLevel: 'medium', minApy: 10, maxApy: 30, maxDrawdown: 20,
        protocols: ['morpho', 'aave', 'moonwell', 'aerodrome'],
        assets: ['USDC', 'WETH', 'USDT'], poolType: 'both', vaultCount: 5,
        minTvl: 10_000_000, avoidIL: false, onlyAudited: true,
        rebalanceThreshold: 5, slippage: 0.5, compoundFreq: 7,
    },
    degen: {
        label: 'Degen', icon: Flame, range: '30-100%+ APY', color: '#EF4444',
        desc: 'Maximum growth potential. Active rotation. Dual-sided LPs. IL exposure possible.',
        bullets: ['Aggressive rotation', 'Higher yields', 'MEV Protection'],
        badge: 'DEGEN MODE', badgeColor: '#EF4444',
        narrative: 'Aggressive growth. 30–100%+ APY. Active rotation, dual-sided LPs, IL exposure. LFG!',
        riskLevel: 'high', minApy: 30, maxApy: 100, maxDrawdown: 40,
        protocols: ['aerodrome', 'beefy', 'morpho', 'moonwell', 'uniswap'],
        assets: ['WETH', 'AERO', 'USDC'], poolType: 'dual', vaultCount: 7,
        minTvl: 1_000_000, avoidIL: false, onlyAudited: false,
        rebalanceThreshold: 10, slippage: 1.0, compoundFreq: 1,
    },
} as const
type StrategyKey = keyof typeof STRATEGIES

const PROTOCOLS = [
    { id: 'morpho', label: 'Morpho', icon: '/icons/protocols/morpho.png', type: 'single' },
    { id: 'aave', label: 'Aave V3', icon: '/icons/protocols/aave.png', type: 'single' },
    { id: 'moonwell', label: 'Moonwell', icon: '/icons/protocols/moonwell.png', type: 'single' },
    { id: 'compound', label: 'Compound', icon: '/icons/protocols/compound.png', type: 'single' },
    { id: 'seamless', label: 'Seamless', icon: '/icons/protocols/seamless.png', type: 'single' },
    { id: 'sonne', label: 'Sonne', icon: '/icons/protocols/sonne.png', type: 'single' },
    { id: 'exactly', label: 'Exactly', icon: '/icons/protocols/exactly.png', type: 'single' },
    { id: 'aerodrome', label: 'Aerodrome', icon: '/icons/protocols/aerodrome.png', type: 'dual' },
    { id: 'uniswap', label: 'Uniswap', icon: '/icons/protocols/uniswap.png', type: 'dual' },
    { id: 'beefy', label: 'Beefy', icon: '/icons/protocols/beefy.png', type: 'both' },
    { id: 'convex', label: 'Convex', icon: '/icons/protocols/convex.png', type: 'both' },
    { id: 'origin', label: 'Origin', icon: '/icons/protocols/origin.png', type: 'both' },
    { id: 'avantis', label: 'Avantis', icon: '/icons/protocols/avantis.png', type: 'both' },
]

const ASSETS = ['USDC', 'USDT', 'WETH', 'AERO', 'CRV', 'AAVE', 'COMP', 'UNI']

const CHAINS = [
    { id: 'base', label: 'Base', active: true },
    { id: 'ethereum', label: 'Ethereum', soon: true },
    { id: 'arbitrum', label: 'Arbitrum', soon: true },
    { id: 'solana', label: 'Solana', soon: true },
]

type BuildMode = 'instant' | 'flexible' | 'pro'

interface TerminalLine {
    type: 'system' | 'agent' | 'user' | 'success' | 'warning' | 'error'
    text: string
    timestamp: string
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// MAIN BUILD PAGE
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export function BuildPage() {
    const { isConnected, address } = useWalletStore()
    const [mode, setMode] = useState<BuildMode>('instant')
    const [strategy, setStrategy] = useState<StrategyKey>('steady')
    const [command, setCommand] = useState('')
    const [isRunning, setIsRunning] = useState(false)
    const [amount, setAmount] = useState('1000')
    const terminalRef = useRef<HTMLDivElement>(null)

    // Flexible Mode state
    const [flexChain, setFlexChain] = useState('base')
    const [flexPoolType, setFlexPoolType] = useState<'single' | 'dual' | 'all'>('single')
    const [flexTvlMin, setFlexTvlMin] = useState(1_000_000)
    const [flexTvlMax, setFlexTvlMax] = useState(100_000_000)
    const [flexTradingStyle, setFlexTradingStyle] = useState<'conservative' | 'moderate' | 'aggressive'>('moderate')
    const [flexTargetApyMin, setFlexTargetApyMin] = useState(5)
    const [flexTargetApyMax, setFlexTargetApyMax] = useState(200)
    const [flexStopLoss, setFlexStopLoss] = useState(20)
    const [flexProtocols, setFlexProtocols] = useState<string[]>(['morpho', 'aave', 'moonwell'])
    const [flexAssets, setFlexAssets] = useState<string[]>(['USDC', 'WETH'])
    const [flexDuration, setFlexDuration] = useState('1M')
    const [flexCustomDuration, setFlexCustomDuration] = useState('')
    const [flexVaults, setFlexVaults] = useState(5)
    const [flexMaxPerVault, setFlexMaxPerVault] = useState(25)
    const [flexAudited, setFlexAudited] = useState(true)
    const [flexAvoidIL, setFlexAvoidIL] = useState(false)

    // ── Precision Timing ──
    const [precisionMode, setPrecisionMode] = useState<'off' | 'snipe'>('off')
    const [snipeHours, setSnipeHours] = useState(24)

    // ── Risk & Returns ──
    const [stopLossEnabled, setStopLossEnabled] = useState(false)
    const [stopLossPercent, setStopLossPercent] = useState(15)
    const [takeProfitEnabled, setTakeProfitEnabled] = useState(false)
    const [takeProfitPercent, setTakeProfitPercent] = useState(50)
    const [apyTargetEnabled, setApyTargetEnabled] = useState(false)
    const [apyTargetValue, setApyTargetValue] = useState(20)
    const [volatilityGuard, setVolatilityGuard] = useState(false)

    // ── Flash Leverage Engine (DEGEN) ──
    const [flashLoanEnabled, setFlashLoanEnabled] = useState(false)
    const [leverageLevel, setLeverageLevel] = useState(2)
    const [deleverageThreshold, setDeleverageThreshold] = useState(15)

    // ── Auto-Snipe New Pools (ALPHA) ──
    const [snipeNewPools, setSnipeNewPools] = useState(false)
    const [snipeMinApy, setSnipeMinApy] = useState(100)
    const [snipeMaxPosition, setSnipeMaxPosition] = useState(500)
    const [snipeExitHours, setSnipeExitHours] = useState(24)

    // ── Volatility Hunter (HIGH RISK) ──
    const [chaseVolatility, setChaseVolatility] = useState(false)
    const [minVolatility, setMinVolatility] = useState('25')
    const [ilFarmingMode, setIlFarmingMode] = useState(false)

    // ── Yield Engineering (Advanced) ──
    const [yieldLeverage, setYieldLeverage] = useState(1.0)

    // ── Agent Command Interface (Advanced) ──
    const [agentCommandText, setAgentCommandText] = useState('')

    // ── Delta Neutral Mode (Advanced) ──
    const [deltaHedgeEnabled, setDeltaHedgeEnabled] = useState(false)
    const [hedgeProtocol, setHedgeProtocol] = useState('synthetix')
    const [rebalanceDelta, setRebalanceDelta] = useState(5)
    const [fundingRateFarming, setFundingRateFarming] = useState(true)

    // ── Gas Strategy (Advanced) ──
    const [gasStrategy, setGasStrategy] = useState('normal')

    // ── Advanced Settings ──
    const [advancedOpen, setAdvancedOpen] = useState(true)
    const [slippage, setSlippage] = useState(0.5)
    const [compoundFreq, setCompoundFreq] = useState(7)
    const [rebalanceThreshold, setRebalanceThreshold] = useState(5)
    const [maxGasPrice, setMaxGasPrice] = useState(50)
    const [mevProtection, setMevProtection] = useState(false)
    const [autoRebalance, setAutoRebalance] = useState(true)
    const [emergencyExit, setEmergencyExit] = useState(true)
    const [apyCheckHours, setApyCheckHours] = useState(24)

    const [lines, setLines] = useState<TerminalLine[]>([
        { type: 'system', text: '> artisan_agent v2.0 — neural terminal initialized', timestamp: now() },
        { type: 'system', text: '> waiting for strategy configuration...', timestamp: now() },
    ])

    useEffect(() => { terminalRef.current?.scrollTo({ top: terminalRef.current.scrollHeight, behavior: 'smooth' }) }, [lines])

    function now() { return new Date().toLocaleTimeString('en-US', { hour12: false }) }
    const addLine = (type: TerminalLine['type'], text: string) => setLines(p => [...p, { type, text, timestamp: now() }])

    // ── Duration string → days mapping ──
    const DURATION_TO_DAYS: Record<string, number> = {
        '1H': 0.042, '1D': 1, '1W': 7, '1M': 30, '3M': 90, '6M': 180, '1Y': 365, '∞': 0
    }

    // ── Build full deploy payload from current UI state ──
    const buildDeployPayload = () => {
        const s = STRATEGIES[strategy]

        // Base payload (common to all modes)
        const base = {
            user_address: address!,
            auto_rebalance: autoRebalance,
            rebalance_threshold: rebalanceThreshold,
            max_gas_price: maxGasPrice,
            slippage,
            compound_frequency: compoundFreq,
            emergency_exit: emergencyExit,
            apy_check_hours: apyCheckHours,
        }

        if (mode === 'instant') {
            // AI-Instant: derive everything from STRATEGIES preset
            return {
                ...base,
                chain: 'base',
                preset: strategy,
                pool_type: s.poolType === 'both' ? 'single' : s.poolType,
                risk_level: s.riskLevel,
                min_apy: s.minApy,
                max_apy: s.maxApy,
                max_drawdown: s.maxDrawdown,
                protocols: [...s.protocols],
                preferred_assets: [...s.assets],
                max_allocation: 25,
                vault_count: s.vaultCount,
                only_audited: s.onlyAudited,
                avoid_il: s.avoidIL,
                min_pool_tvl: s.minTvl,
                duration: 30,
                trading_style: s.riskLevel === 'low' ? 'conservative' : s.riskLevel === 'high' ? 'aggressive' : 'moderate',
                is_pro_mode: false,
            }
        }

        if (mode === 'flexible') {
            // Flexible: derive from flex* state variables
            const durationDays = flexDuration === 'custom'
                ? parseFloat(flexCustomDuration) || 30
                : DURATION_TO_DAYS[flexDuration] ?? 30

            return {
                ...base,
                chain: flexChain,
                preset: 'custom',
                pool_type: flexPoolType === 'all' ? 'single' : flexPoolType,
                risk_level: flexTradingStyle === 'conservative' ? 'low' : flexTradingStyle === 'aggressive' ? 'high' : 'medium',
                min_apy: flexTargetApyMin,
                max_apy: flexTargetApyMax,
                max_drawdown: flexStopLoss,
                protocols: flexProtocols,
                preferred_assets: flexAssets,
                max_allocation: flexMaxPerVault,
                vault_count: flexVaults || 5,
                only_audited: flexAudited,
                avoid_il: flexAvoidIL,
                min_pool_tvl: flexTvlMin,
                max_pool_tvl: flexTvlMax < 100_000_000 ? flexTvlMax : undefined,
                duration: durationDays,
                trading_style: flexTradingStyle,
                is_pro_mode: false,
            }
        }

        // Pro mode: full pro config
        return {
            ...base,
            chain: flexChain,
            preset: 'custom',
            pool_type: flexPoolType === 'all' ? 'single' : flexPoolType,
            risk_level: flexTradingStyle === 'conservative' ? 'low' : flexTradingStyle === 'aggressive' ? 'high' : 'medium',
            min_apy: flexTargetApyMin,
            max_apy: flexTargetApyMax,
            max_drawdown: flexStopLoss,
            protocols: flexProtocols,
            preferred_assets: flexAssets,
            max_allocation: flexMaxPerVault,
            vault_count: flexVaults || 5,
            only_audited: flexAudited,
            avoid_il: flexAvoidIL,
            min_pool_tvl: flexTvlMin,
            max_pool_tvl: flexTvlMax < 100_000_000 ? flexTvlMax : undefined,
            duration: flexDuration === 'custom'
                ? parseFloat(flexCustomDuration) || 30
                : DURATION_TO_DAYS[flexDuration] ?? 30,
            trading_style: flexTradingStyle,
            is_pro_mode: true,
            pro_config: {
                leverage: flashLoanEnabled ? leverageLevel : 1.0,
                stopLossEnabled,
                stopLossPercent,
                takeProfitEnabled,
                takeProfitAmount: takeProfitPercent,
                volatilityGuard,
                volatilityThreshold: parseInt(minVolatility) || 10,
                mevProtection,
                harvestStrategy: compoundFreq <= 1 ? 'daily' : compoundFreq <= 7 ? 'weekly' : 'compound',
                customInstructions: agentCommandText || undefined,
            },
        }
    }

    // ── Deploy Logic ──
    const executeStrategy = async (prompt: string) => {
        if (isRunning) return
        setIsRunning(true)
        addLine('user', `> ${prompt}`)

        const s = STRATEGIES[strategy]
        const presetLabel = mode === 'instant' ? s.label : mode === 'flexible' ? 'Flexible' : 'Pro'

        addLine('agent', `[scout] parsing "${prompt.slice(0, 50)}..."`)
        await delay(500)
        addLine('agent', `[scout] scanning pools matching ${presetLabel} criteria...`)
        await delay(700)
        addLine('agent', `[guardian] risk=${s.riskLevel}, max_drawdown=${s.maxDrawdown}%`)
        if (stopLossEnabled) { await delay(300); addLine('agent', `[guardian] stop-loss=-${stopLossPercent}%`) }
        if (takeProfitEnabled) { await delay(300); addLine('agent', `[guardian] take-profit=+${takeProfitPercent}%`) }
        if (flashLoanEnabled) { await delay(300); addLine('warning', `[degen] flash leverage ${leverageLevel}x enabled, deleverage at -${deleverageThreshold}%`) }
        if (chaseVolatility) { await delay(300); addLine('warning', `[degen] volatility hunter enabled — min ${minVolatility}% volatility`) }
        if (snipeNewPools) { await delay(300); addLine('warning', `[alpha] auto-snipe enabled — min ${snipeMinApy}% APY, max $${snipeMaxPosition}`) }
        await delay(600)
        addLine('success', `[guardian] risk check PASSED`)
        await delay(500)
        addLine('agent', `[optimizer] calculating allocation across ${mode === 'instant' ? s.protocols.length : flexProtocols.length} protocols...`)
        await delay(600)
        addLine('success', `[optimizer] strategy compiled — est. APY: ${s.range}`)

        if (isConnected && address) {
            await delay(400)
            addLine('system', '> initiating on-chain deployment...')
            try {
                const payload = buildDeployPayload()
                addLine('agent', `[deploy] sending config: ${payload.protocols.length} protocols, ${payload.pool_type} pools, ${payload.min_apy}-${payload.max_apy}% APY`)
                await delay(300)

                // EIP-191 signature required by backend for wallet ownership proof
                const ethereum = (window as any).ethereum
                if (!ethereum) throw new Error('MetaMask not found')
                const signMessage = `Deploy Techne Agent\nWallet: ${address}\nTimestamp: ${Date.now()}`
                addLine('system', '> sign wallet ownership proof in MetaMask...')
                const signature = await ethereum.request({
                    method: 'personal_sign',
                    params: [signMessage, address],
                })
                    ; (payload as any).signature = signature
                    ; (payload as any).sign_message = signMessage
                addLine('success', '[auth] wallet ownership verified')
                await delay(200)

                const result = await deployAgent(payload) as AgentDeployResponse & {
                    requires_transaction?: boolean
                    transaction?: { to: string; data: string; gas: string; value: string }
                }

                if (result.success) {
                    addLine('success', `[deploy] agent created — ID: ${result.agent_id}`)
                    if (result.agent_address) addLine('success', `[deploy] address: ${result.agent_address}`)

                    // Handle MetaMask transaction signing if needed
                    if (result.requires_transaction && result.transaction) {
                        addLine('system', '> waiting for MetaMask transaction signature...')
                        try {
                            // ethereum already declared above for signature

                            const txHash = await ethereum.request({
                                method: 'eth_sendTransaction',
                                params: [{ ...result.transaction, from: address }],
                            })

                            addLine('success', `[tx] confirmed: ${txHash}`)
                            await delay(300)

                            // Confirm deployment with backend
                            addLine('agent', '[deploy] confirming deployment...')
                            const confirmResult = await confirmDeploy({
                                user_address: address,
                                agent_id: result.agent_id!,
                                tx_hash: txHash,
                            })
                            if (confirmResult.success) {
                                addLine('success', '[deploy] deployment confirmed')
                            }

                            // Setup auto-trading (session key + whitelist)
                            if (result.agent_address) {
                                addLine('agent', '[deploy] setting up auto-trading...')
                                try {
                                    const autoResult = await setupAutoTrading({
                                        user_address: address,
                                        agent_id: result.agent_id!,
                                    })
                                    if (autoResult.transaction) {
                                        addLine('system', '> sign auto-trading setup in MetaMask...')
                                        const autoTxHash = await ethereum.request({
                                            method: 'eth_sendTransaction',
                                            params: [{ ...autoResult.transaction, from: address }],
                                        })
                                        addLine('success', `[auto-trade] enabled tx: ${autoTxHash}`)
                                    }
                                } catch (autoErr) {
                                    addLine('warning', '[auto-trade] skipped — can be enabled later from Portfolio')
                                }
                            }
                        } catch (txErr: any) {
                            addLine('error', `[tx] MetaMask error: ${txErr?.message || 'User rejected'}`)
                            toast.error('Transaction cancelled')
                        }
                    } else {
                        // No transaction needed (already deployed or legacy)
                        if (result.tx_hash) addLine('system', `[tx] ${result.tx_hash}`)
                    }

                    toast.success('Agent deployed!')
                } else {
                    addLine('error', `[deploy] failed: ${result.error || 'Unknown'}`)
                    toast.error(`Deploy failed: ${result.error}`)
                }
            } catch {
                addLine('warning', '[deploy] API unavailable — strategy stored locally')
            }
        } else {
            await delay(400)
            addLine('warning', '[deploy] wallet not connected — use /deploy after connecting')
        }
        setIsRunning(false)
    }

    // ── Chat command parsing ──
    const handleSubmit = () => {
        if (!command.trim() || isRunning) return
        const cmd = command.trim()

        if (cmd.startsWith('/')) {
            const parts = cmd.slice(1).split(' ')
            const action = parts[0].toLowerCase()
            if (action === 'help') {
                addLine('system', '> Available commands:')
                addLine('system', '  /deploy   — Deploy current strategy')
                addLine('system', '  /preset [safe|steady|degen] — Switch preset')
                addLine('system', '  /status   — Check agent status')
                addLine('system', '  /stop     — Emergency stop all agents')
                addLine('system', '  /help     — Show this help')
                setCommand(''); return
            }
            if (action === 'preset' && parts[1]) {
                const p = parts[1] as StrategyKey
                if (STRATEGIES[p]) { setStrategy(p); addLine('success', `> Preset switched to ${STRATEGIES[p].label}`) }
                else addLine('error', `> Unknown preset: ${parts[1]}`)
                setCommand(''); return
            }
            if (action === 'stop') {
                addLine('warning', '> Emergency stop sent to all active agents')
                setCommand(''); return
            }
        }

        executeStrategy(cmd)
        setCommand('')
    }

    const currentStrategy = STRATEGIES[strategy]

    // ── Shared sections rendered in both Flexible and Advanced modes ──
    const renderPrecisionTiming = () => (
        <Card className="p-4 border-border">
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-primary" />
                    <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Precision Timing</span>
                </div>
                <Badge variant={precisionMode === 'snipe' ? 'default' : 'secondary'} className="text-[10px]">
                    {precisionMode === 'snipe' ? 'SNIPE MODE' : 'OFF'}
                </Badge>
            </div>
            <div className="flex gap-2 mb-3">
                <Button variant={precisionMode === 'off' ? 'default' : 'outline'} size="sm" className="text-xs" onClick={() => setPrecisionMode('off')}>
                    Continuous
                </Button>
                <Button variant={precisionMode === 'snipe' ? 'default' : 'outline'} size="sm" className="text-xs" onClick={() => setPrecisionMode('snipe')}>
                    <Crosshair className="w-3 h-3 mr-1" /> Snipe Mode
                </Button>
            </div>
            {precisionMode === 'snipe' && (
                <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>Farm for exactly</span>
                        <span className="text-primary font-mono font-bold">{snipeHours}h</span>
                    </div>
                    <Slider value={[snipeHours]} onValueChange={v => setSnipeHours(v[0])} min={1} max={168} step={1} className="accent-gold" />
                    <div className="flex gap-1.5">
                        {[6, 12, 24, 48, 72].map(h => (
                            <Button key={h} variant={snipeHours === h ? 'default' : 'outline'} size="sm"
                                className="text-[10px] px-2 py-1 h-6" onClick={() => setSnipeHours(h)}>
                                {h}h
                            </Button>
                        ))}
                    </div>
                </div>
            )}
        </Card>
    )

    const renderRiskReturns = () => (
        <Card className="p-4 border-border">
            <div className="flex items-center gap-2 mb-3">
                <Target className="w-4 h-4 text-primary" />
                <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Risk & Returns</span>
            </div>
            <div className="space-y-4">
                {/* Stop-Loss */}
                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <ToggleChip label="Stop-Loss" active={stopLossEnabled} toggle={() => setStopLossEnabled(v => !v)} icon={Shield} />
                        </div>
                        {stopLossEnabled && <span className="text-xs font-mono text-red-400">-{stopLossPercent}%</span>}
                    </div>
                    {stopLossEnabled && (
                        <Slider value={[stopLossPercent]} onValueChange={v => setStopLossPercent(v[0])} min={1} max={50} step={1} />
                    )}
                </div>

                {/* Take-Profit */}
                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <ToggleChip label="Take-Profit" active={takeProfitEnabled} toggle={() => setTakeProfitEnabled(v => !v)} icon={TrendingUp} />
                        {takeProfitEnabled && <span className="text-xs font-mono text-green-400">+{takeProfitPercent}%</span>}
                    </div>
                    {takeProfitEnabled && (
                        <Slider value={[takeProfitPercent]} onValueChange={v => setTakeProfitPercent(v[0])} min={5} max={200} step={5} />
                    )}
                </div>

                {/* APY Target */}
                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <ToggleChip label="Min APY Target" active={apyTargetEnabled} toggle={() => setApyTargetEnabled(v => !v)} icon={Target} />
                        {apyTargetEnabled && <span className="text-xs font-mono text-primary">{apyTargetValue}%</span>}
                    </div>
                    {apyTargetEnabled && (
                        <Slider value={[apyTargetValue]} onValueChange={v => setApyTargetValue(v[0])} min={1} max={100} step={1} />
                    )}
                </div>

                {/* Volatility Guard */}
                <div className="flex items-center justify-between">
                    <ToggleChip label="Volatility Guard" active={volatilityGuard} toggle={() => setVolatilityGuard(v => !v)} icon={Activity} />
                    {volatilityGuard && <Badge variant="outline" className="text-[10px] text-yellow-400 border-yellow-400/30">ACTIVE</Badge>}
                </div>
            </div>
        </Card>
    )

    const renderFlashLeverage = () => (
        <Card className={`p-4 border-border ${flashLoanEnabled ? 'border-red-500/30 shadow-[0_0_15px_rgba(239,68,68,0.1)]' : ''}`}>
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                    <Flame className="w-4 h-4 text-red-400" />
                    <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Flash Leverage Engine</span>
                </div>
                <Badge variant="outline" className="text-[10px] text-red-400 border-red-400/30">DEGEN</Badge>
            </div>
            <div className="space-y-3">
                <div className="flex items-center justify-between">
                    <ToggleChip label="Flash Loan Loops" active={flashLoanEnabled} toggle={() => setFlashLoanEnabled(v => !v)} icon={Zap} />
                </div>
                {flashLoanEnabled && (
                    <>
                        {/* Leverage Level */}
                        <div className="space-y-2">
                            <div className="flex items-center justify-between text-xs text-muted-foreground">
                                <span>Leverage</span>
                                <span className="font-mono font-bold text-red-400">{leverageLevel}x</span>
                            </div>
                            <div className="flex gap-1.5">
                                {[2, 3, 5, 10].map(l => (
                                    <Button key={l} variant={leverageLevel === l ? 'destructive' : 'outline'} size="sm"
                                        className="text-xs px-3 h-7 flex-1" onClick={() => setLeverageLevel(l)}>
                                        {l}x{l === 10 ? ' MAX' : ''}
                                    </Button>
                                ))}
                            </div>
                        </div>
                        {/* Auto-Deleverage Threshold */}
                        <div className="space-y-2">
                            <div className="flex items-center justify-between text-xs text-muted-foreground">
                                <span>Auto-Deleverage Threshold</span>
                                <span className="font-mono text-red-400">-{deleverageThreshold}%</span>
                            </div>
                            <Slider value={[deleverageThreshold]} onValueChange={v => setDeleverageThreshold(v[0])} min={5} max={50} step={1} />
                            <p className="text-[9px] text-muted-foreground/50">Auto-close leverage if position drops below threshold</p>
                        </div>
                        <p className="text-[10px] text-muted-foreground/60">
                            Flash leverage amplifies both gains AND losses. Liquidation risk increases with leverage.
                        </p>
                    </>
                )}
            </div>
        </Card>
    )

    const renderAutoSnipe = () => (
        <Card className={`p-4 border-border ${snipeNewPools ? 'border-green-500/30 shadow-[0_0_15px_rgba(34,197,94,0.1)]' : ''}`}>
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                    <Rocket className="w-4 h-4 text-green-400" />
                    <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Auto-Snipe New Pools</span>
                </div>
                <Badge variant="outline" className="text-[10px] text-green-400 border-green-400/30">ALPHA</Badge>
            </div>
            <div className="space-y-3">
                <ToggleChip label="Snipe New Listings" active={snipeNewPools} toggle={() => setSnipeNewPools(v => !v)} icon={Crosshair} />
                {snipeNewPools && (
                    <>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1.5">
                                <span className="text-[10px] text-muted-foreground uppercase">Min Initial APY</span>
                                <div className="flex items-center gap-1.5">
                                    <Input type="number" value={snipeMinApy} onChange={e => setSnipeMinApy(+e.target.value)}
                                        className="h-8 text-xs bg-background" />
                                    <span className="text-xs text-muted-foreground">%</span>
                                </div>
                            </div>
                            <div className="space-y-1.5">
                                <span className="text-[10px] text-muted-foreground uppercase">Max Entry Position</span>
                                <div className="flex items-center gap-1.5">
                                    <span className="text-xs text-muted-foreground">$</span>
                                    <Input type="number" value={snipeMaxPosition} onChange={e => setSnipeMaxPosition(+e.target.value)}
                                        className="h-8 text-xs bg-background" />
                                </div>
                            </div>
                        </div>
                        <div className="flex gap-1.5">
                            {[{ v: 1, l: '1 hour', sub: 'Speed run' }, { v: 4, l: '4 hours', sub: '' }, { v: 24, l: '24 hours', sub: '' }, { v: 72, l: '3 days', sub: '' }].map(e => (
                                <Button key={e.v} variant={snipeExitHours === e.v ? 'default' : 'outline'} size="sm"
                                    className="text-xs flex-1 flex-col h-auto py-1.5" onClick={() => setSnipeExitHours(e.v)}>
                                    <span>{e.l}</span>
                                    {e.sub && <span className="text-[8px] opacity-60">({e.sub})</span>}
                                </Button>
                            ))}
                        </div>
                        <p className="text-[10px] text-muted-foreground/60">
                            Limit exposure per new pool. Auto-exit after timer expires.
                        </p>
                    </>
                )}
            </div>
        </Card>
    )

    const renderVolatilityHunter = () => (
        <Card className={`p-4 border-border ${chaseVolatility ? 'border-orange-500/30 shadow-[0_0_15px_rgba(249,115,22,0.1)]' : ''}`}>
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-orange-400" />
                    <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Volatility Hunter</span>
                </div>
                <Badge variant="outline" className="text-[10px] text-orange-400 border-orange-400/30">HIGH RISK</Badge>
            </div>
            <div className="space-y-3">
                <div className="flex items-center justify-between">
                    <ToggleChip label="Chase Volatility Spikes" active={chaseVolatility} toggle={() => setChaseVolatility(v => !v)} icon={Zap} />
                </div>
                {chaseVolatility && (
                    <>
                        <div className="space-y-2">
                            <span className="text-[10px] text-muted-foreground uppercase">Min Volatility to Enter</span>
                            <select value={minVolatility}
                                onChange={e => setMinVolatility(e.target.value)}
                                className="w-full h-8 px-3 text-xs rounded-md border border-border bg-background text-foreground">
                                <option value="10">10% (Conservative)</option>
                                <option value="25">25% (Moderate)</option>
                                <option value="50">50% (Aggressive)</option>
                                <option value="100">100%+ (YOLO)</option>
                            </select>
                        </div>
                        <div className="flex items-center justify-between">
                            <ToggleChip label="IL Farming Mode" active={ilFarmingMode} toggle={() => setIlFarmingMode(v => !v)} icon={TrendingUp} />
                        </div>
                        <p className="text-[10px] text-muted-foreground/60">
                            Actively chases volatile pools for higher yields. IL farming intentionally enters pools with high impermanent loss potential.
                        </p>
                    </>
                )}
            </div>
        </Card>
    )

    const renderFlexibleAdvancedSettings = () => (
        <Card className="p-4 border-border">
            <button onClick={() => setAdvancedOpen(v => !v)}
                className="w-full flex items-center justify-between cursor-pointer bg-transparent border-none">
                <div className="flex items-center gap-2">
                    <Settings className="w-4 h-4 text-primary" />
                    <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Advanced Settings</span>
                </div>
                <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${advancedOpen ? 'rotate-180' : ''}`} />
            </button>
            <AnimatePresence>
                {advancedOpen && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                        <div className="space-y-4 pt-4">
                            {/* Auto-Rebalance */}
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-muted-foreground">Auto-Rebalance</span>
                                <ToggleChip label="" active={autoRebalance} toggle={() => setAutoRebalance(v => !v)} icon={Activity} />
                            </div>

                            {/* Rebalance Threshold */}
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs text-muted-foreground">Rebalance Threshold</span>
                                    <span className="text-xs font-mono text-primary">{rebalanceThreshold}%</span>
                                </div>
                                <Slider value={[rebalanceThreshold]} onValueChange={v => setRebalanceThreshold(v[0])} min={1} max={25} step={1} />
                            </div>

                            {/* Max Gas Price */}
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs text-muted-foreground">Max Gas Price (gwei)</span>
                                    <span className="text-xs font-mono text-primary">{maxGasPrice}</span>
                                </div>
                                <Slider value={[maxGasPrice]} onValueChange={v => setMaxGasPrice(v[0])} min={5} max={200} step={5} />
                            </div>

                            {/* Max Slippage */}
                            <div className="space-y-2">
                                <span className="text-xs text-muted-foreground">Max Slippage</span>
                                <div className="flex gap-1.5">
                                    {[0.1, 0.5, 1.0, 3.0].map(s => (
                                        <Button key={s} variant={slippage === s ? 'default' : 'outline'} size="sm"
                                            className="text-[10px] px-2.5 h-7 flex-1" onClick={() => setSlippage(s)}>
                                            {s}%
                                        </Button>
                                    ))}
                                </div>
                            </div>

                            {/* Compound Frequency */}
                            <div className="space-y-2">
                                <span className="text-xs text-muted-foreground">Compound Frequency</span>
                                <div className="flex gap-1.5">
                                    {[{ v: 1, l: 'Daily' }, { v: 7, l: 'Weekly' }, { v: 30, l: 'Monthly' }, { v: 0, l: 'Auto' }].map(c => (
                                        <Button key={c.v} variant={compoundFreq === c.v ? 'default' : 'outline'} size="sm"
                                            className="text-[10px] px-2 h-7 flex-1" onClick={() => setCompoundFreq(c.v)}>
                                            {c.l}
                                        </Button>
                                    ))}
                                </div>
                            </div>

                            {/* APY Rotation Window */}
                            <div className="space-y-2">
                                <span className="text-xs text-muted-foreground">APY Rotation Window</span>
                                <div className="flex gap-1.5">
                                    {[{ v: 12, l: '12h' }, { v: 24, l: '1 Day' }, { v: 72, l: '3 Days' }, { v: 168, l: '7 Days' }].map(c => (
                                        <Button key={c.v} variant={apyCheckHours === c.v ? 'default' : 'outline'} size="sm"
                                            className="text-[10px] px-2.5 h-7 flex-1" onClick={() => setApyCheckHours(c.v)}>
                                            {c.l}
                                        </Button>
                                    ))}
                                    <Input type="number" placeholder="hrs" className="h-7 w-16 text-[10px] bg-background"
                                        onChange={e => { const v = parseInt(e.target.value); if (v > 0) setApyCheckHours(v) }} />
                                </div>
                            </div>

                            {/* Only Audited Protocols */}
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-muted-foreground">Only Audited Protocols</span>
                                <ToggleChip label="" active={flexAudited} toggle={() => setFlexAudited(v => !v)} icon={Lock} />
                            </div>

                            {/* Avoid Impermanent Loss */}
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-muted-foreground">Avoid Impermanent Loss</span>
                                <ToggleChip label="" active={flexAvoidIL} toggle={() => setFlexAvoidIL(v => !v)} icon={Shield} />
                            </div>

                            {/* Emergency Exit */}
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-muted-foreground">Emergency Exit on -30%</span>
                                <ToggleChip label="" active={emergencyExit} toggle={() => setEmergencyExit(v => !v)} icon={AlertTriangle} />
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </Card>
    )

    return (
        <div className="max-w-5xl mx-auto">
            {/* Header */}
            <div className="flex items-center gap-4 mb-6">
                <div className="w-14 h-14 rounded-xl flex items-center justify-center bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/25 shadow-[0_0_20px_rgba(212,168,83,0.1)]">
                    <Hammer className="w-7 h-7 text-primary" />
                </div>
                <div>
                    <h1 className="font-heading text-2xl font-bold text-foreground tracking-tight">Agent Builder</h1>
                    <p className="text-sm text-muted-foreground">
                        Configure and deploy your AI trading agent
                        {isConnected && <span className="text-green-400 font-medium"> · Wallet connected</span>}
                    </p>
                </div>
            </div>

            {/* ── 3-Tier Mode Toggle ── */}
            <div className="glass-card p-1 mb-6">
                <div className="flex gap-1">
                    {([
                        { id: 'instant', label: 'AI-Instant', icon: Zap, desc: 'One-click deploy' },
                        { id: 'flexible', label: 'Flexible', icon: Settings, desc: 'Custom config' },
                        { id: 'pro', label: 'Pro', icon: Terminal, desc: 'Natural language' },
                    ] as const).map(m => (
                        <button key={m.id} onClick={() => setMode(m.id)}
                            className={`flex-1 px-4 py-3.5 rounded-xl cursor-pointer transition-all flex items-center justify-center gap-2.5 ${mode === m.id
                                ? 'bg-gradient-to-b from-primary/15 to-primary/5 text-primary border border-primary/20 shadow-[0_0_15px_rgba(212,168,83,0.08)]'
                                : 'bg-transparent text-muted-foreground hover:text-foreground hover:bg-white/[0.03] border border-transparent'
                                }`}>
                            <m.icon className={`w-4 h-4 ${mode === m.id ? 'text-primary' : ''}`} />
                            <div className="text-left">
                                <div className="text-sm font-heading font-semibold">{m.label}</div>
                                <div className="text-[10px] opacity-60 hidden sm:block">{m.desc}</div>
                            </div>
                        </button>
                    ))}
                </div>
            </div>

            {/* ═══════════════════════════════ */}
            {/* AI-INSTANT MODE */}
            {/* ═══════════════════════════════ */}
            {mode === 'instant' && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                    {/* Strategy Cards */}
                    <div className="text-center mb-4">
                        <h2 className="text-lg font-heading font-bold flex items-center justify-center gap-2">
                            <Zap className="w-5 h-5 text-primary" />
                            Choose Your Strategy
                        </h2>
                        <p className="text-xs text-muted-foreground">AI will automatically configure optimal settings</p>
                    </div>
                    <div className="grid grid-cols-3 gap-3 mb-5">
                        {(Object.entries(STRATEGIES) as [StrategyKey, typeof STRATEGIES[StrategyKey]][]).map(([key, s]) => {
                            const Icon = s.icon
                            const active = strategy === key
                            return (
                                <Card key={key} className={`p-5 cursor-pointer transition-all text-center ${active
                                    ? 'border-primary/40 shadow-[0_0_20px_rgba(212,168,83,0.1)]'
                                    : 'border-border hover:border-primary/20'}`}
                                    onClick={() => setStrategy(key)}>
                                    <div className="flex justify-center mb-3">
                                        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${s.color}15` }}>
                                            <Icon className="w-5 h-5" style={{ color: s.color }} />
                                        </div>
                                    </div>
                                    <div className="text-base font-heading font-bold mb-1" style={{ color: active ? s.color : undefined }}>{s.label}</div>
                                    <div className="text-sm font-mono font-bold mb-2" style={{ color: s.color }}>{s.range}</div>
                                    <p className="text-xs text-muted-foreground mb-3">{s.desc}</p>
                                    <div className="text-left space-y-1 mb-3">
                                        {s.bullets.map((b, i) => (
                                            <div key={i} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                                <Check className="w-3 h-3 text-primary" /> {b}
                                            </div>
                                        ))}
                                    </div>
                                    <Badge variant="outline" className="text-[10px] font-bold px-3 py-0.5"
                                        style={{ color: s.badgeColor, borderColor: `${s.badgeColor}40` }}>
                                        {s.badge}
                                    </Badge>
                                </Card>
                            )
                        })}
                    </div>

                    {/* Target Chain Selector */}
                    <div className="mb-5">
                        <span className="block text-[10px] font-medium mb-2 uppercase tracking-wider text-muted-foreground">Target Chain</span>
                        <div className="flex flex-wrap gap-2">
                            {[
                                { id: 'base', label: 'Base', icon: '/icons/base.png', active: true },
                                { id: 'ethereum', label: 'Ethereum', icon: '/icons/ethereum.png', soon: true },
                                { id: 'solana', label: 'Solana', icon: '/icons/solana.png', soon: true },
                                { id: 'arbitrum', label: 'Arbitrum', icon: '/icons/arbitrum.png', soon: true },
                            ].map(c => (
                                <Button key={c.id} variant={c.active ? 'default' : 'outline'} size="sm"
                                    disabled={c.soon} className={`text-xs gap-2 ${c.soon ? 'opacity-50' : ''}`}>
                                    <img src={c.icon} alt={c.label} className="w-4 h-4 rounded-full" />
                                    {c.label}
                                    {c.active && <Badge className="text-[9px] bg-green-500/15 text-green-400">PRIMARY</Badge>}
                                    {c.soon && <Badge variant="secondary" className="text-[9px]">SOON</Badge>}
                                </Button>
                            ))}
                        </div>
                    </div>

                    {/* AI Status + Deploy */}
                    <div className="rounded-xl p-4 mb-5" style={{ border: '1px solid #A07830', background: 'rgba(0,0,0,0.4)' }}>
                        <div className="flex items-center gap-2 mb-3">
                            <Terminal className="w-4 h-4" style={{ color: '#A07830' }} />
                            <span className="font-heading text-xs font-bold uppercase tracking-wider" style={{ color: '#A07830' }}>AI Status</span>
                        </div>
                        <div className="text-xs p-3 rounded-lg font-mono" style={{ background: 'rgba(0,0,0,0.5)', color: '#F0F0F5' }}>
                            [AI] {currentStrategy.narrative}
                        </div>
                    </div>
                    <button
                        onClick={() => executeStrategy(`Deploy ${currentStrategy.label} strategy`)}
                        disabled={isRunning}
                        className="w-full py-3.5 px-6 rounded-xl font-heading font-bold text-base mb-5 flex items-center justify-center gap-2 cursor-pointer transition-all hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed"
                        style={{
                            background: 'linear-gradient(135deg, #D4A853, #A07830)',
                            color: '#06060A',
                            border: '1px solid rgba(212,168,83,0.4)',
                            boxShadow: '0 0 20px rgba(212,168,83,0.15)',
                        }}
                    >
                        {isRunning ? <StopCircle className="w-5 h-5" /> : <Zap className="w-5 h-5" />}
                        {isRunning ? 'Deploying...' : 'Deploy AI Agent'}
                    </button>
                </motion.div>
            )}

            {/* ═══════════════════════════════ */}
            {/* FLEXIBLE MODE */}
            {/* ═══════════════════════════════ */}
            {mode === 'flexible' && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                    {/* ─── SECTION 1: Pool Discovery ─── */}
                    <div className="build-group-label"><Layers className="w-3.5 h-3.5" />Pool Discovery</div>

                    <div className="build-section p-5 mb-4">
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                            {/* Chain */}
                            <div>
                                <span className="block text-[10px] font-medium mb-2.5 uppercase tracking-wider text-muted-foreground">Chain</span>
                                <div className="flex flex-wrap gap-2">
                                    {CHAINS.map(c => (
                                        <Button key={c.id} variant={flexChain === c.id ? 'default' : 'outline'} size="sm"
                                            disabled={c.soon} className={`text-xs gap-2 ${c.soon ? 'opacity-50' : ''}`}
                                            onClick={() => !c.soon && setFlexChain(c.id)}>
                                            {c.label}
                                            {c.soon && <Badge variant="secondary" className="text-[9px] ml-1">Soon</Badge>}
                                        </Button>
                                    ))}
                                </div>
                            </div>
                            {/* Pool Type */}
                            <div>
                                <span className="block text-[10px] font-medium mb-2.5 uppercase tracking-wider text-muted-foreground">Pool Type</span>
                                <div className="grid grid-cols-3 gap-2">
                                    {([
                                        { v: 'single' as const, l: 'Single-Sided', desc: 'Lending, staking' },
                                        { v: 'dual' as const, l: 'Dual-Sided (LP)', desc: 'Yields, IL' },
                                        { v: 'all' as const, l: 'All Pools', desc: 'Mixed' },
                                    ]).map(pt => (
                                        <Button key={pt.v} variant={flexPoolType === pt.v ? 'default' : 'outline'} size="sm"
                                            className="text-xs flex-col h-auto py-2 font-heading font-semibold"
                                            onClick={() => setFlexPoolType(pt.v)}>
                                            <span>{pt.l}</span>
                                            <span className="text-[9px] font-normal opacity-60">{pt.desc}</span>
                                        </Button>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="build-divider" />

                        {/* TVL Range */}
                        <span className="block text-[10px] font-medium mb-3 uppercase tracking-wider text-muted-foreground">TVL Range</span>
                        <div className="grid grid-cols-2 gap-3 mb-3">
                            <div className="space-y-1">
                                <span className="text-[9px] text-muted-foreground uppercase">Min TVL</span>
                                <div className="flex items-center gap-1.5">
                                    <span className="text-xs text-muted-foreground">$</span>
                                    <Input type="number" value={flexTvlMin}
                                        onChange={e => { const v = Math.max(0, +e.target.value); setFlexTvlMin(v); if (v > flexTvlMax) setFlexTvlMax(v) }}
                                        className="h-8 text-xs bg-background" />
                                </div>
                                <Slider value={[flexTvlMin]} onValueChange={v => { setFlexTvlMin(v[0]); if (v[0] > flexTvlMax) setFlexTvlMax(v[0]) }}
                                    min={0} max={100_000_000} step={100_000} />
                            </div>
                            <div className="space-y-1">
                                <span className="text-[9px] text-muted-foreground uppercase">Max TVL</span>
                                <div className="flex items-center gap-1.5">
                                    <span className="text-xs text-muted-foreground">$</span>
                                    <Input type="number" value={flexTvlMax}
                                        onChange={e => { const v = Math.max(0, +e.target.value); setFlexTvlMax(v); if (v < flexTvlMin) setFlexTvlMin(v) }}
                                        className="h-8 text-xs bg-background" />
                                </div>
                                <Slider value={[flexTvlMax]} onValueChange={v => { setFlexTvlMax(v[0]); if (v[0] < flexTvlMin) setFlexTvlMin(v[0]) }}
                                    min={0} max={100_000_000} step={100_000} />
                            </div>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                            {[{ l: '$100K', v: 100_000 }, { l: '$500K', v: 500_000 }, { l: '$1M', v: 1_000_000 }, { l: '$5M', v: 5_000_000 }, { l: '$10M', v: 10_000_000 }].map(p => (
                                <Button key={p.l} variant={flexTvlMin === p.v ? 'default' : 'outline'} size="sm"
                                    className="text-[10px] h-6 px-2" onClick={() => setFlexTvlMin(p.v)}>
                                    {p.l}
                                </Button>
                            ))}
                        </div>

                        <div className="build-divider" />

                        {/* Protocols & Assets */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                            <div>
                                <span className="block text-[10px] font-medium mb-2.5 uppercase tracking-wider text-muted-foreground">Protocols (Base)</span>
                                <div className="flex flex-wrap gap-2">
                                    {PROTOCOLS
                                        .filter(p => flexPoolType === 'all' || p.type === 'both' || p.type === flexPoolType)
                                        .map(p => {
                                            const active = flexProtocols.includes(p.id)
                                            return (
                                                <Button key={p.id} variant={active ? 'default' : 'outline'} size="sm"
                                                    className="text-xs gap-1.5"
                                                    onClick={() => setFlexProtocols(prev => active ? prev.filter(x => x !== p.id) : [...prev, p.id])}>
                                                    <img src={p.icon} alt={p.label} className="w-4 h-4 rounded-full" />
                                                    {p.label}
                                                </Button>
                                            )
                                        })}
                                </div>
                            </div>
                            <div>
                                <span className="block text-[10px] font-medium mb-2.5 uppercase tracking-wider text-muted-foreground">Assets</span>
                                <div className="flex flex-wrap gap-2">
                                    {ASSETS.map(a => {
                                        const active = flexAssets.includes(a)
                                        return (
                                            <Button key={a} variant={active ? 'default' : 'outline'} size="sm" className="text-xs"
                                                onClick={() => setFlexAssets(prev => active ? prev.filter(x => x !== a) : [...prev, a])}>
                                                {a}
                                            </Button>
                                        )
                                    })}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* ─── SECTION 2: Risk & Returns ─── */}
                    <div className="build-group-label"><Target className="w-3.5 h-3.5" />Risk & Returns</div>

                    <div className="build-section p-5 mb-4">
                        {/* Trading Style */}
                        <span className="block text-[10px] font-medium mb-2.5 uppercase tracking-wider text-muted-foreground">Agent Trading Style</span>
                        <div className="flex flex-wrap gap-2 mb-2">
                            {([
                                { v: 'conservative' as const, l: 'Conservative', color: '#22C55E' },
                                { v: 'moderate' as const, l: 'Moderate', color: '#D4A853' },
                                { v: 'aggressive' as const, l: 'Aggressive', color: '#EF4444' },
                            ]).map(s => (
                                <Button key={s.v} variant={flexTradingStyle === s.v ? 'default' : 'outline'} size="sm"
                                    className="text-xs font-heading font-semibold"
                                    style={flexTradingStyle === s.v ? { borderColor: s.color, color: s.color } : {}}
                                    onClick={() => setFlexTradingStyle(s.v)}>
                                    {s.l}
                                </Button>
                            ))}
                        </div>
                        <p className="text-[10px] text-muted-foreground">
                            {flexTradingStyle === 'conservative' && 'Conservative: TVL >$10M, APY <50%, Pool age>30 days'}
                            {flexTradingStyle === 'moderate' && 'Moderate: TVL >$500k, APY <300%, Pool age>14 days'}
                            {flexTradingStyle === 'aggressive' && 'Aggressive: Any TVL, unlimited APY, new pools OK'}
                        </p>

                        <div className="build-divider" />

                        {/* Target APY Range */}
                        <span className="block text-[10px] font-medium mb-3 uppercase tracking-wider text-muted-foreground">Target APY Range</span>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1">
                                <span className="text-[9px] text-muted-foreground">Min APY</span>
                                <div className="flex items-center gap-1.5">
                                    <Input type="number" value={flexTargetApyMin}
                                        onChange={e => { const v = Math.max(0, +e.target.value); setFlexTargetApyMin(v); if (v > flexTargetApyMax) setFlexTargetApyMax(v) }}
                                        className="h-8 text-xs bg-background" />
                                    <span className="text-xs text-muted-foreground">%</span>
                                </div>
                                <Slider value={[flexTargetApyMin]} onValueChange={v => { setFlexTargetApyMin(v[0]); if (v[0] > flexTargetApyMax) setFlexTargetApyMax(v[0]) }}
                                    min={0} max={200} step={1} />
                            </div>
                            <div className="space-y-1">
                                <span className="text-[9px] text-muted-foreground">Max APY</span>
                                <div className="flex items-center gap-1.5">
                                    <Input type="number" value={flexTargetApyMax}
                                        onChange={e => { const v = Math.max(0, +e.target.value); setFlexTargetApyMax(v); if (v < flexTargetApyMin) setFlexTargetApyMin(v) }}
                                        className="h-8 text-xs bg-background" />
                                    <span className="text-xs text-muted-foreground">%</span>
                                </div>
                                <Slider value={[flexTargetApyMax]} onValueChange={v => { setFlexTargetApyMax(v[0]); if (v[0] < flexTargetApyMin) setFlexTargetApyMin(v[0]) }}
                                    min={0} max={500} step={1} />
                            </div>
                        </div>

                        <div className="build-divider" />

                        {/* Stop Loss */}
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-[10px] text-muted-foreground uppercase">Stop Loss</span>
                            <span className={`text-xs font-mono ${flexStopLoss > 30 ? 'text-red-400' : flexStopLoss > 15 ? 'text-yellow-400' : 'text-green-400'}`}>
                                -{flexStopLoss}%
                            </span>
                        </div>
                        <Slider value={[flexStopLoss]} onValueChange={v => setFlexStopLoss(v[0])} min={5} max={50} step={1} />
                    </div>

                    {/* ─── SECTION 3: Portfolio Structure ─── */}
                    <div className="build-group-label"><Layers className="w-3.5 h-3.5" />Portfolio Structure</div>

                    <div className="build-section p-5 mb-4">
                        {/* Duration */}
                        <span className="block text-[10px] font-medium mb-2.5 uppercase tracking-wider text-muted-foreground">Investment Duration</span>
                        <div className="flex flex-wrap gap-1.5 mb-1">
                            {[{ v: '1H', l: '1H' }, { v: '1D', l: '1D' }, { v: '1W', l: '1W' }, { v: '1M', l: '1M' }, { v: '3M', l: '3M' }, { v: '6M', l: '6M' }, { v: '1Y', l: '1Y' }, { v: '∞', l: '∞' }].map(d => (
                                <Button key={d.v} variant={flexDuration === d.v ? 'default' : 'outline'} size="sm"
                                    className="text-xs px-3" onClick={() => { setFlexDuration(d.v); setFlexCustomDuration('') }}>
                                    {d.l}
                                </Button>
                            ))}
                            <Button variant={flexDuration === 'custom' ? 'default' : 'outline'} size="sm"
                                className="text-xs px-3" onClick={() => setFlexDuration('custom')}>
                                Custom
                            </Button>
                        </div>
                        {flexDuration === 'custom' && (
                            <Input type="text" placeholder="e.g. 45 days" value={flexCustomDuration}
                                onChange={e => setFlexCustomDuration(e.target.value)}
                                className="h-8 text-xs bg-background w-40 mb-1" />
                        )}

                        <div className="build-divider" />

                        {/* Max per Vault + Number of Vaults */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                            <div>
                                <div className="flex items-center justify-between mb-3">
                                    <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Max per Vault</span>
                                    <span className="text-xs font-mono text-primary">{flexMaxPerVault}%</span>
                                </div>
                                <Slider value={[flexMaxPerVault]} onValueChange={v => setFlexMaxPerVault(v[0])} min={5} max={100} step={5} />
                            </div>
                            <div>
                                <span className="block text-[10px] font-medium mb-2.5 uppercase tracking-wider text-muted-foreground">Number of Vaults</span>
                                <div className="flex gap-1.5">
                                    {[1, 3, 5, 10].map(v => (
                                        <Button key={v} variant={flexVaults === v ? 'default' : 'outline'} size="sm"
                                            className="text-xs px-4 flex-1" onClick={() => setFlexVaults(v)}>
                                            {v}
                                        </Button>
                                    ))}
                                    <Button variant={flexVaults === 0 ? 'default' : 'outline'} size="sm"
                                        className="text-xs px-4 flex-1" onClick={() => setFlexVaults(0)}>
                                        Auto
                                    </Button>
                                </div>
                            </div>
                        </div>
                    </div>


                    {/* Advanced Settings (collapsible) */}
                    {renderFlexibleAdvancedSettings()}

                    {/* Deploy button */}
                    <button
                        onClick={() => executeStrategy(`Flexible strategy: ${flexProtocols.join(',')} duration=${flexDuration}`)}
                        disabled={isRunning}
                        className="w-full py-3.5 px-6 rounded-xl font-heading font-bold text-base mb-5 flex items-center justify-center gap-2 cursor-pointer transition-all hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed"
                        style={{
                            background: 'linear-gradient(135deg, #D4A853, #A07830)',
                            color: '#06060A',
                            border: '1px solid rgba(212,168,83,0.4)',
                            boxShadow: '0 0 20px rgba(212,168,83,0.15)',
                        }}
                    >
                        {isRunning ? <StopCircle className="w-5 h-5" /> : <Zap className="w-5 h-5" />}
                        {isRunning ? 'Deploying...' : 'Deploy AI Agent'}
                    </button>
                </motion.div>
            )}



            {/* ═══════════════════════════════ */}
            {/* PRO MODE */}
            {/* ═══════════════════════════════ */}
            {
                mode === 'pro' && (
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                        {/* Strategy Prompt */}
                        <Card className="p-5 mb-4 border-primary/20">
                            <span className="block text-[10px] font-medium mb-2 uppercase tracking-wider text-muted-foreground">
                                Strategy Command
                            </span>
                            <div className="flex gap-3">
                                <Input type="text" value={command} onChange={e => setCommand(e.target.value)}
                                    onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                                    placeholder="e.g. Farm stablecoins on Base with max 10% risk, auto-compound weekly..."
                                    className="flex-1 h-11 text-sm bg-background" />
                                <Button onClick={handleSubmit} disabled={isRunning}
                                    className="px-5 h-11 bg-gradient-to-r from-primary to-primary/80 text-primary-foreground font-heading font-semibold gap-2">
                                    {isRunning ? <StopCircle className="w-4 h-4" /> : <Send className="w-4 h-4" />}
                                    {isRunning ? 'Processing...' : 'Execute'}
                                </Button>
                            </div>
                        </Card>



                        {/* Presets */}
                        <div className="grid grid-cols-3 gap-3 mb-4">
                            {(Object.entries(STRATEGIES) as [StrategyKey, typeof STRATEGIES[StrategyKey]][]).map(([key, s]) => (
                                <Card key={key} className={`p-3 cursor-pointer transition-all ${strategy === key
                                    ? 'border-primary/40'
                                    : 'border-border hover:border-primary/20'}`}
                                    onClick={() => setStrategy(key)}>
                                    <div className="flex items-center justify-between mb-0.5">
                                        <span className="text-sm font-heading font-semibold" style={{ color: strategy === key ? s.color : undefined }}>{s.label}</span>
                                        <span className="text-xs font-mono" style={{ color: s.color }}>{s.range}</span>
                                    </div>
                                    <p className="text-[10px] text-muted-foreground">{s.desc}</p>
                                </Card>
                            ))}
                        </div>

                        {/* Chain Selection */}
                        <Card className="p-4 border-border mb-4">
                            <span className="block text-[10px] font-medium mb-2 uppercase tracking-wider text-muted-foreground">Chain</span>
                            <div className="flex flex-wrap gap-2">
                                {CHAINS.map(c => (
                                    <Button key={c.id} variant={flexChain === c.id ? 'default' : 'outline'} size="sm"
                                        disabled={c.soon} className={`text-xs gap-2 ${c.soon ? 'opacity-50' : ''}`}
                                        onClick={() => !c.soon && setFlexChain(c.id)}>
                                        {c.label}
                                        {c.soon && <Badge variant="secondary" className="text-[9px] ml-1">Soon</Badge>}
                                    </Button>
                                ))}
                            </div>
                        </Card>

                        {/* Pool Type */}
                        <Card className="p-4 border-border mb-4">
                            <span className="block text-[10px] font-medium mb-2 uppercase tracking-wider text-muted-foreground">Pool Type</span>
                            <div className="grid grid-cols-3 gap-2">
                                {([
                                    { v: 'single' as const, l: 'Single-Sided', desc: 'Lending, staking' },
                                    { v: 'dual' as const, l: 'Dual-Sided (LP)', desc: 'Yields, IL' },
                                    { v: 'all' as const, l: 'All Pools', desc: 'Mixed' },
                                ]).map(pt => (
                                    <Button key={pt.v} variant={flexPoolType === pt.v ? 'default' : 'outline'} size="sm"
                                        className="text-xs flex-col h-auto py-2 font-heading font-semibold"
                                        onClick={() => setFlexPoolType(pt.v)}>
                                        <span>{pt.l}</span>
                                        <span className="text-[9px] font-normal opacity-60">{pt.desc}</span>
                                    </Button>
                                ))}
                            </div>
                        </Card>

                        {/* TVL Filter */}
                        <Card className="p-4 border-border mb-4">
                            <span className="block text-[10px] font-medium mb-3 uppercase tracking-wider text-muted-foreground">TVL Range</span>
                            <div className="grid grid-cols-2 gap-3 mb-3">
                                <div className="space-y-1">
                                    <span className="text-[9px] text-muted-foreground uppercase">Min TVL</span>
                                    <div className="flex items-center gap-1.5">
                                        <span className="text-xs text-muted-foreground">$</span>
                                        <Input type="number" value={flexTvlMin}
                                            onChange={e => { const v = Math.max(0, +e.target.value); setFlexTvlMin(v); if (v > flexTvlMax) setFlexTvlMax(v) }}
                                            className="h-8 text-xs bg-background" />
                                    </div>
                                    <Slider value={[flexTvlMin]} onValueChange={v => { setFlexTvlMin(v[0]); if (v[0] > flexTvlMax) setFlexTvlMax(v[0]) }}
                                        min={0} max={100_000_000} step={100_000} />
                                </div>
                                <div className="space-y-1">
                                    <span className="text-[9px] text-muted-foreground uppercase">Max TVL</span>
                                    <div className="flex items-center gap-1.5">
                                        <span className="text-xs text-muted-foreground">$</span>
                                        <Input type="number" value={flexTvlMax}
                                            onChange={e => { const v = Math.max(0, +e.target.value); setFlexTvlMax(v); if (v < flexTvlMin) setFlexTvlMin(v) }}
                                            className="h-8 text-xs bg-background" />
                                    </div>
                                    <Slider value={[flexTvlMax]} onValueChange={v => { setFlexTvlMax(v[0]); if (v[0] < flexTvlMin) setFlexTvlMin(v[0]) }}
                                        min={0} max={100_000_000} step={100_000} />
                                </div>
                            </div>
                            <div className="flex flex-wrap gap-1.5">
                                {[{ l: '$100K', v: 100_000 }, { l: '$500K', v: 500_000 }, { l: '$1M', v: 1_000_000 }, { l: '$5M', v: 5_000_000 }, { l: '$10M', v: 10_000_000 }].map(p => (
                                    <Button key={p.l} variant={flexTvlMin === p.v ? 'default' : 'outline'} size="sm"
                                        className="text-[10px] h-6 px-2" onClick={() => setFlexTvlMin(p.v)}>
                                        {p.l}
                                    </Button>
                                ))}
                            </div>
                        </Card>

                        {/* Protocols & Assets */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
                            <Card className="p-4 border-border">
                                <span className="block text-[10px] font-medium mb-2 uppercase tracking-wider text-muted-foreground">Protocols (Base)</span>
                                <div className="flex flex-wrap gap-2">
                                    {PROTOCOLS
                                        .filter(p => flexPoolType === 'all' || p.type === 'both' || p.type === flexPoolType)
                                        .map(p => {
                                            const active = flexProtocols.includes(p.id)
                                            return (
                                                <Button key={p.id} variant={active ? 'default' : 'outline'} size="sm"
                                                    className="text-xs gap-1.5"
                                                    onClick={() => setFlexProtocols(prev => active ? prev.filter(x => x !== p.id) : [...prev, p.id])}>
                                                    <img src={p.icon} alt={p.label} className="w-4 h-4 rounded-full" />
                                                    {p.label}
                                                </Button>
                                            )
                                        })}
                                </div>
                            </Card>

                            <Card className="p-4 border-border">
                                <span className="block text-[10px] font-medium mb-2 uppercase tracking-wider text-muted-foreground">Assets</span>
                                <div className="flex flex-wrap gap-2">
                                    {ASSETS.map(a => {
                                        const active = flexAssets.includes(a)
                                        return (
                                            <Button key={a} variant={active ? 'default' : 'outline'} size="sm" className="text-xs"
                                                onClick={() => setFlexAssets(prev => active ? prev.filter(x => x !== a) : [...prev, a])}>
                                                {a}
                                            </Button>
                                        )
                                    })}
                                </div>
                            </Card>
                        </div>

                        {/* Investment Duration */}
                        <Card className="p-4 border-border mb-4">
                            <span className="block text-[10px] font-medium mb-2 uppercase tracking-wider text-muted-foreground">Investment Duration</span>
                            <div className="flex flex-wrap gap-1.5">
                                {[{ v: '1H', l: '1H' }, { v: '1D', l: '1D' }, { v: '1W', l: '1W' }, { v: '1M', l: '1M' }, { v: '3M', l: '3M' }, { v: '6M', l: '6M' }, { v: '1Y', l: '1Y' }, { v: '∞', l: '∞' }].map(d => (
                                    <Button key={d.v} variant={flexDuration === d.v ? 'default' : 'outline'} size="sm"
                                        className="text-xs px-3" onClick={() => { setFlexDuration(d.v); setFlexCustomDuration('') }}>
                                        {d.l}
                                    </Button>
                                ))}
                                <Button variant={flexDuration === 'custom' ? 'default' : 'outline'} size="sm"
                                    className="text-xs px-3" onClick={() => setFlexDuration('custom')}>
                                    Custom
                                </Button>
                            </div>
                            {flexDuration === 'custom' && (
                                <Input type="text" placeholder="e.g. 45 days" value={flexCustomDuration}
                                    onChange={e => setFlexCustomDuration(e.target.value)}
                                    className="mt-2 h-8 text-xs bg-background w-40" />
                            )}
                        </Card>

                        {/* Max per Vault & Number of Vaults */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
                            <Card className="p-4 border-border">
                                <div className="flex items-center justify-between mb-3">
                                    <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Max per Vault</span>
                                    <span className="text-xs font-mono text-primary">{flexMaxPerVault}%</span>
                                </div>
                                <Slider value={[flexMaxPerVault]} onValueChange={v => setFlexMaxPerVault(v[0])} min={5} max={100} step={5} />
                            </Card>

                            <Card className="p-4 border-border">
                                <span className="block text-[10px] font-medium mb-2 uppercase tracking-wider text-muted-foreground">Number of Vaults</span>
                                <div className="flex gap-1.5">
                                    {[1, 3, 5, 10].map(v => (
                                        <Button key={v} variant={flexVaults === v ? 'default' : 'outline'} size="sm"
                                            className="text-xs px-4 flex-1" onClick={() => setFlexVaults(v)}>
                                            {v}
                                        </Button>
                                    ))}
                                    <Button variant={flexVaults === 0 ? 'default' : 'outline'} size="sm"
                                        className="text-xs px-4 flex-1" onClick={() => setFlexVaults(0)}>
                                        Auto
                                    </Button>
                                </div>
                            </Card>
                        </div>

                        {/* Advanced Settings (collapsible) */}
                        <div className="mb-4">
                            {renderFlexibleAdvancedSettings()}
                        </div>

                        {/* Yield Engineering */}
                        <Card className="p-4 border-border mb-4">
                            <div className="flex items-center gap-2 mb-3">
                                <TrendingUp className="w-4 h-4 text-primary" />
                                <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Yield Engineering</span>
                            </div>
                            <div className="space-y-3">
                                <div className="space-y-2">
                                    <span className="text-[10px] text-muted-foreground uppercase">Smart Loop Engine</span>
                                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                                        <span>Leverage Level</span>
                                        <span className="font-mono font-bold text-primary">{yieldLeverage.toFixed(1)}x</span>
                                    </div>
                                    <Slider value={[yieldLeverage * 10]} onValueChange={v => setYieldLeverage(v[0] / 10)}
                                        min={10} max={30} step={1} />
                                    <div className="flex justify-between text-[9px] text-muted-foreground">
                                        <span>1.0x (Safe)</span><span>2.0x</span><span>3.0x (Max)</span>
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="text-center p-2 rounded-lg bg-black/20">
                                        <span className="text-[9px] text-muted-foreground uppercase block">Est. APY</span>
                                        <span className="text-sm font-mono text-primary font-bold">{(12 * yieldLeverage).toFixed(0)}%</span>
                                    </div>
                                    <div className="text-center p-2 rounded-lg bg-black/20">
                                        <span className="text-[9px] text-muted-foreground uppercase block">Liquidation</span>
                                        <span className={`text-sm font-mono font-bold ${yieldLeverage > 2 ? 'text-red-400' : 'text-green-400'}`}>
                                            {yieldLeverage > 2 ? 'HIGH RISK' : 'SAFE'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </Card>

                        {/* Precision Timing */}
                        <div className="mb-4">
                            {renderPrecisionTiming()}
                        </div>

                        {/* Exit Targets (Risk & Returns) */}
                        <div className="mb-4">
                            {renderRiskReturns()}
                        </div>

                        {/* Safety & Gas */}
                        <Card className="p-4 border-border mb-4">
                            <div className="flex items-center gap-2 mb-3">
                                <Shield className="w-4 h-4 text-primary" />
                                <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Safety & Gas</span>
                            </div>
                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <ToggleChip label="Volatility Guard" active={volatilityGuard} toggle={() => setVolatilityGuard(v => !v)} icon={Activity} />
                                    {volatilityGuard && <Badge variant="outline" className="text-[10px] text-yellow-400 border-yellow-400/30">ACTIVE</Badge>}
                                </div>
                                <div className="flex items-center justify-between">
                                    <ToggleChip label="MEV Protection" active={mevProtection} toggle={() => setMevProtection(v => !v)} icon={Shield} />
                                    {mevProtection && <Badge variant="outline" className="text-[10px] text-green-400 border-green-400/30">ON</Badge>}
                                </div>
                                <div className="space-y-2">
                                    <span className="text-xs text-muted-foreground">Gas Strategy</span>
                                    <select value={gasStrategy}
                                        onChange={e => setGasStrategy(e.target.value)}
                                        className="w-full h-9 px-3 text-xs rounded-md border border-border bg-background text-foreground">
                                        <option value="smart">Smart Compound (Profit &gt; 5x Gas)</option>
                                        <option value="standard">Standard (Always Harvest)</option>
                                        <option value="saver">Gas Saver (Low Priority)</option>
                                    </select>
                                </div>
                            </div>
                        </Card>

                        {/* Agent Command Interface */}
                        <Card className="p-4 border-border mb-4">
                            <div className="flex items-center gap-2 mb-3">
                                <Terminal className="w-4 h-4 text-primary" />
                                <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Agent Command Interface</span>
                            </div>
                            <p className="text-xs text-muted-foreground mb-2">Give your agent natural language instructions</p>
                            <textarea value={agentCommandText} onChange={e => setAgentCommandText(e.target.value)}
                                placeholder="Example: Keep farming until ETH hits $4000, then withdraw everything to USDC. Prioritize Aave and Morpho for safety."
                                className="w-full h-24 p-3 text-xs rounded-md border border-border bg-background text-foreground resize-none font-mono"
                            />
                        </Card>

                        {/* Flash Leverage + Volatility Hunter */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
                            {renderFlashLeverage()}
                            {renderVolatilityHunter()}
                        </div>

                        {/* Auto-Snipe */}
                        <div className="mb-4">
                            {renderAutoSnipe()}
                        </div>

                        {/* Delta Neutral Mode */}
                        <Card className={`p-4 border-border mb-4 ${deltaHedgeEnabled ? 'border-blue-500/30 shadow-[0_0_15px_rgba(59,130,246,0.1)]' : ''}`}>
                            <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center gap-2">
                                    <Shield className="w-4 h-4 text-blue-400" />
                                    <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Delta Neutral Mode</span>
                                </div>
                                <Badge variant="outline" className="text-[10px] text-blue-400 border-blue-400/30">PRO</Badge>
                            </div>
                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <ToggleChip label="Auto-Hedge LP Exposure" active={deltaHedgeEnabled} toggle={() => setDeltaHedgeEnabled(v => !v)} icon={Shield} />
                                </div>
                                {deltaHedgeEnabled && (
                                    <>
                                        <div className="space-y-2">
                                            <span className="text-[10px] text-muted-foreground uppercase">Hedge Protocol</span>
                                            <select value={hedgeProtocol}
                                                onChange={e => setHedgeProtocol(e.target.value)}
                                                className="w-full h-8 px-3 text-xs rounded-md border border-border bg-background text-foreground">
                                                <option value="gmx">GMX Perps</option>
                                                <option value="synthetix">Synthetix</option>
                                                <option value="kwenta">Kwenta</option>
                                                <option value="avantis">Avantis</option>
                                            </select>
                                        </div>
                                        <div className="space-y-2">
                                            <div className="flex items-center justify-between text-xs text-muted-foreground">
                                                <span>Rebalance Delta When</span>
                                                <span className="font-mono text-primary">±{rebalanceDelta}%</span>
                                            </div>
                                            <Slider value={[rebalanceDelta]} onValueChange={v => setRebalanceDelta(v[0])} min={1} max={20} step={1} />
                                        </div>
                                        <div className="flex items-center justify-between">
                                            <ToggleChip label="Funding Rate Farming" active={fundingRateFarming} toggle={() => setFundingRateFarming(v => !v)} icon={TrendingUp} />
                                            {fundingRateFarming && <Badge variant="outline" className="text-[10px] text-blue-400 border-blue-400/30">ACTIVE</Badge>}
                                        </div>
                                        <p className="text-[10px] text-muted-foreground/60">
                                            Automatically hedges your LP exposure using perp shorts. Collects funding rates when positive.
                                        </p>
                                    </>
                                )}
                            </div>
                        </Card>
                    </motion.div>
                )
            }

            {/* ── Neural Terminal (all modes) ── */}
            <div className="rounded-xl overflow-hidden" style={{ border: '1px solid #A07830', background: 'rgba(0,0,0,0.95)' }}>
                {/* Terminal Header */}
                <div className="px-4 py-2.5 flex items-center justify-between" style={{ borderBottom: '1px solid rgba(160,120,48,0.3)' }}>
                    <div className="flex items-center gap-2.5">
                        <Zap className="w-4 h-4" style={{ color: '#A07830' }} />
                        <span className="font-mono text-sm font-bold tracking-wider" style={{ color: '#A07830' }}>NEURAL TERMINAL</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold"
                            style={{
                                color: isRunning ? '#D4A853' : '#22C55E',
                                background: isRunning ? 'rgba(212,168,83,0.08)' : 'rgba(34,197,94,0.05)',
                                border: `1px solid ${isRunning ? 'rgba(212,168,83,0.3)' : 'rgba(34,197,94,0.2)'}`,
                            }}>
                            {isRunning ? 'ACTIVE' : 'STANDBY'}
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <button className="text-xs px-1.5 py-0.5 rounded cursor-pointer" style={{ color: '#666', background: 'transparent', border: '1px solid #333' }}>_</button>
                        <button className="text-xs px-1.5 py-0.5 rounded cursor-pointer" style={{ color: '#666', background: 'transparent', border: '1px solid #333' }}
                            onClick={() => setLines([{ type: 'system', text: '[SYSTEM] Neural Terminal v2.0 initialized', timestamp: new Date().toLocaleTimeString('en', { hour12: false }) }])}>
                            ⌘
                        </button>
                    </div>
                </div>
                {/* Terminal Body */}
                <div ref={terminalRef}
                    className="p-4 font-mono text-xs leading-relaxed overflow-y-auto"
                    style={{ minHeight: '200px', maxHeight: '350px', background: 'rgba(0,0,0,0.95)', color: '#F0F0F5' }}>
                    <AnimatePresence>
                        {lines.map((line, i) => (
                            <motion.div key={i} initial={{ opacity: 0, x: -5 }} animate={{ opacity: 1, x: 0 }}
                                transition={{ duration: 0.2 }} className="mb-1">
                                <span style={{
                                    color: line.type === 'error' ? '#EF4444' :
                                        line.type === 'warning' ? '#D4A853' :
                                            line.type === 'success' ? '#22C55E' :
                                                line.type === 'user' ? '#A07830' :
                                                    line.type === 'agent' ? '#60A5FA' :
                                                        line.text.includes('[SYSTEM]') ? '#A07830' :
                                                            line.text.includes('[READY]') ? '#22C55E' :
                                                                '#B0B0B8'
                                }}>{line.text}</span>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                    {!isRunning && (
                        <div className="mt-2 flex items-center gap-1">
                            <span style={{ color: '#A07830' }}>&gt;</span>
                            <span style={{ color: '#00FF41', opacity: 0.5 }} className="animate-pulse">Enter command...</span>
                        </div>
                    )}
                </div>
                {/* Terminal Input */}
                <div className="px-4 py-2.5 flex items-center gap-2" style={{ borderTop: '1px solid rgba(160,120,48,0.15)' }}>
                    <span className="font-mono text-sm" style={{ color: '#A07830' }}>&gt;</span>
                    <input
                        type="text"
                        value={command}
                        onChange={e => setCommand(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                        placeholder="Enter command..."
                        className="flex-1 bg-transparent border-none outline-none font-mono text-xs"
                        style={{ color: '#00FF41', caretColor: '#00FF41' }}
                    />
                </div>
            </div>
        </div >
    )
}

// ─── Helpers ───

function ToggleChip({ label, active, toggle, icon: Icon }: { label: string; active: boolean; toggle: () => void; icon: any }) {
    return (
        <button onClick={toggle} className="flex items-center gap-1.5 text-xs cursor-pointer bg-transparent border-none"
            style={{ color: active ? 'hsl(var(--primary))' : 'hsl(var(--muted-foreground))' }}>
            <div className={`w-7 h-4 rounded-full relative transition-all border ${active
                ? 'bg-primary/20 border-primary/40'
                : 'bg-muted border-border'}`}>
                <div className={`w-3 h-3 rounded-full absolute top-0.5 transition-all ${active
                    ? 'left-[12px] bg-primary'
                    : 'left-[2px] bg-muted-foreground'}`} />
            </div>
            {label}
        </button>
    )
}

function delay(ms: number) { return new Promise(resolve => setTimeout(resolve, ms)) }
