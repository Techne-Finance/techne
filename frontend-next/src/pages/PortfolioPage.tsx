/**
 * Portfolio Dashboard — Draggable panel system with dot-grid background
 * Trading-terminal-inspired layout: reorderable panels, visibility toolbar,
 * framer-motion Reorder, localStorage persistence
 */
import { useState, useCallback, useRef, useEffect, useMemo } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { DepositModal } from '@/components/modals/DepositModal'
import { WithdrawModal } from '@/components/modals/WithdrawModal'
import { motion, AnimatePresence, Reorder } from 'framer-motion'
import {
    PieChart, TrendingUp, Wallet, Activity, BarChart3, Shield, Terminal, Zap,
    GripVertical, ChevronDown, ChevronUp, Eye, EyeOff, RotateCcw, LayoutDashboard,
} from 'lucide-react'
import { useWalletStore } from '@/stores/walletStore'
import { formatUsd, createSessionKey, revokeSessionKey } from '@/lib/api'
import { useWebSocket } from '@/hooks/useWebSocket'
import {
    useAgentManagement, usePortfolioData, useQuickActions, useRiskIndicators,
} from '@/hooks/usePortfolio'
import {
    AgentSelector, AgentSidebar, RiskPanel, AllocationChart,
    PositionsTable, QuickActions, HoldingsTable, TransactionHistory,
    PerformanceChart, Toast,
} from '@/components/portfolio/PortfolioComponents'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

// ─── Panel Registry ───
const DEFAULT_PANEL_ORDER = ['stats', 'allocation', 'positions', 'performance', 'terminal', 'history']
const PANEL_META: Record<string, { label: string; icon: any }> = {
    stats: { label: 'Overview', icon: BarChart3 },
    allocation: { label: 'Allocation', icon: PieChart },
    positions: { label: 'Positions', icon: Activity },
    performance: { label: 'Performance', icon: TrendingUp },
    terminal: { label: 'Terminal', icon: Terminal },
    history: { label: 'History', icon: Wallet },
}
const STORAGE_KEY = 'techne_portfolio_layout'

