/**
 * Sidebar — Explore filter panel
 * shadcn/ui + Tailwind + Framer Motion + Lucide + Zustand
 *
 * Components: Card, Badge, Button, Separator, Slider
 * All inline styles replaced with Tailwind classes + shadcn semantic tokens
 */
import { motion } from 'framer-motion'
import {
    Shield, Radar, Search, RotateCcw, Zap, Lock, Coins,
    BookOpen, Github, Twitter, Send,
} from 'lucide-react'
import { useFilterStore } from '@/stores/filterStore'
import { useCreditsStore, CREDIT_COSTS } from '@/stores/creditsStore'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from '@/components/Toast'
import { getProtocolIconUrl } from '@/lib/icons'

import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Slider } from '@/components/ui/slider'

const agents = [
    { name: 'Scout', icon: Search, status: 'Active' },
    { name: 'Guardian', icon: Shield, status: 'Active' },
    { name: 'Airdrop', icon: Radar, status: 'Active' },
]

const riskOptions = ['all', 'low', 'medium', 'high', 'critical']
const assetOptions = ['stablecoin', 'eth', 'sol', 'all']
const poolTypeOptions = ['all', 'pair', 'single']

const ALL_PROTOCOL_NAMES = [
    'Lido', 'Aave', 'Uniswap', 'Morpho', 'Pendle', 'Compound', 'Jito', 'Curve',
    'Jupiter', 'Spark', 'Aerodrome', 'Marinade', 'Convex', 'Meteora', 'Kamino',
    'Raydium', 'Sanctum', 'Balancer', 'Drift', 'GMX', 'Moonwell', 'Yearn',
    'Beefy', 'Orca', 'MarginFi', 'Merkl', 'Origin', 'Seamless', 'Solend',
    'Exactly', 'InfiniFi', 'Extra Finance', 'Radiant', 'Sonne', 'Avantis',
    'Peapods', 'MemeDollar',
]

