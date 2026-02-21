/**
 * Network Selector Modal — porting button-handler.js showNetworkSelector()
 * Grid of supported chains: Base (active), Ethereum, Arbitrum, Optimism, Polygon, Solana (soon)
 */
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'

const NETWORKS = [
    { id: 'base', name: 'Base', icon: '/icons/base.png', active: true, chainId: 8453 },
    { id: 'ethereum', name: 'Ethereum', icon: '/icons/ethereum.png', active: false, chainId: 1 },
    { id: 'arbitrum', name: 'Arbitrum', icon: '/icons/arbitrum.png', active: false, chainId: 42161 },
    { id: 'optimism', name: 'Optimism', icon: '/icons/optimism.png', active: false, chainId: 10 },
    { id: 'polygon', name: 'Polygon', icon: '/icons/polygon.png', active: false, chainId: 137 },
    { id: 'solana', name: 'Solana', icon: '/icons/solana.png', active: false, soon: true, chainId: 0 },
]

interface Props { isOpen: boolean; onClose: () => void }

export function NetworkSelectorModal({ isOpen, onClose }: Props) {
    const [switching, setSwitching] = useState<string | null>(null)

    const switchNetwork = async (network: typeof NETWORKS[0]) => {
        if (network.soon || !(window as any).ethereum) return
        setSwitching(network.id)
        try {
            await (window as any).ethereum.request({
                method: 'wallet_switchEthereumChain',
                params: [{ chainId: '0x' + network.chainId.toString(16) }],
            })
            onClose()
        } catch (e: any) {
            if (e.code === 4902) {
                // Chain not added - would need wallet_addEthereumChain
                console.warn('Chain not added to wallet:', network.name)
            }
        }
        setSwitching(null)
    }

    if (!isOpen) return null

    return (
        <AnimatePresence>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="fixed inset-0 z-[10000] flex items-center justify-center"
                style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)' }}
                onClick={e => { if (e.target === e.currentTarget) onClose() }}>
                <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
                    className="w-[420px] max-w-[90vw] rounded-2xl p-6 relative"
                    style={{
                        background: 'linear-gradient(145deg, rgba(20,20,25,0.98), rgba(10,10,15,0.98))',
                        border: '1px solid rgba(212,168,83,0.2)'
                    }}>
                    <button onClick={onClose} className="absolute right-4 top-4 text-xl cursor-pointer bg-transparent border-none"
                        style={{ color: '#9ca3af' }}>
                        <X className="w-5 h-5" />
                    </button>
                    <h2 className="text-lg font-semibold text-white mb-5">Select Network</h2>
                    <div className="grid grid-cols-3 gap-3">
                        {NETWORKS.map(n => (
                            <button key={n.id} onClick={() => switchNetwork(n)}
                                disabled={!!n.soon || switching === n.id}
                                className="flex flex-col items-center gap-2 py-4 px-3 rounded-xl cursor-pointer transition-all relative"
                                style={{
                                    background: n.active ? 'rgba(212,168,83,0.15)' : 'rgba(255,255,255,0.03)',
                                    border: `1px solid ${n.active ? 'rgba(212,168,83,0.5)' : 'rgba(255,255,255,0.08)'}`,
                                    opacity: n.soon ? 0.5 : 1,
                                    cursor: n.soon ? 'not-allowed' : 'pointer',
                                }}>
                                <img src={n.icon} alt={n.name} className="w-8 h-8 rounded-full object-cover"
                                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
                                <span className="text-xs font-medium text-white">{n.name}</span>
                                {n.soon && (
                                    <span className="absolute top-1 right-1 px-1.5 py-0.5 rounded text-[9px] font-bold"
                                        style={{ background: '#d4a853', color: '#000' }}>SOON</span>
                                )}
                                {n.active && (
                                    <span className="absolute top-1 left-1 w-1.5 h-1.5 rounded-full" style={{ background: '#22c55e' }} />
                                )}
                            </button>
                        ))}
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    )
}
