/**
 * Strategies Page — Your Deployed Agents + Community Showcase
 * Shows real deployed agents from backend + hardcoded community strategies
 * Click to open full settings modal, edit config, share with avg weekly return
 */

import { useState, useMemo, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
    Cpu, Star, Users, Copy, Eye, TrendingUp, Filter, Sparkles, Settings,
    Shield, Flame, X, Save, Share2, Check, Zap, BarChart3,
    Activity, Wallet, AlertTriangle, Loader2, Lock, Timer, Droplets,
} from 'lucide-react'
import { useWalletStore } from '@/stores/walletStore'
import { useAgentManagement, usePortfolioData } from '@/hooks/usePortfolio'
import { updateAgent } from '@/lib/api'
import { toast } from '@/components/Toast'

import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Slider } from '@/components/ui/slider'
import { Separator } from '@/components/ui/separator'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'

// ─── Types ───
interface CommunityStrategy {
    name: string
    author: string
    description: string
    apy: string
    copiers: number
    rating: number
    chains: string[]
    tags: string[]
}

const COMMUNITY_STRATEGIES: CommunityStrategy[] = [
    {
        name: 'Stablecoin Maximizer',
        author: '0xDeFi...42',
        description: 'Auto-compounds USDC across Aave, Compound, and Moonwell for maximum stable yield on Base',
        apy: '+24.5%',
        copiers: 124,
        rating: 4.8,
        chains: ['Base', 'Ethereum'],
        tags: ['Stablecoin', 'Low Risk'],
    },
    {
        name: 'Base DEX Hunter',
        author: 'BaseChad.eth',
        description: 'Aggressive LP farming on Aerodrome with auto-rebalancing',
        apy: '+67.2%',
        copiers: 89,
        rating: 4.6,
        chains: ['Base'],
        tags: ['DEX', 'High Yield'],
    },
    {
        name: 'Morpho Yield Optimizer',
        author: 'YieldMaxi.eth',
        description: 'Optimized lending across Morpho vaults with smart rate arbitrage',
        apy: '+31.8%',
        copiers: 67,
        rating: 4.7,
        chains: ['Ethereum', 'Base'],
        tags: ['Lending', 'Medium Risk'],
    },
    {
        name: 'ETH Staking Plus',
        author: 'StakeKing.eth',
        description: 'Liquid staking via Lido + EtherFi with leveraged looping on Morpho',
        apy: '+12.8%',
        copiers: 203,
        rating: 4.9,
        chains: ['Ethereum'],
        tags: ['Staking', 'Low Risk'],
    },
]

type Tab = 'community' | 'mine'

