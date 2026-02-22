/**
 * API Client — full endpoint coverage
 * Maps to backend routers per frontend_endpoint_map.md
 * In dev: Vite proxy forwards /api/* to localhost:8000
 */

const API_BASE = import.meta.env.VITE_API_BASE || ''

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
    const url = `${API_BASE}${path}`
    const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json', ...options?.headers },
        ...options,
    })
    if (!res.ok) {
        const errorBody = await res.text().catch(() => 'Unknown error')
        throw new Error(`API ${res.status}: ${errorBody}`)
    }
    return res.json()
}

// ========== Pool Types ==========

export interface Pool {
    pool_id: string
    pool?: string
    project: string
    symbol: string
    chain?: string
    apy: number
    tvl: number
    tvl_formatted?: string
    volume_24h?: number
    volume_24h_formatted?: string
    volume_7d?: number
    stablecoin?: boolean
    pool_type?: string
    risk_score?: number
    risk_level?: string
    risk_color?: string
    risk_reasons?: string[]
    il_risk?: string
    il_risk_level?: string
    reward_token?: string
    source?: string
    source_name?: string
    source_badge?: string
    unlock_price_usd?: number
    apyBase?: number
    apyReward?: number
    explorer_url?: string
    defillama_url?: string
    address?: string
    pool_address?: string
    underlyingTokens?: string[]
    category?: string
    category_icon?: string
    category_label?: string
    verified?: boolean
    agent_verified?: boolean
    dataSource?: string
}

export interface PoolsResponse {
    success: boolean
    count: number
    asset_type: string
    chains: string[]
    sources: string[]
    combined: Pool[]
}

export interface PoolDetailResponse {
    pool: Pool
    history?: { timestamp: string; apy: number; tvl: number }[]
    similar_pools?: Pool[]
}

// ========== Scout / Verify ==========

export interface ScoutResolveResponse {
    success: boolean
    pool_address?: string
    chain?: string
    input_type?: string
}

export interface ScoutVerifyResponse {
    success: boolean
    pool?: Pool
    source?: string
    risk_analysis?: {
        risk_score: number
        risk_level: string
        risk_reasons: string[]
    }
}

export interface ScoutPairResponse {
    success: boolean
    pool?: Pool & { pool_address?: string; address?: string }
}

// ========== Agent Types ==========

export interface AgentInfo {
    id: string
    agent_id?: string
    agent_address?: string
    status: 'active' | 'paused' | 'stopped' | 'deploying'
    strategy_mode?: string
    created_at?: string
    total_deposited?: number
    total_earned?: number
    current_apy?: number
    positions?: AgentPosition[]
}

export interface AgentPosition {
    pool_address: string
    pool_name?: string
    protocol: string
    chain: string
    amount_usd: number
    apy: number
    entry_date?: string
    pnl?: number
    pnl_pct?: number
    token_id?: string
}

export interface AgentStatusResponse {
    success: boolean
    agents: AgentInfo[]
    total_value?: number
}

export interface AgentDeployResponse {
    success: boolean
    agent_id?: string
    agent_address?: string
    tx_hash?: string
    error?: string
}

// ========== Wallet Types ==========

export interface TokenBalance {
    token: string
    symbol: string
    balance: string
    balance_formatted: number
    usd_value: number
    price?: number
    logo?: string
}

export interface WalletBalancesResponse {
    success: boolean
    balances: TokenBalance[]
    total_usd: number
    agent_address?: string
}

export interface WalletInfoResponse {
    success: boolean
    address?: string
    smart_account?: string
    has_session_key?: boolean
}

// ========== Portfolio Types ==========

export interface PortfolioResponse {
    success: boolean
    total_value: number
    positions: AgentPosition[]
    pnl_24h?: number
    pnl_7d?: number
    deposit_history?: { date: string; amount: number }[]
}

export interface PortfolioSummaryResponse {
    success: boolean
    total_value: number
    total_pnl: number
    total_earned: number
    active_positions: number
    agents_count: number
}

// ========== Premium / Payment Types ==========

export interface PaymentRequirements {
    usdcAddress: string
    recipientAddress: string
    amount: string
    chainId: number
    maxTimeoutSeconds: number
    credits: number
    priceDisplay: string
}

export interface PremiumRequirements extends PaymentRequirements {
    period: string
    features: string[]
}

export interface SettleResponse {
    success: boolean
    credits?: number
    error?: string
    tx_hash?: string
}

export interface SubscriptionTier {
    id: string
    name: string
    price_usdc: number
    features: string[]
    limits: Record<string, number>
}

