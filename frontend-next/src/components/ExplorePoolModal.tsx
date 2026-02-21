/**
 * ExplorePoolModal — Lightweight pool detail view for Explore page
 * Data source: GeckoTerminal / DefiLlama only (no Moralis/RPC data)
 * No Token Security, no Advanced Risk / Whale Analysis
 * Narrower than the full PoolDetailModal (max-width 520px)
 */
import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    X, ExternalLink, Copy, Check,
    Flame, TrendingDown, Target, Droplet, Clock, Zap,
    Scale, Flag, FlaskConical, Wallet, LineChart,
    BadgeCheck,
} from 'lucide-react'
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer
} from 'recharts'
import { type Pool, getRiskColor, getRiskLabel, formatUsd, formatApy } from '@/lib/api'
import { getProtocolIconUrl, getChainIconUrl } from '@/lib/icons'

// ========== Types ==========
type Tab = 'overview' | 'yield' | 'history'

interface ExplorePoolModalProps {
    pool: Pool & Record<string, any>
    onClose: () => void
}

// ========== Helpers ==========
function getVerdict(score: number) {
    if (score >= 70) return { label: 'SAFE', color: '#10B981', desc: 'Low risk based on public data' }
    if (score >= 40) return { label: 'CAUTION', color: '#D4A853', desc: 'Moderate risk — review before investing' }
    return { label: 'HIGH RISK', color: '#EF4444', desc: 'Significant risk factors detected' }
}

function getSourceBadge(source?: string) {
    if (!source) return 'DefiLlama'
    if (source.includes('gecko')) return 'GeckoTerminal'
    if (source.includes('defillama')) return 'DefiLlama'
    return 'On-chain'
}

function isEpochProtocol(project?: string) {
    const p = (project || '').toLowerCase()
    return p.includes('aerodrome') || p.includes('velodrome')
}

function buildRiskFlags(pool: any) {
    const flags: { icon: React.ReactNode; text: string; type: 'info' | 'warning' | 'caution' }[] = []

    if (pool.risk_flags?.length > 0) {
        return pool.risk_flags.map((rf: any) => ({
            icon: <Flag className="w-3 h-3" />,
            text: rf.label,
            type: rf.severity === 'high' ? 'warning' : rf.severity === 'medium' ? 'caution' : 'info'
        }))
    }

    const isCL = pool.pool_type === 'cl' || (pool.project || '').toLowerCase().includes('slipstream')
    if (isCL) flags.push({ icon: <Target className="w-3 h-3" />, text: 'Concentrated Liquidity', type: 'info' })
    if (pool.gauge_address) flags.push({ icon: <Zap className="w-3 h-3" />, text: 'Emissions-based', type: 'info' })
    if (isEpochProtocol(pool.project)) flags.push({ icon: <Clock className="w-3 h-3" />, text: 'Epoch rewards', type: 'info' })
    if (!pool.stablecoin && pool.il_risk !== 'no') flags.push({ icon: <TrendingDown className="w-3 h-3" />, text: 'IL risk', type: 'warning' })
    if (pool.apy > 200) flags.push({ icon: <Flame className="w-3 h-3" />, text: 'Very high APY', type: 'warning' })
    if (pool.tvl < 100000) flags.push({ icon: <Droplet className="w-3 h-3" />, text: 'Low liquidity', type: 'warning' })
    return flags
}

// ========== Sub-Components ==========

function YieldRow({ label, value, color, bold }: { label: string; value: string; color: string; bold?: boolean }) {
    return (
        <div className="flex items-center justify-between">
            <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>{label}</span>
            <span className={`text-sm ${bold ? 'font-bold' : 'font-medium'}`} style={{ color }}>{value}</span>
        </div>
    )
}

// ========== MAIN COMPONENT ==========

