/**
 * Portfolio Dashboard hooks — agent management, balance loading, positions, actions
 * Ports the PortfolioDashboard class from portfolio.js into React hooks
 */
import { useState, useCallback, useEffect, useMemo } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useWalletStore } from '@/stores/walletStore'
import {
    fetchAgentStatus, fetchPortfolio, fetchPositions, fetchTradeHistory,
    fetchTrustScore, fetchSessionKey, fetchAuditRecent,
    deleteAgent as apiDeleteAgent, harvestRewards, rebalanceAgent,
    pauseAllAgents, toggleAgentActive as apiToggleAgent,
    closePosition as apiClosePosition, exportAuditCSV,
} from '@/lib/api'

// ─── Types ───
export interface Agent {
    id: string; name?: string; preset?: string;
    address?: string; agent_address?: string; user_address?: string;
    isActive?: boolean; is_active?: boolean; paused?: boolean;
    deployedAt?: string; deployed_at?: string;
    pool_type?: string; poolType?: string;
    avoid_il?: boolean; avoidIL?: boolean;
    max_drawdown?: number; maxDrawdown?: number;
    proConfig?: any; pro_config?: any;
}

export interface Holding {
    asset: string; balance: number; value: number; value_usd?: number; change: number; label?: string;
}

export interface Position {
    id: string | number; pool_name?: string; protocol: string; vaultName?: string;
    deposited: number; current: number; value_usd?: number; entry_value?: number;
    pnl: number; apy: number; asset?: string; chain?: string; isLP?: boolean;
    token0_symbol?: string; token1_symbol?: string;
    token0_amount?: number; token1_amount?: number;
    il_risk?: string; apy_spike?: boolean;
}

export interface Transaction {
    type: string; vault?: string; time?: string; amount: number; hash?: string;
    timestamp?: string; asset?: string; valueUsd?: number; txHash?: string;
}

// ─── Agent Management Hook ───
export function useAgentManagement() {
    const { address } = useWalletStore()
    useQueryClient() // retain hook call for future invalidation
    const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)
    const [toast, setToast] = useState<{ msg: string; type: string } | null>(null)

    const showToast = useCallback((msg: string, type = 'info') => {
        setToast({ msg, type }); setTimeout(() => setToast(null), 4000)
    }, [])

    // Load agents from backend → localStorage fallback (mirroring loadAgents())
    const { data: agentsData, isLoading: loadingAgents, refetch: refetchAgents } = useQuery({
        queryKey: ['agent-status', address],
        queryFn: async () => {
            if (!address) return { agents: [] }
            try {
                const resp = await fetchAgentStatus(address)
                if (resp.success && resp.agents?.length) {
                    const mapped = resp.agents.map((a: any) => ({
                        ...a, isActive: a.is_active, userAddress: a.user_address, address: a.agent_address,
                    }))
                    const key = `techne_agents_${address.toLowerCase()}`
                    localStorage.setItem(key, JSON.stringify(mapped))
                    localStorage.setItem('techne_deployed_agents', JSON.stringify(mapped))
                    return { agents: mapped as Agent[] }
                }
            } catch { /* backend fail → localStorage */ }
            // Fallback
            const key = `techne_agents_${address.toLowerCase()}`
            const saved = localStorage.getItem(key) || localStorage.getItem('techne_deployed_agents')
            return { agents: saved ? JSON.parse(saved) : [] }
        },
        enabled: !!address, staleTime: 30_000,
    })

    const agents: Agent[] = agentsData?.agents || []

    // Auto-select first active agent
    useEffect(() => {
        if (agents.length && !selectedAgentId) {
            const active = agents.find(a => a.isActive || a.is_active)
            setSelectedAgentId((active || agents[0]).id)
        }
    }, [agents, selectedAgentId])

    const selectedAgent = useMemo(
        () => agents.find(a => a.id === selectedAgentId) || agents[0] || null,
        [agents, selectedAgentId]
    )

    const selectAgent = useCallback((id: string) => setSelectedAgentId(id), [])

    const removeAgent = useCallback(async (agentId: string) => {
        if (!address) { console.error('[removeAgent] No wallet address'); return }
        console.log('[removeAgent] Deleting:', { address, agentId })
        try {
            const result = await apiDeleteAgent(address, agentId)
            console.log('[removeAgent] API response:', result)
            // Clear localStorage cache so deleted agent can't be resurrected by fallback
            const key = `techne_agents_${address.toLowerCase()}`
            const cached = localStorage.getItem(key)
            if (cached) {
                try {
                    const agents = JSON.parse(cached).filter((a: any) => a.id !== agentId)
                    localStorage.setItem(key, JSON.stringify(agents))
                    localStorage.setItem('techne_deployed_agents', JSON.stringify(agents))
                } catch { localStorage.removeItem(key); localStorage.removeItem('techne_deployed_agents') }
            }
            setSelectedAgentId(null)
            showToast('Agent deleted', 'success')
            refetchAgents()
        } catch (err) {
            console.error('[removeAgent] FAILED:', err, { address, agentId })
            showToast('Failed to delete agent', 'error')
        }
    }, [address, showToast, refetchAgents])

    const toggleAgent = useCallback(async (activate: boolean) => {
        if (!address || !selectedAgent) return
        try {
            const res = await apiToggleAgent(address, selectedAgent.id, activate)
            if (res.success) {
                showToast(activate ? 'Agent resumed' : 'Agent paused', 'success')
                refetchAgents()
            } else { showToast(res.message || 'Failed', 'error') }
        } catch { showToast('Network error', 'error') }
    }, [address, selectedAgent, showToast, refetchAgents])

    const emergencyPause = useCallback(async () => {
        if (!address || !confirm('EMERGENCY PAUSE ALL AGENTS?\nNo new trades will be executed.')) return
        try {
            await pauseAllAgents({ user_address: address })
            showToast('All agents paused!', 'warning')
            refetchAgents()
        } catch { showToast('Pause failed', 'error') }
    }, [address, showToast, refetchAgents])

    return {
        agents, loadingAgents, selectedAgent, selectedAgentId,
        selectAgent, removeAgent, toggleAgent, emergencyPause,
        toast, showToast, refetchAgents,
    }
}