export function PortfolioPage() {
    const { isConnected, address } = useWalletStore()
    const [txFilter, setTxFilter] = useState('all')
    const [chartPeriod, setChartPeriod] = useState('7d')
    const [depositOpen, setDepositOpen] = useState(false)
    const [withdrawOpen, setWithdrawOpen] = useState(false)

    // ─── Panel Layout State ───
    const [panelOrder, setPanelOrder] = useState<string[]>(() => {
        try {
            const saved = localStorage.getItem(STORAGE_KEY)
            if (saved) { const parsed = JSON.parse(saved); return parsed.order || DEFAULT_PANEL_ORDER }
        } catch { /* ignore */ }
        return DEFAULT_PANEL_ORDER
    })
    const [hiddenPanels, setHiddenPanels] = useState<Set<string>>(() => {
        try {
            const saved = localStorage.getItem(STORAGE_KEY)
            if (saved) { const parsed = JSON.parse(saved); return new Set(parsed.hidden || []) }
        } catch { /* ignore */ }
        return new Set()
    })
    const [collapsedPanels, setCollapsedPanels] = useState<Set<string>>(new Set())

    // Persist layout to localStorage
    useEffect(() => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({
            order: panelOrder, hidden: Array.from(hiddenPanels),
        }))
    }, [panelOrder, hiddenPanels])

    const togglePanelVisibility = (id: string) => {
        setHiddenPanels(prev => {
            const next = new Set(prev)
            next.has(id) ? next.delete(id) : next.add(id)
            return next
        })
    }
    const togglePanelCollapse = (id: string) => {
        setCollapsedPanels(prev => {
            const next = new Set(prev)
            next.has(id) ? next.delete(id) : next.add(id)
            return next
        })
    }
    const resetLayout = () => {
        setPanelOrder([...DEFAULT_PANEL_ORDER])
        setHiddenPanels(new Set())
        setCollapsedPanels(new Set())
        localStorage.removeItem(STORAGE_KEY)
    }

    // ─── Hooks ───
    const {
        agents, loadingAgents, selectedAgent, selectedAgentId,
        selectAgent, removeAgent, toggleAgent, emergencyPause,
        toast, showToast, refetchAgents: _refetchAgents,
    } = useAgentManagement()

    const {
        holdings, positions, totalValue, totalPnL, avgApy,
        trades, auditEntries, trustData, sessionData,
        loadingPortfolio: _loadingPortfolio, refetchPortfolio, refetchPositions,
    } = usePortfolioData(address || undefined, selectedAgent)

    const { harvest, rebalance, handleClosePosition, handleExportCSV, actionLoading } =
        useQuickActions(address || undefined, selectedAgent, showToast, refetchPortfolio, refetchPositions)

    const riskIndicators = useRiskIndicators(selectedAgent, positions)

    // ─── WebSocket (polling-based real-time updates) ───
    const agentAddr = selectedAgent?.agent_address || selectedAgent?.address || ''
    const ws = useWebSocket({
        walletAddress: address || undefined,
        agentAddress: agentAddr || undefined,
        interval: 30_000,
        enabled: isConnected,
    })

    // ─── Session Key Management ───
    const queryClient = useQueryClient()
    const [sessionKeyLoading, setSessionKeyLoading] = useState(false)

    const handleCreateSessionKey = useCallback(async () => {
        if (!address || !agentAddr) { showToast('No agent selected', 'warning'); return }
        setSessionKeyLoading(true)
        try {
            const res = await createSessionKey({ agent_address: agentAddr, user_address: address })
            if (res.success) {
                showToast('Session key created', 'success')
                queryClient.invalidateQueries({ queryKey: ['session-key', agentAddr] })
            } else {
                showToast(res.error || 'Failed to create session key', 'error')
            }
        } catch { showToast('Session key creation submitted', 'success') }
        setSessionKeyLoading(false)
    }, [address, agentAddr, showToast, queryClient])

    const handleRevokeSessionKey = useCallback(async () => {
        if (!address || !agentAddr) return
        if (!confirm('Revoke session key? Your agent will need a new key to execute trades.')) return
        setSessionKeyLoading(true)
        try {
            const res = await revokeSessionKey({ agent_address: agentAddr, user_address: address })
            if (res.success) {
                showToast('Session key revoked', 'warning')
                queryClient.invalidateQueries({ queryKey: ['session-key', agentAddr] })
            } else {
                showToast(res.error || 'Failed to revoke', 'error')
            }
        } catch { showToast('Revoke submitted', 'warning') }
        setSessionKeyLoading(false)
    }, [address, agentAddr, showToast, queryClient])

    // ─── Not Connected ───
    if (!isConnected) {
        return (
            <div className="flex flex-col items-center justify-center py-24">
                <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                    className="w-20 h-20 rounded-2xl flex items-center justify-center mb-5 bg-accent border border-primary/20 shadow-[0_0_20px_rgba(212,168,83,0.15)]">
                    <Wallet className="w-10 h-10 text-primary" />
                </motion.div>
                <h2 className="font-heading text-xl font-bold mb-2 text-foreground">
                    Connect Your Wallet
                </h2>
                <p className="text-sm max-w-sm text-center text-muted-foreground">
                    Connect your wallet to view portfolio performance, manage agents, and track positions.
                </p>
                <Button className="mt-5 bg-gradient-to-r from-primary to-[var(--color-gold-bright)] text-primary-foreground font-heading font-semibold">
                    <Wallet className="w-4 h-4 mr-2" /> Connect Wallet
                </Button>
            </div>
        )
    }

    const pnlPercent = totalValue > 0 ? (totalPnL / totalValue * 100) : 0
    const activePositions = positions.filter(p => p.deposited > 0)

    // Panel content registry
    const renderPanel = (id: string) => {
        switch (id) {
            case 'stats': return (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <StatCard icon={PieChart} label="Total Value" value={formatUsd(totalValue)} />
                    <StatCard icon={TrendingUp} label="Total P&L"
                        value={`${totalPnL >= 0 ? '+' : ''}$${Math.abs(totalPnL).toFixed(2)}`}
                        sub={`${pnlPercent >= 0 ? '+' : ''}${pnlPercent.toFixed(1)}%`}
                        color={totalPnL >= 0 ? 'text-green-500' : 'text-destructive'} />
                    <StatCard icon={BarChart3} label="Avg APY" value={`${avgApy.toFixed(1)}%`} gold />
                    <StatCard icon={Activity} label="Positions" value={`${activePositions.length} Active`} />
                </div>
            )
            case 'allocation': return (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <Card className="border-primary/20 shadow-[0_0_20px_rgba(212,168,83,0.1)] relative">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-heading">Allocation</CardTitle>
                        </CardHeader>
                        <CardContent className="relative">
                            <AllocationChart holdings={holdings} positions={positions} />
                        </CardContent>
                    </Card>
                    <div className="lg:col-span-2">
                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-heading">Asset Holdings</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <HoldingsTable holdings={holdings} />
                            </CardContent>
                        </Card>
                    </div>
                </div>
            )
            case 'positions': return (
                <Card>
                    <CardContent className="pt-4">
                        <PositionsTable positions={positions} onClose={handleClosePosition} loading={actionLoading} />
                    </CardContent>
                </Card>
            )
            case 'performance': return (
                <Card>
                    <CardContent className="pt-4">
                        <PerformanceChart totalValue={totalValue} period={chartPeriod} onPeriodChange={setChartPeriod} />
                    </CardContent>
                </Card>
            )
            case 'terminal': return (
                <NeuralTerminal auditEntries={auditEntries} trades={trades} agent={selectedAgent} />
            )
            case 'history': return (
                <Card>
                    <CardContent className="pt-4">
                        <TransactionHistory trades={trades} filter={txFilter} onFilterChange={setTxFilter} />
                    </CardContent>
                </Card>
            )
            default: return null
        }
    }

    return (
        <div className="relative"
            style={{
                backgroundImage: `
                    radial-gradient(circle, rgba(212,168,83,0.12) 1px, transparent 1px),
                    linear-gradient(rgba(212,168,83,0.03) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(212,168,83,0.03) 1px, transparent 1px)
                `,
                backgroundSize: '24px 24px, 24px 24px, 24px 24px',
            }}>
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <div>
                    <h1 className="font-heading text-2xl font-bold mb-0.5 text-foreground">
                        Portfolio
                    </h1>
                    <p className="text-xs text-muted-foreground flex items-center gap-2">
                        {address ? `${address.slice(0, 6)}...${address.slice(-4)}` : 'Dashboard'}
                        {ws.isConnected && (
                            <span className="flex items-center gap-1 text-green-500">
                                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                                Live
                            </span>
                        )}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button onClick={() => setDepositOpen(true)}
                        className="bg-gradient-to-r from-primary to-[var(--color-gold-bright)] text-primary-foreground font-heading font-semibold text-xs h-9">
                        <Shield className="w-3.5 h-3.5 mr-1.5" /> Fund Agent
                    </Button>
                    <Button variant="outline" onClick={() => setWithdrawOpen(true)}
                        className="font-heading font-semibold text-xs h-9">
                        <Wallet className="w-3.5 h-3.5 mr-1.5" /> Withdraw
                    </Button>
                    <QuickActions onHarvest={harvest} onRebalance={rebalance} onExportCSV={handleExportCSV} loading={actionLoading} />
                </div>
            </div>

            {/* ─── Panel Toolbar ─── */}
            <div className="flex items-center gap-2 mb-4 px-3 py-2 rounded-lg overflow-x-auto"
                style={{
                    background: 'var(--color-glass, rgba(22,22,26,0.6))',
                    border: '1px solid rgba(255,255,255,0.06)',
                    backdropFilter: 'blur(8px)',
                }}>
                <LayoutDashboard className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                <span className="text-[10px] uppercase tracking-widest text-muted-foreground font-heading font-semibold flex-shrink-0 mr-1">Panels</span>

                {DEFAULT_PANEL_ORDER.map(id => {
                    const meta = PANEL_META[id]
                    const Icon = meta.icon
                    const isHidden = hiddenPanels.has(id)
                    return (
                        <button key={id} onClick={() => togglePanelVisibility(id)}
                            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium cursor-pointer transition-all flex-shrink-0"
                            style={{
                                background: isHidden ? 'rgba(255,255,255,0.03)' : 'rgba(212,168,83,0.08)',
                                border: isHidden ? '1px solid rgba(255,255,255,0.06)' : '1px solid rgba(212,168,83,0.2)',
                                color: isHidden ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.8)',
                                opacity: isHidden ? 0.5 : 1,
                            }}>
                            <Icon className="w-3 h-3" />
                            {meta.label}
                            {isHidden ? <EyeOff className="w-2.5 h-2.5 ml-0.5" /> : <Eye className="w-2.5 h-2.5 ml-0.5" />}
                        </button>
                    )
                })}

                <div className="flex-1" />
                <button onClick={resetLayout}
                    className="flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium cursor-pointer transition-all flex-shrink-0"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.4)' }}>
                    <RotateCcw className="w-2.5 h-2.5" /> Reset
                </button>
            </div>

            {/* Main Grid: Content + Sidebar */}
            <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
                {/* ─── Main Content (3 cols) — Reorderable Panels ─── */}
                <div className="xl:col-span-3">
                    <Reorder.Group axis="y" values={panelOrder} onReorder={setPanelOrder} className="space-y-4">
                        {panelOrder.map(id => {
                            if (hiddenPanels.has(id)) return null
                            const meta = PANEL_META[id]
                            if (!meta) return null
                            const Icon = meta.icon
                            const isCollapsed = collapsedPanels.has(id)

                            return (
                                <Reorder.Item key={id} value={id}
                                    initial={{ opacity: 0, y: 8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -8 }}
                                    transition={{ duration: 0.2 }}
                                    className="list-none">
                                    {/* Panel Header — drag handle */}
                                    <div className="flex items-center gap-2 mb-1.5 px-1 group">
                                        <div className="cursor-grab active:cursor-grabbing p-0.5 rounded hover:bg-white/5 transition-colors">
                                            <GripVertical className="w-3.5 h-3.5 text-muted-foreground/30 group-hover:text-primary/50 transition-colors" />
                                        </div>
                                        <Icon className="w-3 h-3 text-muted-foreground/50" />
                                        <span className="text-[10px] uppercase tracking-widest text-muted-foreground/50 font-heading font-semibold">
                                            {meta.label}
                                        </span>
                                        <div className="flex-1" />
                                        <button onClick={() => togglePanelCollapse(id)}
                                            className="p-0.5 rounded hover:bg-white/5 cursor-pointer transition-colors opacity-0 group-hover:opacity-100">
                                            {isCollapsed
                                                ? <ChevronDown className="w-3 h-3 text-muted-foreground/40" />
                                                : <ChevronUp className="w-3 h-3 text-muted-foreground/40" />}
                                        </button>
                                        <button onClick={() => togglePanelVisibility(id)}
                                            className="p-0.5 rounded hover:bg-white/5 cursor-pointer transition-colors opacity-0 group-hover:opacity-100">
                                            <EyeOff className="w-3 h-3 text-muted-foreground/40" />
                                        </button>
                                    </div>

                                    {/* Panel Content */}
                                    <AnimatePresence initial={false}>
                                        {!isCollapsed && (
                                            <motion.div
                                                initial={{ height: 0, opacity: 0 }}
                                                animate={{ height: 'auto', opacity: 1 }}
                                                exit={{ height: 0, opacity: 0 }}
                                                transition={{ duration: 0.2 }}>
                                                {renderPanel(id)}
                                            </motion.div>
                                        )}
                                    </AnimatePresence>
                                </Reorder.Item>
                            )
                        })}
                    </Reorder.Group>
                </div>

                {/* ─── Sidebar (1 col) ─── */}
                <div className="space-y-4">
                    {/* Agent Selector */}
                    <motion.div initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }}>
                        <Card className="border-primary/20 shadow-[0_0_20px_rgba(212,168,83,0.1)]">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-heading flex items-center gap-1.5">
                                    <Shield className="w-4 h-4 text-primary" /> Agent
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <AgentSelector agents={agents} selectedId={selectedAgentId} onSelect={selectAgent}
                                    onDelete={removeAgent} loading={loadingAgents} />
                            </CardContent>
                        </Card>
                    </motion.div>

                    {/* Agent Info */}
                    <motion.div initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.05 }}>
                        <Card>
                            <CardContent className="pt-4">
                                <AgentSidebar agent={selectedAgent} sessionData={sessionData} trustData={trustData}
                                    onToggle={toggleAgent} onEmergencyPause={emergencyPause}
                                    onCreateSessionKey={handleCreateSessionKey}
                                    onRevokeSessionKey={handleRevokeSessionKey}
                                    sessionKeyLoading={sessionKeyLoading} />
                            </CardContent>
                        </Card>
                    </motion.div>

                    {/* Risk Indicators */}
                    <motion.div initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }}>
                        <Card>
                            <CardContent className="pt-4">
                                <RiskPanel indicators={riskIndicators} />
                            </CardContent>
                        </Card>
                    </motion.div>

                    {/* Audit Log */}
                    <motion.div initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.15 }}>
                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-xs font-heading">Audit Log</CardTitle>
                            </CardHeader>
                            <CardContent>
                                {auditEntries.length === 0 ? (
                                    <div className="text-[10px] py-3 text-center text-muted-foreground">
                                        No transactions yet
                                    </div>
                                ) : (
                                    <div className="space-y-1">
                                        {auditEntries.slice(0, 8).map((e: any, i: number) => (
                                            <div key={i} className="flex items-center justify-between py-1.5 text-[10px] border-b border-border last:border-0">
                                                <span className="text-foreground">
                                                    {e.action_type || 'action'}
                                                </span>
                                                <div className="flex gap-2">
                                                    {e.value_usd && <span className="text-green-500">${e.value_usd.toFixed(2)}</span>}
                                                    <span className="text-muted-foreground">
                                                        {e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : ''}
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </motion.div>
                </div>
            </div>

            {/* Modals */}
            <DepositModal isOpen={depositOpen} onClose={() => setDepositOpen(false)} />
            <WithdrawModal isOpen={withdrawOpen} onClose={() => setWithdrawOpen(false)} />

            {/* Toast */}
            <Toast toast={toast} />
        </div>
    )
}

// ─── Stat Card ───
function StatCard({ icon: Icon, label, value, sub, gold, color }: {
    icon: any; label: string; value: string; sub?: string; gold?: boolean; color?: string;
}) {
    return (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
            <Card className={gold ? 'border-primary/20 shadow-[0_0_20px_rgba(212,168,83,0.1)]' : ''}>
                <CardContent className="p-3.5">
                    <div className="flex items-center gap-1.5 mb-1.5">
                        <Icon className={`w-3.5 h-3.5 ${gold ? 'text-primary' : 'text-muted-foreground'}`} />
                        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</span>
                    </div>
                    <div className={`text-xl font-heading font-bold ${color || (gold ? 'text-primary' : 'text-foreground')}`}>
                        {value}
                    </div>
                    {sub && <div className={`text-xs mt-0.5 ${color || ''}`}>{sub}</div>}
                </CardContent>
            </Card>
        </motion.div>
    )
}

// ─── Neural Terminal ───
function NeuralTerminal({ auditEntries, trades, agent }: {
    auditEntries: any[]; trades: any[]; agent: any
}) {
    const scrollRef = useRef<HTMLDivElement>(null)

    const lines = useMemo(() => {
        const allLines: { time: number; type: string; text: string }[] = []

        auditEntries.forEach((e: any) => {
            const ts = new Date(e.timestamp || e.created_at || Date.now()).getTime()
            const action = (e.action_type || e.action || 'event').toLowerCase()
            let lineType = 'system'
            if (action.includes('deposit') || action.includes('harvest') || action.includes('compound')) lineType = 'success'
            else if (action.includes('exit') || action.includes('withdraw') || action.includes('error') || action.includes('stop')) lineType = 'error'
            else if (action.includes('rebalance') || action.includes('swap') || action.includes('rotate')) lineType = 'info'
            else if (action.includes('scan') || action.includes('check') || action.includes('monitor')) lineType = 'agent'

            const value = e.value_usd ? ` ($${e.value_usd.toFixed(2)})` : ''
            const protocol = e.protocol ? ` [${e.protocol}]` : ''
            allLines.push({ time: ts, type: lineType, text: `${e.action_type || e.action || 'event'}${protocol}${value}` })
        })

        trades.forEach((t: any) => {
            const ts = new Date(t.timestamp || t.created_at || Date.now()).getTime()
            const action = (t.action || t.type || 'trade').toLowerCase()
            let lineType = 'system'
            if (action.includes('deposit') || action.includes('buy') || action.includes('open')) lineType = 'success'
            else if (action.includes('withdraw') || action.includes('sell') || action.includes('close')) lineType = 'error'
            else if (action.includes('swap') || action.includes('rebalance')) lineType = 'info'

            const value = t.amount_usd || t.value_usd ? ` $${(t.amount_usd || t.value_usd).toFixed(2)}` : ''
            const pair = t.pair || t.pool_name || ''
            allLines.push({ time: ts, type: lineType, text: `${t.action || t.type || 'trade'} ${pair}${value}`.trim() })
        })

        allLines.sort((a, b) => a.time - b.time)

        if (allLines.length === 0) {
            const now = Date.now()
            return [
                { time: now - 60000, type: 'system', text: 'neural-terminal v2.0 initialized' },
                { time: now - 50000, type: 'agent', text: 'connecting to agent scheduler...' },
                { time: now - 40000, type: 'system', text: 'awaiting agent activity — deploy an agent to see live feed' },
            ]
        }
        return allLines
    }, [auditEntries, trades])

    useEffect(() => {
        if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }, [lines])

    const fmt = (ts: number) => new Date(ts).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })

    const color = (t: string) => {
        if (t === 'success') return '#22c55e'
        if (t === 'error') return '#ef4444'
        if (t === 'info') return '#22d3ee'
        if (t === 'agent') return '#d4a853'
        return 'rgba(255,255,255,0.55)'
    }

    const prefix = (t: string) => {
        if (t === 'success') return '✓ '
        if (t === 'error') return '✗ '
        if (t === 'info') return '↻ '
        if (t === 'agent') return '◈ '
        return '› '
    }

    const agentName = agent?.name || agent?.preset || 'techne-agent'

    return (
        <div className="rounded-xl overflow-hidden" style={{ border: '1px solid rgba(160,120,48,0.4)', background: 'rgba(0,0,0,0.95)' }}>
            {/* Terminal Header */}
            <div className="px-4 py-2.5 flex items-center justify-between" style={{ borderBottom: '1px solid rgba(160,120,48,0.2)', background: 'rgba(0,0,0,0.6)' }}>
                <div className="flex items-center gap-2.5">
                    <Zap className="w-3.5 h-3.5" style={{ color: '#A07830' }} />
                    <span className="font-mono text-xs font-bold tracking-wider" style={{ color: '#A07830' }}>NEURAL TERMINAL</span>
                    <span className="text-[10px] font-mono" style={{ color: 'rgba(160,120,48,0.5)' }}>— {agentName}</span>
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold"
                        style={{
                            color: '#22C55E',
                            background: 'rgba(34,197,94,0.05)',
                            border: '1px solid rgba(34,197,94,0.15)',
                        }}>
                        LIVE
                    </span>
                </div>
                <div className="flex items-center gap-1.5">
                    <Badge variant="outline" className="text-[9px] px-1.5 py-0 h-4 font-mono border-[#A07830]/20" style={{ color: 'rgba(160,120,48,0.6)' }}>
                        {lines.length} events
                    </Badge>
                    <button className="text-[10px] px-1 py-0.5 rounded cursor-pointer" style={{ color: '#555', background: 'transparent', border: '1px solid #2a2a2a' }}>_</button>
                    <button className="text-[10px] px-1 py-0.5 rounded cursor-pointer" style={{ color: '#555', background: 'transparent', border: '1px solid #2a2a2a' }}>⌘</button>
                </div>
            </div>

            {/* Terminal Body */}
            <div ref={scrollRef}
                className="relative overflow-y-auto font-mono text-[11px] leading-relaxed px-4 py-3"
                style={{
                    background: 'rgba(0,0,0,0.95)',
                    height: '260px',
                    scrollbarWidth: 'thin',
                    scrollbarColor: 'rgba(160,120,48,0.15) transparent',
                }}>
                {/* Subtle CRT scanlines */}
                <div className="pointer-events-none absolute inset-0 z-10"
                    style={{
                        background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(160,120,48,0.015) 2px, rgba(160,120,48,0.015) 4px)',
                    }} />

                <div className="relative z-20">
                    <AnimatePresence>
                        {lines.map((line, i) => (
                            <motion.div key={i} initial={{ opacity: 0, x: -4 }} animate={{ opacity: 1, x: 0 }}
                                transition={{ duration: 0.15 }}
                                className="flex gap-2 hover:bg-white/[0.02] px-1 -mx-1 rounded mb-0.5">
                                <span className="select-none flex-shrink-0" style={{ minWidth: '62px', color: 'rgba(160,120,48,0.3)' }}>
                                    {fmt(line.time)}
                                </span>
                                <span style={{ color: color(line.type) }}>
                                    {prefix(line.type)}{line.text}
                                </span>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                    {/* Green hacker cursor */}
                    <div className="flex gap-2 px-1 -mx-1 mt-1">
                        <span style={{ minWidth: '62px', color: 'rgba(160,120,48,0.3)' }} className="select-none">
                            {fmt(Date.now())}
                        </span>
                        <span className="flex items-center gap-1">
                            <span style={{ color: '#A07830' }}>&gt;</span>
                            <span style={{ color: '#00FF41', opacity: 0.4 }} className="animate-pulse">█</span>
                        </span>
                    </div>
                </div>
            </div>
        </div>
    )
}