// ========== Engineer Types ==========

export interface EngineerTask {
    task_id: string
    status: 'pending' | 'executing' | 'completed' | 'failed'
    action: string
    details?: any
    result?: any
    created_at: string
}

// ========== Audit Types ==========

export interface AuditEntry {
    id: string
    action: string
    agent_id?: string
    details?: any
    timestamp: string
    status: string
    tx_hash?: string
}

// ================================================================
//                        API FUNCTIONS
// ================================================================

// --- Pools (main.py inline) ---
export function fetchPools(params?: Record<string, string>) {
    const query = params ? '?' + new URLSearchParams(params).toString() : ''
    return apiFetch<PoolsResponse>(`/api/pools${query}`)
}

export function fetchPoolDetail(poolId: string) {
    return apiFetch<PoolDetailResponse>(`/api/scout/pool/${poolId}`)
}

export function fetchGeckoPools() {
    return apiFetch<PoolsResponse>('/api/pools/gecko')
}

export function fetchYields() {
    return apiFetch<any>('/api/yields')
}

export function fetchYieldDetail(poolId: string) {
    return apiFetch<any>(`/api/yields/${poolId}`)
}

export function fetchChains() {
    return apiFetch<{ chains: string[] }>('/api/chains')
}

export function fetchStats() {
    return apiFetch<any>('/api/stats')
}

// --- Scout / Verify (scout_router.py) ---
export function scoutResolve(input: string, chain = 'base') {
    return apiFetch<ScoutResolveResponse>(
        `/api/scout/resolve?input=${encodeURIComponent(input)}&chain=${chain}`
    )
}

export function scoutVerifyRpc(poolAddress: string, chain = 'base') {
    return apiFetch<ScoutVerifyResponse>(
        `/api/scout/verify-rpc?pool_address=${encodeURIComponent(poolAddress)}&chain=${chain}`
    )
}

export function scoutVerifyOnchain(poolAddress: string, protocol = 'auto', chain = 'base') {
    return apiFetch<any>(
        `/api/scout/verify-onchain?pool_address=${encodeURIComponent(poolAddress)}&protocol=${encodeURIComponent(protocol)}&chain=${chain}`
    )
}

export function scoutPoolPair(token0: string, token1: string, opts?: {
    protocol?: string
    chain?: string
    stable?: boolean
}) {
    const params = new URLSearchParams({
        token0, token1,
        protocol: opts?.protocol || '',
        chain: opts?.chain || '',
        stable: opts?.stable ? 'true' : 'false',
    })
    return apiFetch<ScoutPairResponse>(`/api/scout/pool-pair?${params}`)
}

// --- Agent Operations (agent_router.py) ---
export function fetchAgentStatus(userAddress: string) {
    return apiFetch<AgentStatusResponse>(`/api/agent/status/${userAddress}`)
}

export function syncAgent(body: { user_address: string; agent: Record<string, any> }) {
    return apiFetch<any>('/api/agent/sync', {
        method: 'POST', body: JSON.stringify(body)
    })
}

export function deleteAgent(userAddress: string, agentId: string) {
    return apiFetch<any>(`/api/agent/delete/${userAddress}/${agentId}`, {
        method: 'DELETE'
    })
}

export function harvestRewards(body: { user_address: string; agent_id: string }) {
    return apiFetch<any>('/api/agent/harvest', {
        method: 'POST', body: JSON.stringify({ wallet: body.user_address, agentId: body.agent_id })
    })
}

export function rebalanceAgent(body: { user_address: string; agent_id: string }) {
    return apiFetch<any>('/api/agent/rebalance', {
        method: 'POST', body: JSON.stringify({ wallet: body.user_address, agentId: body.agent_id })
    })
}

export function pauseAllAgents(body: { user_address: string }) {
    return apiFetch<any>('/api/agent/pause-all', {
        method: 'POST', body: JSON.stringify({ wallet: body.user_address })
    })
}

export function fetchLpPositions(userAddress: string) {
    return apiFetch<any>(`/api/agent/lp-positions/${userAddress}`)
}

export function fetchRecommendations(userAddress: string) {
    return apiFetch<any>(`/api/agent/recommendations/${userAddress}`)
}

export function triggerAllocation(body: { user_address: string }) {
    return apiFetch<any>('/api/agent/trigger-allocation', {
        method: 'POST', body: JSON.stringify(body)
    })
}

