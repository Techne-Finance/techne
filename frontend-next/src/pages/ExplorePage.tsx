/**
 * Explore Page — Pool discovery with shadcn/ui
 * shadcn: Card, Badge, Button, Table (semantic)
 * Tailwind, Framer Motion, Lucide, Zustand, React Query
 */
import { useState, useMemo, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
    Compass, TrendingUp, Shield, Layers, LayoutGrid, List,
    ChevronDown, ChevronUp, ArrowUpDown, Eye, Lock, Zap,
} from 'lucide-react'
import { fetchPools, formatUsd, formatApy, getRiskColor, getRiskLabel, type Pool } from '@/lib/api'
import { CREDIT_COSTS } from '@/stores/creditsStore'
import { getProtocolIconUrl, getChainIconUrl } from '@/lib/icons'
import { useFilterStore } from '@/stores/filterStore'
import { ExplorePoolModal } from '@/components/ExplorePoolModal'

import { Card, CardContent } from '@/components/ui/card'
// Badge import removed - not currently used
import { Button } from '@/components/ui/button'

type SortKey = 'apy' | 'tvl' | 'risk_score' | 'symbol' | 'project'
type SortDir = 'asc' | 'desc'

// 15-pool daily free limit (deterministic daily seed)
const FREE_POOL_LIMIT = 15

function getDailySeed(): number {
    const d = new Date()
    return d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate()
}

function shuffleWithSeed<T>(arr: T[], seed: number): T[] {
    const copy = [...arr]
    let s = seed
    for (let i = copy.length - 1; i > 0; i--) {
        s = ((s * 9301 + 49297) % 233280)
        const j = Math.floor((s / 233280) * (i + 1))
            ;[copy[i], copy[j]] = [copy[j], copy[i]]
    }
    return copy
}

