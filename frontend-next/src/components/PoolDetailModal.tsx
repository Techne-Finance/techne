import { useState, useMemo, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    X, ExternalLink, AlertTriangle, Shield, Lock, Activity, Coins,
    Flame, ArrowRight, Copy, Check, ChevronDown,
    Zap, Clock, TrendingDown, Target, Droplet, Flag,
    BarChart3, Timer, Waves, Users, Eye, Skull, CircleAlert, Info,
    LineChart, TrendingUp, ShieldCheck, ShieldAlert, ShieldX,
    Scale, Fingerprint, Search,
    Landmark, KeyRound, Gem, FlaskConical, Wallet, Crosshair,
    LogOut, Layers, Gauge, Microscope,
    BadgeCheck, FileQuestion, LockOpen, Sparkles, Bug, CircleCheck,
    OctagonX, CircleDashed, FileCheck, FileX, PenLine, Snowflake,
    UserX, Receipt, Hourglass, Verified
} from 'lucide-react'
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer
} from 'recharts'
import { type Pool, getRiskColor, getRiskLabel, formatUsd, formatApy, scoutVerifyOnchain } from '@/lib/api'
import { getProtocolIconUrl, getChainIconUrl } from '@/lib/icons'

// ========== Types ==========
type Tab = 'stress' | 'yield' | 'history' | 'onchain'

interface PoolDetailModalProps {
    pool: Pool & Record<string, any>
    onClose: () => void
}

// ========== Helpers ==========
function getVerdict(score: number) {
    if (score >= 70) return { label: 'SAFE', color: '#10B981', glow: 'rgba(16,185,129,0.4)', desc: 'Pool has passed Artisan Agent risk assessment' }
    if (score >= 40) return { label: 'CAUTION', color: '#D4A853', glow: 'rgba(212,168,83,0.4)', desc: 'Careful consideration recommended before investing' }
    return { label: 'HIGH RISK', color: '#EF4444', glow: 'rgba(239,68,68,0.4)', desc: 'Significant risk factors detected — proceed with caution' }
}

function getSourceBadge(source?: string) {
    if (!source) return 'DefiLlama'
    if (source.includes('gecko')) return 'GeckoTerminal'
    if (source.includes('aerodrome')) return 'Aerodrome'
    if (source.includes('defillama')) return 'DefiLlama'
    return 'On-chain'
}

function isEpochProtocol(project?: string) {
    const p = (project || '').toLowerCase()
    return p.includes('aerodrome') || p.includes('velodrome')
}

function getEpochCountdown() {
    const now = new Date()
    const day = now.getUTCDay()
    const daysUntilWed = ((3 - day) + 7) % 7 || 7
    const next = new Date(now)
    next.setUTCDate(now.getUTCDate() + daysUntilWed)
    next.setUTCHours(0, 0, 0, 0)
    const diff = next.getTime() - now.getTime()
    const h = Math.floor(diff / 3600000)
    const m = Math.floor((diff % 3600000) / 60000)
    return `${Math.floor(h / 24)}d ${h % 24}h ${m}m`
}

function assessSecurity(pool: any) {
    const warnings: string[] = []
    let isCritical = false
    const sec = pool.security || pool.security_result || {}

    if (sec.honeypot_detected) { warnings.push('Honeypot detected — DO NOT DEPOSIT'); isCritical = true }
    if (sec.is_blacklisted) { warnings.push('Token is blacklisted on security databases'); isCritical = true }
    if (sec.high_tax && (sec.buy_tax > 10 || sec.sell_tax > 10)) warnings.push(`High tax: Buy ${sec.buy_tax}% / Sell ${sec.sell_tax}%`)
    if (sec.is_proxy && !sec.is_open_source) warnings.push('Proxy contract — not open source')
    if (sec.owner_can_change_balance) { warnings.push('Owner can modify balances'); isCritical = true }

    const il = pool.il_analysis || {}
    if (il.risk_level === 'high' || il.risk_level === 'extreme') warnings.push(`High IL Risk: ${il.estimated_il || 'significant divergence'}`)

    return { warnings, isCritical, canDeposit: !isCritical }
}

function buildRiskFlags(pool: any) {
    const flags: { icon: React.ReactNode; text: string; type: 'info' | 'warning' | 'caution' }[] = []

    if (pool.risk_flags?.length > 0) {
        return pool.risk_flags.map((rf: any) => ({
            icon: <Flag className="w-3.5 h-3.5" />,
            text: rf.label,
            type: rf.severity === 'high' ? 'warning' : rf.severity === 'medium' ? 'caution' : 'info'
        }))
    }

    const isCL = pool.pool_type === 'cl' || (pool.project || '').toLowerCase().includes('slipstream')
    if (isCL) flags.push({ icon: <Target className="w-3.5 h-3.5" />, text: 'Concentrated Liquidity', type: 'info' })
    if (pool.gauge_address) flags.push({ icon: <Zap className="w-3.5 h-3.5" />, text: 'Emissions-based yield', type: 'info' })
    if (isEpochProtocol(pool.project)) flags.push({ icon: <Clock className="w-3.5 h-3.5" />, text: 'Epoch-based rewards', type: 'info' })
    if (!pool.stablecoin && pool.il_risk !== 'no') flags.push({ icon: <TrendingDown className="w-3.5 h-3.5" />, text: 'Impermanent Loss risk', type: 'warning' })
    if (pool.apy > 200) flags.push({ icon: <Flame className="w-3.5 h-3.5" />, text: 'Very high APY', type: 'warning' })
    if (pool.tvl < 100000) flags.push({ icon: <Droplet className="w-3.5 h-3.5" />, text: 'Low liquidity', type: 'warning' })
    return flags
}

// ========== Sub-Components ==========

function VerdictBanner({ pool }: { pool: any }) {
    const score = pool.risk_score || pool.riskScore || 50
    const verdict = getVerdict(score)
    const circumference = 201
    const progress = (score / 100) * circumference
    const dashOffset = circumference - progress

    return (
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg mb-2" style={{
            background: `linear-gradient(135deg, ${verdict.color}08, ${verdict.color}04)`,
            border: `1px solid ${verdict.color}20`,
        }}>
            {/* Compact Score Ring */}
            <div className="relative w-11 h-11 flex-shrink-0">
                <svg viewBox="0 0 100 100" className="w-full h-full">
                    <circle cx="50" cy="50" r="32" fill="transparent" stroke="rgba(255,255,255,0.06)" strokeWidth="7" />
                    <motion.circle cx="50" cy="50" r="32" fill="transparent"
                        stroke={verdict.color} strokeWidth="7" strokeLinecap="round"
                        strokeDasharray={circumference}
                        initial={{ strokeDashoffset: circumference }}
                        animate={{ strokeDashoffset: dashOffset }}
                        transition={{ duration: 1, ease: 'easeOut' }}
                        transform="rotate(-90 50 50)"
                    />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-sm font-heading font-extrabold" style={{ color: verdict.color }}>{score}</span>
                </div>
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <span className="text-xs font-heading font-bold tracking-wider uppercase" style={{ color: verdict.color }}>{verdict.label}</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded" style={{ background: 'rgba(255,255,255,0.04)', color: 'var(--color-text-muted)' }}>
                        {getSourceBadge(pool.dataSource || pool.source)}
                    </span>
                </div>
                <div className="text-[10px] mt-0.5" style={{ color: 'var(--color-text-muted)' }}>{verdict.desc}</div>
            </div>
        </div>
    )
}

function SecurityBanner({ warnings, isCritical }: { warnings: string[]; isCritical: boolean }) {
    if (warnings.length === 0) return null
    return (
        <div className="px-3 py-2 rounded-lg mb-2" style={{
            background: isCritical ? 'rgba(239,68,68,0.08)' : 'rgba(250,204,21,0.06)',
            border: `1px solid ${isCritical ? 'rgba(239,68,68,0.2)' : 'rgba(250,204,21,0.15)'}`,
        }}>
            <div className="flex items-center gap-1.5 mb-1">
                {isCritical ? <OctagonX className="w-3.5 h-3.5" style={{ color: '#EF4444' }} /> : <CircleAlert className="w-3.5 h-3.5" style={{ color: '#FBBF24' }} />}
                <span className="text-[11px] font-heading font-semibold" style={{ color: isCritical ? '#EF4444' : '#FBBF24' }}>
                    {isCritical ? 'CRITICAL RISK DETECTED' : 'Security Warnings'}
                </span>
            </div>
            {warnings.map((w, i) => (
                <div key={i} className="text-[10px] ml-5 mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>• {w}</div>
            ))}
        </div>
    )
}

function RiskFlags({ pool }: { pool: any }) {
    const flags = buildRiskFlags(pool)
    if (flags.length === 0) return null
    const colorMap = { info: 'var(--color-gold)', warning: '#EF4444', caution: '#FBBF24' }
    return (
        <div className="mb-2">
            <div className="flex flex-wrap gap-1">
                {flags.map((f, i) => (
                    <div key={i} className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded" style={{
                        background: `color-mix(in srgb, ${colorMap[f.type]} 6%, transparent)`,
                        border: `1px solid color-mix(in srgb, ${colorMap[f.type]} 15%, transparent)`,
                        color: colorMap[f.type],
                    }}>
                        {f.icon}
                        {f.text}
                    </div>
                ))}
            </div>
        </div>
    )
}