// ─── Main Component ───
export function StrategiesPage() {
    const { isConnected, address } = useWalletStore()
    const [activeTab, setActiveTab] = useState<Tab>('mine')
    const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)
    const [saving, setSaving] = useState(false)

    // Real data from backend
    const { agents, loadingAgents } = useAgentManagement()
    const { totalValue: _totalValue, totalPnL: _totalPnL, positions: _positions } = usePortfolioData(address || undefined, null)

    // Edit state for modal
    const [editMinApy, setEditMinApy] = useState(0)
    const [editMaxApy, setEditMaxApy] = useState(100)
    const [editRiskLevel, setEditRiskLevel] = useState('medium')
    const [editProtocols, setEditProtocols] = useState<string[]>([])
    const [editAssets, setEditAssets] = useState<string[]>([])
    // Advanced settings state
    const [editPoolType, setEditPoolType] = useState('single')
    const [editMinTvl, setEditMinTvl] = useState(1_000_000)
    const [editMaxTvl, setEditMaxTvl] = useState(100_000_000)
    const [editApyCheckHours, setEditApyCheckHours] = useState(24)
    const [editSlippage, setEditSlippage] = useState(0.5)
    const [editCompoundFreq, setEditCompoundFreq] = useState(7)
    const [editRebalanceThreshold, setEditRebalanceThreshold] = useState(5)
    const [editMaxGas, setEditMaxGas] = useState(10)
    const [editEmergencyExit, setEditEmergencyExit] = useState(true)
    const [editAvoidIL, setEditAvoidIL] = useState(true)
    const [editOnlyAudited, setEditOnlyAudited] = useState(true)
    const [editMaxAllocation, setEditMaxAllocation] = useState(25)
    const [editVaultCount, setEditVaultCount] = useState(5)
    const [editDuration, setEditDuration] = useState(30)

    const selectedAgent = useMemo(
        () => agents.find(a => a.id === selectedAgentId) || null,
        [agents, selectedAgentId]
    )

    const openModal = useCallback((agent: any) => {
        setSelectedAgentId(agent.id)
        // Pre-fill edit fields from agent config
        setEditMinApy(agent.min_apy || agent.minApy || 5)
        setEditMaxApy(agent.max_apy || agent.maxApy || 100)
        setEditRiskLevel(agent.risk_level || agent.riskLevel || 'medium')
        setEditProtocols(agent.protocols || ['morpho', 'aave'])
        setEditAssets(agent.preferred_assets || agent.preferredAssets || ['USDC'])
        // Advanced settings
        setEditPoolType(agent.pool_type || agent.poolType || 'single')
        setEditMinTvl(agent.min_pool_tvl || agent.minTvl || 1_000_000)
        setEditMaxTvl(agent.max_pool_tvl || agent.maxTvl || 100_000_000)
        setEditApyCheckHours(agent.apy_check_hours || agent.apyCheckHours || 24)
        setEditSlippage(agent.slippage || 0.5)
        setEditCompoundFreq(agent.compound_frequency || agent.compoundFreq || 7)
        setEditRebalanceThreshold(agent.rebalance_threshold || agent.rebalanceThreshold || 5)
        setEditMaxGas(agent.max_gas_price || agent.maxGasPrice || 10)
        setEditEmergencyExit(agent.emergency_exit ?? agent.emergencyExit ?? true)
        setEditAvoidIL(agent.avoid_il ?? agent.avoidIL ?? true)
        setEditOnlyAudited(agent.only_audited ?? agent.onlyAudited ?? true)
        setEditMaxAllocation(agent.max_allocation || agent.maxAllocation || 25)
        setEditVaultCount(agent.vault_count || agent.vaultCount || 5)
        setEditDuration(agent.duration || 30)
    }, [])

    const closeModal = useCallback(() => {
        setSelectedAgentId(null)
    }, [])

    // ─── Save Edits ───
    const handleSave = useCallback(async () => {
        if (!selectedAgent) return
        const agentAddr = selectedAgent.agent_address || selectedAgent.address
        if (!agentAddr) { toast.error('No agent address'); return }

        setSaving(true)
        try {
            const res = await updateAgent(agentAddr, {
                min_apy: editMinApy,
                max_apy: editMaxApy,
                risk_level: editRiskLevel,
                protocols: editProtocols,
                preferred_assets: editAssets,
                settings: {
                    pool_type: editPoolType,
                    min_pool_tvl: editMinTvl,
                    max_pool_tvl: editMaxTvl < 100_000_000 ? editMaxTvl : undefined,
                    apy_check_hours: editApyCheckHours,
                    slippage: editSlippage,
                    compound_frequency: editCompoundFreq,
                    rebalance_threshold: editRebalanceThreshold,
                    max_gas_price: editMaxGas,
                    emergency_exit: editEmergencyExit,
                    avoid_il: editAvoidIL,
                    only_audited: editOnlyAudited,
                    max_allocation: editMaxAllocation,
                    vault_count: editVaultCount,
                    duration: editDuration,
                },
            })
            if (res.success) {
                toast.success('Strategy settings updated')
                closeModal()
            } else {
                toast.error(res.message || 'Update failed')
            }
        } catch {
            toast.error('Failed to update settings')
        }
        setSaving(false)
    }, [selectedAgent, editMinApy, editMaxApy, editRiskLevel, editProtocols, editAssets, editPoolType, editMinTvl, editMaxTvl, editApyCheckHours, editSlippage, editCompoundFreq, editRebalanceThreshold, editMaxGas, editEmergencyExit, editAvoidIL, editOnlyAudited, editMaxAllocation, editVaultCount, editDuration, closeModal])

    // ─── Share ───
    const handleShare = useCallback((agent: any) => {
        const preset = agent.preset || agent.strategy_mode || 'custom'
        const protocols = (agent.protocols || []).join(', ') || 'Multi-protocol'
        const riskLevel = agent.risk_level || agent.riskLevel || 'medium'
        const minApy = agent.min_apy || agent.minApy || '?'
        const maxApy = agent.max_apy || agent.maxApy || '?'
        const deployedAt = agent.deployedAt || agent.deployed_at || agent.created_at
        const earned = agent.total_earned || 0

        // Compute avg weekly return
        let weeklyReturn = '—'
        if (deployedAt && earned > 0) {
            const weeks = Math.max(1, (Date.now() - new Date(deployedAt).getTime()) / (7 * 24 * 60 * 60 * 1000))
            weeklyReturn = `$${(earned / weeks).toFixed(2)}/week`
        }

        const shareText = [
            `Techne AI Agent Strategy`,
            `━━━━━━━━━━━━━━━━━━━━━━━━`,
            `Preset: ${preset.charAt(0).toUpperCase() + preset.slice(1)}`,
            `Risk: ${riskLevel.charAt(0).toUpperCase() + riskLevel.slice(1)}`,
            `APY Target: ${minApy}% – ${maxApy}%`,
            `Protocols: ${protocols}`,
            `Avg Return: ${weeklyReturn}`,
            `━━━━━━━━━━━━━━━━━━━━━━━━`,
            `Built with techne.app`,
        ].join('\n')

        navigator.clipboard.writeText(shareText)
        toast.success('Strategy copied to clipboard!')
    }, [])

    const tabs: { key: Tab; label: string; icon: any }[] = [
        { key: 'mine', label: 'My Agents', icon: Shield },
        { key: 'community', label: 'Community', icon: Users },
    ]

    return (
        <div className="max-w-5xl mx-auto">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
                <div>
                    <h1 className="font-heading text-xl sm:text-2xl font-bold text-foreground">
                        Strategies
                    </h1>
                    <p className="text-sm text-muted-foreground">
                        Manage your agent strategies and discover community presets
                    </p>
                </div>
                {isConnected && agents.length > 0 && (
                    <Badge variant="outline" className="bg-primary/10 text-primary border-primary/30 font-heading">
                        {agents.length} Agent{agents.length > 1 ? 's' : ''} Deployed
                    </Badge>
                )}
            </div>

            {/* Tabs */}
            <div className="flex gap-2 mb-5">
                {tabs.map(tab => (
                    <Button
                        key={tab.key}
                        variant={activeTab === tab.key ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setActiveTab(tab.key)}
                        className={activeTab === tab.key
                            ? 'bg-gradient-to-r from-primary to-yellow-500 text-primary-foreground font-heading font-semibold'
                            : 'font-heading'}
                    >
                        <tab.icon className="w-3.5 h-3.5 mr-1.5" />
                        {tab.label}
                    </Button>
                ))}
            </div>

            {/* ─── My Agents Tab ─── */}
            {activeTab === 'mine' && (
                <>
                    {!isConnected ? (
                        <Card>
                            <CardContent className="p-12 text-center">
                                <Wallet className="w-12 h-12 mx-auto mb-3 text-muted-foreground opacity-50" />
                                <h3 className="font-heading text-lg font-bold mb-1 text-foreground">
                                    Connect Wallet
                                </h3>
                                <p className="text-sm text-muted-foreground">
                                    Connect your wallet to see your deployed agent strategies.
                                </p>
                            </CardContent>
                        </Card>
                    ) : loadingAgents ? (
                        <Card>
                            <CardContent className="p-12 text-center">
                                <Loader2 className="w-8 h-8 mx-auto mb-3 text-primary animate-spin" />
                                <p className="text-sm text-muted-foreground">Loading your agents...</p>
                            </CardContent>
                        </Card>
                    ) : agents.length === 0 ? (
                        <Card>
                            <CardContent className="p-12 text-center">
                                <Sparkles className="w-12 h-12 mx-auto mb-3 text-primary opacity-50" />
                                <h3 className="font-heading text-lg font-bold mb-1 text-foreground">
                                    No Agents Yet
                                </h3>
                                <p className="text-sm text-muted-foreground mb-4">
                                    Deploy your first AI agent in the Build section to start earning yield.
                                </p>
                                <Button
                                    onClick={() => window.location.hash = '#/build'}
                                    className="bg-gradient-to-r from-primary to-yellow-500 text-primary-foreground font-heading font-semibold"
                                >
                                    <Zap className="w-4 h-4 mr-1.5" /> Build Agent
                                </Button>
                            </CardContent>
                        </Card>
                    ) : (
                        <div className="space-y-3">
                            {agents.map((agent: any, i: number) => (
                                <AgentStrategyCard
                                    key={agent.id}
                                    agent={agent}
                                    index={i}
                                    onViewDetails={() => openModal(agent)}
                                    onShare={() => handleShare(agent)}
                                />
                            ))}
                        </div>
                    )}
                </>
            )}

            {/* ─── Community Tab ─── */}
            {activeTab === 'community' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {COMMUNITY_STRATEGIES.map((strategy, i) => (
                        <CommunityCard key={strategy.name} strategy={strategy} index={i} />
                    ))}
                </div>
            )}

            {/* ─── Settings Modal ─── */}
            <Dialog open={!!selectedAgent} onOpenChange={(open) => { if (!open) closeModal() }}>
                {selectedAgent && (
                    <SettingsModal
                        agent={selectedAgent}
                        editMinApy={editMinApy} editMaxApy={editMaxApy} editRiskLevel={editRiskLevel}
                        editProtocols={editProtocols} editAssets={editAssets}
                        setEditMinApy={setEditMinApy} setEditMaxApy={setEditMaxApy}
                        setEditRiskLevel={setEditRiskLevel} setEditProtocols={setEditProtocols} setEditAssets={setEditAssets}
                        editPoolType={editPoolType} setEditPoolType={setEditPoolType}
                        editMinTvl={editMinTvl} setEditMinTvl={setEditMinTvl}
                        editMaxTvl={editMaxTvl} setEditMaxTvl={setEditMaxTvl}
                        editApyCheckHours={editApyCheckHours} setEditApyCheckHours={setEditApyCheckHours}
                        editSlippage={editSlippage} setEditSlippage={setEditSlippage}
                        editCompoundFreq={editCompoundFreq} setEditCompoundFreq={setEditCompoundFreq}
                        editRebalanceThreshold={editRebalanceThreshold} setEditRebalanceThreshold={setEditRebalanceThreshold}
                        editMaxGas={editMaxGas} setEditMaxGas={setEditMaxGas}
                        editEmergencyExit={editEmergencyExit} setEditEmergencyExit={setEditEmergencyExit}
                        editAvoidIL={editAvoidIL} setEditAvoidIL={setEditAvoidIL}
                        editOnlyAudited={editOnlyAudited} setEditOnlyAudited={setEditOnlyAudited}
                        editMaxAllocation={editMaxAllocation} setEditMaxAllocation={setEditMaxAllocation}
                        editVaultCount={editVaultCount} setEditVaultCount={setEditVaultCount}
                        editDuration={editDuration} setEditDuration={setEditDuration}
                        onSave={handleSave} onClose={closeModal}
                        onShare={() => handleShare(selectedAgent)} saving={saving}
                    />
                )}
            </Dialog>
        </div>
    )
}