// --- Agent Deploy (agent_config_router.py) ---
export function deployAgent(config: any) {
    return apiFetch<AgentDeployResponse>('/api/agent/deploy', {
        method: 'POST', body: JSON.stringify(config)
    })
}

export function confirmDeploy(body: { user_address: string; agent_id: string; tx_hash: string }) {
    return apiFetch<any>('/api/agent/confirm-deploy', {
        method: 'POST', body: JSON.stringify(body)
    })
}

export function setupAutoTrading(body: { user_address: string; agent_id: string; agent_address: string }) {
    return apiFetch<any>('/api/agent/setup-auto-trading', {
        method: 'POST', body: JSON.stringify(body)
    })
}

// --- Scalable Agent Service (agent_service_router.py) ---
export function fetchUserAgents(userAddress: string) {
    return apiFetch<{ agents: AgentInfo[] }>(`/api/agents/user/${userAddress}`)
}

export function fetchAgentDetails(agentAddress: string) {
    return apiFetch<AgentInfo>(`/api/agents/details/${agentAddress}`)
}

export function updateAgent(agentAddress: string, updates: Record<string, any>) {
    return apiFetch<{ success: boolean; message?: string }>(`/api/agents/${agentAddress}`, {
        method: 'PUT', body: JSON.stringify(updates)
    })
}

export function pauseAgent(agentAddress: string) {
    return apiFetch<any>(`/api/agents/${agentAddress}/pause`, { method: 'POST' })
}

export function resumeAgent(agentAddress: string) {
    return apiFetch<any>(`/api/agents/${agentAddress}/resume`, { method: 'POST' })
}

export function fetchAgentBalances(agentAddress: string) {
    return apiFetch<WalletBalancesResponse>(`/api/agents/${agentAddress}/balances`)
}

export function fetchAgentPositions(agentAddress: string) {
    return apiFetch<{ positions: AgentPosition[] }>(`/api/agents/${agentAddress}/positions`)
}

export function fetchAgentTransactions(agentAddress: string) {
    return apiFetch<{ transactions: AuditEntry[] }>(`/api/agents/${agentAddress}/transactions`)
}

export function fetchAgentAudit(agentAddress: string) {
    return apiFetch<{ entries: AuditEntry[] }>(`/api/agents/${agentAddress}/audit`)
}

export function fetchPortfolioSummary(userAddress: string) {
    return apiFetch<PortfolioSummaryResponse>(`/api/agents/user/${userAddress}/summary`)
}

export function deleteAgentScalable(agentAddress: string) {
    return apiFetch<any>(`/api/agents/${agentAddress}`, { method: 'DELETE' })
}

// --- Agent Wallet (agent_wallet_router.py) ---
export function createAgentWallet(body: { user_address: string }) {
    return apiFetch<WalletInfoResponse>('/api/agent-wallet/create', {
        method: 'POST', body: JSON.stringify(body)
    })
}

export function fetchWalletInfo() {
    return apiFetch<WalletInfoResponse>('/api/agent-wallet/info')
}

export function fetchAgentWalletBalances() {
    return apiFetch<WalletBalancesResponse>('/api/agent-wallet/balances')
}

export function fetchTokenPrices() {
    return apiFetch<any>('/api/agent-wallet/prices')
}

export function depositNotify(body: { user_address: string; tx_hash: string; amount: string }) {
    return apiFetch<any>('/api/agent-wallet/deposit', {
        method: 'POST', body: JSON.stringify(body)
    })
}

export function withdrawFunds(body: { user_address: string; token: string; amount: string; to: string }) {
    return apiFetch<any>('/api/agent-wallet/withdraw', {
        method: 'POST', body: JSON.stringify(body)
    })
}

export function withdrawSmartAccount(body: any) {
    return apiFetch<any>('/api/agent-wallet/withdraw-smart-account', {
        method: 'POST', body: JSON.stringify(body)
    })
}

export function emergencyDrain(body: { user_address: string }) {
    return apiFetch<any>('/api/agent-wallet/emergency-drain', {
        method: 'POST', body: JSON.stringify(body)
    })
}

export function refreshBalances() {
    return apiFetch<WalletBalancesResponse>('/api/agent-wallet/refresh-balances', {
        method: 'POST'
    })
}

// --- Portfolio (portfolio_router.py + main.py inline) ---
export function fetchPortfolio(walletAddress: string) {
    return apiFetch<PortfolioResponse>(`/api/portfolio/${walletAddress}`)
}

export function fetchSessionKey(agentAddr: string) {
    return apiFetch<any>(`/api/portfolio/${agentAddr}/session-key`)
}