export function ExplorePage() {
    const [view, setView] = useState<'grid' | 'list'>('grid')
    const [sortKey, setSortKey] = useState<SortKey>('apy')
    const [sortDir, setSortDir] = useState<SortDir>('desc')
    const [selectedPool, setSelectedPool] = useState<Pool | null>(null)
    const filters = useFilterStore()
    const applied = filters.appliedFilters

    // Build server-side query params from APPLIED filters
    const queryParams: Record<string, string> = {}
    if (applied.assetType !== 'all') queryParams.asset_type = applied.assetType
    if (applied.chain !== 'all') queryParams.chain = applied.chain
    if (applied.protocols.length > 0) {
        queryParams.protocols = applied.protocols.join(',')
        queryParams.limit = '200'  // fetch more when filtering by protocols
    } else {
        queryParams.limit = '50'
    }

    const { data, isLoading, error } = useQuery({
        queryKey: ['pools', queryParams],
        queryFn: () => fetchPools(queryParams),
        staleTime: 60_000,
    })

    const hasCustomFilters =
        applied.chain !== 'all' ||
        applied.riskLevel !== 'all' ||
        applied.assetType !== 'all' ||
        applied.poolType !== 'all' ||
        applied.protocols.length > 0

    const pools = useMemo(() => {
        let list = data?.combined || []

        // Client-side filters — uses APPLIED snapshot only
        if (applied.riskLevel !== 'all') {
            list = list.filter(p => {
                const label = getRiskLabel(p.risk_score).toLowerCase()
                return label === applied.riskLevel
            })
        }
        if (applied.poolType !== 'all') {
            list = list.filter(p => {
                if (applied.poolType === 'single') return p.pool_type === 'single' || !p.symbol?.includes('-')
                return p.pool_type !== 'single' && p.symbol?.includes('-')
            })
        }
        if (applied.protocols.length > 0) {
            list = list.filter(p => {
                const proj = (p.project || '').toLowerCase().replace(/[\s_]+/g, '-')
                return applied.protocols.some(fp => {
                    const norm = fp.replace(/[\s_]+/g, '-')
                    return proj.startsWith(norm) || proj === norm || proj.includes(norm)
                })
            })
        }

        // Sort
        list = [...list].sort((a, b) => {
            const av = a[sortKey] ?? 0
            const bv = b[sortKey] ?? 0
            if (typeof av === 'string') return sortDir === 'asc' ? (av as string).localeCompare(bv as string) : (bv as string).localeCompare(av as string)
            return sortDir === 'asc' ? (av as number) - (bv as number) : (bv as number) - (av as number)
        })

        // 16-pool free limit when no custom filters applied
        if (!hasCustomFilters && list.length > FREE_POOL_LIMIT) {
            const shuffled = shuffleWithSeed(list, getDailySeed())
            list = shuffled.slice(0, FREE_POOL_LIMIT)
        }

        return list
    }, [data, applied, sortKey, sortDir, hasCustomFilters])

    const stats = useMemo(() => ({
        totalTvl: pools.reduce((s, p) => s + (p.tvl || 0), 0),
        avgApy: pools.length ? pools.reduce((s, p) => s + (p.apy || 0), 0) / pools.length : 0,
        protocols: new Set(pools.map(p => p.project)).size,
        chains: new Set(pools.map(p => p.chain).filter(Boolean)).size,
    }), [pools])

    const toggleSort = useCallback((key: SortKey) => {
        if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
        else { setSortKey(key); setSortDir('desc') }
    }, [sortKey])

    const SortIcon = ({ field }: { field: SortKey }) => {
        if (sortKey !== field) return <ArrowUpDown className="w-3 h-3 opacity-30" />
        return sortDir === 'desc' ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />
    }

    const handlePoolClick = useCallback((pool: Pool) => {
        setSelectedPool(pool)
    }, [])

    const totalAvailable = data?.combined?.length || 0

    return (
        <div>
            {/* Header */}
            <div className="flex items-center justify-between mb-5">
                <div>
                    <h1 className="font-heading text-2xl font-bold text-foreground">
                        Explore Opportunities
                    </h1>
                    <p className="text-sm mt-0.5 text-muted-foreground">
                        {isLoading ? 'Scanning protocols...' : `${pools.length} pools across ${stats.chains} chains`}
                        {!hasCustomFilters && totalAvailable > FREE_POOL_LIMIT && (
                            <span className="text-primary">
                                {' '}· {FREE_POOL_LIMIT} free daily • Apply filters for full access
                            </span>
                        )}
                    </p>
                </div>
                <div className="flex gap-1.5 p-1 rounded-lg bg-secondary">
                    {(['grid', 'list'] as const).map(v => (
                        <Button
                            key={v}
                            variant="ghost"
                            size="sm"
                            onClick={() => setView(v)}
                            className={`text-xs h-7 px-3 ${view === v
                                ? 'bg-primary/10 text-primary'
                                : 'text-muted-foreground hover:text-foreground'
                                }`}
                        >
                            {v === 'grid' ? <LayoutGrid className="w-3.5 h-3.5 mr-1" /> : <List className="w-3.5 h-3.5 mr-1" />}
                            {v === 'grid' ? 'Grid' : 'List'}
                        </Button>
                    ))}
                </div>
            </div>

            {/* Free limit banner */}
            {!hasCustomFilters && totalAvailable > FREE_POOL_LIMIT && (
                <motion.div
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-4 p-3 rounded-xl flex items-center justify-between bg-primary/10 border border-primary/20"
                >
                    <div className="flex items-center gap-2">
                        <Eye className="w-4 h-4 text-primary" />
                        <span className="text-xs text-primary">
                            Free tier: {FREE_POOL_LIMIT} of {totalAvailable} pools shown daily.
                            Apply sidebar filters ({CREDIT_COSTS.FILTER} cr) to unlock all pools.
                        </span>
                    </div>
                    <Lock className="w-3.5 h-3.5 flex-shrink-0 text-primary" />
                </motion.div>
            )}

            {/* Stats Bar — Premium glassmorphism */}
            <div className="mb-5 rounded-xl p-[1px]" style={{
                background: 'linear-gradient(135deg, rgba(212,168,83,0.3), rgba(212,168,83,0.05) 50%, rgba(212,168,83,0.15))',
            }}>
                <div className="rounded-xl p-4 grid grid-cols-2 md:grid-cols-4 gap-3" style={{
                    background: 'linear-gradient(180deg, rgba(20,20,20,0.95), rgba(12,12,12,0.98))',
                    backdropFilter: 'blur(12px)',
                }}>
                    <StatItem icon={Layers} label="Total TVL" value={formatUsd(stats.totalTvl)} />
                    <StatItem icon={TrendingUp} label="Avg APY" value={formatApy(stats.avgApy)} gold />
                    <StatItem icon={Shield} label="Protocols" value={String(stats.protocols)} />
                    <StatItem icon={Compass} label="Chains" value={String(stats.chains)} />
                </div>
            </div>

            {/* Content */}
            {isLoading ? (
                <LoadingSkeleton count={view === 'grid' ? 9 : 6} />
            ) : error ? (
                <Card className="border-destructive/30">
                    <CardContent className="p-12 text-center text-destructive">
                        <Shield className="w-8 h-8 mx-auto mb-3 opacity-50" />
                        <p className="font-heading font-semibold">Failed to load pools</p>
                        <p className="text-xs mt-1 text-muted-foreground">
                            {(error as Error).message}
                        </p>
                    </CardContent>
                </Card>
            ) : view === 'list' ? (
                /* List View */
                <Card className="overflow-hidden">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-border">
                                {[
                                    { key: 'symbol' as SortKey, label: 'Pool' },
                                    { key: 'apy' as SortKey, label: 'APY' },
                                    { key: 'tvl' as SortKey, label: 'TVL' },
                                    { key: 'risk_score' as SortKey, label: 'Risk' },
                                ].map(col => (
                                    <th
                                        key={col.key}
                                        onClick={() => toggleSort(col.key)}
                                        className="text-left px-4 py-3 font-medium cursor-pointer select-none text-[11px] text-muted-foreground uppercase tracking-wider"
                                    >
                                        <span className="inline-flex items-center gap-1">
                                            {col.label} <SortIcon field={col.key} />
                                        </span>
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            <AnimatePresence>
                                {pools.slice(0, 50).map((pool, i) => (
                                    <motion.tr
                                        key={pool.pool_id}
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        transition={{ delay: i * 0.02 }}
                                        onClick={() => handlePoolClick(pool)}
                                        className="cursor-pointer border-b border-border hover:bg-accent transition-colors"
                                    >
                                        <td className="px-4 py-3">
                                            <div className="flex items-center gap-2.5">
                                                <ProtocolIcon project={pool.project} chain={pool.chain} />
                                                <div>
                                                    <div className="font-medium text-foreground">{pool.symbol}</div>
                                                    <div className="text-xs text-muted-foreground">
                                                        {pool.project} · {pool.chain || 'base'}
                                                    </div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className="font-heading font-bold text-green-500">
                                                {formatApy(pool.apy)}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-foreground">
                                            {pool.tvl_formatted || formatUsd(pool.tvl)}
                                        </td>
                                        <td className="px-4 py-3">
                                            <RiskBadge score={pool.risk_score} />
                                        </td>
                                    </motion.tr>
                                ))}
                            </AnimatePresence>
                        </tbody>
                    </table>
                </Card>
            ) : (
                /* Grid View */
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    <AnimatePresence>
                        {pools.slice(0, 30).map((pool, i) => (
                            <PoolCard key={pool.pool_id} pool={pool} index={i} onClick={() => handlePoolClick(pool)} />
                        ))}
                    </AnimatePresence>
                </div>
            )}

            {/* Pool Detail Modal */}
            {selectedPool && (
                <ExplorePoolModal
                    pool={selectedPool}
                    onClose={() => setSelectedPool(null)}
                />
            )}
        </div>
    )
}

// ========== Sub-components ==========

function ProtocolIcon({ project, chain }: { project: string; chain?: string }) {
    return (
        <div className="relative flex-shrink-0">
            <img
                src={getProtocolIconUrl(project)}
                alt={project}
                className="w-8 h-8 rounded-full bg-secondary"
                onError={(e) => {
                    const el = e.target as HTMLImageElement
                    el.style.display = 'none'
                    el.parentElement!.classList.add('icon-fallback')
                }}
            />
            {chain && (
                <img
                    src={getChainIconUrl(chain)}
                    alt={chain}
                    className="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full border-2 border-card"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                />
            )}
        </div>
    )
}

function StatItem({ icon: Icon, label, value, gold }: { icon: any; label: string; value: string; gold?: boolean }) {
    return (
        <div className="flex items-center gap-3 group">
            <div className="relative w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0" style={{
                background: gold
                    ? 'linear-gradient(135deg, rgba(212,168,83,0.15), rgba(212,168,83,0.05))'
                    : 'linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))',
                border: gold ? '1px solid rgba(212,168,83,0.25)' : '1px solid rgba(255,255,255,0.07)',
                boxShadow: gold ? '0 0 10px rgba(212,168,83,0.08)' : 'none',
            }}>
                <Icon className="w-4 h-4" style={{ color: gold ? '#D4A853' : 'rgba(255,255,255,0.45)' }} />
            </div>
            <div>
                <div className="text-base font-heading font-semibold" style={{ color: gold ? '#D4A853' : '#fff' }}>{value}</div>
                <div className="text-[10px] uppercase tracking-wider" style={{ color: 'rgba(255,255,255,0.35)' }}>{label}</div>
            </div>
        </div>
    )
}

function RiskBadge({ score }: { score?: number }) {
    const s = score ?? 50
    const label = getRiskLabel(s)
    const color = getRiskColor(s)

    return (
        <span className="text-[10px] font-medium px-2 py-0.5 rounded-full" style={{
            background: `${color}18`,
            color: color,
            border: `1px solid ${color}30`,
        }}>
            {label} ({s.toFixed(0)})
        </span>
    )
}

function PoolCard({ pool, index, onClick }: { pool: Pool; index: number; onClick: () => void }) {
    const riskColor = getRiskColor(pool.risk_score)
    const isHighApy = pool.apy > 200

    // Pick a subtle accent color per protocol for variety
    const accentColors: Record<string, string> = {
        'aerodrome': '#3B82F6', 'uniswap': '#FF007A', 'aave': '#B6509E',
        'morpho': '#8B5CF6', 'compound': '#00D395', 'curve': '#F7E44D',
        'lido': '#00A3FF', 'pendle': '#4ECDC4', 'spark': '#F79C42',
    }
    const projKey = Object.keys(accentColors).find(k => (pool.project || '').toLowerCase().includes(k))
    const protocolAccent = projKey ? accentColors[projKey] : '#D4A853'

    return (
        <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{ delay: index * 0.035, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            onClick={onClick}
            whileHover={{ y: -3, transition: { duration: 0.2 } }}
            className="cursor-pointer group"
        >
            <div className="relative rounded-xl overflow-hidden" style={{
                background: 'linear-gradient(180deg, rgba(22,22,22,0.95), rgba(14,14,14,0.98))',
                border: '1px solid rgba(255,255,255,0.06)',
                transition: 'all 0.3s ease',
            }}>
                {/* Top accent — protocol-colored gradient */}
                <div className="h-[2px]" style={{
                    background: `linear-gradient(90deg, ${protocolAccent}50, ${riskColor}40, ${protocolAccent}50)`,
                }} />

                {/* Hover glow */}
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-400 pointer-events-none" style={{
                    background: `radial-gradient(ellipse at 50% 0%, ${protocolAccent}08 0%, transparent 65%)`,
                }} />

                <div className="p-3.5 relative z-10">
                    {/* Protocol + Risk */}
                    <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                            <div className="relative">
                                <div className="absolute inset-0 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" style={{
                                    background: `radial-gradient(circle, ${protocolAccent}18, transparent)`,
                                    filter: 'blur(5px)',
                                }} />
                                <ProtocolIcon project={pool.project} chain={pool.chain} />
                            </div>
                            <div>
                                <div className="text-[13px] font-medium text-white group-hover:transition-colors" style={{
                                    transition: 'color 0.2s',
                                }}>
                                    <span className="group-hover:text-white">{pool.symbol}</span>
                                </div>
                                <div className="text-[10px] flex items-center gap-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
                                    <span style={{ color: `${protocolAccent}90` }}>{pool.project}</span>
                                    <span>·</span>
                                    <span>{pool.chain || 'Base'}</span>
                                </div>
                            </div>
                        </div>
                        <RiskBadge score={pool.risk_score} />
                    </div>

                    {/* APY + TVL */}
                    <div className="flex items-end justify-between">
                        <div>
                            <div className="text-[9px] uppercase tracking-widest mb-0.5" style={{ color: 'rgba(255,255,255,0.3)' }}>APY</div>
                            <div className="flex items-center gap-1">
                                {isHighApy && (
                                    <motion.div
                                        animate={{ opacity: [0.4, 1, 0.4] }}
                                        transition={{ duration: 1.8, repeat: Infinity }}
                                    >
                                        <Zap className="w-3 h-3" style={{ color: '#FBBF24' }} />
                                    </motion.div>
                                )}
                                <span className="text-xl font-heading font-bold" style={{
                                    background: isHighApy
                                        ? 'linear-gradient(135deg, #FBBF24, #F59E0B)'
                                        : 'linear-gradient(135deg, #34D399, #10B981)',
                                    WebkitBackgroundClip: 'text',
                                    WebkitTextFillColor: 'transparent',
                                }}>
                                    {formatApy(pool.apy)}
                                </span>
                            </div>
                        </div>
                        <div className="text-right">
                            <div className="text-[9px] uppercase tracking-widest mb-0.5" style={{ color: 'rgba(255,255,255,0.3)' }}>TVL</div>
                            <div className="text-sm font-medium text-white">
                                {pool.tvl_formatted || formatUsd(pool.tvl)}
                            </div>
                        </div>
                    </div>

                    {/* Volume row — always visible, N/A when missing */}
                    <div className="mt-2.5 pt-2 flex items-center justify-between" style={{
                        borderTop: '1px solid rgba(255,255,255,0.04)',
                    }}>
                        <span className="text-[10px]" style={{ color: 'rgba(255,255,255,0.3)' }}>24h Vol</span>
                        <span className="text-[10px] font-medium" style={{
                            color: pool.volume_24h && pool.volume_24h > 0
                                ? `${protocolAccent}80`
                                : 'rgba(255,255,255,0.25)',
                        }}>
                            {pool.volume_24h && pool.volume_24h > 0
                                ? (pool.volume_24h_formatted || formatUsd(pool.volume_24h))
                                : 'N/A'}
                        </span>
                    </div>
                </div>

                {/* Bottom corner accent — protocol colored */}
                <div className="absolute bottom-0 right-0 w-14 h-14 opacity-0 group-hover:opacity-100 transition-opacity duration-400 pointer-events-none" style={{
                    background: `radial-gradient(circle at 100% 100%, ${protocolAccent}0A, transparent 70%)`,
                }} />
            </div>
        </motion.div>
    )
}

function LoadingSkeleton({ count }: { count: number }) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {Array.from({ length: count }).map((_, i) => (
                <div key={i} className="rounded-xl overflow-hidden" style={{
                    background: 'linear-gradient(180deg, rgba(22,22,22,0.95), rgba(14,14,14,0.98))',
                    border: '1px solid rgba(255,255,255,0.06)',
                }}>
                    <div className="h-[2px]" style={{ background: 'linear-gradient(90deg, rgba(212,168,83,0.1), rgba(212,168,83,0.05))' }} />
                    <div className="p-4 animate-pulse">
                        <div className="flex items-center gap-2.5 mb-4">
                            <div className="w-8 h-8 rounded-full" style={{ background: 'rgba(255,255,255,0.06)' }} />
                            <div>
                                <div className="h-3 w-20 rounded mb-1.5" style={{ background: 'rgba(255,255,255,0.06)' }} />
                                <div className="h-2 w-28 rounded" style={{ background: 'rgba(255,255,255,0.04)' }} />
                            </div>
                        </div>
                        <div className="flex justify-between items-end">
                            <div className="h-7 w-20 rounded" style={{ background: 'rgba(255,255,255,0.06)' }} />
                            <div className="h-4 w-16 rounded" style={{ background: 'rgba(255,255,255,0.04)' }} />
                        </div>
                    </div>
                </div>
            ))}
        </div>
    )
}
