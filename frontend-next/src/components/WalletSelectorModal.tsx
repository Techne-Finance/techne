/**
 * Wallet Selector Modal — Multi-wallet connection support
 * Ported from frontend/wallet-connect.js
 *
 * Supports: MetaMask, Coinbase, WalletConnect, Trust, Phantom, Rabby
 * Uses EIP-6963 provider detection when available
 */

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Loader2, ExternalLink, Wallet } from 'lucide-react'
import { useWalletStore } from '@/stores/walletStore'
import { toast } from '@/components/Toast'

// ============ Wallet Definitions ============

export interface WalletOption {
    id: string
    name: string
    icon: string
    description: string
    rdns?: string     // EIP-6963 reverse DNS
    color: string
    downloadUrl?: string
}

const WALLETS: WalletOption[] = [
    {
        id: 'metamask',
        name: 'MetaMask',
        icon: 'https://upload.wikimedia.org/wikipedia/commons/3/36/MetaMask_Fox.svg',
        description: 'Browser extension wallet',
        rdns: 'io.metamask',
        color: '#FF6B2C',
        downloadUrl: 'https://metamask.io/download/',
    },
    {
        id: 'coinbase',
        name: 'Coinbase Wallet',
        icon: 'https://altcoinsbox.com/wp-content/uploads/2022/12/coinbase-logo-300x300.webp',
        description: 'Coinbase smart wallet',
        rdns: 'com.coinbase.wallet',
        color: '#0052FF',
        downloadUrl: 'https://www.coinbase.com/wallet',
    },
    {
        id: 'trust',
        name: 'Trust Wallet',
        icon: 'https://trustwallet.com/assets/images/media/assets/TWT.png',
        description: 'Multi-chain mobile wallet',
        rdns: 'com.trustwallet.app',
        color: '#3375BB',
        downloadUrl: 'https://trustwallet.com/',
    },
    {
        id: 'phantom',
        name: 'Phantom',
        icon: '/icons/wallets/phantom.svg',
        description: 'Multi-chain wallet',
        rdns: 'app.phantom',
        color: '#AB9FF2',
        downloadUrl: 'https://phantom.app/',
    },
    {
        id: 'rabby',
        name: 'Rabby',
        icon: '/icons/wallets/rabby.svg',
        description: 'Security-focused wallet',
        rdns: 'io.rabby',
        color: '#8697FF',
        downloadUrl: 'https://rabby.io/',
    },
    {
        id: 'walletconnect',
        name: 'WalletConnect',
        icon: 'https://avatars.githubusercontent.com/u/37784886?s=200&v=4',
        description: 'Scan with mobile wallet',
        color: '#3B99FC',
    },
]

// ============ Detection ============

function detectAvailableWallets(): string[] {
    const available: string[] = []
    const ethereum = (window as any).ethereum

    if (!ethereum) return available

    // Check if MetaMask
    if (ethereum.isMetaMask) available.push('metamask')

    // Check Coinbase
    if (ethereum.isCoinbaseWallet || (ethereum.providers?.some((p: any) => p.isCoinbaseWallet))) {
        available.push('coinbase')
    }

    // Check Trust
    if (ethereum.isTrust || ethereum.isTrustWallet) {
        available.push('trust')
    }

    // Check Phantom (EVM mode)
    if ((window as any).phantom?.ethereum) {
        available.push('phantom')
    }

    // Check Rabby
    if (ethereum.isRabby) {
        available.push('rabby')
    }

    // EIP-6963 providers
    if (typeof document !== 'undefined') {
        const eip6963Providers = (window as any).__eip6963_providers || []
        for (const provider of eip6963Providers) {
            const rdns = provider.info?.rdns
            const wallet = WALLETS.find(w => w.rdns === rdns)
            if (wallet && !available.includes(wallet.id)) {
                available.push(wallet.id)
            }
        }
    }

    return available
}

function getProvider(walletId: string): any {
    const ethereum = (window as any).ethereum

    switch (walletId) {
        case 'metamask':
            // Handle multi-provider scenario
            if (ethereum?.providers) {
                return ethereum.providers.find((p: any) => p.isMetaMask) || ethereum
            }
            return ethereum

        case 'coinbase':
            if (ethereum?.providers) {
                return ethereum.providers.find((p: any) => p.isCoinbaseWallet)
            }
            return ethereum?.isCoinbaseWallet ? ethereum : null

        case 'trust':
            return ethereum?.isTrust ? ethereum : null

        case 'phantom':
            return (window as any).phantom?.ethereum || null

        case 'rabby':
            return ethereum?.isRabby ? ethereum : null

        default:
            return ethereum
    }
}

// ============ Component ============

interface Props {
    isOpen: boolean
    onClose: () => void
}

