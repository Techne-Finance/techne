/**
 * Wallet Store — MetaMask / injected wallet connection
 * Ported from frontend/app.js connectWallet()
 */

import { create } from 'zustand'

interface WalletState {
    isConnected: boolean
    address: string | null
    chainId: number | null
    credits: number
    provider: any | null
    signer: any | null

    connect: () => Promise<void>
    disconnect: () => void
    setCredits: (credits: number) => void
}

export const useWalletStore = create<WalletState>((set, get) => ({
    isConnected: false,
    address: null,
    chainId: null,
    credits: 0,
    provider: null,
    signer: null,

    connect: async () => {
        const ethereum = (window as any).ethereum
        if (!ethereum) {
            alert('No Web3 wallet detected. Please install MetaMask.')
            return
        }

        try {
            // Force account picker (allows switching wallets)
            await ethereum.request({
                method: 'wallet_requestPermissions',
                params: [{ eth_accounts: {} }],
            })

            const accounts: string[] = await ethereum.request({ method: 'eth_accounts' })

            if (accounts && accounts.length > 0) {
                const address = accounts[0]

                // Get chain ID
                const chainIdHex = await ethereum.request({ method: 'eth_chainId' })
                const chainId = parseInt(chainIdHex, 16)

                // Try to create ethers provider/signer if available
                let provider = null
                let signer = null
                if ((window as any).ethers) {
                    provider = new (window as any).ethers.BrowserProvider(ethereum)
                    signer = await provider.getSigner()
                }

                set({
                    isConnected: true,
                    address,
                    chainId,
                    provider,
                    signer,
                })

                // Persist connection
                localStorage.setItem('techne_wallet_connected', address)

                // Listen for account/chain changes
                ethereum.on('accountsChanged', (accs: string[]) => {
                    if (accs.length === 0) {
                        get().disconnect()
                    } else {
                        set({ address: accs[0] })
                        localStorage.setItem('techne_wallet_connected', accs[0])
                    }
                })

                ethereum.on('chainChanged', (hex: string) => {
                    set({ chainId: parseInt(hex, 16) })
                })
            }
        } catch (e: any) {
            if (e.code === 4001) {
                console.log('[Wallet] Connection rejected by user')
            } else if (e.code === -32002) {
                alert('Please check MetaMask — request pending!')
            } else {
                console.error('[Wallet] Connection failed:', e)
            }
        }
    },

    disconnect: () => {
        set({
            isConnected: false,
            address: null,
            chainId: null,
            provider: null,
            signer: null,
        })
        localStorage.removeItem('techne_wallet_connected')
    },

    setCredits: (credits) => set({ credits }),
}))

// Auto-reconnect if previously connected
export function initWalletAutoConnect() {
    const saved = localStorage.getItem('techne_wallet_connected')
    const ethereum = (window as any).ethereum
    if (saved && ethereum) {
        ethereum.request({ method: 'eth_accounts' }).then((accounts: string[]) => {
            if (accounts.includes(saved)) {
                // Silent reconnect
                ethereum.request({ method: 'eth_chainId' }).then((hex: string) => {
                    useWalletStore.setState({
                        isConnected: true,
                        address: saved,
                        chainId: parseInt(hex, 16),
                    })
                })
            }
        }).catch(() => { })
    }
}