// ─── Portfolio Data Hook ───
export function usePortfolioData(wallet?: string, selectedAgent?: Agent | null) {
    const agentAddr = selectedAgent?.agent_address || selectedAgent?.address || ''

    // Portfolio (holdings + positions combined from backend)
    const { data: portfolioData, isLoading: loadingPortfolio, refetch: refetchPortfolio } = useQuery({
        queryKey: ['portfolio', wallet],
        queryFn: () => fetchPortfolio(wallet!),
        enabled: !!wallet, staleTime: 30_000, refetchInterval: 120_000,
    })

    // Positions detail
    const { data: positionsData, refetch: refetchPositions } = useQuery({
        queryKey: ['positions', wallet],
        queryFn: () => fetchPositions(wallet!),
        enabled: !!wallet, staleTime: 30_000,
    })

    // Trade history
    const { data: historyData } = useQuery({
        queryKey: ['trade-history'],
        queryFn: fetchTradeHistory,
        staleTime: 60_000,
    })

    // Audit log
    const { data: auditData } = useQuery({
        queryKey: ['audit-recent'],
        queryFn: () => fetchAuditRecent(10),
        staleTime: 60_000,
    })

    // Trust score (ERC-8004)
    const { data: trustData } = useQuery({
        queryKey: ['trust-score', agentAddr],
        queryFn: () => fetchTrustScore(agentAddr),
        enabled: !!agentAddr, staleTime: 120_000,
    })

    // Session key
    const { data: sessionData } = useQuery({
        queryKey: ['session-key', agentAddr],
        queryFn: () => fetchSessionKey(agentAddr),
        enabled: !!agentAddr, staleTime: 120_000,
    })

    // Derived data
    const holdings: Holding[] = useMemo(() => {
        const raw = portfolioData?.positions || []  // portfolio endpoint returns positions array with holdings
        const h = (portfolioData as any)?.holdings || raw
        return h.map((item: any) => ({
            asset: item.asset || item.symbol || item.pool_name || 'Unknown',
            balance: item.balance || item.balance_formatted || 0,
            value: item.value_usd || item.usd_value || item.value || 0,
            change: item.change || 0, label: item.label,
        })).filter((h: Holding) => h.value > 0.01)
    }, [portfolioData])

    const positions: Position[] = useMemo(() => {
        const raw = positionsData?.positions || []
        return raw.map((p: any) => ({
            id: p.id || p.pool_address, pool_name: p.pool_name, protocol: p.protocol || 'Unknown',
            vaultName: p.vaultName || p.pool_name, deposited: p.deposited || p.entry_value || p.amount_usd || 0,
            current: p.current_value || p.value_usd || p.amount_usd || 0,
            value_usd: p.value_usd, entry_value: p.entry_value, pnl: p.pnl || 0,
            apy: p.apy || 0, asset: p.asset, chain: p.chain, isLP: !!p.token0_symbol,
            token0_symbol: p.token0_symbol, token1_symbol: p.token1_symbol,
            token0_amount: p.token0_amount, token1_amount: p.token1_amount,
            il_risk: p.il_risk, apy_spike: p.apy_spike,
        })).filter((p: Position) => p.deposited > 0 || p.current > 0)
    }, [positionsData])

    const totalValue = (portfolioData as any)?.total_value_usd ??
        (portfolioData as any)?.total_value ??
        holdings.reduce((s, h) => s + h.value, 0) + positions.reduce((s, p) => s + p.current, 0)

    const totalPnL = positions.reduce((s, p) => s + p.pnl, 0)
    const avgApy = positions.length ? positions.reduce((s, p) => s + p.apy, 0) / positions.length : 0
    const trades: Transaction[] = historyData?.trades || historyData?.history || []
    const auditEntries = auditData?.entries || []

    return {
        holdings, positions, totalValue, totalPnL, avgApy,
        trades, auditEntries, trustData, sessionData,
        loadingPortfolio, refetchPortfolio, refetchPositions,
    }
}

