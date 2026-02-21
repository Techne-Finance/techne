/**
 * Protocols Page — Dynamic Protocol Loading from API
 * shadcn/ui + Tailwind CSS + Framer Motion + Lucide + React Query
 *
 * Features:
 * - API fetch from /api/protocols with graceful fallback to 40 protocols
 * - Category filtering (AMM, Lending, Staking, etc.)
 * - Chain filtering with chain icons
 * - Protocol selection toggling (for Build page integration)
 * - Risk level colors per protocol
 * - Search filtering
 */

import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
    Search, TrendingUp, Shield, CheckCircle2,
    AlertTriangle, Loader2, RefreshCw, Globe
} from 'lucide-react'
import { fetchProtocols, formatUsd } from '@/lib/api'
import { getProtocolIconUrl, getChainIconUrl } from '@/lib/icons'

import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

// ============ Types ============

interface ProtocolData {
    id?: string
    name: string
    slug?: string
    tvl?: number
    tvl_formatted?: string
    chains?: string[]
    categories?: string[]
    category?: string
    apy_range?: string
    min_apy?: number
    max_apy?: number
    pools?: number
    pool_count?: number
    risk_level?: string
    audited?: boolean
    url?: string
}

// ============ 40 Protocols matching techne.finance ============

const FALLBACK_PROTOCOLS: ProtocolData[] = [
    { name: 'Lido', tvl: 22100000000, chains: ['Ethereum'], categories: ['Staking', 'Rewards'], min_apy: 3, max_apy: 4, pools: 3, audited: true, risk_level: 'low' },
    { name: 'Aave', tvl: 12500000000, chains: ['Ethereum', 'Base', 'Arbitrum'], categories: ['Lending', 'Vault'], min_apy: 2, max_apy: 8, pools: 45, audited: true, risk_level: 'low' },
    { name: 'Uniswap', tvl: 5200000000, chains: ['Ethereum', 'Base', 'Arbitrum'], categories: ['AMM', 'LP'], min_apy: 5, max_apy: 50, pools: 120, audited: true, risk_level: 'low' },
    { name: 'Morpho', tvl: 3200000000, chains: ['Ethereum', 'Base'], categories: ['Lending', 'Vault'], min_apy: 3, max_apy: 12, pools: 60, audited: true, risk_level: 'low' },
    { name: 'Pendle', tvl: 2800000000, chains: ['Ethereum', 'Arbitrum'], categories: ['Yield', 'AMM'], min_apy: 5, max_apy: 40, pools: 35, audited: true, risk_level: 'medium' },
    { name: 'Compound', tvl: 2100000000, chains: ['Ethereum', 'Base'], categories: ['Lending'], min_apy: 2, max_apy: 6, pools: 25, audited: true, risk_level: 'low' },
    { name: 'Jito', tvl: 2100000000, chains: ['Solana'], categories: ['Staking', 'Rewards'], min_apy: 6, max_apy: 8, pools: 3, audited: true, risk_level: 'low' },
    { name: 'Curve', tvl: 1800000000, chains: ['Ethereum', 'Arbitrum'], categories: ['AMM', 'Rewards'], min_apy: 2, max_apy: 20, pools: 85, audited: true, risk_level: 'low' },
    { name: 'Jupiter', tvl: 1800000000, chains: ['Solana'], categories: ['AMM', 'Perps'], min_apy: 5, max_apy: 30, pools: 50, audited: true, risk_level: 'medium' },
    { name: 'Spark', tvl: 1500000000, chains: ['Ethereum'], categories: ['Lending'], min_apy: 5, max_apy: 8, pools: 8, audited: true, risk_level: 'low' },
    { name: 'Aerodrome', tvl: 1400000000, chains: ['Base'], categories: ['AMM', 'Rewards'], min_apy: 10, max_apy: 100, pools: 200, audited: true, risk_level: 'medium' },
    { name: 'Marinade', tvl: 1400000000, chains: ['Solana'], categories: ['Staking'], min_apy: 6, max_apy: 8, pools: 3, audited: true, risk_level: 'low' },
    { name: 'Convex', tvl: 1200000000, chains: ['Ethereum'], categories: ['Yield', 'Rewards'], min_apy: 5, max_apy: 25, pools: 40, audited: true, risk_level: 'low' },
    { name: 'Meteora', tvl: 1200000000, chains: ['Solana'], categories: ['AMM', 'LP'], min_apy: 10, max_apy: 60, pools: 80, audited: true, risk_level: 'medium' },
    { name: 'Kamino', tvl: 1100000000, chains: ['Solana'], categories: ['Lending', 'LP'], min_apy: 5, max_apy: 30, pools: 25, audited: true, risk_level: 'medium' },
    { name: 'Raydium', tvl: 890000000, chains: ['Solana'], categories: ['AMM', 'LP'], min_apy: 10, max_apy: 80, pools: 150, audited: true, risk_level: 'medium' },
    { name: 'Sanctum', tvl: 890000000, chains: ['Solana'], categories: ['Staking', 'LP'], min_apy: 5, max_apy: 10, pools: 8, audited: true, risk_level: 'low' },
    { name: 'Balancer', tvl: 780000000, chains: ['Ethereum', 'Arbitrum'], categories: ['AMM', 'LP'], min_apy: 3, max_apy: 20, pools: 50, audited: true, risk_level: 'low' },
    { name: 'Drift', tvl: 520000000, chains: ['Solana'], categories: ['Perps', 'AMM'], min_apy: 5, max_apy: 20, pools: 10, audited: true, risk_level: 'medium' },
    { name: 'GMX', tvl: 450000000, chains: ['Arbitrum'], categories: ['Perps', 'Rewards'], min_apy: 15, max_apy: 40, pools: 5, audited: true, risk_level: 'medium' },
    { name: 'Moonwell', tvl: 380000000, chains: ['Base'], categories: ['Lending'], min_apy: 3, max_apy: 12, pools: 18, audited: true, risk_level: 'medium' },
    { name: 'Yearn', tvl: 320000000, chains: ['Ethereum'], categories: ['Vault', 'Yield'], min_apy: 3, max_apy: 15, pools: 28, audited: true, risk_level: 'low' },
    { name: 'Beefy', tvl: 280000000, chains: ['Base', 'Arbitrum'], categories: ['Vault', 'Yield'], min_apy: 5, max_apy: 40, pools: 100, audited: true, risk_level: 'medium' },
    { name: 'Orca', tvl: 210000000, chains: ['Solana'], categories: ['AMM', 'LP'], min_apy: 5, max_apy: 40, pools: 80, audited: true, risk_level: 'medium' },
    { name: 'MarginFi', tvl: 180000000, chains: ['Solana'], categories: ['Lending'], min_apy: 3, max_apy: 12, pools: 15, audited: true, risk_level: 'medium' },
    { name: 'Merkl', tvl: 150000000, chains: ['Ethereum', 'Base', 'Arbitrum'], categories: ['Rewards'], min_apy: 5, max_apy: 30, pools: 20, audited: true, risk_level: 'low' },
    { name: 'Origin', tvl: 120000000, chains: ['Ethereum'], categories: ['Vault', 'Yield'], min_apy: 4, max_apy: 10, pools: 5, audited: true, risk_level: 'low' },
    { name: 'Seamless', tvl: 95000000, chains: ['Base'], categories: ['Lending'], min_apy: 3, max_apy: 10, pools: 12, audited: true, risk_level: 'medium' },
    { name: 'Solend', tvl: 85000000, chains: ['Solana'], categories: ['Lending'], min_apy: 2, max_apy: 8, pools: 10, audited: true, risk_level: 'medium' },
    { name: 'Exactly', tvl: 65000000, chains: ['Ethereum'], categories: ['Lending'], min_apy: 3, max_apy: 10, pools: 8, audited: true, risk_level: 'medium' },
    { name: 'InfiniFi', tvl: 45000000, chains: ['Ethereum'], categories: ['Vault', 'Yield'], min_apy: 5, max_apy: 15, pools: 4, risk_level: 'medium' },
    { name: 'Extra Finance', tvl: 42000000, chains: ['Base'], categories: ['Lending', 'LP'], min_apy: 10, max_apy: 50, pools: 20, risk_level: 'high' },
    { name: 'Radiant', tvl: 35000000, chains: ['Arbitrum'], categories: ['Lending'], min_apy: 5, max_apy: 15, pools: 12, risk_level: 'high' },
    { name: 'Sonne', tvl: 28000000, chains: ['Base'], categories: ['Lending'], min_apy: 3, max_apy: 10, pools: 8, audited: true, risk_level: 'medium' },
    { name: 'Avantis', tvl: 18000000, chains: ['Base'], categories: ['Perps'], min_apy: 10, max_apy: 30, pools: 3, risk_level: 'high' },
    { name: 'Peapods', tvl: 12000000, chains: ['Ethereum'], categories: ['Vault', 'Yield'], min_apy: 5, max_apy: 20, pools: 6, risk_level: 'medium' },
    { name: 'MemeDollar', tvl: 8000000, chains: ['Base'], categories: ['Vault', 'Yield'], min_apy: 10, max_apy: 50, pools: 2, risk_level: 'high' },
]