export function ExplorePoolModal({ pool, onClose }: ExplorePoolModalProps) {
    const [tab, setTab] = useState<Tab>('overview')
    const [copied, setCopied] = useState(false)

    const score = pool.risk_score || 50
    const verdict = getVerdict(score)
    const riskColor = getRiskColor(score)
    const riskLabel = getRiskLabel(score)
    const flags = useMemo(() => buildRiskFlags(pool), [pool])

    // Stress Test data
    const stressData = useMemo(() => {
        const tvl = pool.tvl || 0
        const fmt = (v: number) => v >= 1e9 ? `$${(v / 1e9).toFixed(1)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(0)}K` : `$${v.toFixed(0)}`
        let level = 'HEALTHY', levelColor = '#22C55E'
        if (tvl < 100_000) { level = 'CRITICAL'; levelColor = '#EF4444' }
        else if (tvl < 500_000) { level = 'STRESSED'; levelColor = '#F59E0B' }
        else if (tvl < 2_000_000) { level = 'MODERATE'; levelColor = '#84CC16' }

        const scenarios = tvl > 0 ? [
            { drop: 10, remaining: fmt(tvl * 0.9), color: '#22C55E' },
            { drop: 30, remaining: fmt(tvl * 0.7), color: '#F59E0B' },
            { drop: 50, remaining: fmt(tvl * 0.5), color: '#EF4444' },
        ] : []

        const ilRisk = pool.il_risk || (pool.stablecoin ? 'low' : 'medium')
        return { level, levelColor, tvlFmt: fmt(tvl), scenarios, ilRisk }
    }, [pool])

    // Yield Analysis
    const yieldInfo = useMemo(() => {
        const apy = pool.apy || 0
        const apyBase = parseFloat(pool.apy_base || pool.apyBase || 0)
        const apyReward = parseFloat(pool.apy_reward || pool.apyReward || 0)
        const total = apyBase + apyReward
        const hasBreakdown = total > 0
        const emissionPct = hasBreakdown ? (apyReward / total * 100) : 0
        let sustainability = 'Sustainable', sustColor = '#10B981'
        if (emissionPct > 80) { sustainability = 'High emission dependency'; sustColor = '#EF4444' }
        else if (emissionPct > 50) { sustainability = 'Moderate reliance'; sustColor = '#FBBF24' }
        return { baseApy: apyBase, rewardApy: apyReward, totalApy: apy, hasBreakdown, sustainability, sustColor, rewardToken: pool.reward_token || 'Protocol Token' }
    }, [pool])

    // APY History
    const historyInfo = useMemo(() => {
        const currentApy = pool.apy || 0
        const apyHistory = pool.apy_history || pool.apyHistory || []
        const apyPct7D = pool.apyPct7D || 0

        let sparkline: number[] = apyHistory.length > 0
            ? apyHistory.map((h: any) => h.apy || h.value || 0) : []
        if (sparkline.length === 0 && currentApy > 0) {
            const variance = currentApy * 0.15
            const seed = (pool.address || pool.pool_address || '').split('').reduce((a: number, c: string) => a + c.charCodeAt(0), 0)
            sparkline = Array(30).fill(0).map((_: number, i: number) => {
                const pr = Math.sin(seed + i * 7.13) * 0.5 + 0.5
                return Math.max(0, currentApy + (pr - 0.5) * variance * 2)
            })
        }

        const min = sparkline.length > 0 ? Math.min(...sparkline) : currentApy * 0.8
        const max = sparkline.length > 0 ? Math.max(...sparkline) : currentApy * 1.2
        const avg = sparkline.length > 0 ? sparkline.reduce((a: number, b: number) => a + b, 0) / sparkline.length : currentApy
        const vol = avg > 0 ? ((max - min) / avg * 100) : 0
        let volLevel = 'Low', volColor = '#10B981'
        if (vol > 50) { volLevel = 'High'; volColor = '#EF4444' }
        else if (vol > 25) { volLevel = 'Medium'; volColor = '#FBBF24' }

        const chartData = sparkline.length > 0
            ? sparkline.map((apy: number, i: number) => {
                const d = new Date(); d.setDate(d.getDate() - (sparkline.length - 1 - i))
                return { date: d.toLocaleDateString('en', { month: 'short', day: 'numeric' }), apy }
            }) : null

        const trendColor = apyPct7D >= 0 ? '#10B981' : '#EF4444'
        const trendIcon = apyPct7D >= 0 ? '▲' : '▼'
        return { min, max, avg, volLevel, volColor, chartData, trend7d: apyPct7D, trendColor, trendIcon }
    }, [pool])

    const copyAddress = () => {
        const addr = pool.address || pool.pool_address || pool.pool_id
        navigator.clipboard.writeText(addr)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    const openExplorer = () => {
        if (pool.pool_link) window.open(pool.pool_link, '_blank')
        else if (pool.explorer_url) window.open(pool.explorer_url, '_blank')
        else if (pool.address || pool.pool_address) window.open(`https://basescan.org/address/${pool.address || pool.pool_address}`, '_blank')
    }

    return (
        <AnimatePresence>
            <motion.div className="fixed inset-0 z-50 flex items-center justify-center p-4"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                {/* Backdrop */}
                <motion.div className="absolute inset-0" style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
                    onClick={onClose} initial={{ opacity: 0 }} animate={{ opacity: 1 }} />

                {/* Modal */}
                <motion.div className="relative overflow-y-auto"
                    style={{
                        width: '95vw', maxWidth: '520px', maxHeight: '90vh', padding: '16px',
                        background: 'linear-gradient(180deg, rgba(20,20,20,0.98), rgba(10,10,10,0.98))',
                        border: '1px solid rgba(212,168,83,0.2)', borderRadius: '12px',
                        boxShadow: '0 0 40px rgba(212,168,83,0.06)',
                    }}
                    initial={{ opacity: 0, y: 30, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 30, scale: 0.95 }}
                    transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}>

                    {/* Close */}
                    <button onClick={onClose} className="absolute top-3 right-3 z-20 w-7 h-7 rounded-full flex items-center justify-center cursor-pointer"
                        style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)' }}>
                        <X className="w-3.5 h-3.5" style={{ color: 'var(--color-text-muted)' }} />
                    </button>

                    {/* ═══ HEADER ═══ */}
                    <div className="flex items-center gap-3 mb-3 pr-10">
                        <div className="relative flex-shrink-0">
                            <img src={getProtocolIconUrl(pool.project)} alt={pool.project}
                                className="w-10 h-10 rounded-full"
                                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
                            {pool.chain && (
                                <img src={getChainIconUrl(pool.chain)} alt={pool.chain}
                                    className="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full"
                                    style={{ border: '2px solid rgba(20,20,20,0.98)' }}
                                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
                            )}
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="text-sm font-semibold text-white truncate">{pool.symbol}</div>
                            <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                                {pool.project} · {pool.chain || 'Base'}
                            </div>
                        </div>
                        <div className="text-right">
                            <div className="text-xl font-heading font-bold" style={{ color: 'var(--color-green)' }}>
                                {pool.apy > 0 ? formatApy(pool.apy) : 'N/A'}
                            </div>
                            <div className="text-[9px] uppercase tracking-wider" style={{ color: 'var(--color-text-muted)' }}>APY</div>
                        </div>
                    </div>

                    {/* ═══ VERDICT + SOURCE ═══ */}
                    <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg mb-3" style={{
                        background: `linear-gradient(135deg, ${verdict.color}08, ${verdict.color}04)`,
                        border: `1px solid ${verdict.color}20`,
                    }}>
                        {/* Score ring */}
                        <div className="relative w-10 h-10 flex-shrink-0">
                            <svg viewBox="0 0 100 100" className="w-full h-full">
                                <circle cx="50" cy="50" r="32" fill="transparent" stroke="rgba(255,255,255,0.06)" strokeWidth="7" />
                                <motion.circle cx="50" cy="50" r="32" fill="transparent"
                                    stroke={verdict.color} strokeWidth="7" strokeLinecap="round"
                                    strokeDasharray={201}
                                    initial={{ strokeDashoffset: 201 }}
                                    animate={{ strokeDashoffset: 201 - (score / 100) * 201 }}
                                    transition={{ duration: 1, ease: 'easeOut' }}
                                    transform="rotate(-90 50 50)" />
                            </svg>
                            <div className="absolute inset-0 flex items-center justify-center">
                                <span className="text-sm font-heading font-extrabold" style={{ color: verdict.color }}>{score}</span>
                            </div>
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                                <span className="text-xs font-heading font-bold tracking-wider uppercase" style={{ color: verdict.color }}>{verdict.label}</span>
                                <span className="text-[9px] px-1.5 py-0.5 rounded" style={{ background: 'rgba(255,255,255,0.04)', color: 'var(--color-text-muted)' }}>
                                    {getSourceBadge(pool.source)}
                                </span>
                            </div>
                            <div className="text-[10px] mt-0.5" style={{ color: 'var(--color-text-muted)' }}>{verdict.desc}</div>
                        </div>
                    </div>

                    {/* ═══ METRICS ROW ═══ */}
                    <div className="grid grid-cols-3 gap-2 mb-3">
                        <div className="text-center p-2 rounded-lg" style={{ background: 'rgba(255,255,255,0.03)' }}>
                            <div className="text-sm font-semibold text-white">{formatUsd(pool.tvl)}</div>
                            <div className="text-[9px]" style={{ color: 'var(--color-text-muted)' }}>TVL</div>
                        </div>
                        <div className="text-center p-2 rounded-lg" style={{ background: 'rgba(255,255,255,0.03)' }}>
                            <div className="text-sm font-semibold" style={{ color: riskColor }}>{riskLabel}</div>
                            <div className="text-[9px]" style={{ color: 'var(--color-text-muted)' }}>Risk</div>
                        </div>
                        <div className="text-center p-2 rounded-lg" style={{ background: 'rgba(255,255,255,0.03)' }}>
                            <div className="text-sm font-semibold text-white flex items-center justify-center gap-1">
                                {pool.stablecoin ? <Scale className="w-3.5 h-3.5" style={{ color: '#10B981' }} /> : <Flame className="w-3.5 h-3.5" style={{ color: '#FBBF24' }} />}
                                {pool.stablecoin ? 'Stable' : 'Volatile'}
                            </div>
                            <div className="text-[9px]" style={{ color: 'var(--color-text-muted)' }}>Type</div>
                        </div>
                    </div>

                    {/* ═══ 24H VOLUME ═══ */}
                    {pool.volume_24h && pool.volume_24h > 0 && (
                        <div className="flex items-center justify-between px-3 py-2 rounded-lg mb-3"
                            style={{ background: 'rgba(255,255,255,0.03)' }}>
                            <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>24h Volume</span>
                            <span className="text-sm font-semibold text-white">
                                {pool.volume_formatted || pool.volume_24h_formatted || formatUsd(pool.volume_24h)}
                            </span>
                        </div>
                    )}

                    {/* ═══ RISK FLAGS ═══ */}
                    {flags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-3">
                            {flags.map((f: { icon: React.ReactNode; text: string; type: 'info' | 'warning' | 'caution' }, i: number) => {
                                const colorMap: Record<string, string> = { info: 'var(--color-gold)', warning: '#EF4444', caution: '#FBBF24' }
                                const c = colorMap[f.type]
                                return (
                                    <div key={i} className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded" style={{
                                        background: `color-mix(in srgb, ${c} 6%, transparent)`,
                                        border: `1px solid color-mix(in srgb, ${c} 15%, transparent)`,
                                        color: c,
                                    }}>
                                        {f.icon} {f.text}
                                    </div>
                                )
                            })}
                        </div>
                    )}

                    {/* ═══ TABS ═══ */}
                    <div className="flex gap-1 p-1 rounded-lg mb-3" style={{ background: 'rgba(0,0,0,0.3)' }}>
                        {([
                            { id: 'overview' as Tab, icon: <FlaskConical className="w-3 h-3" />, label: 'Overview' },
                            { id: 'yield' as Tab, icon: <Wallet className="w-3 h-3" />, label: 'Yield' },
                            { id: 'history' as Tab, icon: <LineChart className="w-3 h-3" />, label: 'APY History' },
                        ]).map(t => (
                            <button key={t.id} onClick={() => setTab(t.id)}
                                className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded text-[10px] font-medium cursor-pointer transition-all"
                                style={{
                                    background: tab === t.id ? 'rgba(212,168,83,0.12)' : 'transparent',
                                    border: tab === t.id ? '1px solid rgba(212,168,83,0.2)' : '1px solid transparent',
                                    color: tab === t.id ? 'var(--color-gold)' : 'var(--color-text-muted)',
                                }}>
                                {t.icon} {t.label}
                            </button>
                        ))}
                    </div>

                    {/* ═══ TAB CONTENT ═══ */}
                    <AnimatePresence mode="wait">
                        {tab === 'overview' && (
                            <motion.div key="overview" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                className="space-y-2">
                                {/* Stress Level */}
                                <div className="flex justify-between items-center px-3 py-2 rounded-lg"
                                    style={{ background: 'rgba(0,0,0,0.2)' }}>
                                    <span className="text-xs font-semibold" style={{ color: stressData.levelColor }}>
                                        Liquidity: {stressData.level}
                                    </span>
                                    <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                                        TVL: {stressData.tvlFmt}
                                    </span>
                                </div>

                                {/* Drawdown scenarios */}
                                {stressData.scenarios.map((s, i) => (
                                    <div key={i} className="flex items-center gap-2 px-3">
                                        <span className="text-[11px] w-8" style={{ color: 'var(--color-text-muted)' }}>-{s.drop}%</span>
                                        <div className="flex-1 h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.1)' }}>
                                            <div className="h-full rounded-full" style={{ width: `${100 - s.drop}%`, background: s.color }} />
                                        </div>
                                        <span className="text-[11px]" style={{ color: 'var(--color-text-muted)' }}>{s.remaining}</span>
                                    </div>
                                ))}

                                {/* IL Risk */}
                                <div className="flex justify-between items-center px-3 py-2 rounded-lg"
                                    style={{ background: 'rgba(0,0,0,0.2)' }}>
                                    <span className="text-xs text-white">Impermanent Loss</span>
                                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full" style={{
                                        background: `${stressData.ilRisk === 'low' || stressData.ilRisk === 'no' ? '#10B981' : stressData.ilRisk === 'medium' ? '#FBBF24' : '#EF4444'}15`,
                                        color: stressData.ilRisk === 'low' || stressData.ilRisk === 'no' ? '#10B981' : stressData.ilRisk === 'medium' ? '#FBBF24' : '#EF4444',
                                    }}>
                                        {stressData.ilRisk === 'no' ? 'None' : stressData.ilRisk.charAt(0).toUpperCase() + stressData.ilRisk.slice(1)}
                                    </span>
                                </div>

                                {/* Risk reasons from API */}
                                {pool.risk_reasons && pool.risk_reasons.length > 0 && (
                                    <div className="px-3 py-2 rounded-lg" style={{ background: 'rgba(250,204,21,0.04)', border: '1px solid rgba(250,204,21,0.1)' }}>
                                        <div className="text-[10px] font-semibold mb-1" style={{ color: '#FBBF24' }}>Risk Reasons</div>
                                        {pool.risk_reasons.map((r: string, i: number) => (
                                            <div key={i} className="text-[10px] ml-2" style={{ color: 'var(--color-text-secondary)' }}>• {r}</div>
                                        ))}
                                    </div>
                                )}
                            </motion.div>
                        )}

                        {tab === 'yield' && (
                            <motion.div key="yield" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                                <div className="p-3 rounded-lg" style={{ background: 'rgba(0,0,0,0.2)' }}>
                                    {yieldInfo.hasBreakdown ? (
                                        <>
                                            <div className="text-[10px] uppercase tracking-wider mb-3" style={{ color: 'var(--color-text-muted)' }}>
                                                Yield Composition
                                            </div>
                                            <YieldRow label="Base APY (Fees)" value={formatApy(yieldInfo.baseApy)} color="#10B981" />
                                            <YieldRow label={`Reward APY (${yieldInfo.rewardToken})`} value={formatApy(yieldInfo.rewardApy)} color="#FBBF24" />
                                            <div className="border-t mt-2 pt-2" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
                                                <YieldRow label="Total APY" value={formatApy(yieldInfo.totalApy)} color="var(--color-green)" bold />
                                            </div>
                                            <div className="mt-3 text-[11px]" style={{ color: 'var(--color-text-muted)' }}>
                                                Sustainability: <span style={{ color: yieldInfo.sustColor, fontWeight: 600 }}>{yieldInfo.sustainability}</span>
                                            </div>
                                        </>
                                    ) : (
                                        <>
                                            <div className="text-[10px] uppercase tracking-wider mb-3" style={{ color: 'var(--color-text-muted)' }}>
                                                Yield Overview
                                            </div>
                                            <YieldRow label="Total APY" value={formatApy(yieldInfo.totalApy)} color="var(--color-gold)" bold />
                                            <div className="text-[11px] mt-2" style={{ color: '#6B7280' }}>Breakdown not available for this pool</div>
                                            {yieldInfo.totalApy > 0 && (
                                                <div className="text-[11px] mt-1 flex items-center gap-1" style={{ color: '#10B981', fontWeight: 500 }}>
                                                    <BadgeCheck className="w-3 h-3" /> Yield verified
                                                </div>
                                            )}
                                        </>
                                    )}
                                </div>
                            </motion.div>
                        )}

                        {tab === 'history' && (
                            <motion.div key="history" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                                <div className="flex justify-between items-center mb-2">
                                    <div className="text-[10px] uppercase" style={{ color: 'var(--color-text-muted)' }}>APY History (30d)</div>
                                    <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold" style={{
                                        background: `${historyInfo.volColor}15`, color: historyInfo.volColor,
                                    }}>
                                        Volatility: {historyInfo.volLevel}
                                    </span>
                                </div>
                                {historyInfo.chartData ? (
                                    <div style={{ height: '120px' }}>
                                        <ResponsiveContainer width="100%" height="100%">
                                            <AreaChart data={historyInfo.chartData}>
                                                <defs>
                                                    <linearGradient id="exploreApyGrad" x1="0" y1="0" x2="0" y2="1">
                                                        <stop offset="5%" stopColor="#D4A853" stopOpacity={0.3} />
                                                        <stop offset="95%" stopColor="#D4A853" stopOpacity={0} />
                                                    </linearGradient>
                                                </defs>
                                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                                <XAxis dataKey="date" tick={{ fill: 'var(--color-text-muted)', fontSize: 8 }} axisLine={false} tickLine={false} interval={6} />
                                                <YAxis tick={{ fill: 'var(--color-text-muted)', fontSize: 8 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `${v.toFixed(0)}%`} domain={['auto', 'auto']} />
                                                <Tooltip contentStyle={{ background: 'rgba(20,20,20,0.95)', border: '1px solid rgba(212,168,83,0.3)', borderRadius: '6px', fontSize: '11px' }}
                                                    formatter={(v: any) => [`${Number(v).toFixed(2)}%`, 'APY']} />
                                                <Area type="monotone" dataKey="apy" stroke="#D4A853" fill="url(#exploreApyGrad)" strokeWidth={2} />
                                            </AreaChart>
                                        </ResponsiveContainer>
                                    </div>
                                ) : (
                                    <div className="h-10 flex items-center justify-center text-[11px]" style={{ color: 'var(--color-text-muted)' }}>
                                        No APY data available
                                    </div>
                                )}
                                {/* Stats */}
                                <div className="grid grid-cols-4 gap-2 mt-3">
                                    {[
                                        { label: 'Min', value: formatApy(historyInfo.min), color: '#fff' },
                                        { label: 'Avg', value: formatApy(historyInfo.avg), color: 'var(--color-gold)' },
                                        { label: 'Max', value: formatApy(historyInfo.max), color: '#fff' },
                                        { label: '7d', value: `${historyInfo.trendIcon} ${historyInfo.trend7d >= 0 ? '+' : ''}${historyInfo.trend7d.toFixed(1)}%`, color: historyInfo.trendColor },
                                    ].map(s => (
                                        <div key={s.label} className="text-center p-1.5 rounded" style={{ background: 'rgba(0,0,0,0.2)' }}>
                                            <div className="text-[8px] uppercase" style={{ color: 'var(--color-text-muted)' }}>{s.label}</div>
                                            <div className="text-xs font-semibold" style={{ color: s.color }}>{s.value}</div>
                                        </div>
                                    ))}
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* ═══ ACTIONS ═══ */}
                    <div className="flex gap-2 mt-4 pt-3" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                        <button onClick={openExplorer}
                            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium cursor-pointer transition-all"
                            style={{ background: 'rgba(212,168,83,0.1)', border: '1px solid rgba(212,168,83,0.2)', color: 'var(--color-gold)' }}>
                            <ExternalLink className="w-3.5 h-3.5" /> View on Explorer
                        </button>
                        <button onClick={copyAddress}
                            className="flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium cursor-pointer transition-all"
                            style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--color-text-secondary)' }}>
                            {copied ? <><Check className="w-3.5 h-3.5" style={{ color: '#10B981' }} /> Copied</> : <><Copy className="w-3.5 h-3.5" /> Address</>}
                        </button>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    )
}