export function WalletSelectorModal({ isOpen, onClose }: Props) {
    const [available, setAvailable] = useState<string[]>([])
    const [connecting, setConnecting] = useState<string | null>(null)

    useEffect(() => {
        if (isOpen) {
            const detected = detectAvailableWallets()
            setAvailable(detected)
        }
    }, [isOpen])

    const handleConnect = useCallback(async (walletId: string) => {
        const provider = getProvider(walletId)

        if (!provider) {
            const wallet = WALLETS.find(w => w.id === walletId)
            if (wallet?.downloadUrl) {
                window.open(wallet.downloadUrl, '_blank')
                toast.info(`Install ${wallet.name} and refresh the page`)
            }
            return
        }

        setConnecting(walletId)

        try {
            const accounts = await provider.request({
                method: 'eth_requestAccounts',
            })

            if (accounts && accounts.length > 0) {
                const address = accounts[0]

                // Get chain ID
                const chainIdHex = await provider.request({ method: 'eth_chainId' })
                const chainId = parseInt(chainIdHex, 16)

                // Set wallet state directly — no second popup
                useWalletStore.setState({
                    isConnected: true,
                    address,
                    chainId,
                    provider: null,
                    signer: null,
                })
                localStorage.setItem('techne_wallet_connected', address)

                // Listen for account/chain changes
                provider.on?.('accountsChanged', (accs: string[]) => {
                    if (accs.length === 0) {
                        useWalletStore.getState().disconnect()
                    } else {
                        useWalletStore.setState({ address: accs[0] })
                        localStorage.setItem('techne_wallet_connected', accs[0])
                    }
                })
                provider.on?.('chainChanged', (hex: string) => {
                    useWalletStore.setState({ chainId: parseInt(hex, 16) })
                })

                toast.success(`Connected via ${WALLETS.find(w => w.id === walletId)?.name}`)
                onClose()
            }
        } catch (err: any) {
            if (err.code === 4001) {
                toast.warning('Connection rejected')
            } else if (err.code === -32002) {
                toast.warning('MetaMask request already pending — check the extension')
            } else {
                toast.error(`Connection failed: ${err.message || err}`)
            }
        } finally {
            setConnecting(null)
        }
    }, [onClose])

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 z-[100] flex items-center justify-center"
                    style={{ background: 'rgba(0,0,0,0.85)' }}
                    onClick={onClose}
                >
                    <motion.div
                        initial={{ scale: 0.9, y: 20 }}
                        animate={{ scale: 1, y: 0 }}
                        exit={{ scale: 0.9, y: 20 }}
                        onClick={e => e.stopPropagation()}
                        className="glass-card p-6 max-w-sm mx-4 w-full"
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between mb-5">
                            <div className="flex items-center gap-2">
                                <Wallet className="w-5 h-5" style={{ color: 'var(--color-gold)' }} />
                                <h3 className="font-heading text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
                                    Connect Wallet
                                </h3>
                            </div>
                            <button
                                onClick={onClose}
                                className="cursor-pointer"
                                style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)' }}
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {/* Wallet list */}
                        <div className="space-y-2">
                            {WALLETS.map(wallet => {
                                const isAvailable = available.includes(wallet.id)
                                const isConnecting = connecting === wallet.id
                                const isWC = wallet.id === 'walletconnect'

                                return (
                                    <motion.button
                                        key={wallet.id}
                                        whileHover={{ scale: 1.01 }}
                                        whileTap={{ scale: 0.98 }}
                                        onClick={() => handleConnect(wallet.id)}
                                        disabled={isConnecting || isWC}
                                        className="w-full flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all group"
                                        style={{
                                            background: isConnecting
                                                ? 'var(--color-gold-dim)'
                                                : 'var(--color-glass)',
                                            border: `1px solid ${isConnecting ? 'var(--color-gold-border)' : 'var(--color-glass-border)'}`,
                                            opacity: isWC ? 0.5 : 1,
                                        }}
                                    >
                                        {/* Icon */}
                                        <div
                                            className="w-10 h-10 rounded-xl flex items-center justify-center overflow-hidden flex-shrink-0"
                                            style={{
                                                background: `${wallet.color}20`,
                                                border: `1px solid ${wallet.color}40`,
                                            }}
                                        >
                                            <img src={wallet.icon} alt={wallet.name} className="w-7 h-7 object-contain" />
                                        </div>

                                        {/* Name */}
                                        <div className="flex-1 text-left">
                                            <div className="text-sm font-heading font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                                                {wallet.name}
                                            </div>
                                            <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                                                {isWC ? 'Coming soon' : wallet.description}
                                            </div>
                                        </div>

                                        {/* Status badge */}
                                        <div className="flex-shrink-0">
                                            {isConnecting ? (
                                                <Loader2 className="w-4 h-4 animate-spin" style={{ color: 'var(--color-gold)' }} />
                                            ) : isAvailable ? (
                                                <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                                                    style={{ background: 'var(--color-green)', color: '#000' }}>
                                                    Detected
                                                </span>
                                            ) : !isWC ? (
                                                <ExternalLink className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity"
                                                    style={{ color: 'var(--color-text-muted)' }} />
                                            ) : null}
                                        </div>
                                    </motion.button>
                                )
                            })}
                        </div>

                        {/* Footer note */}
                        <p className="text-center mt-4 text-xs" style={{ color: 'var(--color-text-muted)' }}>
                            Techne never stores your private keys.
                            <br />
                            Base network is required for all transactions.
                        </p>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    )
}
