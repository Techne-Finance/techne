/**
 * Deposit Modal — Premium styled, porting agent-wallet-ui.js showDepositModal()
 * Features: Agent selector, token selector (USDC/ETH), amount input with MAX,
 * summary card (APY, fee, network), approve & deposit CTA
 */
import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Loader2, Vault, ChevronDown, Percent, Globe, CircleCheck, CircleX, Send } from 'lucide-react'
import { useWalletStore } from '@/stores/walletStore'
import { fetchAgentStatus } from '@/lib/api'

// Token definitions matching agent-wallet-ui.js
const TOKENS: Record<string, { address: string | null; decimals: number; symbol: string; image: string; isNative?: boolean }> = {
    USDC: { address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', decimals: 6, symbol: 'USDC', image: '/icons/usdc.png' },
    ETH: { address: null, decimals: 18, symbol: 'ETH', image: '/icons/ethereum.png', isNative: true },
    WETH: { address: '0x4200000000000000000000000000000000000006', decimals: 18, symbol: 'WETH', image: '/icons/ethereum.png' },
}

// Smart Account Factory V3 (kept for future createSmartAccount flow)
// const FACTORY_ADDRESS = '0x36945Cc50Aa50E7473231Eb57731dbffEf60C3a4'

const ERC20_ABI = [
    'function approve(address spender, uint256 amount) returns (bool)',
    'function balanceOf(address account) view returns (uint256)',
    'function allowance(address owner, address spender) view returns (uint256)',
    'function decimals() view returns (uint8)',
]

// BASE chain enforcement
const BASE_CHAIN_ID = 8453

interface Agent {
    id: string; name?: string; preset?: string;
    address?: string; agent_address?: string; smartAccount?: string;
}

interface DepositModalProps {
    isOpen: boolean
    onClose: () => void
}

export function DepositModal({ isOpen, onClose }: DepositModalProps) {
    const { address } = useWalletStore()
    const [agents, setAgents] = useState<Agent[]>([])
    const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)
    const [selectedToken, setSelectedToken] = useState<string>('USDC')
    const [amount, setAmount] = useState('')
    const [balance, setBalance] = useState('--')
    const [loading, setLoading] = useState(false)
    const [status, setStatus] = useState('')
    const [step, setStep] = useState<'input' | 'approving' | 'depositing' | 'done'>('input')

    // Load agents
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

    // Load balance
    useEffect(() => {
        if (!isOpen || !address) return
        const loadBalance = async () => {
            try {
                if (!(window as any).ethereum) { setBalance('No wallet'); return }
                const { ethers } = await import('ethers')
                const provider = new ethers.BrowserProvider((window as any).ethereum)
                if (TOKENS[selectedToken]?.isNative) {
                    const bal = await provider.getBalance(address)
                    setBalance(ethers.formatEther(bal))
                } else {
                    const tokenAddr = TOKENS[selectedToken]?.address
                    if (!tokenAddr) { setBalance('--'); return }
                    const token = new ethers.Contract(tokenAddr, ERC20_ABI, provider)
                    const bal = await token.balanceOf(address)
                    setBalance(ethers.formatUnits(bal, TOKENS[selectedToken].decimals))
                }
            } catch { setBalance('--') }
        }
        loadBalance()
    }, [isOpen, address, selectedToken])

    const setMax = () => setAmount(balance !== '--' ? balance : '')

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

    // Execute deposit
    const executeDeposit = async () => {
        if (!amount || parseFloat(amount) <= 0) return
        if (!selectedAgent?.address && !selectedAgent?.agent_address) {
            setStatus('No agent address found'); return
        }
        const agentAddr = selectedAgent.agent_address || selectedAgent.address!

        setLoading(true)
        try {
            await ensureBase()
            const { ethers } = await import('ethers')
            const provider = new ethers.BrowserProvider((window as any).ethereum)
            const signer = await provider.getSigner()

            if (TOKENS[selectedToken]?.isNative) {
                setStep('depositing'); setStatus('Sending ETH...')
                const tx = await signer.sendTransaction({
                    to: agentAddr,
                    value: ethers.parseEther(amount),
                })
                setStatus('Confirming...')
                await tx.wait()
            } else {
                // ERC20: approve + transfer
                const tokenAddr = TOKENS[selectedToken].address!
                const decimals = TOKENS[selectedToken].decimals
                const erc20 = new ethers.Contract(tokenAddr, ERC20_ABI, signer)
                const amountWei = ethers.parseUnits(amount, decimals)

                // Check allowance
                const currentAllowance = await erc20.allowance(address, agentAddr)
                if (currentAllowance < amountWei) {
                    setStep('approving'); setStatus(`Approving ${selectedToken}...`)
                    const approveTx = await erc20.approve(agentAddr, amountWei)
                    await approveTx.wait()
                }

                // Transfer
                setStep('depositing'); setStatus(`Transferring ${selectedToken}...`)
                const transferAbi = ['function transfer(address to, uint256 amount) returns (bool)']
                const erc20Transfer = new ethers.Contract(tokenAddr, transferAbi, signer)
                const tx = await erc20Transfer.transfer(agentAddr, amountWei)
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
                            style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.25)' }}>
                            <Vault className="w-4.5 h-4.5" style={{ color: '#22c55e' }} />
                        </div>
                        <div className="flex-1 min-w-0">
                            <h2 className="text-sm font-semibold text-white m-0 leading-tight">Fund Agent Vault</h2>
                            <p className="text-[11px] mt-0.5 leading-tight" style={{ color: 'var(--color-text-muted, rgba(255,255,255,0.45))' }}>
                                Deposit {selectedToken} for autonomous yield
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

                        {/* Token Selector */}
                        <div>
                            <label className="block text-[10px] uppercase tracking-widest font-medium mb-1.5"
                                style={{ color: 'var(--color-text-muted)' }}>Select Token</label>
                            <div className="grid grid-cols-3 gap-2">
                                {Object.keys(TOKENS).map(token => (
                                    <button key={token} onClick={() => setSelectedToken(token)}
                                        className="py-2.5 px-3 rounded-lg font-semibold flex items-center justify-center gap-2 cursor-pointer transition-all text-[13px]"
                                        style={{
                                            background: selectedToken === token ? 'rgba(212,168,83,0.1)' : 'rgba(0,0,0,0.2)',
                                            border: selectedToken === token ? '1.5px solid var(--color-gold, #d4a853)' : '1px solid rgba(255,255,255,0.08)',
                                            color: selectedToken === token ? '#fff' : 'rgba(255,255,255,0.6)',
                                        }}>
                                        <img src={TOKENS[token].image} alt={token} className="w-5 h-5 rounded-full" style={{ objectFit: 'cover' }} />
                                        {token}
                                        {token === 'ETH' && (
                                            <span className="px-1.5 py-0.5 rounded text-[8px] font-bold uppercase tracking-wide"
                                                style={{ background: 'rgba(99,102,241,0.15)', color: '#818cf8' }}>Gas</span>
                                        )}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Amount Input */}
                        <div>
                            <label className="block text-[10px] uppercase tracking-widest font-medium mb-1.5" style={{ color: 'var(--color-text-muted)' }}>
                                Amount ({selectedToken})
                            </label>
                            <div className="flex rounded-lg overflow-hidden" style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.08)' }}>
                                <input type="number" value={amount} onChange={e => setAmount(e.target.value)}
                                    placeholder="0.00" min="0.001" step="any"
                                    className="flex-1 bg-transparent border-none px-3 py-3 text-lg font-medium text-white outline-none"
                                    style={{ appearance: 'textfield' }} />
                                <button onClick={setMax} className="px-4 font-semibold text-[11px] cursor-pointer transition-colors"
                                    style={{
                                        background: 'rgba(34,197,94,0.1)',
                                        borderLeft: '1px solid rgba(255,255,255,0.08)', color: '#22c55e'
                                    }}>MAX</button>
                            </div>
                            <div className="flex justify-between mt-1.5 text-[11px]" style={{ color: 'var(--color-text-muted)' }}>
                                <span>Balance: <span style={{ color: 'var(--color-gold, #d4a853)' }}>{parseFloat(balance).toFixed(TOKENS[selectedToken]?.decimals === 18 ? 6 : 2)}</span> {selectedToken}</span>
                                <span>Min: {TOKENS[selectedToken]?.isNative ? '0.001 ETH' : `10 ${selectedToken}`}</span>
                            </div>
                        </div>

                        {/* Summary Card */}
                        <div className="rounded-lg overflow-hidden" style={{ border: '1px solid rgba(255,255,255,0.06)' }}>
                            {[
                                { label: 'Estimated APY', value: '—', icon: <Percent className="w-3 h-3" />, color: '#22c55e' },
                                { label: 'Performance Fee', value: '10% of yield', icon: <Percent className="w-3 h-3" />, color: 'rgba(255,255,255,0.7)' },
                                { label: 'Network', value: 'Base', icon: <Globe className="w-3 h-3" />, color: '#fff', hasNetworkIcon: true },
                            ].map((r, i) => (
                                <div key={i} className="flex justify-between items-center px-4 py-2.5"
                                    style={{ background: i % 2 === 0 ? 'rgba(0,0,0,0.15)' : 'rgba(0,0,0,0.08)', borderBottom: i < 2 ? '1px solid rgba(255,255,255,0.04)' : 'none' }}>
                                    <span className="text-[12px] flex items-center gap-2" style={{ color: 'var(--color-text-muted)' }}>
                                        {r.icon} {r.label}
                                    </span>
                                    <span className="font-semibold text-[12px] flex items-center gap-1.5" style={{ color: r.color }}>
                                        {r.hasNetworkIcon && <img src="/icons/base.png" alt="Base" className="w-3.5 h-3.5 rounded-full" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />}
                                        {r.value}
                                    </span>
                                </div>
                            ))}
                        </div>

                        {/* Status */}
                        {status && (
                            <div className="text-center text-[11px] py-1 flex items-center justify-center gap-1.5"
                                style={{ color: status.startsWith('error:') ? '#ef4444' : status === 'done' ? '#22c55e' : 'var(--color-gold, #d4a853)' }}>
                                {status === 'done' ? <><CircleCheck className="w-3.5 h-3.5" /> Deposit successful!</> :
                                    status.startsWith('error:') ? <><CircleX className="w-3.5 h-3.5" /> {status.replace('error:', '')}</> :
                                        status}
                            </div>
                        )}

                        {/* CTA */}
                        <motion.button whileHover={{ y: -1 }} whileTap={{ scale: 0.98 }}
                            onClick={executeDeposit} disabled={loading || !amount || parseFloat(amount) <= 0}
                            className="w-full py-3 rounded-lg text-[13px] font-semibold flex items-center justify-center gap-2 cursor-pointer transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                            style={{ background: 'linear-gradient(135deg, #22c55e, #16a34a)', color: '#fff', border: 'none' }}>
                            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                            {step === 'approving' ? 'Approving...' : step === 'depositing' ? 'Depositing...' : step === 'done' ? 'Done!' : 'Approve & Deposit'}
                        </motion.button>

                        <p className="text-[10px] text-center leading-relaxed" style={{ color: 'rgba(255,255,255,0.3)' }}>
                            By depositing, you authorize the Techne Agent to manage your funds across DeFi protocols.
                        </p>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    )
}