export function Sidebar() {
    const filters = useFilterStore()
    const queryClient = useQueryClient()
    const { credits, useCredits, canAfford } = useCreditsStore()

    const isDefaultFilters =
        filters.chain === 'all' &&
        filters.riskLevel === 'all' &&
        filters.assetType === 'all' &&
        filters.poolType === 'all' &&
        filters.protocols.length === 0

    const handleApply = () => {
        if (isDefaultFilters) {
            filters.applyFilters()
            queryClient.invalidateQueries({ queryKey: ['pools'] })
            toast.info('Pools refreshed')
            return
        }
        if (!canAfford(CREDIT_COSTS.FILTER)) {
            toast.error(`Need ${CREDIT_COSTS.FILTER} credits to apply filters. Buy more credits on Premium page.`)
            return
        }
        const success = useCredits(CREDIT_COSTS.FILTER)
        if (success) {
            filters.applyFilters()
            queryClient.invalidateQueries({ queryKey: ['pools'] })
            toast.success(`Filters applied • ${CREDIT_COSTS.FILTER} credits used`)
        }
    }

    return (
        <aside className="hidden lg:flex flex-col w-72 overflow-y-auto flex-shrink-0 bg-card border-r border-primary/20">
            {/* Agent Status Panel */}
            <div className="p-4 border-b border-border">
                <div className="flex items-center gap-2 mb-3">
                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="font-heading font-semibold text-sm text-foreground">
                        Artisan AI
                    </span>
                    <Badge variant="outline" className="ml-auto bg-green-500/15 text-green-500 border-green-500/30 text-[10px]">
                        ONLINE
                    </Badge>
                </div>
                <div className="space-y-2">
                    {agents.map(({ name, icon: Icon, status }) => (
                        <div key={name} className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <Icon className="w-3.5 h-3.5 text-primary" />
                                <span className="text-xs text-muted-foreground">{name}</span>
                            </div>
                            <Badge variant="outline" className="bg-green-500/15 text-green-500 border-green-500/30 text-[10px]">
                                {status}
                            </Badge>
                        </div>
                    ))}
                    <div className="flex items-center justify-between">
                        <span className="text-[11px] text-muted-foreground">+19 more agents</span>
                        <Badge variant="outline" className="bg-green-500/15 text-green-500 border-green-500/30 text-[10px]">
                            All Active
                        </Badge>
                    </div>
                </div>
            </div>

            {/* Terminal Preview */}
            <div className="p-4 border-b border-border">
                <Card className="bg-card border-border">
                    <CardContent className="p-3 font-mono text-xs leading-relaxed text-green-500 min-h-[90px]">
                        <div className="text-muted-foreground">{'>'} neural_terminal v2.0</div>
                        <div>
                            <span className="text-primary">scout</span>: scanning 1,247 pools...
                        </div>
                        <div>
                            <span className="text-primary">guardian</span>: risk check OK
                        </div>
                        <div className="text-muted-foreground animate-pulse">
                            awaiting command
                            <span className="inline-block w-1.5 h-3.5 bg-green-500 ml-0.5 align-middle" />
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Filters */}
            <div className="p-4 flex-1">
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                        <Search className="w-3.5 h-3.5 text-primary" />
                        <span className="font-heading font-semibold text-sm text-foreground">
                            Filters
                        </span>
                    </div>
                    <Button variant="ghost" size="sm"
                        onClick={filters.resetFilters}
                        className="text-xs h-6 px-2 text-muted-foreground hover:text-primary">
                        <RotateCcw className="w-3 h-3 mr-1" /> Reset
                    </Button>
                </div>

                {/* Chain */}
                <FilterGroup label="Chain">
                    <div className="flex flex-wrap gap-1.5">
                        {[
                            { id: 'all', label: 'All' },
                            { id: 'solana', label: 'SOL', iconSrc: '/icons/solana.png' },
                            { id: 'base', label: 'Base', iconSrc: '/icons/base.png' },
                            { id: 'ethereum', label: 'ETH', iconSrc: '/icons/ethereum.png' },
                        ].map(c => {
                            const active = filters.chain === c.id
                            return (
                                <button
                                    key={c.id}
                                    onClick={() => filters.setChain(c.id)}
                                    className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs cursor-pointer transition-all border ${active
                                        ? 'bg-primary/10 border-primary/30 text-primary'
                                        : 'bg-secondary border-border text-muted-foreground hover:border-primary/20 hover:text-foreground'
                                        }`}
                                >
                                    {c.iconSrc ? (
                                        <img src={c.iconSrc} alt="" className="w-3.5 h-3.5 rounded-full" />
                                    ) : null}
                                    <span className="font-medium">{c.label}</span>
                                </button>
                            )
                        })}
                        <button className="px-2.5 py-1.5 rounded-lg text-xs cursor-pointer bg-secondary border border-border text-muted-foreground hover:text-foreground transition-colors">
                            ... More
                        </button>
                    </div>
                </FilterGroup>

                {/* Risk Level */}
                <FilterGroup label="Risk Level">
                    <FilterPills
                        options={riskOptions}
                        value={filters.riskLevel}
                        onChange={filters.setRiskLevel}
                    />
                </FilterGroup>

                {/* Asset Type */}
                <FilterGroup label="Asset Type">
                    <FilterPills
                        options={assetOptions}
                        value={filters.assetType}
                        onChange={filters.setAssetType}
                        labels={{ stablecoin: 'Stablecoins', eth: 'ETH', sol: 'SOL', all: 'All' }}
                    />
                </FilterGroup>

                {/* Pool Type */}
                <FilterGroup label="Pool Type">
                    <FilterPills
                        options={poolTypeOptions}
                        value={filters.poolType}
                        onChange={filters.setPoolType}
                        labels={{ all: 'All', pair: 'LP Pairs', single: 'Single' }}
                    />
                </FilterGroup>

                {/* Protocol Filter */}
                <FilterGroup label="Protocols">
                    <div className="flex flex-wrap gap-1.5 max-h-[180px] overflow-y-auto pr-1 scrollbar-thin">
                        {ALL_PROTOCOL_NAMES.map(name => {
                            const key = name.toLowerCase()
                            const active = filters.protocols.includes(key)
                            return (
                                <button
                                    key={name}
                                    onClick={() => {
                                        const next = active
                                            ? filters.protocols.filter(p => p !== key)
                                            : [...filters.protocols, key]
                                        filters.setProtocols(next)
                                    }}
                                    className={`flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] cursor-pointer transition-all border ${active
                                        ? 'bg-primary/10 border-primary/30 text-primary'
                                        : 'bg-secondary border-border text-muted-foreground hover:border-primary/20 hover:text-foreground'
                                        }`}
                                >
                                    <img
                                        src={getProtocolIconUrl(name)}
                                        alt={name}
                                        className="w-3.5 h-3.5 rounded-full"
                                        onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
                                    />
                                    <span className="font-medium">{name}</span>
                                </button>
                            )
                        })}
                    </div>
                    <div className="flex gap-1.5 mt-1.5">
                        <button
                            onClick={() => filters.setProtocols(ALL_PROTOCOL_NAMES.map(n => n.toLowerCase()))}
                            className="text-[10px] text-primary hover:underline cursor-pointer"
                        >
                            Select All
                        </button>
                        <span className="text-[10px] text-muted-foreground">·</span>
                        <button
                            onClick={() => filters.setProtocols([])}
                            className="text-[10px] text-muted-foreground hover:text-foreground hover:underline cursor-pointer"
                        >
                            Clear
                        </button>
                    </div>
                </FilterGroup>

                {/* TVL Range Slider */}
                <FilterGroup label="TVL Range">
                    <RangeSlider
                        min={0}
                        max={9}
                        value={filters.tvlRange}
                        onChange={filters.setTvlRange}
                        formatLabel={(v) => {
                            const labels = ['$0', '$10K', '$50K', '$100K', '$500K', '$1M', '$5M', '$10M', '$50M', '$100M+']
                            return labels[v] || `$${v}`
                        }}
                    />
                </FilterGroup>

                {/* APY Range Slider */}
                <FilterGroup label="APY Range">
                    <RangeSlider
                        min={0}
                        max={100}
                        value={filters.apyRange}
                        onChange={filters.setApyRange}
                        formatLabel={(v) => `${v}%`}
                        step={5}
                    />
                </FilterGroup>

                {/* Apply Button with Credit Gate */}
                <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}>
                    <Button
                        onClick={handleApply}
                        className={`w-full mt-3 font-heading font-semibold ${isDefaultFilters || canAfford(CREDIT_COSTS.FILTER)
                            ? 'bg-gradient-to-br from-primary to-yellow-500 text-primary-foreground hover:from-primary/90 hover:to-yellow-500/90'
                            : 'bg-secondary text-muted-foreground border border-border'
                            }`}
                    >
                        {isDefaultFilters ? (
                            <><Zap className="w-4 h-4 mr-1.5" /> Refresh Pools</>
                        ) : canAfford(CREDIT_COSTS.FILTER) ? (
                            <><Zap className="w-4 h-4 mr-1.5" /> Apply Filters ({CREDIT_COSTS.FILTER} cr)</>
                        ) : (
                            <><Lock className="w-4 h-4 mr-1.5" /> Need {CREDIT_COSTS.FILTER} Credits</>
                        )}
                    </Button>
                </motion.div>

                {/* Credit Balance */}
                <div className="flex items-center justify-center gap-1.5 mt-2">
                    <Coins className="w-3 h-3 text-primary" />
                    <span className="text-[10px] text-muted-foreground">
                        {credits} credits remaining
                    </span>
                </div>
            </div>

            <Separator />

            {/* Footer Links */}
            <div className="p-4 flex items-center justify-center gap-4">
                {[
                    { icon: BookOpen, label: 'Docs', href: 'https://docs.techne.finance' },
                    { icon: Github, label: 'GitHub', href: 'https://github.com/techne-finance' },
                    { icon: Twitter, label: 'Twitter', href: 'https://twitter.com/technefinance' },
                    { icon: Send, label: 'Telegram', href: 'https://t.me/technefinance' },
                ].map(({ icon: Icon, label, href }) => (
                    <a
                        key={label}
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex flex-col items-center gap-0.5 text-muted-foreground hover:text-primary transition-colors"
                    >
                        <Icon className="w-3.5 h-3.5" />
                        <span className="text-[9px]">{label}</span>
                    </a>
                ))}
            </div>
        </aside>
    )
}

// ========== Sub-components ==========

function FilterGroup({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div className="mb-3.5">
            <label className="block text-[10px] font-medium mb-1.5 text-muted-foreground uppercase tracking-wider">
                {label}
            </label>
            {children}
        </div>
    )
}

function FilterPills({
    options,
    value,
    onChange,
    labels,
}: {
    options: string[]
    value: string
    onChange: (v: string) => void
    labels?: Record<string, string>
}) {
    return (
        <div className="flex flex-wrap gap-1.5">
            {options.map(opt => {
                const isSelected = value === opt
                return (
                    <button
                        key={opt}
                        onClick={() => onChange(opt)}
                        className={`px-2.5 py-1 rounded-md text-xs font-medium cursor-pointer transition-all border ${isSelected
                            ? 'bg-primary/10 border-primary/30 text-primary'
                            : 'bg-secondary border-border text-muted-foreground hover:border-primary/20 hover:text-foreground'
                            }`}
                    >
                        {labels?.[opt] || opt.charAt(0).toUpperCase() + opt.slice(1)}
                    </button>
                )
            })}
        </div>
    )
}

// ─── Range Slider (dual-thumb via shadcn Slider) ───
function RangeSlider({
    min, max, value, onChange, formatLabel, step = 1,
}: {
    min: number; max: number; value: [number, number];
    onChange: (v: [number, number]) => void; formatLabel: (v: number) => string;
    step?: number;
}) {
    return (
        <div>
            <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-semibold text-primary">
                    {formatLabel(value[0])}
                </span>
                <span className="text-[10px] text-muted-foreground">—</span>
                <span className="text-[11px] font-semibold text-primary">
                    {formatLabel(value[1])}
                </span>
            </div>
            <Slider
                min={min}
                max={max}
                step={step}
                value={value}
                onValueChange={(v) => onChange(v as [number, number])}
                className="[&_[role=slider]]:bg-primary [&_[role=slider]]:border-primary/50 [&_[data-orientation=horizontal]>[data-orientation=horizontal]]:bg-primary"
            />
        </div>
    )
}
