/**
 * Withdraw Modal — Premium styled, matching DepositModal design system
 * Features: Agent selector via API, asset selector (USDC/ETH/WETH), amount input with presets,
 * balance display, withdraw execution via smart account
 */
import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Loader2, ArrowDownLeft, ChevronDown, Globe, CircleCheck, CircleX, AlertTriangle } from 'lucide-react'
import { useWalletStore } from '@/stores/walletStore'
import { fetchAgentStatus, formatUsd } from '@/lib/api'

const TOKENS: Record<string, { address: string | null; decimals: number; symbol: string; image: string }> = {
    USDC: { address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', decimals: 6, symbol: 'USDC', image: '/icons/usdc.png' },
    ETH: { address: null, decimals: 18, symbol: 'ETH', image: '/icons/ethereum.png' },
    WETH: { address: '0x4200000000000000000000000000000000000006', decimals: 18, symbol: 'WETH', image: '/icons/ethereum.png' },
}

const ERC20_ABI = [
    'function transfer(address to, uint256 amount) returns (bool)',
    'function balanceOf(address account) view returns (uint256)',
]

const SMART_ACCOUNT_ABI = [
    'function execute(address target, uint256 value, bytes data) returns (bytes)',
    'function owner() view returns (address)',
]

const BASE_CHAIN_ID = 8453

interface Agent {
    id: string; name?: string; preset?: string;
    address?: string; agent_address?: string; smartAccount?: string;
}

interface WithdrawModalProps {
    isOpen: boolean
    onClose: () => void
    initialAsset?: string
}

export function WithdrawModal({ isOpen, onClose, initialAsset = 'USDC' }: WithdrawModalProps) {
    const { address } = useWalletStore()
    const [agents, setAgents] = useState<Agent[]>([])
    const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)
    const [asset, setAsset] = useState(initialAsset)
    const [amount, setAmount] = useState('')
    const [agentBalance, setAgentBalance] = useState(0)
    const [agentBalanceUsd, setAgentBalanceUsd] = useState(0)
    const [loading, setLoading] = useState(false)
    const [status, setStatus] = useState('')
    const [step, setStep] = useState<'input' | 'withdrawing' | 'done'>('input')

    // Load agents (same as DepositModal — API first, localStorage fallback)
    useEffect(() => {
        if (!isOpen || !address) return
        const loadAgents = async () => {
            try {
                const resp = await fetchAgentStatus(address)
                if (resp.success && resp.agents?.length) {
                    const mapped = resp.agents.map((a: any) => ({
                        ...a, address: a.agent_address || a.address || a.smartAccount,
                    }))
                    setAgents(mapped)
                    setSelectedAgent(mapped[0])
                    return
                }
            } catch { /* fallback */ }
            const saved = localStorage.getItem('techne_deployed_agents')
            const local = saved ? JSON.parse(saved) : []
            setAgents(local)
            if (local.length) setSelectedAgent(local[0])
        }
        loadAgents()
    }, [isOpen, address])

    // Load agent balance on-chain
    useEffect(() => {
        if (!isOpen || !selectedAgent) return
        const agentAddr = selectedAgent.agent_address || selectedAgent.address
        if (!agentAddr) return
        const loadBalance = async () => {
            try {
                if (!(window as any).ethereum) { setAgentBalance(0); return }
                const { ethers } = await import('ethers')
                const provider = new ethers.BrowserProvider((window as any).ethereum)
                if (asset === 'ETH') {
                    const bal = await provider.getBalance(agentAddr)
                    setAgentBalance(parseFloat(ethers.formatEther(bal)))
                    // Rough ETH price estimation
                    setAgentBalanceUsd(parseFloat(ethers.formatEther(bal)) * 2500)
                } else {
                    const tokenAddr = TOKENS[asset]?.address
                    if (!tokenAddr) { setAgentBalance(0); return }
                    const contract = new ethers.Contract(tokenAddr, ERC20_ABI, provider)
                    const bal = await contract.balanceOf(agentAddr)
                    const dec = TOKENS[asset].decimals
                    const parsed = parseFloat(ethers.formatUnits(bal, dec))
                    setAgentBalance(parsed)
                    setAgentBalanceUsd(asset === 'USDC' ? parsed : parsed * 2500)
                }
            } catch { setAgentBalance(0); setAgentBalanceUsd(0) }
        }
        loadBalance()
    }, [isOpen, selectedAgent, asset])

    const setPercent = (pct: number) => {
        setAmount((agentBalance * pct / 100).toFixed(asset === 'USDC' ? 2 : 6))
    }

    const setMax = () => setPercent(100)

    // Ensure Base network
    const ensureBase = async () => {
        if (!(window as any).ethereum) throw new Error('No wallet')
        const chainId = await (window as any).ethereum.request({ method: 'eth_chainId' })
        if (parseInt(chainId, 16) !== BASE_CHAIN_ID) {
            try {
                await (window as any).ethereum.request({
                    method: 'wallet_switchEthereumChain',
                    params: [{ chainId: '0x' + BASE_CHAIN_ID.toString(16) }],
                })
            } catch (e: any) {
                if (e.code === 4902) {
                    await (window as any).ethereum.request({
                        method: 'wallet_addEthereumChain',
                        params: [{
                            chainId: '0x' + BASE_CHAIN_ID.toString(16),
                            chainName: 'Base', rpcUrls: ['https://mainnet.base.org'],
                            nativeCurrency: { name: 'ETH', symbol: 'ETH', decimals: 18 },
                            blockExplorerUrls: ['https://basescan.org'],
                        }],
                    })
                } else throw e
            }
        }
    }

    // Execute withdrawal
    const executeWithdraw = async () => {
        if (!amount || parseFloat(amount) <= 0 || !address) return
        const agentAddr = selectedAgent?.agent_address || selectedAgent?.address
        if (!agentAddr) { setStatus('error:No agent address found'); return }

        setLoading(true)
        try {
            await ensureBase()
            const { ethers } = await import('ethers')
            const provider = new ethers.BrowserProvider((window as any).ethereum)
            const signer = await provider.getSigner()

            if (asset === 'ETH') {
                setStep('withdrawing'); setStatus('Withdrawing ETH...')
                const smartAccount = new ethers.Contract(agentAddr, SMART_ACCOUNT_ABI, signer)
                const tx = await smartAccount.execute(address, ethers.parseEther(amount), '0x')
                setStatus('Confirming...')
                await tx.wait()
            } else {
                setStep('withdrawing'); setStatus(`Withdrawing ${asset}...`)
                const tokenAddr = TOKENS[asset]?.address
                if (!tokenAddr) throw new Error('Unknown token')
                const iface = new ethers.Interface(ERC20_ABI)
                const decimals = TOKENS[asset].decimals
                const calldata = iface.encodeFunctionData('transfer', [address, ethers.parseUnits(amount, decimals)])
                const smartAccount = new ethers.Contract(agentAddr, SMART_ACCOUNT_ABI, signer)
                const tx = await smartAccount.execute(tokenAddr, 0, calldata)
                setStatus('Confirming...')
                await tx.wait()
            }

            setStep('done'); setStatus('done')
            setTimeout(() => { onClose(); setStep('input'); setAmount(''); setStatus('') }, 2000)
        } catch (e: any) {
            setStatus(`error:${e.message?.slice(0, 80) || 'Transaction failed'}`)
            setStep('input')
        }
        setLoading(false)
    }

    if (!isOpen) return null

    return (
        <AnimatePresence>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="fixed inset-0 z-[10000] flex items-center justify-center"
                style={{ background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(8px)' }}
                onClick={e => { if (e.target === e.currentTarget) onClose() }}>
                <motion.div initial={{ opacity: 0, y: 12, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 12 }} className="w-[400px] max-w-[95vw] rounded-xl overflow-hidden"
                    style={{
                        background: 'var(--color-glass, rgba(22,22,26,0.97))',
                        border: '1px solid var(--color-glass-border, rgba(255,255,255,0.08))',
                        boxShadow: '0 16px 48px rgba(0,0,0,0.5)'
                    }}>

                    {/* Header */}
                    <div className="flex items-center gap-3 px-5 py-4"
                        style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        <div className="w-9 h-9 rounded-lg flex items-center justify-center"
                            style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)' }}>
                            <ArrowDownLeft className="w-4.5 h-4.5" style={{ color: '#ef4444' }} />
                        </div>
                        <div className="flex-1 min-w-0">
                            <h2 className="text-sm font-semibold text-white m-0 leading-tight">Withdraw from Agent</h2>
                            <p className="text-[11px] mt-0.5 leading-tight" style={{ color: 'var(--color-text-muted, rgba(255,255,255,0.45))' }}>
                                Withdraw {asset} to your wallet
                            </p>
                        </div>
                        <button onClick={onClose} className="w-7 h-7 rounded-md flex items-center justify-center cursor-pointer transition-colors hover:bg-white/10"
                            style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.08)', color: 'var(--color-text-muted)' }}>
                            <X className="w-3.5 h-3.5" />
                        </button>
                    </div>

                    {/* Body */}
                    <div className="px-5 py-4 space-y-4">
                        {/* Agent Selector */}
                        <div>
                            <label className="block text-[10px] uppercase tracking-widest font-medium mb-1.5"
                                style={{ color: 'var(--color-text-muted)' }}>Select Agent</label>
                            <div className="relative">
                                <select value={selectedAgent?.id || ''}
                                    onChange={e => setSelectedAgent(agents.find(a => a.id === e.target.value) || null)}
                                    className="w-full px-3 py-2.5 rounded-lg text-[13px] font-medium cursor-pointer pr-8"
                                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.08)', color: '#fff', appearance: 'none' }}>
                                    {agents.length === 0 ? <option value="">No agents deployed</option> :
                                        agents.map(a => (
                                            <option key={a.id} value={a.id}>
                                                {a.name || a.preset || 'Agent'} — {(a.agent_address || a.address || '').slice(0, 10)}...
                                            </option>
                                        ))
                                    }
                                </select>
                                <ChevronDown className="w-3.5 h-3.5 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: 'var(--color-text-muted)' }} />
                            </div>
                        </div>

                        {/* Asset Selector */}
                        <div>
                            <label className="block text-[10px] uppercase tracking-widest font-medium mb-1.5"
                                style={{ color: 'var(--color-text-muted)' }}>Select Asset</label>
                            <div className="grid grid-cols-3 gap-2">
                                {Object.keys(TOKENS).map(t => (
                                    <button key={t} onClick={() => setAsset(t)}
                                        className="py-2.5 px-3 rounded-lg font-semibold flex items-center justify-center gap-2 cursor-pointer transition-all text-[13px]"
                                        style={{
                                            background: asset === t ? 'rgba(212,168,83,0.1)' : 'rgba(0,0,0,0.2)',
                                            border: asset === t ? '1.5px solid var(--color-gold, #d4a853)' : '1px solid rgba(255,255,255,0.08)',
                                            color: asset === t ? '#fff' : 'rgba(255,255,255,0.6)',
                                        }}>
                                        <img src={TOKENS[t].image} alt={t} className="w-5 h-5 rounded-full" style={{ objectFit: 'cover' }} />
                                        {t}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Balance Info */}
                        <div className="rounded-lg overflow-hidden" style={{ border: '1px solid rgba(255,255,255,0.06)' }}>
                            {[
                                { label: 'Agent Balance', value: `${agentBalance.toFixed(asset === 'USDC' ? 2 : 6)} ${asset}`, color: 'var(--color-gold, #d4a853)' },
                                { label: 'Value', value: formatUsd(agentBalanceUsd), color: 'rgba(255,255,255,0.7)' },
                                { label: 'Network', value: 'Base', color: '#fff', hasNetworkIcon: true },
                            ].map((r, i) => (
                                <div key={i} className="flex justify-between items-center px-4 py-2.5"
                                    style={{ background: i % 2 === 0 ? 'rgba(0,0,0,0.15)' : 'rgba(0,0,0,0.08)', borderBottom: i < 2 ? '1px solid rgba(255,255,255,0.04)' : 'none' }}>
                                    <span className="text-[12px] flex items-center gap-2" style={{ color: 'var(--color-text-muted)' }}>
                                        {r.hasNetworkIcon && <Globe className="w-3 h-3" />} {r.label}
                                    </span>
                                    <span className="font-semibold text-[12px] flex items-center gap-1.5" style={{ color: r.color }}>
                                        {r.hasNetworkIcon && <img src="/icons/base.png" alt="Base" className="w-3.5 h-3.5 rounded-full" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />}
                                        {r.value}
                                    </span>
                                </div>
                            ))}
                        </div>

                        {/* Amount Input */}
                        <div>
                            <label className="block text-[10px] uppercase tracking-widest font-medium mb-1.5" style={{ color: 'var(--color-text-muted)' }}>
                                Amount ({asset})
                            </label>
                            <div className="flex rounded-lg overflow-hidden" style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.08)' }}>
                                <input type="number" value={amount} onChange={e => setAmount(e.target.value)}
                                    placeholder="0.00" min="0" step="any"
                                    className="flex-1 bg-transparent border-none px-3 py-3 text-lg font-medium text-white outline-none"
                                    style={{ appearance: 'textfield' }} />
                                <button onClick={setMax} className="px-4 font-semibold text-[11px] cursor-pointer transition-colors"
                                    style={{
                                        background: 'rgba(239,68,68,0.1)',
                                        borderLeft: '1px solid rgba(255,255,255,0.08)', color: '#ef4444'
                                    }}>MAX</button>
                            </div>
                            {/* Presets */}
                            <div className="flex gap-1.5 mt-1.5">
                                {[25, 50, 75, 100].map(pct => (
                                    <button key={pct} onClick={() => setPercent(pct)}
                                        className="flex-1 py-1.5 rounded-md text-[10px] font-semibold cursor-pointer transition-colors"
                                        style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.5)' }}>
                                        {pct}%
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Warning */}
                        {parseFloat(amount) > agentBalance && agentBalance > 0 && (
                            <div className="flex items-center gap-2 p-2 rounded-lg text-[11px]"
                                style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.15)', color: '#ef4444' }}>
                                <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                                Amount exceeds available balance
                            </div>
                        )}

                        {/* Status */}
                        {status && (
                            <div className="text-center text-[11px] py-1 flex items-center justify-center gap-1.5"
                                style={{ color: status.startsWith('error:') ? '#ef4444' : status === 'done' ? '#22c55e' : 'var(--color-gold, #d4a853)' }}>
                                {status === 'done' ? <><CircleCheck className="w-3.5 h-3.5" /> Withdrawal successful!</> :
                                    status.startsWith('error:') ? <><CircleX className="w-3.5 h-3.5" /> {status.replace('error:', '')}</> :
                                        status}
                            </div>
                        )}

                        {/* CTA */}
                        <motion.button whileHover={{ y: -1 }} whileTap={{ scale: 0.98 }}
                            onClick={executeWithdraw} disabled={loading || !amount || parseFloat(amount) <= 0}
                            className="w-full py-3 rounded-lg text-[13px] font-semibold flex items-center justify-center gap-2 cursor-pointer transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                            style={{ background: 'linear-gradient(135deg, #ef4444, #dc2626)', color: '#fff', border: 'none' }}>
                            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowDownLeft className="w-4 h-4" />}
                            {step === 'withdrawing' ? 'Withdrawing...' : step === 'done' ? 'Done!' : 'Confirm Withdrawal'}
                        </motion.button>

                        <p className="text-[10px] text-center leading-relaxed" style={{ color: 'rgba(255,255,255,0.3)' }}>
                            Withdrawal will be sent directly to your connected wallet on Base.
                        </p>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    )
}