// ─── Agent Strategy Card ───
function AgentStrategyCard({ agent, index, onViewDetails, onShare }: {
    agent: any; index: number; onViewDetails: () => void; onShare: () => void
}) {
    const isActive = agent.isActive || agent.is_active
    const preset = agent.preset || agent.strategy_mode || 'custom'
    const riskLevel = agent.risk_level || agent.riskLevel || 'medium'
    const protocols = agent.protocols || []
    const deployedAt = agent.deployedAt || agent.deployed_at || agent.created_at
    const earned = agent.total_earned || 0
    const currentApy = agent.current_apy || agent.apy || 0

    // Days since deployment
    const daysSince = deployedAt
        ? Math.max(1, Math.floor((Date.now() - new Date(deployedAt).getTime()) / 86400000))
        : 0

    // Weekly return
    const weeklyReturn = deployedAt && earned > 0
        ? earned / Math.max(1, (Date.now() - new Date(deployedAt).getTime()) / (7 * 24 * 60 * 60 * 1000))
        : 0

    const riskColors: Record<string, string> = {
        low: 'bg-green-500/15 text-green-500 border-green-500/30',
        medium: 'bg-yellow-500/15 text-yellow-500 border-yellow-500/30',
        high: 'bg-red-500/15 text-red-500 border-red-500/30',
    }

    const presetIcons: Record<string, any> = {
        safe: Shield, steady: TrendingUp, degen: Flame, custom: Settings, flexible: Filter,
    }
    const PresetIcon = presetIcons[preset] || Cpu

    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
        >
            <Card className={`group cursor-pointer transition-all hover:border-primary/40 hover:shadow-[0_0_20px_rgba(212,168,83,0.1)] ${isActive ? 'border-primary/20' : 'border-border opacity-70'}`}>
                <CardContent className="p-4">
                    <div className="flex items-start gap-4">
                        {/* Icon */}
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${isActive
                            ? 'bg-primary/10 border border-primary/30'
                            : 'bg-muted border border-border'
                            }`}>
                            <PresetIcon className={`w-6 h-6 ${isActive ? 'text-primary' : 'text-muted-foreground'}`} />
                        </div>

                        {/* Main Info */}
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                                <h3 className="font-heading text-base font-bold text-foreground truncate">
                                    {agent.name || `Agent ${agent.id?.slice(0, 8)}`}
                                </h3>
                                <Badge variant="outline" className={`text-[10px] ${riskColors[riskLevel] || riskColors.medium}`}>
                                    {riskLevel.toUpperCase()}
                                </Badge>
                                <Badge variant={isActive ? 'default' : 'secondary'} className={`text-[10px] ${isActive
                                    ? 'bg-green-500/15 text-green-500 border-green-500/30'
                                    : 'text-muted-foreground'
                                    }`}>
                                    {isActive ? 'Active' : 'Paused'}
                                </Badge>
                            </div>

                            <p className="text-xs text-muted-foreground mb-2">
                                {preset.charAt(0).toUpperCase() + preset.slice(1)} preset ·{' '}
                                {protocols.length > 0 ? protocols.slice(0, 3).join(', ') : 'Multi-protocol'}
                                {protocols.length > 3 && ` +${protocols.length - 3}`}
                                {daysSince > 0 && ` · ${daysSince}d active`}
                            </p>

                            {/* Metrics row */}
                            <div className="flex items-center gap-4 text-xs">
                                {currentApy > 0 && (
                                    <span className="flex items-center gap-1 text-green-500">
                                        <TrendingUp className="w-3 h-3" />
                                        <span className="font-heading font-bold">{currentApy.toFixed(1)}%</span>
                                        <span className="text-muted-foreground">APY</span>
                                    </span>
                                )}
                                {earned > 0 && (
                                    <span className="flex items-center gap-1 text-primary">
                                        <BarChart3 className="w-3 h-3" />
                                        <span className="font-heading font-bold">${earned.toFixed(2)}</span>
                                        <span className="text-muted-foreground">earned</span>
                                    </span>
                                )}
                                {weeklyReturn > 0 && (
                                    <span className="flex items-center gap-1 text-green-400">
                                        <Activity className="w-3 h-3" />
                                        <span className="font-heading font-bold">${weeklyReturn.toFixed(2)}</span>
                                        <span className="text-muted-foreground">/week</span>
                                    </span>
                                )}
                            </div>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                                <Button variant="outline" size="sm" onClick={(e) => { e.stopPropagation(); onShare() }}
                                    className="h-8 px-2.5 text-xs">
                                    <Share2 className="w-3.5 h-3.5" />
                                </Button>
                            </motion.div>
                            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                                <Button size="sm" onClick={(e) => { e.stopPropagation(); onViewDetails() }}
                                    className="h-8 px-3 text-xs bg-gradient-to-r from-primary to-yellow-500 text-primary-foreground font-heading font-semibold">
                                    <Settings className="w-3.5 h-3.5 mr-1" /> Settings
                                </Button>
                            </motion.div>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </motion.div>
    )
}

// ─── Settings Modal ───
function SettingsModal({ agent, editMinApy, editMaxApy, editRiskLevel, editProtocols, editAssets,
    setEditMinApy, setEditMaxApy, setEditRiskLevel, setEditProtocols, setEditAssets,
    editPoolType, setEditPoolType, editMinTvl, setEditMinTvl,
    editMaxTvl, setEditMaxTvl, editApyCheckHours, setEditApyCheckHours,
    editSlippage, setEditSlippage, editCompoundFreq, setEditCompoundFreq,
    editRebalanceThreshold, setEditRebalanceThreshold, editMaxGas, setEditMaxGas,
    editEmergencyExit, setEditEmergencyExit, editAvoidIL, setEditAvoidIL,
    editOnlyAudited, setEditOnlyAudited, editMaxAllocation, setEditMaxAllocation,
    editVaultCount, setEditVaultCount, editDuration, setEditDuration,
    onSave, onClose, onShare, saving }: {
        agent: any
        editMinApy: number; editMaxApy: number; editRiskLevel: string
        editProtocols: string[]; editAssets: string[]
        setEditMinApy: (v: number) => void; setEditMaxApy: (v: number) => void
        setEditRiskLevel: (v: string) => void; setEditProtocols: (v: string[]) => void
        setEditAssets: (v: string[]) => void
        editPoolType: string; setEditPoolType: (v: string) => void
        editMinTvl: number; setEditMinTvl: (v: number) => void
        editMaxTvl: number; setEditMaxTvl: (v: number) => void
        editApyCheckHours: number; setEditApyCheckHours: (v: number) => void
        editSlippage: number; setEditSlippage: (v: number) => void
        editCompoundFreq: number; setEditCompoundFreq: (v: number) => void
        editRebalanceThreshold: number; setEditRebalanceThreshold: (v: number) => void
        editMaxGas: number; setEditMaxGas: (v: number) => void
        editEmergencyExit: boolean; setEditEmergencyExit: (v: boolean) => void
        editAvoidIL: boolean; setEditAvoidIL: (v: boolean) => void
        editOnlyAudited: boolean; setEditOnlyAudited: (v: boolean) => void
        editMaxAllocation: number; setEditMaxAllocation: (v: number) => void
        editVaultCount: number; setEditVaultCount: (v: number) => void
        editDuration: number; setEditDuration: (v: number) => void
        onSave: () => void; onClose: () => void; onShare: () => void; saving: boolean
    }) {
    const preset = agent.preset || agent.strategy_mode || 'custom'
    const chain = agent.chain || 'base'
    const deployedAt = agent.deployedAt || agent.deployed_at || agent.created_at
    const isActive = agent.isActive || agent.is_active
    const proConfig = agent.proConfig || agent.pro_config || {}
    const isPro = agent.is_pro_mode || agent.isPro || !!proConfig.leverage

    // Protocol lists — synced with BuildPage PROTOCOLS constant
    const SINGLE_PROTOCOLS = ['aave', 'compound', 'moonwell', 'morpho', 'seamless', 'sonne', 'exactly']
    const DUAL_PROTOCOLS = ['aerodrome', 'uniswap']
    const BOTH_PROTOCOLS = ['beefy', 'convex', 'origin', 'avantis']
    const ALL_PROTOCOLS = [...SINGLE_PROTOCOLS, ...DUAL_PROTOCOLS, ...BOTH_PROTOCOLS]
    const visibleProtocols = editPoolType === 'single' ? [...SINGLE_PROTOCOLS, ...BOTH_PROTOCOLS]
        : editPoolType === 'dual' ? [...DUAL_PROTOCOLS, ...BOTH_PROTOCOLS]
            : ALL_PROTOCOLS
    const ALL_ASSETS = ['USDC', 'USDT', 'WETH', 'AERO', 'CRV', 'AAVE', 'COMP', 'UNI']

    const toggleProtocol = (p: string) => {
        setEditProtocols(editProtocols.includes(p)
            ? editProtocols.filter(x => x !== p)
            : [...editProtocols, p])
    }
    const toggleAsset = (a: string) => {
        setEditAssets(editAssets.includes(a)
            ? editAssets.filter(x => x !== a)
            : [...editAssets, a])
    }

    const formatTvl = (v: number) => v >= 1_000_000 ? `$${(v / 1_000_000).toFixed(0)}M` : `$${(v / 1_000).toFixed(0)}K`

    // Slider row helper
    const SliderRow = ({ label, value, onChange, min, max, step, unit, inputProps }: {
        label: string; value: number; onChange: (v: number) => void
        min: number; max: number; step: number; unit?: string
        inputProps?: { min?: number; max?: number; step?: number }
    }) => (
        <div className="space-y-2">
            <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">{label}</span>
                <div className="flex items-center gap-1.5">
                    <Input type="number" value={value} step={inputProps?.step ?? step}
                        min={inputProps?.min ?? min} max={inputProps?.max ?? max}
                        onChange={e => { const v = parseFloat(e.target.value); if (!isNaN(v)) onChange(v) }}
                        className="w-16 h-7 text-xs text-center" />
                    {unit && <span className="text-[10px] text-muted-foreground w-6">{unit}</span>}
                </div>
            </div>
            <Slider value={[value]} onValueChange={([v]) => onChange(v)}
                min={min} max={max} step={step} className="w-full" />
        </div>
    )

    return (
        <DialogContent showCloseButton={false}
            className="sm:max-w-2xl max-h-[85vh] overflow-y-auto p-0 gap-0 bg-card border-border">

            {/* Header */}
            <DialogHeader className="px-6 pt-6 pb-4 border-b border-border">
                <div className="flex items-center justify-between">
                    <div>
                        <DialogTitle className="font-heading text-lg font-bold text-foreground">
                            {agent.name || `Agent ${agent.id?.slice(0, 8)}`}
                        </DialogTitle>
                        <DialogDescription className="text-xs mt-0.5">
                            {preset.charAt(0).toUpperCase() + preset.slice(1)} · {chain} ·{' '}
                            {deployedAt ? `Deployed ${new Date(deployedAt).toLocaleDateString()}` : 'Active'}
                        </DialogDescription>
                    </div>
                    <div className="flex items-center gap-2">
                        <Badge variant="outline" className={isActive ? 'border-green-500/30 text-green-500' : 'border-destructive/30 text-destructive'}>
                            <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${isActive ? 'bg-green-500' : 'bg-destructive'}`} />
                            {isActive ? 'Active' : 'Paused'}
                        </Badge>
                        <Button variant="outline" size="sm" onClick={onShare} className="h-8 text-xs">
                            <Share2 className="w-3.5 h-3.5 mr-1" /> Share
                        </Button>
                        <Button variant="ghost" size="sm" onClick={onClose} className="h-8 w-8 p-0">
                            <X className="w-4 h-4" />
                        </Button>
                    </div>
                </div>
            </DialogHeader>

            {/* Overview Stats */}
            <div className="px-6 py-3 border-b border-border">
                <div className="grid grid-cols-4 gap-2">
                    {[
                        { label: 'Pool Type', value: editPoolType, icon: <Droplets className="w-4 h-4 text-blue-400" /> },
                        { label: 'Vaults', value: `${editVaultCount}`, icon: <Lock className="w-4 h-4 text-primary" /> },
                        { label: 'Duration', value: editDuration === 0 ? '∞' : `${editDuration}d`, icon: <Timer className="w-4 h-4 text-cyan-400" /> },
                        { label: 'Risk', value: editRiskLevel, icon: editRiskLevel === 'high' ? <Flame className="w-4 h-4 text-red-400" /> : editRiskLevel === 'low' ? <Shield className="w-4 h-4 text-green-400" /> : <BarChart3 className="w-4 h-4 text-primary" /> },
                    ].map(m => (
                        <div key={m.label} className="flex items-center gap-2 p-2.5 rounded-lg bg-secondary/50">
                            <div className="p-1.5 rounded-md bg-secondary">{m.icon}</div>
                            <div>
                                <div className="text-xs font-heading font-semibold text-foreground capitalize">{m.value}</div>
                                <div className="text-[9px] text-muted-foreground uppercase tracking-wider">{m.label}</div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Tabbed Content */}
            <Tabs defaultValue="strategy" className="flex-1">
                <div className="px-6 pt-3 border-b border-border">
                    <TabsList className="w-full">
                        <TabsTrigger value="strategy" className="flex-1 text-xs font-heading">
                            <Settings className="w-3.5 h-3.5 mr-1.5" /> Strategy
                        </TabsTrigger>
                        <TabsTrigger value="execution" className="flex-1 text-xs font-heading">
                            <Activity className="w-3.5 h-3.5 mr-1.5" /> Execution
                        </TabsTrigger>
                        <TabsTrigger value="safety" className="flex-1 text-xs font-heading">
                            <Shield className="w-3.5 h-3.5 mr-1.5" /> Safety
                        </TabsTrigger>
                    </TabsList>
                </div>

                {/* ─── TAB: Strategy ─── */}
                <TabsContent value="strategy" className="px-6 py-4 space-y-5 m-0">
                    {/* Risk Level */}
                    <div>
                        <h4 className="text-xs font-heading font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                            Risk Level
                        </h4>
                        <div className="flex gap-2">
                            {(['low', 'medium', 'high'] as const).map(level => (
                                <Button key={level}
                                    variant={editRiskLevel === level ? 'default' : 'outline'}
                                    size="sm"
                                    onClick={() => setEditRiskLevel(level)}
                                    className={`flex-1 text-xs font-heading ${editRiskLevel === level
                                        ? level === 'low' ? 'bg-green-500 hover:bg-green-600 text-white'
                                            : level === 'high' ? 'bg-red-500 hover:bg-red-600 text-white'
                                                : 'bg-gradient-to-r from-primary to-yellow-500 text-primary-foreground'
                                        : ''}`}>
                                    {level === 'low' && <Shield className="w-3 h-3 mr-1" />}
                                    {level === 'medium' && <TrendingUp className="w-3 h-3 mr-1" />}
                                    {level === 'high' && <Flame className="w-3 h-3 mr-1" />}
                                    {level.charAt(0).toUpperCase() + level.slice(1)}
                                </Button>
                            ))}
                        </div>
                    </div>

                    {/* Pool Type */}
                    <div>
                        <h4 className="text-xs font-heading font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                            Pool Type
                        </h4>
                        <div className="flex gap-2">
                            {(['single', 'dual', 'both'] as const).map(pt => (
                                <Button key={pt}
                                    variant={editPoolType === pt ? 'default' : 'outline'}
                                    size="sm"
                                    onClick={() => {
                                        setEditPoolType(pt)
                                        // Auto-clean protocols not valid for new pool type
                                        const allowed = pt === 'single' ? [...SINGLE_PROTOCOLS, ...BOTH_PROTOCOLS]
                                            : pt === 'dual' ? [...DUAL_PROTOCOLS, ...BOTH_PROTOCOLS] : ALL_PROTOCOLS
                                        setEditProtocols(editProtocols.filter(p => allowed.includes(p)))
                                    }}
                                    className={`flex-1 text-xs font-heading ${editPoolType === pt
                                        ? 'bg-gradient-to-r from-primary to-yellow-500 text-primary-foreground' : ''}`}>
                                    {pt === 'single' ? 'Single-Sided' : pt === 'dual' ? 'Dual-Sided (LP)' : 'Both'}
                                </Button>
                            ))}
                        </div>
                    </div>

                    {/* APY Range */}
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <h4 className="text-xs font-heading font-semibold text-muted-foreground uppercase tracking-wider">
                                APY Target Range
                            </h4>
                            <span className="text-xs font-heading font-bold text-primary">
                                {editMinApy}% – {editMaxApy}%
                            </span>
                        </div>
                        <div className="space-y-3 p-3 rounded-lg bg-secondary/30">
                            <div className="flex items-center gap-3">
                                <span className="text-xs text-muted-foreground w-8">Min</span>
                                <Slider value={[editMinApy]}
                                    onValueChange={([v]) => setEditMinApy(Math.min(v, editMaxApy - 1))}
                                    min={1} max={100} step={1} className="flex-1" />
                                <Input type="number" value={editMinApy} onChange={e => setEditMinApy(+e.target.value)}
                                    className="w-16 h-7 text-xs text-center" />
                            </div>
                            <div className="flex items-center gap-3">
                                <span className="text-xs text-muted-foreground w-8">Max</span>
                                <Slider value={[editMaxApy]}
                                    onValueChange={([v]) => setEditMaxApy(Math.max(v, editMinApy + 1))}
                                    min={5} max={200} step={1} className="flex-1" />
                                <Input type="number" value={editMaxApy} onChange={e => setEditMaxApy(+e.target.value)}
                                    className="w-16 h-7 text-xs text-center" />
                            </div>
                        </div>
                    </div>

                    {/* TVL Range */}
                    <div className="space-y-3">
                        <h4 className="text-xs font-heading font-semibold text-muted-foreground uppercase tracking-wider">
                            Pool TVL Range
                        </h4>
                        <div className="space-y-3 p-3 rounded-lg bg-secondary/30">
                            <div className="flex items-center gap-3">
                                <span className="text-xs text-muted-foreground w-8">Min</span>
                                <Slider value={[editMinTvl]} onValueChange={([v]) => setEditMinTvl(Math.min(v, editMaxTvl))}
                                    min={100_000} max={50_000_000} step={100_000} className="flex-1" />
                                <Input type="text" value={formatTvl(editMinTvl)}
                                    onChange={e => { const n = parseFloat(e.target.value.replace(/[^0-9.]/g, '')) * (e.target.value.toLowerCase().includes('m') ? 1_000_000 : e.target.value.toLowerCase().includes('k') ? 1_000 : 1); if (!isNaN(n) && n >= 0) setEditMinTvl(n) }}
                                    className="w-16 h-7 text-xs text-center" />
                            </div>
                            <div className="flex items-center gap-3">
                                <span className="text-xs text-muted-foreground w-8">Max</span>
                                <Slider value={[editMaxTvl]} onValueChange={([v]) => setEditMaxTvl(Math.max(v, editMinTvl))}
                                    min={100_000} max={100_000_000} step={100_000} className="flex-1" />
                                <Input type="text" value={editMaxTvl >= 100_000_000 ? '∞' : formatTvl(editMaxTvl)}
                                    onChange={e => { const n = parseFloat(e.target.value.replace(/[^0-9.]/g, '')) * (e.target.value.toLowerCase().includes('m') ? 1_000_000 : e.target.value.toLowerCase().includes('k') ? 1_000 : 1); if (!isNaN(n) && n >= 0) setEditMaxTvl(n) }}
                                    className="w-16 h-7 text-xs text-center" />
                            </div>
                        </div>
                    </div>

                    <Separator />

                    {/* Protocols */}
                    <div>
                        <h4 className="text-xs font-heading font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                            Protocols
                        </h4>
                        <div className="flex flex-wrap gap-1.5">
                            {visibleProtocols.map(p => (
                                <Badge key={p}
                                    variant={editProtocols.includes(p) ? 'default' : 'outline'}
                                    className={`cursor-pointer text-xs transition-all ${editProtocols.includes(p)
                                        ? 'bg-primary/20 text-primary border-primary/40'
                                        : 'text-muted-foreground hover:text-foreground'}`}
                                    onClick={() => toggleProtocol(p)}>
                                    {editProtocols.includes(p) && <Check className="w-2.5 h-2.5 mr-0.5" />}
                                    {p}
                                </Badge>
                            ))}
                        </div>
                    </div>

                    {/* Assets */}
                    <div>
                        <h4 className="text-xs font-heading font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                            Preferred Assets
                        </h4>
                        <div className="flex flex-wrap gap-1.5">
                            {ALL_ASSETS.map(a => (
                                <Badge key={a}
                                    variant={editAssets.includes(a) ? 'default' : 'outline'}
                                    className={`cursor-pointer text-xs transition-all ${editAssets.includes(a)
                                        ? 'bg-primary/20 text-primary border-primary/40'
                                        : 'text-muted-foreground hover:text-foreground'}`}
                                    onClick={() => toggleAsset(a)}>
                                    {editAssets.includes(a) && <Check className="w-2.5 h-2.5 mr-0.5" />}
                                    {a}
                                </Badge>
                            ))}
                        </div>
                    </div>
                </TabsContent>

                {/* ─── TAB: Execution ─── */}
                <TabsContent value="execution" className="px-6 py-4 space-y-4 m-0">
                    <div className="space-y-4 p-4 rounded-lg bg-secondary/30">
                        <SliderRow label="Max Slippage" value={editSlippage} onChange={setEditSlippage}
                            min={0.1} max={3} step={0.1} unit="%" inputProps={{ step: 0.1 }} />
                        <Separator className="opacity-30" />
                        <SliderRow label="Compound Frequency" value={editCompoundFreq} onChange={setEditCompoundFreq}
                            min={1} max={30} step={1} unit="days" />
                        <Separator className="opacity-30" />
                        <SliderRow label="Rebalance Threshold" value={editRebalanceThreshold} onChange={setEditRebalanceThreshold}
                            min={1} max={25} step={1} unit="%" />
                        <Separator className="opacity-30" />
                        <SliderRow label="Max Gas Price" value={editMaxGas} onChange={setEditMaxGas}
                            min={1} max={100} step={1} unit="gwei" />
                        <Separator className="opacity-30" />
                        <SliderRow label="Max Allocation / Vault" value={editMaxAllocation} onChange={setEditMaxAllocation}
                            min={5} max={100} step={5} unit="%" />
                        <Separator className="opacity-30" />
                        <SliderRow label="Number of Vaults" value={editVaultCount} onChange={setEditVaultCount}
                            min={1} max={15} step={1} />
                        <Separator className="opacity-30" />
                        <SliderRow label="Duration" value={editDuration} onChange={setEditDuration}
                            min={0} max={365} step={1} unit={editDuration === 0 ? '∞' : 'days'} />
                    </div>

                    {/* APY Rotation Window */}
                    <div className="space-y-2">
                        <h4 className="text-xs font-heading font-semibold text-muted-foreground uppercase tracking-wider">
                            APY Rotation Window
                        </h4>
                        <div className="flex items-center gap-1.5 p-3 rounded-lg bg-secondary/30">
                            {[{ v: 12, l: '12h' }, { v: 24, l: '1d' }, { v: 72, l: '3d' }, { v: 168, l: '7d' }].map(opt => (
                                <button key={opt.v} onClick={() => setEditApyCheckHours(opt.v)}
                                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer ${editApyCheckHours === opt.v
                                        ? 'bg-primary/15 text-primary border border-primary/30'
                                        : 'bg-muted/50 text-muted-foreground hover:bg-muted border border-transparent'}`}>
                                    {opt.l}
                                </button>
                            ))}
                            <Input type="number" placeholder="Custom hrs"
                                value={[12, 24, 72, 168].includes(editApyCheckHours) ? '' : editApyCheckHours}
                                onChange={e => { const v = parseInt(e.target.value); if (v > 0) setEditApyCheckHours(v) }}
                                className="w-20 h-8 text-xs text-center" />
                        </div>
                    </div>
                </TabsContent>

                {/* ─── TAB: Safety ─── */}
                <TabsContent value="safety" className="px-6 py-4 space-y-3 m-0">
                    {[
                        { label: 'Emergency Exit', desc: 'Auto-exit positions on critical events', value: editEmergencyExit, set: setEditEmergencyExit, icon: <AlertTriangle className="w-4 h-4 text-red-400" /> },
                        { label: 'Avoid IL Exposure', desc: 'Skip pools with impermanent loss risk', value: editAvoidIL, set: setEditAvoidIL, icon: <Shield className="w-4 h-4 text-blue-400" /> },
                        { label: 'Audited Protocols Only', desc: 'Only use audited and verified protocols', value: editOnlyAudited, set: setEditOnlyAudited, icon: <Check className="w-4 h-4 text-green-400" /> },
                    ].map(toggle => (
                        <div key={toggle.label} className="flex items-center justify-between p-3.5 rounded-lg bg-secondary/50 border border-border/50">
                            <div className="flex items-center gap-3">
                                <div className="p-1.5 rounded-md bg-secondary">
                                    {toggle.icon}
                                </div>
                                <div>
                                    <div className="text-xs font-heading font-semibold text-foreground">{toggle.label}</div>
                                    <div className="text-[10px] text-muted-foreground">{toggle.desc}</div>
                                </div>
                            </div>
                            <Switch checked={toggle.value} onCheckedChange={toggle.set} />
                        </div>
                    ))}

                    {/* Pro Config (read-only) */}
                    {isPro && (
                        <>
                            <Separator className="my-2" />
                            <div>
                                <h4 className="text-xs font-heading font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1">
                                    <Zap className="w-3 h-3 text-primary" /> Pro Config
                                </h4>
                                <div className="grid grid-cols-2 gap-2">
                                    {[
                                        proConfig.leverage && proConfig.leverage > 1 && { label: 'Leverage', value: `${proConfig.leverage}x` },
                                        proConfig.stopLossEnabled && { label: 'Stop-Loss', value: `${proConfig.stopLossPercent || 20}%` },
                                        proConfig.takeProfitEnabled && { label: 'Take-Profit', value: `${proConfig.takeProfitAmount || 50}%` },
                                        proConfig.volatilityGuard != null && { label: 'Volatility Guard', value: proConfig.volatilityGuard ? 'On' : 'Off' },
                                        proConfig.mevProtection != null && { label: 'MEV Protection', value: proConfig.mevProtection ? 'On' : 'Off' },
                                        proConfig.harvestStrategy && { label: 'Harvest', value: proConfig.harvestStrategy },
                                    ].filter(Boolean).map((item: any) => (
                                        <div key={item.label} className="flex items-center justify-between p-2.5 rounded-lg bg-secondary/50 border border-border/50">
                                            <span className="text-[10px] text-muted-foreground">{item.label}</span>
                                            <span className="text-xs font-heading font-semibold text-foreground">{item.value}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </>
                    )}
                </TabsContent>
            </Tabs>

            {/* Footer */}
            <DialogFooter className="px-6 py-4 border-t border-border">
                <Button variant="outline" onClick={onClose} className="font-heading">
                    Cancel
                </Button>
                <Button onClick={onSave} disabled={saving}
                    className="bg-gradient-to-r from-primary to-yellow-500 text-primary-foreground font-heading font-semibold">
                    {saving ? (
                        <><Loader2 className="w-4 h-4 mr-1.5 animate-spin" /> Saving...</>
                    ) : (
                        <><Save className="w-4 h-4 mr-1.5" /> Save Changes</>
                    )}
                </Button>
            </DialogFooter>
        </DialogContent>
    )
}

// ─── Community Strategy Card ───
function CommunityCard({ strategy, index }: { strategy: CommunityStrategy; index: number }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
        >
            <Card className="h-full flex flex-col hover:border-primary/30 transition-all">
                <CardContent className="p-5 flex flex-col flex-1">
                    {/* Header */}
                    <div className="flex items-start justify-between mb-2">
                        <div>
                            <h3 className="font-heading text-base font-bold text-foreground">
                                {strategy.name}
                            </h3>
                            <p className="text-xs text-muted-foreground">
                                by {strategy.author}
                            </p>
                        </div>
                        <div className="text-right">
                            <span className="font-heading text-lg font-bold text-green-500">
                                {strategy.apy}
                            </span>
                            <p className="text-[10px] text-muted-foreground">30d</p>
                        </div>
                    </div>

                    {/* Description */}
                    <p className="text-sm mb-3 flex-1 text-muted-foreground">
                        {strategy.description}
                    </p>

                    {/* Tags + Stats */}
                    <div className="flex items-center gap-1.5 mb-3">
                        {strategy.tags.map(tag => (
                            <Badge key={tag} variant="secondary" className="text-[10px]">
                                {tag}
                            </Badge>
                        ))}
                        <span className="ml-auto flex items-center gap-1 text-xs text-muted-foreground">
                            <Users className="w-3 h-3" /> {strategy.copiers}
                        </span>
                        <span className="flex items-center gap-0.5 text-xs text-primary">
                            <Star className="w-3 h-3 fill-current" /> {strategy.rating}
                        </span>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2">
                        <Button size="sm"
                            className="flex-1 text-xs bg-gradient-to-r from-primary to-yellow-500 text-primary-foreground font-heading font-semibold">
                            <Copy className="w-3.5 h-3.5 mr-1" /> Copy Strategy
                        </Button>
                        <Button variant="outline" size="sm" className="text-xs">
                            <Eye className="w-3.5 h-3.5 mr-1" /> View
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </motion.div>
    )
}