// ─── Quick Actions Hook ───
export function useQuickActions(
    wallet?: string, selectedAgent?: Agent | null,
    showToast?: (msg: string, type: string) => void,
    refetchPortfolio?: () => void, refetchPositions?: () => void
) {
    const [actionLoading, setActionLoading] = useState<string | null>(null)

    const harvest = useCallback(async () => {
        if (!wallet || !selectedAgent) { showToast?.('No agent selected', 'warning'); return }
        setActionLoading('harvest')
        try {
            const res = await harvestRewards({ user_address: wallet, agent_id: selectedAgent.id })
            const amt = (res as any).harvestedAmount || 0
            showToast?.(`Harvested $${amt.toFixed(2)}`, 'success')
        } catch { showToast?.('Harvest submitted', 'success') }
        setActionLoading(null); refetchPortfolio?.()
    }, [wallet, selectedAgent, showToast, refetchPortfolio])

    const rebalance = useCallback(async () => {
        if (!wallet || !selectedAgent) { showToast?.('No agent selected', 'warning'); return }
        setActionLoading('rebalance')
        try {
            await rebalanceAgent({ user_address: wallet, agent_id: selectedAgent.id })
            showToast?.('Portfolio rebalanced', 'success')
        } catch { showToast?.('Rebalance submitted', 'success') }
        setActionLoading(null); refetchPortfolio?.()
    }, [wallet, selectedAgent, showToast, refetchPortfolio])

    const handleClosePosition = useCallback(async (positionId: string | number, percent: number, currentValue: number, protocol: string) => {
        const amount = currentValue * (percent / 100)
        if (percent >= 50 && !confirm(`Close ${percent}% of ${protocol} ($${amount.toFixed(2)})?`)) return
        setActionLoading(`close-${positionId}`)
        try {
            const res = await apiClosePosition({ position_id: String(positionId), user_address: wallet! })
            if (res.success) showToast?.(`Closed ${percent}% of ${protocol}`, 'success')
            else showToast?.(res.error || 'Close failed', 'error')
        } catch { showToast?.('Withdrawal submitted', 'success') }
        setActionLoading(null); refetchPositions?.(); refetchPortfolio?.()
    }, [wallet, showToast, refetchPositions, refetchPortfolio])

    const handleExportCSV = useCallback(async () => {
        if (!wallet) return
        try {
            const blob = await exportAuditCSV(wallet)
            const url = URL.createObjectURL(blob); const a = document.createElement('a')
            a.href = url; a.download = `techne_audit_${new Date().toISOString().slice(0, 10)}.csv`
            a.click(); URL.revokeObjectURL(url)
            showToast?.('CSV exported', 'success')
        } catch { showToast?.('Export failed', 'error') }
    }, [wallet, showToast])

    return { harvest, rebalance, handleClosePosition, handleExportCSV, actionLoading }
}

// ─── Risk Indicators ───
export function useRiskIndicators(agent?: Agent | null, positions?: Position[]) {
    return useMemo(() => {
        if (!agent) return { ilRisk: '—', stopLoss: '—', volatility: '—', apyAlert: '—', overall: 'No Agent', overallClass: '' }
        const proConfig = agent.proConfig || agent.pro_config || {}
        const poolType = agent.pool_type || agent.poolType || 'single'
        const avoidIL = agent.avoid_il ?? agent.avoidIL ?? true
        let ilRisk = 'None'
        if (poolType === 'dual' || !avoidIL) { ilRisk = 'Active' }
        else if (positions?.length) {
            for (const p of positions) {
                if (p.il_risk === 'High') { ilRisk = 'High'; break }
                else if (p.il_risk === 'Medium' && ilRisk !== 'High') ilRisk = 'Medium'
                else if (p.il_risk === 'Low' && ilRisk === 'None') ilRisk = 'Low'
            }
        }
        const stopLossEnabled = proConfig.stopLossEnabled ?? true
        const stopLossPct = agent.max_drawdown || agent.maxDrawdown || proConfig.stopLossPercent || 20
        const stopLoss = stopLossEnabled ? `${stopLossPct}% Active` : 'Off'
        const volGuard = proConfig.volatilityGuard ?? true
        const volatility = agent.paused ? 'PAUSED' : volGuard ? 'OK' : 'Off'
        const hasSpike = positions?.some(p => p.apy_spike) || false
        const apyAlert = hasSpike ? 'Spike Detected!' : 'None'
        let overall = 'Low Risk', overallClass = 'low'
        if (ilRisk === 'High' || agent.paused) { overall = 'High Risk'; overallClass = 'high' }
        else if (ilRisk === 'Medium' || ilRisk === 'Active') { overall = 'Medium Risk'; overallClass = 'medium' }
        return { ilRisk, stopLoss, volatility, apyAlert, overall, overallClass }
    }, [agent, positions])
}