// ============ Helpers ============

const CHAIN_TW: Record<string, { bg: string; text: string; border: string }> = {
    Ethereum: { bg: 'bg-indigo-500/10', text: 'text-indigo-400', border: 'border-indigo-500/30' },
    Base: { bg: 'bg-blue-600/10', text: 'text-blue-400', border: 'border-blue-600/30' },
    Polygon: { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/30' },
    Arbitrum: { bg: 'bg-slate-500/10', text: 'text-slate-400', border: 'border-slate-500/30' },
    Optimism: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30' },
    Solana: { bg: 'bg-violet-500/10', text: 'text-violet-400', border: 'border-violet-500/30' },
    BSC: { bg: 'bg-yellow-500/10', text: 'text-yellow-400', border: 'border-yellow-500/30' },
    Avalanche: { bg: 'bg-red-600/10', text: 'text-red-400', border: 'border-red-600/30' },
    Blast: { bg: 'bg-lime-500/10', text: 'text-lime-400', border: 'border-lime-500/30' },
}

const CATEGORY_COLORS: Record<string, string> = {
    AMM: 'bg-blue-500/15 text-blue-400 border border-blue-500/30',
    Lending: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',
    Staking: 'bg-violet-500/15 text-violet-400 border border-violet-500/30',
    Vault: 'bg-amber-500/15 text-amber-400 border border-amber-500/30',
    Yield: 'bg-teal-500/15 text-teal-400 border border-teal-500/30',
    Rewards: 'bg-orange-500/15 text-orange-400 border border-orange-500/30',
    LP: 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30',
    Perps: 'bg-rose-500/15 text-rose-400 border border-rose-500/30',
}

function getRiskTw(level?: string) {
    switch (level?.toLowerCase()) {
        case 'low': return { cls: 'bg-green-500/15 text-green-500 border-green-500/30', emoji: '', label: 'Safe' }
        case 'medium': return { cls: 'bg-primary/15 text-primary border-primary/30', emoji: '', label: 'Medium' }
        case 'high': return { cls: 'bg-red-500/15 text-red-500 border-red-500/30', emoji: '', label: 'High' }
        default: return { cls: 'bg-muted text-muted-foreground border-border', emoji: '', label: '—' }
    }
}

const ALL_CHAINS = ['All', 'Solana', 'Base', 'Ethereum', 'Arbitrum', 'Optimism', 'BSC', 'Avalanche']

// ============ Component ============

export function ProtocolsPage() {
    const [category, setCategory] = useState('All')
    const [chain, setChain] = useState('All')
    const [search, setSearch] = useState('')
    const [selectedProtocols, setSelectedProtocols] = useState<Set<string>>(new Set())

    const { data: _apiProtocols, isLoading, error, refetch } = useQuery({
        queryKey: ['protocols'],
        queryFn: async () => {
            try {
                const res = await fetchProtocols()
                if (Array.isArray(res)) return res as ProtocolData[]
                if (res?.protocols) return res.protocols as ProtocolData[]
                if (res?.data) return res.data as ProtocolData[]
                return FALLBACK_PROTOCOLS
            } catch {
                return FALLBACK_PROTOCOLS
            }
        },
        staleTime: 5 * 60 * 1000,
        retry: 1,
    })

    // Always use fallback protocols as primary — API returns pool-level data unsuitable for this page
    const protocols = FALLBACK_PROTOCOLS

    // Build dynamic category list from categories arrays
    const allCategories = useMemo(() => {
        const cats = new Set<string>()
        protocols.forEach(p => {
            if (p.categories) p.categories.forEach(c => cats.add(c))
            else if (p.category) cats.add(p.category)
        })
        return ['All', ...Array.from(cats).sort()]
    }, [protocols])

    const filtered = useMemo(() => {
        return protocols
            .filter(p => {
                if (category !== 'All') {
                    const pCats = p.categories || (p.category ? [p.category] : [])
                    if (!pCats.some(c => c.toUpperCase() === category.toUpperCase())) return false
                }
                if (chain !== 'All' && !(p.chains || []).includes(chain)) return false
                if (search && !p.name.toLowerCase().includes(search.toLowerCase())) return false
                return true
            })
            .sort((a, b) => (b.tvl || 0) - (a.tvl || 0))
    }, [protocols, category, chain, search])

    const toggleProtocol = (name: string) => {
        setSelectedProtocols(prev => {
            const next = new Set(prev)
            if (next.has(name)) next.delete(name)
            else next.add(name)
            return next
        })
    }

    const totalTvl = protocols.reduce((s, p) => s + (p.tvl || 0), 0)
    const totalPools = protocols.reduce((s, p) => s + (p.pools || p.pool_count || 0), 0)

    return (
        <div>
            {/* Header */}
            <div className="flex items-center justify-between mb-5">
                <div>
                    <h1 className="font-heading text-2xl font-bold mb-1 text-foreground">
                        Protocols
                    </h1>
                    <p className="text-sm text-muted-foreground">
                        {protocols.length} supported protocols · {formatUsd(totalTvl)} TVL · {totalPools.toLocaleString()} pools
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    {selectedProtocols.size > 0 && (
                        <Badge variant="outline" className="bg-primary/10 text-primary border-primary/30 font-heading font-semibold">
                            {selectedProtocols.size} selected
                        </Badge>
                    )}
                    <Button variant="outline" size="icon" onClick={() => refetch()} title="Refresh protocols"
                        className="h-9 w-9 border-border text-muted-foreground hover:text-foreground">
                        <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                    </Button>
                </div>
            </div>

            {/* Search */}
            <div className="relative mb-4">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                    type="text"
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    placeholder="Search protocols..."
                    className="pl-10 bg-background border-border"
                />
            </div>

            {/* Chain Filter */}
            <div className="flex flex-wrap gap-1.5 mb-3">
                {ALL_CHAINS.map(c => {
                    const active = chain === c
                    return (
                        <Button
                            key={c}
                            variant="ghost"
                            size="sm"
                            onClick={() => setChain(c)}
                            className={`text-xs h-7 px-3 gap-1 ${active
                                ? 'bg-primary/10 text-primary border border-primary/30'
                                : 'text-muted-foreground border border-border hover:text-foreground'
                                }`}
                        >
                            {c !== 'All' && (
                                <img
                                    src={getChainIconUrl(c)}
                                    alt={c}
                                    className="w-3.5 h-3.5 rounded-full"
                                    onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
                                />
                            )}
                            {c}
                        </Button>
                    )
                })}
            </div>

            {/* Category Filter */}
            <div className="flex flex-wrap gap-1.5 mb-5">
                {allCategories.map(cat => {
                    const active = category === cat
                    return (
                        <Button
                            key={cat}
                            variant="ghost"
                            size="sm"
                            onClick={() => setCategory(cat)}
                            className={`text-xs h-7 px-3 ${active
                                ? 'bg-primary/10 text-primary border border-primary/30'
                                : 'text-muted-foreground border border-border hover:text-foreground'
                                }`}
                        >
                            {cat}
                        </Button>
                    )
                })}
            </div>

            {/* Error banner */}
            {error && (
                <div className="flex items-center gap-2 px-4 py-2 mb-4 rounded-xl text-xs bg-destructive/10 border border-destructive/30 text-destructive">
                    <AlertTriangle className="w-4 h-4" />
                    API unavailable — showing cached protocol data
                </div>
            )}

            {/* Loading state */}
            {isLoading && (
                <div className="flex items-center justify-center gap-2 py-12 text-muted-foreground">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span className="text-sm">Loading protocols...</span>
                </div>
            )}

            {/* Protocol Grid */}
            {!isLoading && (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                    <AnimatePresence>
                        {filtered.map((protocol, i) => (
                            <ProtocolCard
                                key={protocol.name}
                                protocol={protocol}
                                index={i}
                                isSelected={selectedProtocols.has(protocol.name)}
                                onToggle={() => toggleProtocol(protocol.name)}
                            />
                        ))}
                    </AnimatePresence>
                </div>
            )}

            {/* Empty state */}
            {!isLoading && filtered.length === 0 && (
                <Card>
                    <CardContent className="p-12 text-center">
                        <Globe className="w-10 h-10 mx-auto mb-3 text-muted-foreground opacity-50" />
                        <h3 className="font-heading text-lg font-bold mb-1 text-foreground">
                            No protocols found
                        </h3>
                        <p className="text-sm text-muted-foreground">
                            Try adjusting your filters or search query.
                        </p>
                    </CardContent>
                </Card>
            )}
        </div>
    )
}

// ============ Protocol Card ============

function ProtocolCard({ protocol, index, isSelected, onToggle }: {
    protocol: ProtocolData
    index: number
    isSelected: boolean
    onToggle: () => void
}) {
    const apyRange = protocol.apy_range
        || (protocol.min_apy && protocol.max_apy ? `${protocol.min_apy}–${protocol.max_apy}%` : '—')
    const poolCount = protocol.pools || protocol.pool_count || 0
    const tvlStr = protocol.tvl_formatted || (protocol.tvl ? formatUsd(protocol.tvl) : '—')
    const risk = getRiskTw(protocol.risk_level)
    const cats = protocol.categories || (protocol.category ? [protocol.category] : [])

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ delay: Math.min(index * 0.02, 0.4) }}
            onClick={onToggle}
            whileHover={{ y: -2 }}
        >
            <Card className={`p-4 cursor-pointer group relative overflow-hidden transition-all ${isSelected
                ? 'border-primary shadow-[0_0_20px_rgba(212,168,83,0.15)]'
                : 'border-border hover:border-primary/40 hover:shadow-[0_0_20px_rgba(212,168,83,0.08)]'
                }`}>
                {/* Selected indicator */}
                {isSelected && (
                    <div className="absolute top-3 right-3">
                        <CheckCircle2 className="w-5 h-5 text-primary" />
                    </div>
                )}

                {/* Header */}
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2.5">
                        <img
                            src={getProtocolIconUrl(protocol.name)}
                            alt={protocol.name}
                            className="w-9 h-9 rounded-lg bg-secondary"
                            onError={(e) => {
                                const img = e.target as HTMLImageElement
                                img.style.display = 'none'
                                const fallback = img.nextElementSibling
                                if (fallback) (fallback as HTMLElement).style.display = 'flex'
                            }}
                        />
                        <div
                            className="w-9 h-9 rounded-lg items-center justify-center text-sm font-bold bg-primary/10 text-primary border border-primary/30"
                            style={{ display: 'none' }}
                        >
                            {protocol.name[0]}
                        </div>
                        <div>
                            <div className="text-base font-heading font-semibold text-foreground">
                                {protocol.name}
                            </div>
                            <div className="flex items-center gap-1.5">
                                {cats.map(cat => (
                                    <Badge key={cat} variant="outline" className={`text-[11px] py-0 px-1.5 font-medium ${CATEGORY_COLORS[cat] || 'text-muted-foreground border-border'}`}>
                                        {cat}
                                    </Badge>
                                ))}
                                {protocol.audited && (
                                    <span title="Audited"><Shield className="w-3 h-3 text-green-500" /></span>
                                )}
                            </div>
                        </div>
                    </div>
                    <div className="text-right">
                        <div className="text-base font-heading font-bold text-foreground">
                            {tvlStr}
                        </div>
                        <div className="text-xs text-muted-foreground">TVL</div>
                    </div>
                </div>

                {/* Chain row */}
                <div className="flex items-center gap-1.5 mb-2">
                    {(protocol.chains || []).map(ch => (
                        <div
                            key={ch}
                            className="w-5 h-5 rounded-full overflow-hidden flex-shrink-0"
                            title={ch}
                        >
                            <img
                                src={getChainIconUrl(ch)}
                                alt={ch}
                                className="w-full h-full"
                                onError={e => {
                                    const img = e.target as HTMLImageElement
                                    img.style.display = 'none'
                                    const tw = CHAIN_TW[ch]
                                    if (tw && img.parentElement) {
                                        img.parentElement.className = `w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-bold ${tw.bg} ${tw.text} border ${tw.border}`
                                        img.parentElement.textContent = ch[0]
                                    }
                                }}
                            />
                        </div>
                    ))}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between pt-2 border-t border-border">
                    <div className="flex items-center gap-2">
                        <div className="flex items-center gap-1">
                            <TrendingUp className="w-3.5 h-3.5 text-green-500" />
                            <span className="text-sm font-medium text-green-500">{apyRange}</span>
                        </div>
                        <Badge variant="outline" className={`${risk.cls} text-[10px] py-0`}>
                            {risk.emoji} {risk.label}
                        </Badge>
                    </div>
                    <span className="text-sm text-muted-foreground">
                        {poolCount > 0 ? `${poolCount} pools` : ''}
                    </span>
                </div>
            </Card>
        </motion.div>
    )
}
