/**
 * Portfolio sub-components — rewritten with shadcn/ui
 * Agent sidebar, Positions table, Risk panel, Donut chart, Tx history
 */
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    Shield, ChevronDown, Trash2, Copy, Check, AlertTriangle, Power,
    RefreshCw, Download, ExternalLink, Eye, EyeOff,
    Zap, TrendingUp, Clock, KeyRound, Loader2,
} from 'lucide-react'
import { PieChart as RechartsPie, Pie, Cell, ResponsiveContainer, Tooltip as RTooltip } from 'recharts'
import { formatUsd } from '@/lib/api'
import type { Agent, Holding, Position, Transaction } from '@/hooks/usePortfolio'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
    Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from '@/components/ui/tooltip'

const PIE_COLORS = ['#22c55e', '#d4a853', '#3b82f6', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4']

// ─── Agent Selector ───
export function AgentSelector({ agents, selectedId, onSelect, onDelete, loading }: {
    agents: Agent[]; selectedId: string | null; onSelect: (id: string) => void;
    onDelete: (id: string) => void; loading: boolean;
}) {
    const [open, setOpen] = useState(false)
    if (loading) return (
        <div className="flex items-center gap-2 text-xs text-muted-foreground animate-pulse py-2">
            <RefreshCw className="w-3 h-3 animate-spin" /> Loading agents...
        </div>
    )
    if (!agents.length) return (
        <div className="text-center py-4 text-xs text-muted-foreground">
            No agents deployed. Go to <b className="text-primary">Build</b> to create one.
        </div>
    )
    const sel = agents.find(a => a.id === selectedId) || agents[0]
    const isActive = sel.isActive || sel.is_active
    return (
        <div className="relative">
            <Button variant="outline" onClick={() => setOpen(!open)}
                className="w-full justify-between h-auto py-2.5 px-3">
                <span className="flex items-center gap-2 text-sm">
                    <span className={`w-2 h-2 rounded-full ${isActive ? 'bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.5)]' : 'bg-muted-foreground'}`} />
                    {sel.name || sel.preset?.replace(/-/g, ' ') || `Agent ${sel.id.slice(0, 6)}`}
                </span>
                <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
            </Button>
            <AnimatePresence>
                {open && (
                    <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }}
                        className="absolute z-30 w-full mt-1 rounded-lg overflow-hidden border border-border bg-popover shadow-lg">
                        {agents.map(a => {
                            const active = a.isActive || a.is_active
                            return (
                                <div key={a.id}
                                    className={`flex items-center justify-between px-3 py-2.5 text-sm cursor-pointer transition-colors hover:bg-accent ${a.id === selectedId ? 'bg-accent' : ''}`}
                                    onClick={() => { onSelect(a.id); setOpen(false) }}>
                                    <span className="flex items-center gap-2">
                                        <span className={`w-2 h-2 rounded-full ${active ? 'bg-green-500' : 'bg-muted-foreground'}`} />
                                        {a.name || a.preset?.replace(/-/g, ' ') || `Agent ${a.id.slice(0, 6)}`}
                                    </span>
                                    <TooltipProvider>
                                        <Tooltip>
                                            <TooltipTrigger asChild>
                                                <button onClick={e => { e.stopPropagation(); onDelete(a.id) }}
                                                    className="p-1 rounded hover:bg-destructive/20 cursor-pointer transition-colors">
                                                    <Trash2 className="w-3 h-3 text-destructive" />
                                                </button>
                                            </TooltipTrigger>
                                            <TooltipContent>Delete Agent</TooltipContent>
                                        </Tooltip>
                                    </TooltipProvider>
                                </div>
                            )
                        })}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}

// ─── Agent Sidebar Info ───
export function AgentSidebar({ agent, sessionData, trustData, onToggle, onEmergencyPause, onCreateSessionKey, onRevokeSessionKey, sessionKeyLoading }: {
    agent: Agent | null; sessionData?: any; trustData?: any;
    onToggle: (active: boolean) => void; onEmergencyPause: () => void;
    onCreateSessionKey?: () => void; onRevokeSessionKey?: () => void; sessionKeyLoading?: boolean;
}) {
    const [copied, setCopied] = useState(false)
    const [showKey, setShowKey] = useState(false)
    if (!agent) return (
        <div className="py-8 text-center text-xs text-muted-foreground">
            <Shield className="w-8 h-8 mx-auto mb-2 opacity-30" /> No agent selected
        </div>
    )
    const isActive = agent.isActive || agent.is_active
    const addr = agent.agent_address || agent.address || ''
    const shortAddr = addr ? `${addr.slice(0, 6)}...${addr.slice(-4)}` : 'Not deployed'
    const strategy = agent.preset?.replace(/-/g, ' ') || 'Custom'
    const deployedAt = agent.deployedAt || agent.deployed_at
    let lastAction = 'Active'
    if (deployedAt) {
        const mins = Math.floor((Date.now() - new Date(deployedAt).getTime()) / 60000)
        lastAction = mins < 1 ? 'Just deployed' : mins < 60 ? `${mins}m ago` : `${Math.floor(mins / 60)}h ago`
    }
    const copyAddr = () => {
        navigator.clipboard.writeText(addr); setCopied(true); setTimeout(() => setCopied(false), 1500)
    }

    return (
        <div className="space-y-3">
            {/* Status + Toggle */}
            <div className="flex items-center justify-between">
                <Badge variant={isActive ? 'default' : 'secondary'}
                    className={isActive ? 'bg-green-500/15 text-green-500 border-green-500/30 hover:bg-green-500/20' : ''}>
                    <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${isActive ? 'bg-green-500 animate-pulse' : 'bg-muted-foreground'}`} />
                    {isActive ? 'Active' : 'Paused'}
                </Badge>
                <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">{isActive ? 'On' : 'Off'}</span>
                    <Switch checked={!!isActive} onCheckedChange={onToggle}
                        className="data-[state=checked]:bg-green-500" />
                </div>
            </div>

            <Separator />

            {/* Details */}
            <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                    <span className="text-muted-foreground">Address</span>
                    <span className="flex items-center gap-1 cursor-pointer text-foreground hover:text-primary transition-colors" onClick={copyAddr}>
                        {shortAddr}
                        {copied ? <Check className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3 opacity-40" />}
                    </span>
                </div>
                <div className="flex justify-between">
                    <span className="text-muted-foreground">Strategy</span>
                    <span className="text-foreground capitalize">{strategy}</span>
                </div>
                <div className="flex justify-between">
                    <span className="text-muted-foreground">Last Action</span>
                    <span className="text-foreground flex items-center gap-1">
                        <Clock className="w-3 h-3 text-muted-foreground" /> {lastAction}
                    </span>
                </div>
            </div>

            {/* Session Key */}
            <Separator />
            <div>
                <div className="flex items-center justify-between text-xs mb-1.5">
                    <span className="text-muted-foreground flex items-center gap-1">
                        <KeyRound className="w-3 h-3" /> Session Key
                    </span>
                    <Badge variant="outline" className={sessionData?.has_session_key
                        ? 'bg-green-500/15 text-green-500 border-green-500/30 text-[10px]'
                        : 'text-[10px]'}>
                        {sessionData?.has_session_key ? 'Active' : 'No Key'}
                    </Badge>
                </div>
                {sessionData?.has_session_key ? (
                    <div className="space-y-1.5">
                        <div className="flex gap-1.5">
                            <Button variant="ghost" size="sm"
                                onClick={() => setShowKey(!showKey)}
                                className="text-xs h-7 px-2 text-primary hover:text-primary/80 flex-1">
                                {showKey ? <><EyeOff className="w-3 h-3 mr-1" /> Hide</> : <><Eye className="w-3 h-3 mr-1" /> View Key</>}
                            </Button>
                            <Button variant="ghost" size="sm"
                                onClick={onRevokeSessionKey}
                                disabled={sessionKeyLoading}
                                className="text-xs h-7 px-2 text-destructive hover:text-destructive/80 hover:bg-destructive/10">
                                {sessionKeyLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Revoke'}
                            </Button>
                        </div>
                        {showKey && sessionData.session_key_address && (
                            <div className="p-2 rounded-lg bg-secondary text-[10px] break-all text-muted-foreground font-mono">
                                {sessionData.session_key_address}
                            </div>
                        )}
                    </div>
                ) : (
                    <Button variant="outline" size="sm"
                        onClick={onCreateSessionKey}
                        disabled={sessionKeyLoading}
                        className="w-full text-xs h-7 mt-1 text-primary border-primary/30 hover:bg-primary/10">
                        {sessionKeyLoading ? (
                            <><Loader2 className="w-3 h-3 mr-1 animate-spin" /> Creating...</>
                        ) : (
                            <><KeyRound className="w-3 h-3 mr-1" /> Create Session Key</>
                        )}
                    </Button>
                )}
            </div>

            {/* ERC-8004 Trust */}
            {trustData?.registered && (
                <>
                    <Separator />
                    <div>
                        <div className="text-xs font-semibold mb-2 text-primary flex items-center gap-1.5">
                            <Shield className="w-3.5 h-3.5" /> ERC-8004 Identity
                        </div>
                        <div className="space-y-1.5 text-xs">
                            <div className="flex justify-between">
                                <span className="text-muted-foreground">Token ID</span>
                                <Badge variant="outline" className="text-[10px]">#{trustData.token_id}</Badge>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-muted-foreground">Trust</span>
                                <span className="text-green-500 font-medium">{trustData.trust_score?.toFixed(1)}%</span>
                            </div>
                            <Progress value={trustData.trust_score || 0}
                                className="h-1.5 bg-secondary [&>div]:bg-gradient-to-r [&>div]:from-green-500 [&>div]:to-primary" />
                        </div>
                    </div>
                </>
            )}

            {/* Emergency Pause */}
            <Button variant="destructive" onClick={onEmergencyPause}
                className="w-full mt-2 bg-destructive/12 text-destructive border border-destructive/25 hover:bg-destructive/20">
                <AlertTriangle className="w-3.5 h-3.5 mr-1.5" /> Emergency Pause All
            </Button>
        </div>
    )
}

// ─── Risk Indicators Panel ───
export function RiskPanel({ indicators }: {
    indicators: { ilRisk: string; stopLoss: string; volatility: string; apyAlert: string; overall: string; overallClass: string };
}) {
    const riskVariant = (v: string): 'destructive' | 'default' | 'secondary' | 'outline' => {
        if (['High', 'Active', 'PAUSED', 'Spike Detected!'].includes(v)) return 'destructive'
        if (v === 'Medium') return 'default'
        if (['OK', 'Low', 'None'].includes(v) || v.includes('Active')) return 'secondary'
        return 'outline'
    }
    const badgeClass = indicators.overallClass === 'high'
        ? 'bg-destructive/15 text-destructive border-destructive/30'
        : indicators.overallClass === 'medium'
            ? 'bg-yellow-500/15 text-yellow-500 border-yellow-500/30'
            : 'bg-green-500/15 text-green-500 border-green-500/30'

    return (
        <div className="space-y-2.5">
            <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                    <Shield className="w-3.5 h-3.5 text-primary" /> Risk Indicators
                </span>
                <Badge variant="outline" className={`text-[10px] ${badgeClass}`}>
                    {indicators.overall}
                </Badge>
            </div>
            {[
                { label: 'IL Risk', value: indicators.ilRisk },
                { label: 'Stop Loss', value: indicators.stopLoss },
                { label: 'Volatility Guard', value: indicators.volatility },
                { label: 'APY Alert', value: indicators.apyAlert },
            ].map(r => {
                const color = riskVariant(r.value) === 'destructive' ? 'text-destructive'
                    : riskVariant(r.value) === 'default' ? 'text-yellow-500'
                        : 'text-green-500'
                return (
                    <div key={r.label} className="flex justify-between text-xs">
                        <span className="text-muted-foreground">{r.label}</span>
                        <span className={`font-medium ${color}`}>{r.value}</span>
                    </div>
                )
            })}
        </div>
    )
}

// ─── Allocation Donut Chart ───
export function AllocationChart({ holdings, positions }: { holdings: Holding[]; positions: Position[] }) {
    const data = [
        ...holdings.filter(h => h.value > 0.10).map(h => ({ name: h.asset, value: h.value })),
        ...positions.filter(p => p.current > 0.10).map(p => ({ name: `LP: ${p.pool_name || p.protocol}`, value: p.current })),
    ]
    const total = data.reduce((s, d) => s + d.value, 0)
    if (total <= 0) return (
        <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">No allocation data</div>
    )
    return (
        <>
            <ResponsiveContainer width="100%" height={190}>
                <RechartsPie>
                    <Pie data={data} cx="50%" cy="50%" innerRadius={55} outerRadius={78} paddingAngle={2} dataKey="value">
                        {data.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                    </Pie>
                    <RTooltip contentStyle={{
                        background: 'var(--popover)', border: '1px solid var(--border)',
                        borderRadius: '8px', fontSize: '12px', color: 'var(--foreground)',
                    }}
                        formatter={(v: number) => [formatUsd(v), '']} />
                </RechartsPie>
            </ResponsiveContainer>
            {/* Center label */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none" style={{ top: '-10px' }}>
                <div className="text-center">
                    <div className="text-lg font-heading font-bold text-foreground">{formatUsd(total)}</div>
                    <div className="text-[10px] text-muted-foreground">Total</div>
                </div>
            </div>
            <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1 justify-center">
                {data.map((d, i) => (
                    <div key={i} className="flex items-center gap-1">
                        <div className="w-2 h-2 rounded-full" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                        <span className="text-[10px] text-muted-foreground">{d.name} ({(d.value / total * 100).toFixed(0)}%)</span>
                    </div>
                ))}
            </div>
        </>
    )
}

// ─── Positions Table (Bybit-style with shadcn Table) ───
export function PositionsTable({ positions, onClose, loading }: {
    positions: Position[]; onClose: (id: string | number, pct: number, val: number, proto: string) => void; loading?: string | null;
}) {
    const real = positions.filter(p => p.deposited > 0 || p.current > 0)
    if (!real.length) return (
        <div className="py-10 text-center text-xs text-muted-foreground">
            No active positions. Funds will be deployed when your agent finds optimal pools.
        </div>
    )
    return (
        <div className="overflow-x-auto">
            <Table>
                <TableHeader>
                    <TableRow className="border-border hover:bg-transparent">
                        <TableHead className="text-[10px] uppercase text-muted-foreground font-semibold">Symbol</TableHead>
                        <TableHead className="text-[10px] uppercase text-muted-foreground font-semibold">Size</TableHead>
                        <TableHead className="text-[10px] uppercase text-muted-foreground font-semibold">Entry</TableHead>
                        <TableHead className="text-[10px] uppercase text-muted-foreground font-semibold">Mark</TableHead>
                        <TableHead className="text-[10px] uppercase text-muted-foreground font-semibold">P&L</TableHead>
                        <TableHead className="text-[10px] uppercase text-muted-foreground font-semibold">APY</TableHead>
                        <TableHead className="text-[10px] uppercase text-muted-foreground font-semibold text-right">Close</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {real.map(pos => {
                        const curr = pos.value_usd || pos.current || 0
                        const entry = pos.entry_value || pos.deposited || curr
                        const pnl = pos.pnl || (curr - entry)
                        const pnlPct = entry > 0 ? (pnl / entry * 100) : 0
                        const isProfit = pnl >= 0
                        const isDual = !!pos.token0_symbol && !!pos.token1_symbol

                        return (
                            <TableRow key={pos.id} className="border-border hover:bg-accent/50 transition-colors">
                                <TableCell>
                                    <div className="font-medium text-foreground">{pos.pool_name || pos.vaultName || pos.protocol}</div>
                                    <div className="text-[10px] text-muted-foreground">{isDual ? 'LP' : pos.asset || 'USDC'}</div>
                                </TableCell>
                                <TableCell>
                                    {isDual ? (
                                        <div className="space-y-0.5 text-[10px] text-foreground">
                                            <div>{pos.token0_amount?.toFixed(4)} {pos.token0_symbol}</div>
                                            <div>{pos.token1_amount?.toFixed(2)} {pos.token1_symbol}</div>
                                        </div>
                                    ) : (
                                        <span className="text-foreground">{pos.deposited?.toFixed(2)} <span className="text-[10px] text-muted-foreground">USDC</span></span>
                                    )}
                                </TableCell>
                                <TableCell className="text-foreground">${entry.toFixed(2)}</TableCell>
                                <TableCell className="text-foreground">${curr.toFixed(2)}</TableCell>
                                <TableCell>
                                    <span className={isProfit ? 'text-green-500' : 'text-destructive'}>{isProfit ? '+' : ''}${Math.abs(pnl).toFixed(2)}</span>
                                    <div className={`text-[10px] ${isProfit ? 'text-green-500' : 'text-destructive'}`}>
                                        ({isProfit ? '+' : ''}{pnlPct.toFixed(2)}%)
                                    </div>
                                </TableCell>
                                <TableCell className="text-primary font-medium">{pos.apy?.toFixed(1)}%</TableCell>
                                <TableCell className="text-right">
                                    <div className="flex gap-1 justify-end">
                                        {[25, 50, 100].map(pct => (
                                            <Button key={pct} variant={pct === 100 ? 'destructive' : 'outline'} size="sm"
                                                onClick={() => onClose(pos.id, pct, curr, pos.protocol)}
                                                disabled={loading === `close-${pos.id}`}
                                                className={`h-6 px-2 text-[10px] font-medium ${pct === 100 ? 'bg-destructive/15 text-destructive border-destructive/30 hover:bg-destructive/25' : ''}`}>
                                                {pct}%
                                            </Button>
                                        ))}
                                    </div>
                                </TableCell>
                            </TableRow>
                        )
                    })}
                </TableBody>
            </Table>
        </div>
    )
}

// ─── Quick Actions Bar ───
export function QuickActions({ onHarvest, onRebalance, onExportCSV, loading }: {
    onHarvest: () => void; onRebalance: () => void; onExportCSV: () => void; loading: string | null;
}) {
    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="h-8 px-3 text-xs">
                    <Power className="w-3.5 h-3.5 mr-1.5" /> Actions
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="bg-popover border-border">
                <DropdownMenuItem onClick={onHarvest} disabled={loading === 'harvest'} className="text-xs cursor-pointer">
                    <Zap className="w-3.5 h-3.5 mr-2 text-primary" /> Harvest Rewards
                </DropdownMenuItem>
                <DropdownMenuItem onClick={onRebalance} disabled={loading === 'rebalance'} className="text-xs cursor-pointer">
                    <RefreshCw className="w-3.5 h-3.5 mr-2 text-primary" /> Rebalance Portfolio
                </DropdownMenuItem>
                <DropdownMenuItem onClick={onExportCSV} className="text-xs cursor-pointer">
                    <Download className="w-3.5 h-3.5 mr-2 text-primary" /> Export Audit CSV
                </DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
    )
}

// ─── Holdings Table ───
export function HoldingsTable({ holdings }: { holdings: Holding[] }) {
    if (!holdings.length) return (
        <div className="py-6 text-center text-xs text-muted-foreground">No holdings found</div>
    )
    return (
        <div className="space-y-1.5">
            {holdings.map((h, i) => (
                <div key={h.asset + i}
                    className="flex items-center justify-between p-2.5 rounded-lg bg-secondary/80 hover:bg-secondary transition-colors">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
                            style={{ background: `${PIE_COLORS[i % PIE_COLORS.length]}20`, color: PIE_COLORS[i % PIE_COLORS.length] }}>
                            {h.asset[0]}
                        </div>
                        <div>
                            <div className="text-sm font-medium text-foreground">{h.asset}</div>
                            <div className="text-[10px] text-muted-foreground">{h.balance.toLocaleString()} tokens</div>
                        </div>
                    </div>
                    <div className="text-right">
                        <div className="text-sm font-medium text-foreground">{formatUsd(h.value)}</div>
                        {h.change !== 0 && (
                            <div className={`text-[10px] ${h.change >= 0 ? 'text-green-500' : 'text-destructive'}`}>
                                {h.change >= 0 ? '+' : ''}{h.change.toFixed(2)}%
                            </div>
                        )}
                    </div>
                </div>
            ))}
        </div>
    )
}

// ─── Transaction History ───
export function TransactionHistory({ trades, filter, onFilterChange }: {
    trades: Transaction[]; filter: string; onFilterChange: (f: string) => void;
}) {
    const ICONS: Record<string, string> = { deposit: 'D', withdraw: 'W', harvest: 'H', rebalance: 'R', swap: 'S', enter_lp: 'LP', exit_lp: 'X' }
    const filters = ['all', 'deposit', 'withdraw', 'harvest', 'swap']
    const filtered = filter === 'all' ? trades : trades.filter(t => (t.type || '').includes(filter))

    return (
        <div>
            <div className="flex gap-1.5 mb-3 flex-wrap">
                {filters.map(f => (
                    <Button key={f} variant={filter === f ? 'default' : 'outline'} size="sm"
                        onClick={() => onFilterChange(f)}
                        className={`h-7 px-2.5 text-xs capitalize ${filter === f ? 'bg-primary/15 text-primary border-primary/30 hover:bg-primary/25' : ''}`}>
                        {f}
                    </Button>
                ))}
            </div>
            {!filtered.length ? (
                <div className="py-6 text-center text-xs text-muted-foreground">No transactions</div>
            ) : (
                <div className="space-y-1">
                    {filtered.slice(0, 20).map((tx, i) => (
                        <div key={i} className="flex items-center justify-between px-3 py-2 rounded-lg bg-secondary/60 hover:bg-secondary transition-colors">
                            <div className="flex items-center gap-2.5">
                                <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-sm ${['deposit', 'buy', 'harvest'].includes(tx.type) ? 'bg-green-500/12' : 'bg-destructive/12'}`}>
                                    {ICONS[tx.type] || 'TX'}
                                </div>
                                <div>
                                    <div className="text-xs font-medium text-foreground">{tx.vault || tx.type}</div>
                                    <div className="text-[10px] text-muted-foreground">{tx.time || tx.timestamp || '—'}</div>
                                </div>
                            </div>
                            <div className="text-right flex items-center gap-2">
                                <span className={`text-xs font-medium ${['withdraw', 'sell'].includes(tx.type) ? 'text-destructive' : 'text-green-500'}`}>
                                    {['withdraw', 'sell'].includes(tx.type) ? '-' : '+'}${(tx.amount || 0).toFixed(2)}
                                </span>
                                {(tx.hash || tx.txHash) && (
                                    <a href={`https://basescan.org/tx/${tx.hash || tx.txHash}`} target="_blank" rel="noopener noreferrer"
                                        className="text-muted-foreground hover:text-primary transition-colors">
                                        <ExternalLink className="w-3 h-3" />
                                    </a>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}

// ─── Performance Chart (SVG) ───
export function PerformanceChart({ totalValue, period, onPeriodChange }: {
    totalValue: number; period: string; onPeriodChange: (p: string) => void;
}) {
    const periods = ['7d', '30d', '90d']
    if (totalValue <= 0) return (
        <div className="flex items-center justify-center py-10 text-xs text-muted-foreground">
            <TrendingUp className="w-4 h-4 mr-2 opacity-30" /> No performance data
        </div>
    )
    const days = period === '7d' ? 7 : period === '30d' ? 30 : 90
    const W = 400; const H = 160; const P = 25
    const pts = Array.from({ length: days + 1 }, (_, i) => {
        const x = P + (i / days) * (W - P * 2)
        const y = H / 2
        return `${x},${y}`
    })
    const pathD = `M ${pts.join(' L ')}`

    return (
        <div>
            <div className="flex items-center justify-between mb-2">
                <div className="flex gap-1">
                    {periods.map(p => (
                        <Button key={p} variant={period === p ? 'default' : 'ghost'} size="sm"
                            onClick={() => onPeriodChange(p)}
                            className={`h-6 px-2 text-[10px] ${period === p ? 'bg-primary/15 text-primary' : 'text-muted-foreground'}`}>
                            {p}
                        </Button>
                    ))}
                </div>
                <Badge variant="outline" className="bg-green-500/15 text-green-500 border-green-500/30 text-[10px]">
                    0.00%
                </Badge>
            </div>
            <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
                <defs>
                    <linearGradient id="perfGrad" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0%" stopColor="#22c55e" stopOpacity="0.2" />
                        <stop offset="100%" stopColor="#22c55e" stopOpacity="0" />
                    </linearGradient>
                </defs>
                <path d={`${pathD} L ${W - P},${H - P} L ${P},${H - P} Z`} fill="url(#perfGrad)" />
                <path d={pathD} fill="none" stroke="#22c55e" strokeWidth="2" />
            </svg>
            <div className="flex justify-between text-[10px] mt-1 text-muted-foreground">
                <span>{formatUsd(totalValue)}</span><span>{formatUsd(totalValue)}</span>
            </div>
        </div>
    )
}

// ─── Toast Notification ───
export function Toast({ toast }: { toast: { msg: string; type: string } | null }) {
    const colorMap: Record<string, string> = {
        error: 'bg-destructive/15 text-destructive border-destructive/30',
        warning: 'bg-yellow-500/15 text-yellow-500 border-yellow-500/30',
        success: 'bg-green-500/15 text-green-500 border-green-500/30',
        info: 'bg-blue-500/15 text-blue-500 border-blue-500/30',
    }
    return (
        <AnimatePresence>
            {toast && (
                <motion.div initial={{ opacity: 0, y: 50 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 50 }}
                    className={`fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-xl text-sm font-medium shadow-lg border backdrop-blur-xl ${colorMap[toast.type] || colorMap.info}`}>
                    {toast.msg}
                </motion.div>
            )}
        </AnimatePresence>
    )
}
