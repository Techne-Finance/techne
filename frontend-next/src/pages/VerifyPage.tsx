/**
 * Verify Page — Pool Verification by address/URL
 * shadcn/ui + Tailwind CSS + Framer Motion + Lucide + Zustand
 *
 * Flow:
 * 1. User pastes pool address or protocol URL
 * 2. parseInput() detects protocol (DefiLlama, Aerodrome, Uniswap, etc.)
 * 3. Calls appropriate scout API endpoint
 * 4. Deducts 10 credits on success
 * 5. Shows results + saves to localStorage history
 */

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    Search, Clock, ChevronRight, Trash2, Loader2, Eye,
} from 'lucide-react'
import {
    type Pool, scoutResolve, scoutVerifyRpc, scoutPoolPair,
    getRiskColor, getRiskLabel, formatUsd, formatApy
} from '@/lib/api'
import { getProtocolIconUrl, getChainIconUrl } from '@/lib/icons'
import { useCreditsStore, CREDIT_COSTS } from '@/stores/creditsStore'
import { toast } from '@/components/Toast'
import { PoolDetailModal } from '@/components/PoolDetailModal'

import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'

// ============ Input Parsing (from verify-pools.js:parseInput) ============

interface ParsedInput {
    type: 'defillama' | 'address' | 'pair' | 'search'
    id?: string
    token0?: string
    token1?: string
    protocol?: string
    chain?: string
    stable?: boolean
    factory?: string
    original?: string
}

function parseInput(input: string): ParsedInput {
    // DefiLlama URL
    if (input.includes('defillama.com')) {
        const match = input.match(/pool\/([a-f0-9-]+)/i)
        if (match) return { type: 'defillama', id: match[1] }
    }

    // Aerodrome URL
    if (input.includes('aerodrome.finance')) {
        const liquidityMatch = input.match(/liquidity\/(0x[a-fA-F0-9]{40})/i)
        if (liquidityMatch) return { type: 'address', id: liquidityMatch[1].toLowerCase(), protocol: 'aerodrome' }

        const token0Match = input.match(/token0=(0x[a-fA-F0-9]{40})/i)
        const token1Match = input.match(/token1=(0x[a-fA-F0-9]{40})/i)
        const typeMatch = input.match(/type=(\d+)/i)

        if (token0Match && token1Match) {
            const poolType = typeMatch ? parseInt(typeMatch[1]) : 0
            return {
                type: 'pair',
                token0: token0Match[1].toLowerCase(),
                token1: token1Match[1].toLowerCase(),
                protocol: 'aerodrome',
                chain: 'Base',
                stable: poolType === 10 || poolType === 1,
                original: input,
            }
        }
    }

    // Velodrome URL
    if (input.includes('velodrome.finance')) {
        const t0 = input.match(/token0=(0x[a-fA-F0-9]{40})/i)
        const t1 = input.match(/token1=(0x[a-fA-F0-9]{40})/i)
        if (t0 && t1) {
            return { type: 'pair', token0: t0[1].toLowerCase(), token1: t1[1].toLowerCase(), protocol: 'velodrome', chain: 'Optimism' }
        }
    }

    // PancakeSwap URL
    if (input.includes('pancakeswap.finance')) {
        const t0 = input.match(/token0=(0x[a-fA-F0-9]{40})/i)
        const t1 = input.match(/token1=(0x[a-fA-F0-9]{40})/i)
        if (t0 && t1) {
            return { type: 'pair', token0: t0[1].toLowerCase(), token1: t1[1].toLowerCase(), protocol: 'pancakeswap' }
        }
    }

    // Uniswap URL
    if (input.includes('uniswap.org') || input.includes('uniswap.com')) {
        const t0 = input.match(/token0=(0x[a-fA-F0-9]{40})/i)
        const t1 = input.match(/token1=(0x[a-fA-F0-9]{40})/i)
        if (t0 && t1) {
            return { type: 'pair', token0: t0[1].toLowerCase(), token1: t1[1].toLowerCase(), protocol: 'uniswap-v3' }
        }
        const poolMatch = input.match(/pools?\/[\w]+\/(0x[a-fA-F0-9]{40})/i)
        if (poolMatch) return { type: 'address', id: poolMatch[1].toLowerCase(), protocol: 'uniswap' }
        const simpleMatch = input.match(/(0x[a-fA-F0-9]{40})/i)
        if (simpleMatch) return { type: 'address', id: simpleMatch[1].toLowerCase(), protocol: 'uniswap' }
    }

    // Curve URL
    if (input.includes('curve.fi')) {
        const poolMatch = input.match(/(0x[a-fA-F0-9]{40})/i)
        if (poolMatch) return { type: 'address', id: poolMatch[1].toLowerCase(), protocol: 'curve' }
    }

    // Raw 0x address
    if (/^0x[a-fA-F0-9]{40}$/i.test(input)) {
        return { type: 'address', id: input.toLowerCase() }
    }

    // UUID (DefiLlama pool ID)
    if (/^[a-f0-9-]{36}$/i.test(input)) {
        return { type: 'defillama', id: input }
    }

    // Fallback: search by symbol
    return { type: 'search', id: input }
}