export function createSessionKey(body: { agent_address: string; user_address: string }) {
    return apiFetch<{ success: boolean; session_key_address?: string; error?: string }>('/api/portfolio/session-key/create', {
        method: 'POST', body: JSON.stringify(body)
    })
}

export function revokeSessionKey(body: { agent_address: string; user_address: string }) {
    return apiFetch<{ success: boolean; error?: string }>('/api/portfolio/session-key/revoke', {
        method: 'POST', body: JSON.stringify(body)
    })
}

export function closePosition(body: { position_id: string; user_address: string }) {
    return apiFetch<any>('/api/portfolio/position/close', {
        method: 'POST', body: JSON.stringify(body)
    })
}

export function fetchPositions(walletAddress: string) {
    return apiFetch<any>(`/api/position/${walletAddress}`)
}

// --- Premium / Meridian (premium_router.py + meridian_router.py) ---
export function fetchPaymentRequirements() {
    return apiFetch<PaymentRequirements>('/api/meridian/payment-requirements')
}

export function fetchPremiumRequirements() {
    return apiFetch<PremiumRequirements>('/api/meridian/premium-requirements')
}

export function settlePayment(paymentPayload: any) {
    return apiFetch<SettleResponse>(
        '/api/meridian/settle',
        { method: 'POST', body: JSON.stringify({ paymentPayload }) }
    )
}

export function subscribePremium(body: { wallet_address: string; paymentPayload: any }) {
    return apiFetch<any>('/api/premium/subscribe', {
        method: 'POST', body: JSON.stringify(body)
    })
}

export function fetchPremiumStatus(userAddress: string) {
    return apiFetch<any>(`/api/premium/status?user_address=${encodeURIComponent(userAddress)}`)
}

export function updatePremiumSettings(body: any) {
    return apiFetch<any>('/api/premium/update-settings', {
        method: 'POST', body: JSON.stringify(body)
    })
}

export function toggleAutoRenewal(userAddress: string, enabled: boolean) {
    return apiFetch<{ success: boolean; auto_renewal_enabled: boolean; message: string }>(
        '/api/premium/auto-renewal',
        { method: 'PUT', body: JSON.stringify({ user_address: userAddress, enabled }) }
    )
}

export function fetchRenewalStatus(userAddress: string) {
    return apiFetch<{
        auto_renewal_enabled: boolean
        can_enable: boolean
        agent_address?: string
        expires_at?: string
        last_renewal_tx?: string
        last_failed?: string
        renewal_cost_usdc: number
        missing: string[]
    }>(`/api/premium/renewal-status?user_address=${encodeURIComponent(userAddress)}`)
}

// --- Revenue (revenue_router.py) ---
export function fetchSubscriptionTiers() {
    return apiFetch<{ tiers: SubscriptionTier[] }>('/api/revenue/tiers')
}

export function fetchUserSubscriptions(userId: string) {
    return apiFetch<any>(`/api/revenue/subscriptions/${userId}`)
}

export function createSubscription(body: any) {
    return apiFetch<any>('/api/revenue/subscriptions/create', {
        method: 'POST', body: JSON.stringify(body)
    })
}

// --- x402 Payments (main.py inline) ---
export function unlockPools(body: { payment_payload: any }) {
    return apiFetch<any>('/api/unlock-pools', {
        method: 'POST', body: JSON.stringify(body)
    })
}

export function verifyUnlock(body: { session_id: string }) {
    return apiFetch<any>('/api/verify-unlock', {
        method: 'POST', body: JSON.stringify(body)
    })
}


// --- Engineer (engineer_router.py) ---
export function engineerDeposit(body: any) {
    return apiFetch<any>('/api/engineer/deposit', {
        method: 'POST', body: JSON.stringify(body)
    })
}

export function engineerWithdraw(body: any) {
    return apiFetch<any>('/api/engineer/withdraw', {
        method: 'POST', body: JSON.stringify(body)
    })
}

export function fetchEngineerTask(taskId: string) {
    return apiFetch<EngineerTask>(`/api/engineer/tasks/${taskId}`)
}

export function fetchUserEngineerTasks(userAddress: string) {
    return apiFetch<{ tasks: EngineerTask[] }>(`/api/engineer/tasks/user/${userAddress}`)
}

export function fetchGasPrice() {
    return apiFetch<{ gas_price: string; gas_price_gwei: number }>('/api/engineer/gas-price')
}

export function fetchRecommendedVaults() {
    return apiFetch<any>('/api/engineer/vaults/recommended')
}