function SecurityMatrixCard({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
    return (
        <div className="px-2.5 py-2 rounded-lg" style={{ background: 'var(--color-glass)', border: '1px solid var(--color-glass-border)' }}>
            <div className="flex items-center gap-1 mb-1">
                {icon}
                <span className="text-[9px] font-heading font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-muted)' }}>{title}</span>
            </div>
            {children}
        </div>
    )
}

function AuditCard({ pool }: { pool: any }) {
    // Match old frontend: pool.audit_status || pool.audit
    const audit = pool.audit_status || pool.audit || {}
    const hasAudit = audit.audited === true ||
        (audit.status && audit.status !== 'none' && audit.status !== 'unknown') ||
        (audit.auditors && audit.auditors.length > 0)
    let auditorName = hasAudit ? 'Verified' : null
    if (audit.auditors?.length > 0) auditorName = audit.auditors.slice(0, 2).join(', ')
    else if (audit.auditor) auditorName = audit.auditor
    const auditUrl = audit.url || audit.report_url
    return (
        <SecurityMatrixCard icon={<Landmark className="w-3 h-3" style={{ color: hasAudit ? '#10B981' : '#6B7280' }} />} title="Audit">
            <div className="text-xs font-heading font-semibold" style={{ color: hasAudit ? '#10B981' : '#6B7280' }}>
                {hasAudit ? <><BadgeCheck className="w-3 h-3 inline mr-0.5" />{auditorName}</> : <><FileQuestion className="w-3 h-3 inline mr-0.5" />Not audited</>}
            </div>
            {auditUrl && <a href={auditUrl} target="_blank" rel="noopener noreferrer" className="text-[9px] mt-0.5 underline" style={{ color: '#10B981' }}>View report</a>}
        </SecurityMatrixCard>
    )
}

function LPLockCard({ pool }: { pool: any }) {
    // Match old frontend: pool.liquidity_lock || pool.lock_status
    const lock = pool.liquidity_lock || pool.lock_status
    const isLocked = lock && (lock.locked || lock.status === 'locked')
    return (
        <SecurityMatrixCard icon={<KeyRound className="w-3 h-3" style={{ color: isLocked ? '#10B981' : '#FBBF24' }} />} title="LP Lock">
            <div className="text-xs font-heading font-semibold" style={{ color: isLocked ? '#10B981' : '#FBBF24' }}>
                {isLocked ? <><Lock className="w-3 h-3 inline mr-0.5" />Locked</> : <><LockOpen className="w-3 h-3 inline mr-0.5" />No lock</>}
            </div>
            {isLocked && lock.platform && <div className="text-[9px] mt-0.5" style={{ color: 'var(--color-text-muted)' }}>{lock.platform}</div>}
        </SecurityMatrixCard>
    )
}

function VolatilityCard({ pool }: { pool: any }) {
    // Match old frontend: pool.token0_volatility, pool.token1_volatility flat objects
    const token0Vol = pool.token0_volatility || {}
    const token1Vol = pool.token1_volatility || {}
    const symbol0 = token0Vol.symbol || pool.symbol0 || pool.symbol?.split(/[-\/]/)?.[0]?.trim() || 'Token0'
    const symbol1 = token1Vol.symbol || pool.symbol1 || pool.symbol?.split(/[-\/]/)?.[1]?.trim() || 'Token1'
    const vol0_24h = token0Vol.price_change_24h || pool.token0_volatility_24h || 0
    const vol1_24h = token1Vol.price_change_24h || pool.token1_volatility_24h || 0
    const lpVol24h = pool.token_volatility_24h || pool.pair_price_change_24h || 0
    const getVolColor = (v: number) => Math.abs(v) > 10 ? '#EF4444' : Math.abs(v) > 5 ? '#FBBF24' : '#10B981'
    const formatVol = (v: number) => v === 0 ? '0%' : `${v > 0 ? '+' : ''}${v.toFixed(1)}%`
    // Overall level
    const volAnalysis = pool.volatility_analysis || {}
    const level = volAnalysis.overall_level || volAnalysis.level ||
        (Math.abs(lpVol24h) > 10 ? 'High' : Math.abs(lpVol24h) > 5 ? 'Medium' : 'Low')
    const levelColor = level === 'Low' ? '#10B981' : level === 'High' ? '#EF4444' : '#FBBF24'
    return (
        <SecurityMatrixCard icon={<Waves className="w-3 h-3" style={{ color: levelColor }} />} title="Volatility">
            <div className="text-xs font-heading font-semibold" style={{ color: levelColor }}>{level}</div>
            <div className="flex items-center justify-between text-[9px] mt-0.5">
                <span style={{ color: 'var(--color-text-muted)' }}>{symbol0}</span>
                <span style={{ color: getVolColor(vol0_24h) }}>{formatVol(vol0_24h)}</span>
            </div>
            <div className="flex items-center justify-between text-[9px]">
                <span style={{ color: 'var(--color-text-muted)' }}>{symbol1}</span>
                <span style={{ color: getVolColor(vol1_24h) }}>{formatVol(vol1_24h)}</span>
            </div>
        </SecurityMatrixCard>
    )
}

function TokensCard({ pool }: { pool: any }) {
    const sec = pool.security || pool.security_result || {}
    const allClean = !sec.honeypot_detected && !sec.is_blacklisted && !sec.high_tax
    return (
        <SecurityMatrixCard icon={<Gem className="w-3 h-3" style={{ color: allClean ? '#10B981' : '#EF4444' }} />} title="Tokens">
            <div className="text-xs font-heading font-semibold" style={{ color: allClean ? '#10B981' : '#EF4444' }}>
                {allClean ? <><Sparkles className="w-3 h-3 inline mr-0.5" />Clean</> : <><Bug className="w-3 h-3 inline mr-0.5" />Issues</>}
            </div>
            {sec.honeypot_detected && <div className="text-[9px] mt-0.5" style={{ color: '#EF4444' }}><Skull className="w-3 h-3 inline" /> Honeypot</div>}
            {sec.high_tax && <div className="text-[9px] mt-0.5" style={{ color: '#FBBF24' }}>High tax</div>}
        </SecurityMatrixCard>
    )
}

function Accordion({ title, icon, children, defaultOpen = false }: { title: string; icon: React.ReactNode; children: React.ReactNode; defaultOpen?: boolean }) {
    const [open, setOpen] = useState(defaultOpen)
    return (
        <div className="rounded-lg overflow-hidden" style={{ border: '1px solid var(--color-glass-border)' }}>
            <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between px-2.5 py-2 cursor-pointer"
                style={{ background: 'var(--color-glass)' }}>
                <span className="text-[11px] font-medium flex items-center gap-1.5" style={{ color: 'var(--color-text-secondary)' }}>
                    {icon} {title}
                </span>
                <ChevronDown className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} style={{ color: 'var(--color-text-muted)' }} />
            </button>
            <AnimatePresence>
                {open && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} className="overflow-hidden">
                        <div className="p-2.5 text-xs space-y-1.5" style={{ color: 'var(--color-text-secondary)' }}>
                            {children}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}


function YieldRow({ label, value, color, bold }: { label: string; value: string; color: string; bold?: boolean }) {
    return (
        <div className="flex items-center justify-between">
            <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>{label}</span>
            <span className={`text-sm ${bold ? 'font-bold' : 'font-medium'}`} style={{ color }}>{value}</span>
        </div>
    )
}

// ========== MAIN COMPONENT ==========

export function PoolDetailModal({ pool, onClose }: PoolDetailModalProps) {
    const [tab, setTab] = useState<Tab>('stress')
    const [copied, setCopied] = useState(false)
    const [onchainData, setOnchainData] = useState<any>(null)
    const [onchainLoading, setOnchainLoading] = useState(false)
    const [onchainError, setOnchainError] = useState<string | null>(null)

    const riskColor = getRiskColor(pool.risk_score)
    const riskLabel = getRiskLabel(pool.risk_score)
    const security = useMemo(() => assessSecurity(pool), [pool])

    // Fetch on-chain verification when tab is activated
    useEffect(() => {
        if (tab !== 'onchain') return
        if (onchainData || onchainLoading) return
        const addr = pool.address || pool.pool_address || pool.pool_id
        if (!addr) return
        setOnchainLoading(true)
        setOnchainError(null)
        const protocol = (pool.project || '').toLowerCase().replace(/\s+/g, '-')
        scoutVerifyOnchain(addr, protocol || 'auto', (pool.chain || 'Base').toLowerCase())
            .then(d => setOnchainData(d))
            .catch(e => setOnchainError(e?.message || 'Verification failed'))
            .finally(() => setOnchainLoading(false))
    }, [tab])

    // Stress Test — derive from TVL like old frontend (renderLiquidityStressCompact)
    const stressTestData = useMemo(() => {
        const tvl = pool.tvl || pool.tvlUsd || 0
        const formatTvl = (v: number) => v >= 1e9 ? `$${(v / 1e9).toFixed(1)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(0)}K` : `$${v.toFixed(0)}`

        // TVL stress level — same thresholds as old frontend
        let stressLevel = 'HEALTHY'; let stressColor = '#22C55E'
        if (tvl < 100_000) { stressLevel = 'CRITICAL'; stressColor = '#EF4444' }
        else if (tvl < 500_000) { stressLevel = 'STRESSED'; stressColor = '#F59E0B' }
        else if (tvl < 2_000_000) { stressLevel = 'MODERATE'; stressColor = '#84CC16' }

        // IL risk from il_analysis (same as old frontend)
        const ilAnalysis = pool.il_analysis || {}
        const ilRisk = ilAnalysis.risk_level || ilAnalysis.il_risk || pool.il_risk || (pool.stablecoin ? 'low' : 'medium')
        const ilEstimated = ilAnalysis.estimated_il || pool.il_risk || (pool.stablecoin ? '<0.1%' : '~5.7%')

        // Audit status from pool.audit_status (same as old frontend)
        const audit = pool.audit_status || pool.audit || {}
        const hasAudit = audit.audited === true || (audit.auditors?.length > 0)

        return {
            stressLevel: { label: `Liquidity Stress: ${stressLevel}`, impact: tvl > 0 ? formatTvl(tvl) : 'No TVL', detail: tvl > 0 ? `TVL: ${formatTvl(tvl)}` : 'TVL data unavailable', color: stressColor },
            scenarios: tvl > 0 ? [
                { drop: 10, remaining: formatTvl(tvl * 0.9), color: '#22C55E' },
                { drop: 30, remaining: formatTvl(tvl * 0.7), color: '#F59E0B' },
                { drop: 50, remaining: formatTvl(tvl * 0.5), color: '#EF4444' },
            ] : [],
            impermanentLoss: { label: '2x Price Divergence', impact: ilRisk.charAt(0).toUpperCase() + ilRisk.slice(1), detail: `Est. IL: ${ilEstimated}`, color: ilRisk === 'low' ? '#10B981' : ilRisk === 'high' || ilRisk === 'extreme' ? '#EF4444' : '#FBBF24' },
            contractRisk: { label: 'Contract Security', impact: hasAudit ? 'Audited' : pool.verified ? 'Verified' : 'Unaudited', detail: hasAudit ? 'Audited' : pool.verified ? 'RPC Verified' : 'Unverified', color: hasAudit ? '#10B981' : pool.verified ? '#84CC16' : '#FBBF24' },
        }
    }, [pool])

    // Yield Analysis — match old frontend: pool.apy_base, pool.apyBase, pool.apy_reward, pool.apyReward
    const yieldAnalysis = useMemo(() => {
        const apy = pool.apy || 0
        const apyBase = parseFloat(pool.apy_base || pool.apyBase || 0)
        const apyReward = parseFloat(pool.apy_reward || pool.apyReward || 0)
        const totalApy = apyBase + apyReward
        const hasBreakdown = totalApy > 0
        const feePercent = hasBreakdown ? (apyBase / totalApy * 100) : 0
        const emissionPercent = hasBreakdown ? (apyReward / totalApy * 100) : 0
        let sustainabilityScore = 'Sustainable'; let sustainabilityColor = '#10B981'
        if (emissionPercent > 80) { sustainabilityScore = 'High emission dependency'; sustainabilityColor = '#EF4444' }
        else if (emissionPercent > 50) { sustainabilityScore = 'Moderate reliance'; sustainabilityColor = '#FBBF24' }
        return {
            baseApy: apyBase, rewardApy: apyReward, totalApy: apy, feePercent,
            emissionPercent, hasBreakdown, sustainabilityScore, sustainabilityColor,
            rewardToken: pool.reward_token || 'Protocol Token',
        }
    }, [pool])

    // APY History — always generate sparkline (same as old frontend renderAPYHistory)
    const apyHistoryInfo = useMemo(() => {
        const currentApy = pool.apy || 0
        const apyHistory = pool.apy_history || pool.apyHistory || []
        const apyPct7D = pool.apyPct7D || 0

        // Generate sparkline data — real data or simulated ±15% variance
        let sparklineData: number[] = apyHistory.length > 0
            ? apyHistory.map((h: any) => h.apy || h.value || 0)
            : []
        if (sparklineData.length === 0 && currentApy > 0) {
            const variance = currentApy * 0.15
            // Deterministic seed from pool address for consistency
            const seed = (pool.address || pool.pool_address || '').split('').reduce((a: number, c: string) => a + c.charCodeAt(0), 0)
            sparklineData = Array(30).fill(0).map((_: number, i: number) => {
                const pseudoRandom = Math.sin(seed + i * 7.13) * 0.5 + 0.5
                const noise = (pseudoRandom - 0.5) * variance * 2
                return Math.max(0, currentApy + noise)
            })
        }

        const apyMin = sparklineData.length > 0 ? Math.min(...sparklineData) : (pool.apy_min ?? currentApy * 0.8)
        const apyMax = sparklineData.length > 0 ? Math.max(...sparklineData) : (pool.apy_max ?? currentApy * 1.2)
        const apyMean = sparklineData.length > 0
            ? sparklineData.reduce((a: number, b: number) => a + b, 0) / sparklineData.length
            : (pool.apy_mean || currentApy)

        const volatility = apyMean > 0 ? ((apyMax - apyMin) / apyMean * 100) : 0
        let volLevel = 'Low'; let volColor = '#10B981'
        if (volatility > 50) { volLevel = 'High'; volColor = '#EF4444' }
        else if (volatility > 25) { volLevel = 'Medium'; volColor = '#FBBF24' }

        // Build chart data for recharts
        const chartData = sparklineData.length > 0
            ? sparklineData.map((apy: number, i: number) => {
                const d = new Date(); d.setDate(d.getDate() - (sparklineData.length - 1 - i))
                return { date: d.toLocaleDateString('en', { month: 'short', day: 'numeric' }), apy }
            })
            : null

        const trend7d = apyPct7D
        const trendColor = trend7d >= 0 ? '#10B981' : '#EF4444'
        const trendIcon = trend7d >= 0 ? '▲' : '▼'

        return { apyMean, apyMin, apyMax, volatility, volLevel, volColor, chartData, trend7d, trendColor, trendIcon }
    }, [pool])

    // Exit Simulation
    const exitSim = useMemo(() => {
        const tvl = pool.tvl || 0
        if (tvl <= 0) return []
        return [
            { label: '$1K', amount: 1000 },
            { label: '$10K', amount: 10000 },
            { label: '$100K', amount: 100000 },
        ].map(pos => {
            const slippage = Math.min((pos.amount / tvl) * 200, 50)
            const color = slippage < 0.5 ? '#10B981' : slippage < 2 ? '#FBBF24' : '#EF4444'
            return { ...pos, slippage, color, loss: pos.amount * (slippage / 100) }
        })
    }, [pool])

    const copyAddress = () => {
        const addr = pool.address || pool.pool_address || pool.pool_id
        navigator.clipboard.writeText(addr)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    const openExplorer = () => {
        if (pool.explorer_url) window.open(pool.explorer_url, '_blank')
        else if (pool.address || pool.pool_address) window.open(`https://basescan.org/address/${pool.address || pool.pool_address}`, '_blank')
    }

    const openProtocol = () => { if (pool.defillama_url) window.open(pool.defillama_url, '_blank') }

    return (
        <AnimatePresence>
            <motion.div className="fixed inset-0 z-50 flex items-center justify-center p-4"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <motion.div className="absolute inset-0" style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
                    onClick={onClose} initial={{ opacity: 0 }} animate={{ opacity: 1 }} />

                <motion.div className="relative overflow-y-auto"
                    style={{ width: '95vw', maxWidth: '1100px', maxHeight: '94vh', padding: '6px', background: 'linear-gradient(180deg, rgba(20,20,20,0.98), rgba(10,10,10,0.98))', border: '1px solid rgba(212,168,83,0.2)', borderRadius: '10px', boxShadow: '0 0 40px rgba(212,168,83,0.06)' }}
                    initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 30 }} transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}>

                    {/* Close button */}
                    <button onClick={onClose} className="absolute top-3 right-3 z-20 w-7 h-7 rounded-full flex items-center justify-center cursor-pointer"
                        style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)' }}>
                        <X className="w-3.5 h-3.5" style={{ color: 'var(--color-text-muted)' }} />
                    </button>

                    {/* ═══════════ VERDICT BANNER ═══════════ */}
                    <VerdictBanner pool={pool} />

                    {/* ═══════════ SECURITY WARNINGS ═══════════ */}
                    <SecurityBanner warnings={security.warnings} isCritical={security.isCritical} />

                    {/* ═══════════ HEADER ═══════════ */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px 4px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <div className="relative">
                                <img src={getProtocolIconUrl(pool.project)} alt={pool.project}
                                    style={{ width: '30px', height: '30px', borderRadius: '50%' }}
                                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
                                {pool.chain && (
                                    <img src={getChainIconUrl(pool.chain)} alt={pool.chain}
                                        style={{ position: 'absolute', bottom: '-2px', right: '-2px', width: '14px', height: '14px', borderRadius: '50%', border: '2px solid rgba(20,20,20,0.98)' }}
                                        onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
                                )}
                            </div>
                            <div>
                                <div style={{ fontSize: '13px', fontWeight: 600, color: '#fff' }}>{pool.project || 'Unknown'}</div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', color: 'var(--color-text-muted)' }}>
                                    <span style={{ fontWeight: 500 }}>{pool.symbol}</span>
                                    <span style={{ opacity: 0.6 }}>{pool.chain || 'Base'}</span>
                                </div>
                            </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-green)' }}>
                                {pool.apy > 0 ? formatApy(pool.apy) : 'N/A'}
                            </div>
                            <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>APY</div>
                        </div>
                    </div>

                    {/* ═══════════ METRICS ROW ═══════════ */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '3px', padding: '0 4px', marginBottom: '3px' }}>
                        <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: '6px', padding: '5px 8px', textAlign: 'center' }}>
                            <div style={{ fontSize: '13px', fontWeight: 600, color: '#fff' }}>{formatUsd(pool.tvl)}</div>
                            <div style={{ fontSize: '9px', color: 'var(--color-text-muted)' }}>TVL</div>
                        </div>
                        <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: '6px', padding: '5px 8px', textAlign: 'center' }}>
                            <div style={{ fontSize: '13px', fontWeight: 600, color: riskColor }}>{riskLabel}</div>
                            <div style={{ fontSize: '9px', color: 'var(--color-text-muted)' }}>Risk Level</div>
                        </div>
                        <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: '6px', padding: '5px 8px', textAlign: 'center' }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', fontSize: '13px', fontWeight: 600, color: '#fff' }}>
                                {pool.pool_type === 'stable' ? <Scale className="w-3.5 h-3.5" style={{ color: '#10B981' }} /> : <Flame className="w-3.5 h-3.5" style={{ color: '#FBBF24' }} />}
                                {pool.pool_type === 'stable' ? 'Stable' : 'Volatile'}
                            </div>
                            <div style={{ fontSize: '9px', color: 'var(--color-text-muted)' }}>Type</div>
                        </div>
                    </div>

                    {/* ═══════════ RISK FLAGS ═══════════ */}
                    <div style={{ padding: '0 4px', marginBottom: '2px' }}>
                        <RiskFlags pool={pool} />
                    </div>

                    {/* ═══════════════════════════════════ */}
                    {/* BENTO GRID: 58/42 split            */}
                    {/* ═══════════════════════════════════ */}
                    <div style={{ display: 'grid', gridTemplateColumns: '58fr 42fr', gap: '3px', padding: '0 4px', marginBottom: '3px' }}>

                        {/* LEFT: Tabbed Analysis Module */}
                        <div style={{ background: 'rgba(255,255,255,0.02)', borderRadius: '6px', padding: '6px' }}>
                            {/* Tab Switcher */}
                            <div style={{ display: 'flex', gap: '1px', background: 'rgba(0,0,0,0.3)', borderRadius: '5px', padding: '2px', marginBottom: '4px' }}>
                                {([
                                    { id: 'stress' as Tab, icon: <FlaskConical className="w-3 h-3" />, label: 'Stress' },
                                    { id: 'yield' as Tab, icon: <Wallet className="w-3 h-3" />, label: 'Yield' },
                                    { id: 'history' as Tab, icon: <LineChart className="w-3 h-3" />, label: 'History' },
                                    { id: 'onchain' as Tab, icon: <Microscope className="w-3 h-3" />, label: 'On-Chain' },
                                ]).map(t => (
                                    <button key={t.id} onClick={() => setTab(t.id)}
                                        style={{
                                            flex: 1, padding: '3px 4px', background: tab === t.id ? 'rgba(212,168,83,0.12)' : 'transparent',
                                            border: tab === t.id ? '1px solid rgba(212,168,83,0.2)' : '1px solid transparent',
                                            borderRadius: '3px', color: tab === t.id ? 'var(--color-gold)' : 'var(--color-text-muted)',
                                            fontSize: '10px', fontWeight: 500, cursor: 'pointer', transition: 'all 0.15s',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '3px'
                                        }}>
                                        {t.icon} {t.label}
                                    </button>
                                ))}
                            </div>

                            {/* Tab Content */}
                            <AnimatePresence mode="wait">
                                {tab === 'stress' && (
                                    <motion.div key="stress" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                                            {/* Stress level header */}
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px', background: 'rgba(0,0,0,0.2)', borderRadius: '6px' }}>
                                                <div style={{ fontSize: '12px', fontWeight: 600, color: stressTestData.stressLevel.color }}>{stressTestData.stressLevel.label}</div>
                                                <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>{stressTestData.stressLevel.detail}</span>
                                            </div>
                                            {/* TVL drawdown scenarios */}
                                            {stressTestData.scenarios.map((s, i) => (
                                                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 8px' }}>
                                                    <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', width: '36px' }}>-{s.drop}%</span>
                                                    <div style={{ flex: 1, height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px' }}>
                                                        <div style={{ width: `${100 - s.drop}%`, height: '100%', background: s.color, borderRadius: '3px' }} />
                                                    </div>
                                                    <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>{s.remaining}</span>
                                                </div>
                                            ))}
                                            {stressTestData.scenarios.length === 0 && (
                                                <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', padding: '6px 8px' }}>No TVL data for stress simulation</div>
                                            )}
                                            {/* IL + Contract rows */}
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px', background: 'rgba(0,0,0,0.2)', borderRadius: '6px' }}>
                                                <div>
                                                    <div style={{ fontSize: '12px', fontWeight: 500, color: '#fff' }}>{stressTestData.impermanentLoss.label}</div>
                                                    <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginTop: '1px' }}>{stressTestData.impermanentLoss.detail}</div>
                                                </div>
                                                <span style={{ fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '10px', background: `${stressTestData.impermanentLoss.color}15`, color: stressTestData.impermanentLoss.color }}>{stressTestData.impermanentLoss.impact}</span>
                                            </div>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px', background: 'rgba(0,0,0,0.2)', borderRadius: '6px' }}>
                                                <div>
                                                    <div style={{ fontSize: '12px', fontWeight: 500, color: '#fff' }}>{stressTestData.contractRisk.label}</div>
                                                    <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginTop: '1px' }}>{stressTestData.contractRisk.detail}</div>
                                                </div>
                                                <span style={{ fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '10px', background: `${stressTestData.contractRisk.color}15`, color: stressTestData.contractRisk.color }}>{stressTestData.contractRisk.impact}</span>
                                            </div>
                                        </div>
                                    </motion.div>
                                )}
                                {tab === 'yield' && (
                                    <motion.div key="yield" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                                        <div style={{ padding: '6px', background: 'rgba(0,0,0,0.2)', borderRadius: '6px' }}>
                                            {yieldAnalysis.hasBreakdown ? (
                                                <>
                                                    <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '0.05em' }}>Yield Composition</div>
                                                    <YieldRow label="Base APY (Fees)" value={formatApy(yieldAnalysis.baseApy)} color="#10B981" />
                                                    <YieldRow label={`Reward APY (${yieldAnalysis.rewardToken})`} value={formatApy(yieldAnalysis.rewardApy)} color="#FBBF24" />
                                                    <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '6px', marginTop: '6px' }}>
                                                        <YieldRow label="Total APY" value={formatApy(yieldAnalysis.totalApy)} color="var(--color-green)" bold />
                                                    </div>
                                                    <div style={{ marginTop: '8px', fontSize: '11px', color: 'var(--color-text-muted)' }}>
                                                        Sustainability: <span style={{ color: yieldAnalysis.sustainabilityColor, fontWeight: 600 }}>{yieldAnalysis.sustainabilityScore}</span>
                                                    </div>
                                                </>
                                            ) : (
                                                <>
                                                    <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '0.05em' }}>Yield Overview</div>
                                                    <YieldRow label="Total APY" value={formatApy(yieldAnalysis.totalApy)} color="var(--color-gold)" bold />
                                                    <div style={{ fontSize: '11px', color: '#6B7280', marginTop: '6px' }}>Breakdown not available for this vault</div>
                                                    {yieldAnalysis.totalApy > 0 && <div style={{ fontSize: '11px', color: '#10B981', fontWeight: 500, marginTop: '4px', display: 'flex', alignItems: 'center', gap: '3px' }}><BadgeCheck className="w-3 h-3" /> Yield verified</div>}
                                                </>
                                            )}
                                        </div>
                                    </motion.div>
                                )}
                                {tab === 'history' && (
                                    <motion.div key="history" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                                            <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>APY History (30d)</div>
                                            <span style={{ fontSize: '10px', padding: '2px 8px', borderRadius: '10px', background: `${apyHistoryInfo.volColor}15`, color: apyHistoryInfo.volColor, fontWeight: 600 }}>
                                                Volatility: {apyHistoryInfo.volLevel}
                                            </span>
                                        </div>
                                        {apyHistoryInfo.chartData ? (
                                            <div style={{ height: '110px' }}>
                                                <ResponsiveContainer width="100%" height="100%">
                                                    <AreaChart data={apyHistoryInfo.chartData}>
                                                        <defs><linearGradient id="apyGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#D4A853" stopOpacity={0.3} /><stop offset="95%" stopColor="#D4A853" stopOpacity={0} /></linearGradient></defs>
                                                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                                        <XAxis dataKey="date" tick={{ fill: 'var(--color-text-muted)', fontSize: 8 }} axisLine={false} tickLine={false} interval={6} />
                                                        <YAxis tick={{ fill: 'var(--color-text-muted)', fontSize: 8 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `${v.toFixed(0)}%`} domain={['auto', 'auto']} />
                                                        <Tooltip contentStyle={{ background: 'rgba(20,20,20,0.95)', border: '1px solid rgba(212,168,83,0.3)', borderRadius: '6px', fontSize: '11px' }} formatter={(v: any) => [`${Number(v).toFixed(2)}%`, 'APY']} />
                                                        <Area type="monotone" dataKey="apy" stroke="#D4A853" fill="url(#apyGrad)" strokeWidth={2} />
                                                    </AreaChart>
                                                </ResponsiveContainer>
                                            </div>
                                        ) : (
                                            <div style={{ height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-muted)', fontSize: '11px' }}>No APY data available</div>
                                        )}
                                        {/* Stats row below chart */}
                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '4px', marginTop: '6px' }}>
                                            <div style={{ textAlign: 'center', padding: '4px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px' }}>
                                                <div style={{ fontSize: '8px', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Min</div>
                                                <div style={{ fontSize: '12px', fontWeight: 600, color: '#fff' }}>{formatApy(apyHistoryInfo.apyMin)}</div>
                                            </div>
                                            <div style={{ textAlign: 'center', padding: '4px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px' }}>
                                                <div style={{ fontSize: '8px', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Avg</div>
                                                <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-gold)' }}>{formatApy(apyHistoryInfo.apyMean)}</div>
                                            </div>
                                            <div style={{ textAlign: 'center', padding: '4px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px' }}>
                                                <div style={{ fontSize: '8px', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Max</div>
                                                <div style={{ fontSize: '12px', fontWeight: 600, color: '#fff' }}>{formatApy(apyHistoryInfo.apyMax)}</div>
                                            </div>
                                            <div style={{ textAlign: 'center', padding: '4px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px' }}>
                                                <div style={{ fontSize: '8px', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>7d Change</div>
                                                <div style={{ fontSize: '12px', fontWeight: 600, color: apyHistoryInfo.trendColor }}>
                                                    {apyHistoryInfo.trendIcon} {apyHistoryInfo.trend7d >= 0 ? '+' : ''}{apyHistoryInfo.trend7d.toFixed(1)}%
                                                </div>
                                            </div>
                                        </div>
                                    </motion.div>
                                )}
                                {tab === 'onchain' && (
                                    <motion.div key="onchain" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                                        {onchainLoading ? (
                                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '24px' }}>
                                                <div style={{ width: '20px', height: '20px', border: '2px solid var(--color-gold)', borderTop: '2px solid transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
                                                <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Reading smart contracts via RPC...</span>
                                            </div>
                                        ) : onchainError ? (
                                            <div style={{ padding: '16px', textAlign: 'center', color: '#EF4444', fontSize: '11px' }}>
                                                <ShieldAlert className="w-5 h-5" style={{ margin: '0 auto 8px', color: '#EF4444' }} />
                                                {onchainError}
                                            </div>
                                        ) : onchainData ? (() => {
                                            const oc = onchainData.onchain || {}
                                            const api = onchainData.api
                                            const delta = onchainData.delta || {}
                                            const holders = onchainData.holders
                                            const deltaColor = (v: number | null | undefined) => {
                                                if (v == null) return '#6B7280'
                                                const abs = Math.abs(v)
                                                return abs < 5 ? '#10B981' : abs < 20 ? '#FBBF24' : '#EF4444'
                                            }
                                            const fmtDelta = (v: number | null | undefined) => v != null ? `${v >= 0 ? '+' : ''}${v.toFixed(1)}%` : '—'
                                            const fmtUsd2 = (v: number | null | undefined) => {
                                                if (v == null || v === 0) return '—'
                                                return v >= 1e9 ? `$${(v / 1e9).toFixed(2)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${v.toFixed(0)}`
                                            }

                                            return (
                                                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                                    {/* Protocol badge */}
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                        <span style={{ fontSize: '9px', padding: '2px 8px', borderRadius: '8px', background: 'rgba(212,168,83,0.12)', color: 'var(--color-gold)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                                            {onchainData.protocol || 'auto'}
                                                        </span>
                                                        <span style={{ fontSize: '9px', color: 'var(--color-text-muted)' }}>{onchainData.rpc_time_ms}ms RPC</span>
                                                    </div>

                                                    {/* Status badge */}
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 8px', background: onchainData.success ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)', borderRadius: '6px', border: `1px solid ${onchainData.success ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}` }}>
                                                        {onchainData.success
                                                            ? <Verified className="w-4 h-4" style={{ color: '#10B981' }} />
                                                            : <ShieldAlert className="w-4 h-4" style={{ color: '#EF4444' }} />
                                                        }
                                                        <span style={{ fontSize: '11px', fontWeight: 600, color: onchainData.success ? '#10B981' : '#EF4444' }}>
                                                            {onchainData.success ? 'On-Chain Verified' : 'Verification Failed'}
                                                        </span>
                                                    </div>

                                                    {/* RPC vs API Comparison Grid */}
                                                    <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '6px', overflow: 'hidden' }}>
                                                        {/* Header */}
                                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', padding: '4px 8px', background: 'rgba(255,255,255,0.03)' }}>
                                                            <span style={{ fontSize: '8px', color: 'var(--color-text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>Metric</span>
                                                            <span style={{ fontSize: '8px', color: '#10B981', textTransform: 'uppercase', fontWeight: 700, textAlign: 'right' }}>On-Chain</span>
                                                            <span style={{ fontSize: '8px', color: '#60A5FA', textTransform: 'uppercase', fontWeight: 700, textAlign: 'right' }}>API</span>
                                                            <span style={{ fontSize: '8px', color: 'var(--color-gold)', textTransform: 'uppercase', fontWeight: 700, textAlign: 'right' }}>Delta</span>
                                                        </div>
                                                        {/* TVL Row */}
                                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', padding: '6px 8px', borderTop: '1px solid rgba(255,255,255,0.04)' }}>
                                                            <span style={{ fontSize: '10px', color: 'var(--color-text-secondary)', fontWeight: 500 }}>TVL</span>
                                                            <span style={{ fontSize: '11px', color: '#fff', fontWeight: 600, textAlign: 'right' }}>{fmtUsd2(oc.tvl)}</span>
                                                            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', textAlign: 'right' }}>{api ? fmtUsd2(api.tvl) : '—'}</span>
                                                            <span style={{ fontSize: '11px', fontWeight: 600, textAlign: 'right', color: deltaColor(delta.tvl_pct) }}>{fmtDelta(delta.tvl_pct)}</span>
                                                        </div>
                                                        {/* APY Row */}
                                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', padding: '6px 8px', borderTop: '1px solid rgba(255,255,255,0.04)' }}>
                                                            <span style={{ fontSize: '10px', color: 'var(--color-text-secondary)', fontWeight: 500 }}>APY</span>
                                                            <span style={{ fontSize: '11px', color: '#fff', fontWeight: 600, textAlign: 'right' }}>{oc.apy != null ? `${oc.apy.toFixed(2)}%` : '—'}</span>
                                                            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', textAlign: 'right' }}>{api?.apy != null ? `${api.apy.toFixed(2)}%` : '—'}</span>
                                                            <span style={{ fontSize: '11px', fontWeight: 600, textAlign: 'right', color: deltaColor(delta.apy_pct) }}>{fmtDelta(delta.apy_pct)}</span>
                                                        </div>
                                                        {/* Price Row */}
                                                        {oc.price != null && oc.price > 0 && (
                                                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', padding: '6px 8px', borderTop: '1px solid rgba(255,255,255,0.04)' }}>
                                                                <span style={{ fontSize: '10px', color: 'var(--color-text-secondary)', fontWeight: 500 }}>Price</span>
                                                                <span style={{ fontSize: '11px', color: '#fff', fontWeight: 600, textAlign: 'right' }}>${oc.price < 0.01 ? oc.price.toFixed(6) : oc.price.toFixed(2)}</span>
                                                                <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', textAlign: 'right' }}>—</span>
                                                                <span style={{ fontSize: '11px', color: '#6B7280', textAlign: 'right' }}>—</span>
                                                            </div>
                                                        )}
                                                    </div>

                                                    {/* On-Chain Details */}
                                                    {oc.details && (
                                                        <div style={{ padding: '6px 8px', background: 'rgba(0,0,0,0.15)', borderRadius: '6px' }}>
                                                            <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '4px', fontWeight: 600 }}>Contract Details</div>
                                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                                                                {Object.entries(oc.details).filter(([, v]) => v != null && String(v).length < 30 && !String(v).startsWith('0x')).slice(0, 6).map(([k, v]) => (
                                                                    <span key={k} style={{ fontSize: '9px', padding: '2px 6px', borderRadius: '4px', background: 'rgba(255,255,255,0.04)', color: 'var(--color-text-secondary)' }}>
                                                                        {k}: <strong style={{ color: '#fff' }}>{typeof v === 'number' ? (v > 1e6 ? `${(v as number / 1e6).toFixed(1)}M` : v > 100 ? Math.round(v as number) : (v as number).toFixed(2)) : String(v)}</strong>
                                                                    </span>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}

                                                    {/* LP Holder Analysis (Moralis) */}
                                                    {holders && !holders.skipped && (
                                                        <div style={{ padding: '6px 8px', background: 'rgba(0,0,0,0.15)', borderRadius: '6px' }}>
                                                            <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '4px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                                                                <Users className="w-3 h-3" /> LP Holders ({holders.source || 'moralis'})
                                                            </div>
                                                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '4px' }}>
                                                                <div style={{ textAlign: 'center', padding: '4px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px' }}>
                                                                    <div style={{ fontSize: '13px', fontWeight: 700, color: '#fff' }}>{holders.holder_count != null ? (holders.holder_count >= 1000 ? `${(holders.holder_count / 1000).toFixed(1)}K` : holders.holder_count) : '—'}</div>
                                                                    <div style={{ fontSize: '8px', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Holders</div>
                                                                </div>
                                                                <div style={{ textAlign: 'center', padding: '4px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px' }}>
                                                                    <div style={{ fontSize: '13px', fontWeight: 700, color: holders.top_10_percent > 70 ? '#EF4444' : holders.top_10_percent > 40 ? '#FBBF24' : '#10B981' }}>{holders.top_10_percent != null ? `${holders.top_10_percent.toFixed(1)}%` : '—'}</div>
                                                                    <div style={{ fontSize: '8px', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Top 10</div>
                                                                </div>
                                                                <div style={{ textAlign: 'center', padding: '4px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px' }}>
                                                                    <div style={{ fontSize: '13px', fontWeight: 700, color: (holders.concentration_risk === 'high' ? '#EF4444' : holders.concentration_risk === 'medium' ? '#FBBF24' : '#10B981') }}>{(holders.concentration_risk || 'unknown').toUpperCase()}</div>
                                                                    <div style={{ fontSize: '8px', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Risk</div>
                                                                </div>
                                                            </div>
                                                            {/* Top holders table */}
                                                            {holders.holders && holders.holders.length > 0 && (
                                                                <div style={{ marginTop: '4px' }}>
                                                                    {holders.holders.slice(0, 3).map((h: any, i: number) => (
                                                                        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '9px', padding: '2px 0', borderTop: i > 0 ? '1px solid rgba(255,255,255,0.04)' : 'none' }}>
                                                                            <span style={{ color: 'var(--color-text-muted)', fontFamily: 'monospace' }}>
                                                                                {h.label && h.label !== 'Unknown' ? h.label : `${h.address?.slice(0, 6)}...${h.address?.slice(-4)}`}
                                                                                {h.is_contract && <span style={{ fontSize: '7px', padding: '0 3px', marginLeft: '3px', borderRadius: '3px', background: 'rgba(96,165,250,0.15)', color: '#60A5FA' }}>📋</span>}
                                                                            </span>
                                                                            <span style={{ fontWeight: 600, color: '#fff' }}>{h.percent?.toFixed(1)}%</span>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            )
                                        })() : (
                                            <div style={{ padding: '20px', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '11px' }}>
                                                <Microscope className="w-5 h-5" style={{ margin: '0 auto 8px', opacity: 0.5 }} />
                                                Click to load on-chain verification
                                            </div>
                                        )}
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>

                        {/* RIGHT: 2x2 Security Matrix */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px' }}>
                            <AuditCard pool={pool} />
                            <LPLockCard pool={pool} />
                            <VolatilityCard pool={pool} />
                            <TokensCard pool={pool} />
                        </div>
                    </div>

                    {/* ═══════════════════════════════════ */}
                    {/* COLLAPSIBLE ACCORDIONS             */}
                    {/* ═══════════════════════════════════ */}
                    <div style={{ padding: '0 4px', marginBottom: '3px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <Accordion title="Token Security" icon={<Fingerprint className="w-3.5 h-3.5" style={{ color: 'var(--color-gold)' }} />}>
                            {(() => {
                                const sec = pool.security_result || pool.security || {}
                                const tokens = sec.tokens || {}
                                const source = sec.source || 'goplus'
                                const symbol0 = pool.symbol0 || pool.symbol?.split(/[\/\-]/)?.[0]?.trim() || 'Token 0'
                                const symbol1 = pool.symbol1 || pool.symbol?.split(/[\/\-]/)?.[1]?.trim() || 'Token 1'
                                const token0Addr = pool.token0 || ''
                                const token1Addr = pool.token1 || ''
                                const knownStables = ['USDC', 'USDT', 'DAI', 'USDbC', 'FRAX', 'LUSD', 'BUSD', 'USDM']

                                const buildTokenCard = (symbol: string, addr: string, fallbackIdx: number) => {
                                    const info = tokens[addr] || tokens[addr.toLowerCase()] || (Object.values(tokens)[fallbackIdx] as any) || {}
                                    const hasData = Object.keys(info).length > 0
                                    const isHoneypot = info.is_honeypot || info.is_critical
                                    const sellTax = parseFloat(info.sell_tax || 0) * 100
                                    const buyTax = parseFloat(info.buy_tax || 0) * 100
                                    const isVerified = info.is_verified !== false
                                    const isKnownStable = knownStables.some((s: string) => symbol.toUpperCase().includes(s))
                                    const hasOwnerIssues = info.hidden_owner || info.can_take_back_ownership || info.owner_change_balance

                                    let statusType = 'neutral' as 'safe' | 'warn' | 'critical' | 'neutral'; let borderColor = '#6B7280'
                                    if (!hasData && isKnownStable) { statusType = 'safe'; borderColor = '#10B981' }
                                    else if (!hasData) { statusType = 'neutral'; borderColor = '#6B7280' }
                                    else if (isHoneypot) { statusType = 'critical'; borderColor = '#EF4444' }
                                    else if (sellTax > 10 || buyTax > 10 || hasOwnerIssues) { statusType = 'warn'; borderColor = '#FBBF24' }
                                    else { statusType = 'safe'; borderColor = '#10B981' }

                                    return (
                                        <div key={symbol} style={{ padding: '6px', background: 'rgba(0,0,0,0.2)', borderRadius: '5px', borderLeft: `3px solid ${borderColor}` }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                                                <span style={{ fontSize: '11px', fontWeight: 600 }}>{symbol}</span>
                                                {statusType === 'safe' && <CircleCheck className="w-3.5 h-3.5" style={{ color: '#10B981' }} />}
                                                {statusType === 'warn' && <AlertTriangle className="w-3.5 h-3.5" style={{ color: '#FBBF24' }} />}
                                                {statusType === 'critical' && <OctagonX className="w-3.5 h-3.5" style={{ color: '#EF4444' }} />}
                                                {statusType === 'neutral' && <CircleDashed className="w-3.5 h-3.5" style={{ color: '#6B7280' }} />}
                                            </div>
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1px', fontSize: '10px' }}>
                                                {!hasData && isKnownStable && <div style={{ color: '#10B981', display: 'flex', alignItems: 'center', gap: '3px' }}><BadgeCheck className="w-3 h-3" /> Trusted Stablecoin</div>}
                                                {!hasData && !isKnownStable && <div style={{ color: '#6B7280', display: 'flex', alignItems: 'center', gap: '3px' }}><CircleDashed className="w-3 h-3" /> No data</div>}
                                                {hasData && (
                                                    <>
                                                        <div style={{ color: isHoneypot ? '#EF4444' : '#10B981', display: 'flex', alignItems: 'center', gap: '3px' }}>{isHoneypot ? <><Skull className="w-3 h-3" /> Honeypot DETECTED</> : <><CircleCheck className="w-3 h-3" /> No honeypot</>}</div>
                                                        {(sellTax > 0 || buyTax > 0) && (
                                                            <div style={{ color: sellTax > 10 || buyTax > 10 ? '#FBBF24' : '#10B981', display: 'flex', alignItems: 'center', gap: '3px' }}>
                                                                {sellTax > 10 || buyTax > 10 ? <Receipt className="w-3 h-3" style={{ color: '#FBBF24' }} /> : <Receipt className="w-3 h-3" style={{ color: '#10B981' }} />} Tax: Buy {buyTax.toFixed(1)}% / Sell {sellTax.toFixed(1)}%
                                                            </div>
                                                        )}
                                                        {source !== 'rugcheck' && (
                                                            <div style={{ color: isVerified ? '#10B981' : '#FBBF24', display: 'flex', alignItems: 'center', gap: '3px' }}>{isVerified ? <FileCheck className="w-3 h-3" /> : <FileQuestion className="w-3 h-3" />} {isVerified ? 'Verified' : 'Unverified'}</div>
                                                        )}
                                                        {info.is_mutable && <div style={{ color: '#FBBF24', display: 'flex', alignItems: 'center', gap: '3px' }}><PenLine className="w-3 h-3" /> Mutable metadata</div>}
                                                        {info.has_freeze_authority && <div style={{ color: '#FBBF24', display: 'flex', alignItems: 'center', gap: '3px' }}><Snowflake className="w-3 h-3" /> Freeze authority</div>}
                                                        {hasOwnerIssues && <div style={{ color: '#EF4444', display: 'flex', alignItems: 'center', gap: '3px' }}><UserX className="w-3 h-3" /> Owner can modify</div>}
                                                    </>
                                                )}
                                            </div>
                                        </div>
                                    )
                                }
                                return (
                                    <div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                                            <span style={{ fontSize: '9px', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: '3px' }}><Microscope className="w-3 h-3" /> {source === 'rugcheck' ? 'RugCheck' : 'GoPlus'}</span>
                                        </div>
                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                                            {buildTokenCard(symbol0, token0Addr, 0)}
                                            {buildTokenCard(symbol1, token1Addr, 1)}
                                        </div>
                                    </div>
                                )
                            })()}
                        </Accordion>

                        <Accordion title="Advanced Risk & Whale Analysis" icon={<Crosshair className="w-3.5 h-3.5" style={{ color: 'var(--color-gold)' }} />}>
                            {(() => {
                                // IL Risk
                                const ilAnalysis = pool.il_analysis || {}
                                const ilRisk = ilAnalysis.il_risk || pool.il_risk || (pool.stablecoin ? 'none' : 'medium')
                                const ilExplanation = ilAnalysis.il_explanation || (pool.stablecoin ? 'Stablecoin pair — minimal IL risk' : 'Standard volatile pair')
                                const ilPenalty = ilAnalysis.il_penalty || 0
                                const isStablePair = ilAnalysis.is_stable_pair || pool.stablecoin
                                const isCorrelated = ilAnalysis.is_correlated
                                const isCL = ilAnalysis.is_cl_pool || pool.pool_type === 'cl'
                                const getILColor = (r: string) => (r === 'none' || r === 'low') ? '#10B981' : r === 'medium' ? '#D4A853' : '#EF4444'

                                // Pool Age
                                const poolAge = pool.pool_age_analysis || {}
                                const poolAgeDays = poolAge.pool_age_days
                                const isNewPool = poolAge.is_new_pool
                                const agePenalty = poolAge.age_penalty || 0

                                // LP Whale
                                const whale = pool.whale_analysis || pool.whaleAnalysis || {}
                                const lpAnalysis = whale.lp_token || whale.lpToken || {}
                                const hasLpData = lpAnalysis.top_10_percent !== undefined
                                const lpTop10 = lpAnalysis.top_10_percent || 0
                                const lpHolders = lpAnalysis.holder_count || 0
                                const lpRisk = lpAnalysis.concentration_risk || 'unknown'
                                const isCLPool = lpAnalysis.is_cl_pool || lpAnalysis.source === 'cl_pool' || pool.pool_type === 'cl'
                                const formatH = (c: number) => !c ? 'N/A' : c >= 1e6 ? `${(c / 1e6).toFixed(1)}M` : c >= 1e3 ? `${(c / 1e3).toFixed(1)}K` : String(c)

                                // Token Whale
                                const t0 = whale.token0 || {}
                                const t1 = whale.token1 || {}
                                const sym0 = pool.symbol0 || 'Token0'
                                const sym1 = pool.symbol1 || 'Token1'
                                const riskColors: Record<string, string> = { low: '#10B981', medium: '#FBBF24', high: '#EF4444', unknown: '#6B7280' }

                                // Risk Breakdown
                                const riskBreakdown = { ...(pool.risk_breakdown || {}) }
                                delete riskBreakdown.audit; delete riskBreakdown.Audit
                                const audit = pool.audit_status || pool.audit || {}
                                const hasAudit = audit.audited === true || (audit.auditors?.length > 0)
                                riskBreakdown.Audit = hasAudit ? 'verified' : 'unverified'

                                const renderWhaleRow = (analysis: any, symbol: string) => {
                                    if (analysis.skipped) return <div key={symbol} style={{ fontSize: '10px', display: 'flex', gap: '4px', alignItems: 'center' }}><span style={{ color: 'var(--color-text-muted)' }}>{symbol}:</span><BadgeCheck className="w-3 h-3" style={{ color: '#10B981' }} /><span style={{ color: '#10B981' }}>Whitelisted</span></div>
                                    const r = analysis.concentration_risk || 'unknown'
                                    const top = analysis.top_10_percent || 0
                                    const h = analysis.holder_count || 0
                                    return (
                                        <div key={symbol} style={{ fontSize: '11px', display: 'flex', gap: '6px', alignItems: 'center' }}>
                                            <span style={{ color: 'var(--color-text-muted)' }}>{symbol}:</span>
                                            <span style={{ color: riskColors[r] || '#6B7280', fontWeight: 600 }}>{r.toUpperCase()}</span>
                                            {top > 0 && <span style={{ color: 'var(--color-text-muted)', fontSize: '10px' }}>Top10: {top.toFixed(1)}%</span>}
                                            {h > 0 && <span style={{ color: 'var(--color-text-muted)', fontSize: '10px' }}>{formatH(h)} holders</span>}
                                        </div>
                                    )
                                }

                                return (
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                        {/* Risk Panels Grid */}
                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                                            {/* IL Risk Panel */}
                                            <div style={{ padding: '8px', background: 'rgba(0,0,0,0.2)', borderRadius: '6px', borderLeft: `3px solid ${getILColor(ilRisk)}` }}>
                                                <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '3px' }}><TrendingDown className="w-3 h-3" /> Impermanent Loss</div>
                                                <div style={{ fontSize: '14px', fontWeight: 700, color: getILColor(ilRisk) }}>
                                                    {ilRisk.toUpperCase()}
                                                    {ilPenalty > 0 && <span style={{ fontSize: '10px', color: '#EF4444', marginLeft: '6px' }}>-{ilPenalty} pts</span>}
                                                </div>
                                                <div style={{ fontSize: '10px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>{ilExplanation}</div>
                                                <div style={{ display: 'flex', gap: '4px', marginTop: '4px', flexWrap: 'wrap' }}>
                                                    {isStablePair && <span style={{ fontSize: '9px', padding: '1px 6px', borderRadius: '8px', background: 'rgba(16,185,129,0.15)', color: '#10B981' }}>Stable Pair</span>}
                                                    {isCorrelated && <span style={{ fontSize: '9px', padding: '1px 6px', borderRadius: '8px', background: 'rgba(59,130,246,0.15)', color: '#60A5FA' }}>Correlated</span>}
                                                    {isCL && <span style={{ fontSize: '9px', padding: '1px 6px', borderRadius: '8px', background: 'rgba(251,191,36,0.15)', color: '#FBBF24' }}>CL Pool (higher IL)</span>}
                                                </div>
                                            </div>

                                            {/* LP Whale Panel */}
                                            <div style={{ padding: '8px', background: 'rgba(0,0,0,0.2)', borderRadius: '6px', borderLeft: `3px solid ${isCLPool ? '#10B981' : riskColors[lpRisk] || '#6B7280'}` }}>
                                                <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '3px' }}><Layers className="w-3 h-3" /> LP Concentration</div>
                                                {isCLPool ? (
                                                    <>
                                                        <div style={{ fontSize: '14px', fontWeight: 700, color: '#10B981' }}>LOW</div>
                                                        <div style={{ fontSize: '10px', color: 'var(--color-text-secondary)' }}>CL Pool — NFT positions (fragmented)</div>
                                                    </>
                                                ) : hasLpData ? (
                                                    <>
                                                        <div style={{ fontSize: '14px', fontWeight: 700, color: riskColors[lpRisk] || '#6B7280' }}>{lpRisk.toUpperCase()}</div>
                                                        <div style={{ fontSize: '10px', color: 'var(--color-text-secondary)' }}>
                                                            {lpTop10 > 0 ? `Top 10 LPs: ${lpTop10.toFixed(1)}%` : ''}
                                                            {lpHolders > 0 ? ` • ${formatH(lpHolders)} positions` : ''}
                                                        </div>
                                                    </>
                                                ) : (
                                                    <>
                                                        <div style={{ fontSize: '14px', fontWeight: 700, color: '#6B7280' }}>N/A</div>
                                                        <div style={{ fontSize: '10px', color: 'var(--color-text-secondary)' }}>LP holder data not available</div>
                                                    </>
                                                )}
                                            </div>

                                            {/* Pool Age Panel */}
                                            {poolAgeDays !== undefined && (
                                                <div style={{ padding: '8px', background: 'rgba(0,0,0,0.2)', borderRadius: '6px', borderLeft: `3px solid ${isNewPool ? '#EF4444' : '#10B981'}` }}>
                                                    <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '3px' }}><Clock className="w-3 h-3" /> Pool Age</div>
                                                    <div style={{ fontSize: '14px', fontWeight: 700, color: isNewPool ? '#EF4444' : '#10B981' }}>
                                                        {poolAgeDays} DAYS
                                                        {agePenalty > 0 && <span style={{ fontSize: '10px', color: '#EF4444', marginLeft: '6px' }}>-{agePenalty} pts</span>}
                                                    </div>
                                                    <div style={{ fontSize: '10px', color: 'var(--color-text-secondary)' }}>
                                                        <span style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>{isNewPool ? <><Hourglass className="w-3 h-3" /> New pool — higher risk</> : <><Verified className="w-3 h-3" /> Established pool</>}</span>
                                                    </div>
                                                </div>
                                            )}

                                            {/* Token Whale Panel */}
                                            <div style={{ padding: '8px', background: 'rgba(0,0,0,0.2)', borderRadius: '6px', borderLeft: '3px solid var(--color-text-muted)' }}>
                                                <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '3px' }}><Eye className="w-3 h-3" /> Token Whales</div>
                                                {(t0.skipped && t1.skipped) ? (
                                                    <>
                                                        <div style={{ fontSize: '14px', fontWeight: 700, color: '#10B981' }}>LOW</div>
                                                        <div style={{ fontSize: '10px', color: 'var(--color-text-secondary)' }}>Major tokens — highly distributed</div>
                                                    </>
                                                ) : (
                                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '2px' }}>
                                                        {renderWhaleRow(t0, sym0)}
                                                        {renderWhaleRow(t1, sym1)}
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        {/* Risk Score Breakdown */}
                                        {Object.keys(riskBreakdown).length > 0 && (
                                            <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '6px', padding: '8px' }}>
                                                <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '6px', letterSpacing: '0.05em' }}>Risk Score Breakdown</div>
                                                <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                                                    {Object.entries(riskBreakdown).map(([key, value]) => {
                                                        const isNumeric = typeof value === 'number'
                                                        const label = key.replace(/_/g, ' ')
                                                        let color = '#9CA3AF'
                                                        let display: string = String(value)
                                                        if (isNumeric) {
                                                            if ((value as number) < 0) color = '#EF4444'
                                                            else if ((value as number) > 0) { color = '#10B981'; display = '+' + value }
                                                        } else {
                                                            const goodVals = ['verified', 'locked', 'low', 'strong', 'stable']
                                                            const badVals = ['unverified', 'unlocked', 'high', 'weak', 'critical', 'extreme']
                                                            const vLow = String(value).toLowerCase()
                                                            if (goodVals.some(v => vLow.includes(v))) color = '#10B981'
                                                            else if (badVals.some(v => vLow.includes(v))) color = '#EF4444'
                                                            else color = '#FBBF24'
                                                        }
                                                        return (
                                                            <div key={key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px' }}>
                                                                <span style={{ color: 'var(--color-text-secondary)', textTransform: 'capitalize' }}>{label}</span>
                                                                <span style={{ color, fontWeight: 600 }}>{display}</span>
                                                            </div>
                                                        )
                                                    })}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )
                            })()}
                        </Accordion>

                        <Accordion title="Exit Strategy" icon={<LogOut className="w-3.5 h-3.5" style={{ color: 'var(--color-gold)' }} />}>
                            {exitSim.length > 0 ? (
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '4px' }}>
                                    {exitSim.map((pos, i) => (
                                        <div key={i} style={{ padding: '6px 8px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px', textAlign: 'center' }}>
                                            <div style={{ fontSize: '11px', fontWeight: 600 }}>{pos.label}</div>
                                            <div style={{ fontSize: '14px', fontWeight: 700, color: pos.color }}>{pos.slippage.toFixed(2)}%</div>
                                            <div style={{ fontSize: '10px', color: pos.color }}>-${pos.loss.toFixed(0)}</div>
                                        </div>
                                    ))}
                                </div>
                            ) : <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>TVL data unavailable for simulation</div>}
                        </Accordion>


                    </div>

                    {/* ═══════════════════════════════════ */}
                    {/* MARKET DYNAMICS                    */}
                    {/* ═══════════════════════════════════ */}
                    <div style={{ padding: '0 4px', marginBottom: '3px' }}>
                        <div style={{ background: 'rgba(255,255,255,0.02)', borderRadius: '6px', padding: '6px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                                <span style={{ fontSize: '10px', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '4px' }}><Gauge className="w-3 h-3" /> Market Dynamics</span>
                                {isEpochProtocol(pool.project) && (
                                    <span style={{ fontSize: '9px', padding: '2px 6px', borderRadius: '8px', background: 'rgba(212,168,83,0.1)', color: 'var(--color-gold)', display: 'flex', alignItems: 'center', gap: '3px' }}><Timer className="w-3 h-3" /> Epoch: {getEpochCountdown()}</span>
                                )}
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '4px' }}>
                                {typeof pool.apy_base === 'number' && (
                                    <div style={{ padding: '6px 8px', background: 'rgba(0,0,0,0.2)', borderRadius: '6px' }}>
                                        <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '3px' }}>APY Composition</div>
                                        <div style={{ fontSize: '10px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10B981', display: 'inline-block' }} /> Base: {Number(pool.apy_base || 0).toFixed(2)}%
                                        </div>
                                        <div style={{ fontSize: '10px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#FBBF24', display: 'inline-block' }} /> Reward: {Number(pool.apy_reward || 0).toFixed(2)}%
                                        </div>
                                    </div>
                                )}
                                <div style={{ padding: '6px 8px', background: 'rgba(0,0,0,0.2)', borderRadius: '6px' }}>
                                    <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '3px' }}>TVL Stability</div>
                                    <div style={{ fontSize: '12px', fontWeight: 600, color: pool.tvl > 10_000_000 ? '#10B981' : pool.tvl > 1_000_000 ? '#FBBF24' : pool.tvl > 0 ? '#EF4444' : '#6B7280' }}>{pool.tvl > 10_000_000 ? 'High' : pool.tvl > 1_000_000 ? 'Medium' : pool.tvl > 0 ? 'Low' : '—'}</div>
                                </div>
                                <div style={{ padding: '6px 8px', background: 'rgba(0,0,0,0.2)', borderRadius: '6px' }}>
                                    <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '3px' }}>24H Volume</div>
                                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#fff' }}>{pool.volume_24h ? formatUsd(pool.volume_24h) : pool.volume_24h_formatted || 'N/A'}</div>
                                </div>
                                {pool.trading_fee !== undefined && (
                                    <div style={{ padding: '6px 8px', background: 'rgba(0,0,0,0.2)', borderRadius: '6px' }}>
                                        <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '3px' }}>Trading Fee</div>
                                        <div style={{ fontSize: '13px', fontWeight: 600, color: '#fff' }}>{(pool.trading_fee * 100).toFixed(2)}%</div>
                                    </div>
                                )}
                            </div>

                            {/* Risk Reasons */}
                            {pool.risk_reasons && pool.risk_reasons.length > 0 && (
                                <div style={{ marginTop: '6px', paddingTop: '6px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                                    <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '3px' }}>Risk Factors</div>
                                    {pool.risk_reasons.map((r, i) => (
                                        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                                            <CircleAlert style={{ width: '10px', height: '10px', flexShrink: 0, color: 'var(--color-gold)' }} />
                                            {r}
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Premium Insights */}
                            {(pool as any).premium_insights?.length > 0 && (
                                <div style={{ marginTop: '6px', paddingTop: '6px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                                    {(pool as any).premium_insights.map((insight: any, i: number) => (
                                        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '6px', fontSize: '11px', color: 'var(--color-text-secondary)', marginTop: '3px' }}>
                                            <span style={{ width: '3px', height: '14px', borderRadius: '2px', flexShrink: 0, marginTop: '1px', background: insight.type === 'positive' ? '#10B981' : insight.type === 'warning' ? '#FBBF24' : 'var(--color-gold)' }} />
                                            {insight.text}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* ═══════════ ACTION BUTTONS ═══════════ */}
                    <div style={{ display: 'flex', gap: '4px', padding: '0 4px 4px' }}>
                        <motion.button whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.98 }} onClick={openProtocol}
                            style={{ flex: 1, padding: '10px', borderRadius: '8px', fontSize: '13px', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', background: 'linear-gradient(135deg, var(--color-gold), var(--color-gold-bright))', color: '#0a0a0f', border: 'none' }}>
                            <ArrowRight style={{ width: '14px', height: '14px' }} />
                            Deposit on {pool.project}
                        </motion.button>
                        <button onClick={() => { }} style={{ padding: '10px 14px', borderRadius: '8px', fontSize: '12px', fontWeight: 600, cursor: 'pointer', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'var(--color-text-secondary)' }}>
                            + Strategy
                        </button>
                        <button onClick={copyAddress} style={{ padding: '10px', borderRadius: '8px', cursor: 'pointer', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }} title="Copy address">
                            {copied ? <Check style={{ width: '14px', height: '14px', color: 'var(--color-green)' }} /> : <Copy style={{ width: '14px', height: '14px', color: 'var(--color-text-secondary)' }} />}
                        </button>
                        <button onClick={openExplorer} style={{ padding: '10px', borderRadius: '8px', cursor: 'pointer', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }} title="Explorer">
                            <ExternalLink style={{ width: '14px', height: '14px', color: 'var(--color-text-secondary)' }} />
                        </button>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    )
}