// ============ History ============

const HISTORY_KEY = 'techne_verify_history'

interface HistoryItem {
    pool: Pool
    timestamp: number
}

function getHistory(): HistoryItem[] {
    try {
        return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
    } catch { return [] }
}

function saveToHistory(pool: Pool) {
    const history = getHistory()
    const filtered = history.filter(h => h.pool.pool_id !== pool.pool_id && h.pool.pool !== pool.pool)
    filtered.unshift({ pool, timestamp: Date.now() })
    localStorage.setItem(HISTORY_KEY, JSON.stringify(filtered.slice(0, 20)))
}

function clearHistory() {
    localStorage.removeItem(HISTORY_KEY)
}

// ============ Component ============

export function VerifyPage() {
    const [query, setQuery] = useState('')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<Pool | null>(null)
    const [showModal, setShowModal] = useState(false)
    const [history, setHistory] = useState<HistoryItem[]>([])
    const credits = useCreditsStore(s => s.credits)
    const useCredits = useCreditsStore(s => s.useCredits)
    const canAfford = useCreditsStore(s => s.canAfford)

    useEffect(() => {
        setHistory(getHistory())
    }, [])

    const handleVerify = async () => {
        const input = query.trim()
        if (!input) {
            toast.warning('Please enter a pool address or URL')
            return
        }
        if (!canAfford(CREDIT_COSTS.VERIFY)) {
            toast.warning(`Need ${CREDIT_COSTS.VERIFY} credits. You have ${credits}.`)
            return
        }

        setLoading(true)
        setResult(null)

        try {
            const parsed = parseInput(input)
            let poolData: Pool | null = null

            if (parsed.type === 'pair') {
                toast.info('Analyzing pool with SmartRouter...')
                const data = await scoutPoolPair(parsed.token0!, parsed.token1!, {
                    protocol: parsed.protocol,
                    chain: parsed.chain,
                    stable: parsed.stable,
                })
                if (data.pool) {
                    const addr = data.pool.pool_address || data.pool.address || data.pool.pool
                    if (addr?.startsWith('0x')) {
                        toast.info('Enriching with on-chain data...')
                        try {
                            const verified = await scoutVerifyRpc(addr, parsed.chain || 'base')
                            if (verified.success && verified.pool) {
                                poolData = verified.pool
                                if (verified.risk_analysis) {
                                    poolData.risk_score = verified.risk_analysis.risk_score
                                    poolData.risk_level = verified.risk_analysis.risk_level
                                    poolData.risk_reasons = verified.risk_analysis.risk_reasons
                                }
                            }
                        } catch { /* fallback to basic data */ }
                    }
                    if (!poolData) poolData = data.pool as Pool
                }
            } else if (parsed.type === 'address' || parsed.type === 'defillama') {
                const rawInput = parsed.original || parsed.id!

                if (rawInput.includes('http') || rawInput.includes('token')) {
                    toast.info('Resolving input...')
                    try {
                        const resolved = await scoutResolve(rawInput, 'base')
                        if (resolved.success && resolved.pool_address) {
                            const verified = await scoutVerifyRpc(resolved.pool_address, 'base')
                            if (verified.success && verified.pool) {
                                poolData = verified.pool
                                if (verified.risk_analysis) {
                                    poolData.risk_score = verified.risk_analysis.risk_score
                                    poolData.risk_level = verified.risk_analysis.risk_level
                                    poolData.risk_reasons = verified.risk_analysis.risk_reasons
                                }
                            }
                        }
                    } catch { /* continue to direct verify */ }
                }

                if (!poolData) {
                    toast.info('Fetching pool data...')
                    try {
                        const verified = await scoutVerifyRpc(parsed.id!, 'base')
                        if (verified.success && verified.pool) {
                            poolData = verified.pool
                            if (verified.risk_analysis) {
                                poolData.risk_score = verified.risk_analysis.risk_score
                                poolData.risk_level = verified.risk_analysis.risk_level
                                poolData.risk_reasons = verified.risk_analysis.risk_reasons
                            }
                        }
                    } catch { /* pool not found */ }
                }
            }

            if (!poolData) {
                throw new Error('Pool not found. Try pasting a direct contract address.')
            }

            useCredits(CREDIT_COSTS.VERIFY)
            toast.success(`Used ${CREDIT_COSTS.VERIFY} credits`)

            saveToHistory(poolData)
            setHistory(getHistory())
            setResult(poolData)
            setShowModal(true)
            setQuery('')

        } catch (error: any) {
            toast.error(`Verification failed: ${error.message}`)
        } finally {
            setLoading(false)
        }
    }

    const handleHistoryClear = () => {
        clearHistory()
        setHistory([])
    }

    const openFromHistory = (item: HistoryItem) => {
        setResult(item.pool)
        setShowModal(true)
    }

    const riskScore = result?.risk_score || 0
    const riskLabel = getRiskLabel(riskScore)
    const riskColor = getRiskColor(riskScore)

    // Map risk color to Tailwind classes
    const riskClasses: Record<string, string> = {
        '#22c55e': 'bg-green-500/15 text-green-500 border-green-500/30',
        '#84cc16': 'bg-lime-500/15 text-lime-500 border-lime-500/30',
        '#eab308': 'bg-yellow-500/15 text-yellow-500 border-yellow-500/30',
        '#f97316': 'bg-orange-500/15 text-orange-500 border-orange-500/30',
        '#ef4444': 'bg-red-500/15 text-red-500 border-red-500/30',
    }
    const riskBadgeClass = riskClasses[riskColor] || 'bg-muted text-muted-foreground border-border'

    return (
        <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="flex items-center gap-3 mb-5">
                <div className="w-12 h-12 rounded-xl flex items-center justify-center bg-primary/10 border border-primary/30">
                    <Search className="w-6 h-6 text-primary" />
                </div>
                <div>
                    <h1 className="font-heading text-2xl font-bold text-foreground">
                        Pool Verification
                    </h1>
                    <p className="text-sm text-muted-foreground">
                        Analyze any pool by address or URL · Powered by Artisan Agent
                    </p>
                </div>
            </div>

            {/* Data Sources */}
            <div className="flex flex-wrap gap-3 mb-5">
                {[
                    { name: 'GeckoTerminal', icon: '', tw: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20', dot: 'bg-emerald-500' },
                    { name: 'DefiLlama', icon: '', tw: 'bg-blue-500/10 text-blue-500 border-blue-500/20', dot: 'bg-blue-500' },
                    { name: 'Base RPC', chainIcon: '/icons/base.png', tw: 'bg-blue-600/10 text-blue-400 border-blue-600/20', dot: 'bg-blue-600' },
                    { name: 'ETH RPC', chainIcon: '/icons/ethereum.png', tw: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20', dot: 'bg-indigo-500' },
                    { name: 'Solana RPC', chainIcon: '/icons/solana.png', tw: 'bg-purple-500/10 text-purple-400 border-purple-500/20', dot: 'bg-purple-500' },
                ].map(src => (
                    <Badge key={src.name} variant="outline" className={`${src.tw} text-xs gap-1.5 py-1 px-3`}>
                        <span className={`w-2 h-2 rounded-full ${src.dot}`} />
                        {src.chainIcon ? (
                            <img src={src.chainIcon} alt="" className="w-3.5 h-3.5 rounded-full" />
                        ) : (
                            <span>{src.icon}</span>
                        )}
                        {src.name}
                    </Badge>
                ))}
            </div>

            {/* Search Box */}
            <Card className="mb-5 border-primary/20 shadow-[0_0_20px_rgba(212,168,83,0.1)]">
                <CardContent className="p-5">
                    <div className="flex items-center gap-2 mb-3">
                        <Badge variant="outline" className="bg-primary/10 text-primary border-primary/30 font-heading font-semibold">
                            {credits} credits
                        </Badge>
                    </div>

                    <div className="flex gap-2">
                        <Input
                            type="text"
                            value={query}
                            onChange={e => setQuery(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && handleVerify()}
                            placeholder="Paste pool address, DefiLlama URL, Aerodrome/Uniswap link..."
                            className="flex-1 bg-background border-border text-foreground"
                        />
                        <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}>
                            <Button
                                onClick={handleVerify}
                                disabled={loading}
                                className="px-6 font-heading font-bold bg-gradient-to-br from-primary to-yellow-500 text-primary-foreground hover:from-primary/90 hover:to-yellow-500/90"
                            >
                                {loading ? (
                                    <><Loader2 className="w-4 h-4 mr-1.5 animate-spin" /> Verifying...</>
                                ) : (
                                    <><Search className="w-4 h-4 mr-1.5" /> VERIFY</>
                                )}
                            </Button>
                        </motion.div>
                    </div>

                    <div className="flex flex-wrap gap-1.5 mt-3">
                        <span className="text-xs text-muted-foreground mr-1">Supported:</span>
                        {['0x Address', 'DefiLlama', 'Aerodrome', 'Uniswap', 'Velodrome', 'Curve'].map(tag => (
                            <Badge key={tag} variant="secondary" className="text-xs text-muted-foreground">
                                {tag}
                            </Badge>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Verification Result — Quick Summary Card */}
            <AnimatePresence>
                {result && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                    >
                        <Card className="mb-5 cursor-pointer group hover:border-primary/40 transition-all"
                            onClick={() => setShowModal(true)}>
                            <CardContent className="p-5">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <img
                                            src={getProtocolIconUrl(result.project)}
                                            alt={result.project}
                                            className="w-10 h-10 rounded-lg bg-secondary"
                                            onError={(e) => { (e.target as HTMLImageElement).src = '/icons/default.svg' }}
                                        />
                                        <div>
                                            <h2 className="font-heading text-lg font-bold text-foreground">
                                                {result.symbol}
                                            </h2>
                                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                <span>{result.project}</span>
                                                {result.chain && (
                                                    <>
                                                        <span>·</span>
                                                        <img src={getChainIconUrl(result.chain)} alt="" className="w-3.5 h-3.5 rounded-full" />
                                                        <span>{result.chain}</span>
                                                    </>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Risk Badge */}
                                    <Badge variant="outline" className={`${riskBadgeClass} text-sm font-heading font-bold py-1 px-3`}>
                                        {riskLabel} Risk
                                    </Badge>
                                </div>

                                {/* Metrics */}
                                <div className="grid grid-cols-4 gap-3 mb-4">
                                    {[
                                        { label: 'APY', value: formatApy(result.apy || 0), cls: 'text-green-500' },
                                        { label: 'TVL', value: formatUsd(result.tvl || 0), cls: 'text-foreground' },
                                        { label: 'Risk Score', value: `${riskScore}/100`, cls: riskBadgeClass.split(' ')[1] || 'text-foreground' },
                                        { label: 'IL Risk', value: result.il_risk_level || result.il_risk || 'N/A', cls: 'text-muted-foreground' },
                                    ].map(m => (
                                        <div key={m.label} className="text-center p-3 rounded-xl bg-secondary">
                                            <div className={`text-lg font-heading font-bold ${m.cls}`}>{m.value}</div>
                                            <div className="text-xs text-muted-foreground">{m.label}</div>
                                        </div>
                                    ))}
                                </div>

                                {/* Risk Score Bar */}
                                <div className="mb-4">
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="text-xs font-heading font-semibold text-muted-foreground">Safety Score</span>
                                        <span className={`text-xs font-heading font-bold ${riskBadgeClass.split(' ')[1] || 'text-foreground'}`}>{riskScore}/100</span>
                                    </div>
                                    <Progress value={riskScore} className="h-2" />
                                </div>

                                {/* View Details Button */}
                                <motion.div whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.98 }}>
                                    <Button
                                        onClick={(e) => { e.stopPropagation(); setShowModal(true) }}
                                        className="w-full font-heading font-bold bg-gradient-to-br from-primary to-yellow-500 text-primary-foreground hover:from-primary/90 hover:to-yellow-500/90"
                                    >
                                        <Eye className="w-4 h-4 mr-2" />
                                        View Full Analysis
                                    </Button>
                                </motion.div>
                            </CardContent>
                        </Card>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Rich Pool Detail Modal */}
            {result && showModal && (
                <PoolDetailModal
                    pool={result}
                    onClose={() => setShowModal(false)}
                />
            )}

            {/* History */}
            <div>
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-muted-foreground" />
                        <h3 className="font-heading text-sm font-semibold text-foreground">
                            Recent Verifications
                        </h3>
                    </div>
                    {history.length > 0 && (
                        <Button variant="ghost" size="sm" onClick={handleHistoryClear}
                            className="text-xs h-7 px-2 text-muted-foreground hover:text-destructive">
                            <Trash2 className="w-3 h-3 mr-1" /> Clear
                        </Button>
                    )}
                </div>

                {history.length === 0 ? (
                    <Card>
                        <CardContent className="p-8 text-center">
                            <Search className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                            <p className="text-sm text-muted-foreground">
                                No verified pools yet. Enter an address above to verify.
                            </p>
                        </CardContent>
                    </Card>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {history.map((item, i) => (
                            <motion.div
                                key={`${item.pool.pool_id || item.pool.pool}-${i}`}
                                initial={{ opacity: 0, y: 5 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.03 }}
                                onClick={() => openFromHistory(item)}
                            >
                                <Card className="p-3 cursor-pointer group hover:border-primary/40 transition-all">
                                    <div className="flex items-center gap-2.5">
                                        <img
                                            src={getProtocolIconUrl(item.pool.project)}
                                            alt=""
                                            className="w-8 h-8 rounded-lg bg-secondary"
                                            onError={(e) => { (e.target as HTMLImageElement).src = '/icons/default.svg' }}
                                        />
                                        <div className="flex-1 min-w-0">
                                            <div className="text-sm font-heading font-semibold truncate text-foreground">
                                                {item.pool.symbol}
                                            </div>
                                            <div className="text-xs truncate text-muted-foreground">
                                                {item.pool.project} · {formatApy(item.pool.apy || 0)} APY
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <div className={`text-xs font-heading font-bold ${(riskClasses[getRiskColor(item.pool.risk_score)]?.split(' ')[1]) || 'text-muted-foreground'
                                                }`}>
                                                {getRiskLabel(item.pool.risk_score)}
                                            </div>
                                            <div className="text-xs text-muted-foreground">
                                                {new Date(item.timestamp).toLocaleDateString()}
                                            </div>
                                        </div>
                                        <ChevronRight className="w-4 h-4 text-primary opacity-0 group-hover:opacity-100 transition-opacity" />
                                    </div>
                                </Card>
                            </motion.div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}