// --- Audit (audit_router.py) ---
export function exportAudit(params?: Record<string, string>) {
    const query = params ? '?' + new URLSearchParams(params).toString() : ''
    return apiFetch<any>(`/api/audit/export${query}`)
}

export function fetchRecentAudit() {
    return apiFetch<{ entries: AuditEntry[] }>('/api/audit/recent')
}

export function fetchReasoningLogs() {
    return apiFetch<any>('/api/audit/reasoning-logs')
}

// --- Protocols (protocols_router.py) ---
export function fetchProtocols() {
    return apiFetch<any>('/api/protocols')
}

// --- Credits (credits_router.py) ---
export function fetchCredits(userAddress: string) {
    return apiFetch<{ credits: number; welcome_bonus_claimed: boolean }>(
        `/api/credits?user_address=${encodeURIComponent(userAddress)}`
    )
}

export function initCreditsApi(userAddress: string) {
    return apiFetch<{ credits: number; bonus_given: boolean }>('/api/credits/init', {
        method: 'POST', body: JSON.stringify({ user_address: userAddress, amount: 0 })
    })
}

export function addCreditsApi(userAddress: string, amount: number) {
    return apiFetch<{ credits: number }>('/api/credits/add', {
        method: 'POST', body: JSON.stringify({ user_address: userAddress, amount })
    })
}

export function useCreditsApi(userAddress: string, cost: number) {
    return apiFetch<{ credits: number; used: number }>('/api/credits/use', {
        method: 'POST', body: JSON.stringify({ user_address: userAddress, cost })
    })
}

// --- Smart Account (main.py inline) ---
export function fetchSmartAccount(userAddress: string) {
    return apiFetch<any>(`/api/smart-account/${userAddress}`)
}

export function createSmartAccount(body: { user_address: string }) {
    return apiFetch<any>('/api/smart-account/create', {
        method: 'POST', body: JSON.stringify(body)
    })
}

// --- Whitelist (main.py inline) ---
export function whitelistUser(body: { user_address: string }) {
    return apiFetch<any>('/api/whitelist', {
        method: 'POST', body: JSON.stringify(body)
    })
}

// --- ERC-8004 Identity ---
export function fetchTrustScore(smartAccount: string) {
    return apiFetch<any>(`/api/agent-trust-score/${smartAccount}`)
}

// --- LP Info ---
export function fetchLpInfo(poolAddress: string) {
    return apiFetch<any>(`/api/lp/info/${poolAddress}`)
}

// --- Trade History (audit_router.py recent endpoint) ---
export function fetchTradeHistory() {
    return apiFetch<{ trades: any[]; history: any[] }>('/api/audit/recent')
}

// --- Aliases for backward compat ---
export const fetchAgentWalletBalance = fetchAgentWalletBalances

// --- Portfolio Operations (new portfolio-specific helpers) ---
export function toggleAgentActive(_wallet: string, agentId: string, activate: boolean) {
    const endpoint = activate ? 'resume' : 'pause'
    return apiFetch<{ success: boolean; message?: string }>(`/api/agents/${agentId}/${endpoint}`, {
        method: 'POST'
    })
}

export function exportAuditCSV(wallet: string) {
    const url = `${API_BASE}/api/audit/export?wallet=${wallet}`
    return fetch(url).then(r => r.ok ? r.blob() : Promise.reject(new Error('Export failed')))
}

export function fetchAuditRecent(limit = 10) {
    return apiFetch<{ entries: { action_type: string; value_usd?: number; timestamp: string }[] }>(`/api/audit/recent?limit=${limit}`)
}

// ========== Helpers ==========

export function getRiskColor(score?: number): string {
    if (!score) return 'var(--color-text-muted)'
    if (score >= 55) return 'var(--color-green)'
    if (score >= 40) return 'var(--color-gold)'
    if (score >= 25) return 'var(--color-red)'
    return '#ff4466'
}

export function getRiskLabel(score?: number): string {
    if (!score) return '—'
    if (score >= 55) return 'Low'
    if (score >= 40) return 'Medium'
    if (score >= 25) return 'High'
    return 'Critical'
}

export function formatUsd(val: number): string {
    if (val >= 1_000_000_000) return `$${(val / 1_000_000_000).toFixed(1)}B`
    if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`
    if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`
    return `$${val.toFixed(0)}`
}

export function formatApy(apy: number): string {
    if (apy >= 100) return `${apy.toFixed(0)}%`
    if (apy >= 10) return `${apy.toFixed(1)}%`
    return `${apy.toFixed(2)}%`
}
