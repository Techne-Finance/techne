/**
 * Credits Store — Supabase-backed, per-wallet credit system
 * localStorage used as local cache; Supabase is source of truth
 *
 * Model:
 * - 20 credits = 1 filter/explore search
 * - 10 credits = 1 pool verification
 * - 100 credits = 0.10 USDC purchase
 * - Premium = 500 credits/day
 */

import { create } from 'zustand'
import { fetchCredits, initCreditsApi, addCreditsApi, useCreditsApi } from '@/lib/api'

const STORAGE_KEY = 'techne_credits'

export const CREDIT_COSTS = {
    FILTER: 20,
    VERIFY: 10,
    PURCHASE_AMOUNT: 100,
    PRICE_USDC: 0.1,
    PREMIUM_DAILY: 500,
    WELCOME_BONUS: 50,
} as const

interface CreditsState {
    credits: number
    walletAddress: string | null
    loading: boolean
    getCredits: () => number
    setCredits: (amount: number) => void
    addCredits: (amount: number) => void
    useCredits: (cost: number) => boolean
    canAfford: (cost: number) => boolean
    initCredits: (walletAddress?: string) => void
    syncWithBackend: (walletAddress: string) => Promise<void>
}

function loadLocalCredits(): number {
    try {
        const stored = localStorage.getItem(STORAGE_KEY)
        if (stored !== null) return parseInt(stored, 10) || 0
    } catch { }
    return 0
}

function saveLocalCredits(amount: number) {
    try {
        localStorage.setItem(STORAGE_KEY, String(Math.max(0, amount)))
    } catch { }
}

export const useCreditsStore = create<CreditsState>((set, get) => ({
    credits: loadLocalCredits(),
    walletAddress: null,
    loading: false,

    getCredits: () => get().credits,

    setCredits: (amount) => {
        const clamped = Math.max(0, amount)
        saveLocalCredits(clamped)
        set({ credits: clamped })
    },

    addCredits: (amount) => {
        const wallet = get().walletAddress
        if (wallet) {
            // Backend-backed: call API
            addCreditsApi(wallet, amount)
                .then(res => {
                    saveLocalCredits(res.credits)
                    set({ credits: res.credits })
                })
                .catch(err => {
                    console.error('[Credits] Failed to add via API:', err)
                    // Fallback: local only
                    const next = get().credits + amount
                    saveLocalCredits(next)
                    set({ credits: next })
                })
        } else {
            // No wallet connected — local only
            const next = get().credits + amount
            saveLocalCredits(next)
            set({ credits: next })
        }
    },

    useCredits: (cost) => {
        const current = get().credits
        if (current < cost) return false
        const next = current - cost

        // Update locally first (optimistic)
        saveLocalCredits(next)
        set({ credits: next })

        // Sync to backend if wallet connected
        const wallet = get().walletAddress
        if (wallet) {
            useCreditsApi(wallet, cost).catch(err => {
                console.error('[Credits] Failed to use via API:', err)
            })
        }
        return true
    },

    canAfford: (cost) => get().credits >= cost,

    initCredits: (walletAddress?: string) => {
        if (walletAddress) {
            // Wallet connected — sync with Supabase
            set({ walletAddress, loading: true })
            initCreditsApi(walletAddress)
                .then(res => {
                    saveLocalCredits(res.credits)
                    set({ credits: res.credits, loading: false })
                    if (res.bonus_given) {
                        console.log(`[Credits] Welcome bonus: ${CREDIT_COSTS.WELCOME_BONUS} credits!`)
                    }
                })
                .catch(err => {
                    console.error('[Credits] Init failed:', err)
                    set({ credits: loadLocalCredits(), loading: false })
                })
        } else {
            // No wallet — use localStorage
            set({ credits: loadLocalCredits(), walletAddress: null })
        }
    },

    syncWithBackend: async (walletAddress: string) => {
        try {
            set({ walletAddress, loading: true })
            const res = await fetchCredits(walletAddress)
            saveLocalCredits(res.credits)
            set({ credits: res.credits, loading: false })
        } catch (err) {
            console.error('[Credits] Sync failed:', err)
            set({ credits: loadLocalCredits(), loading: false })
        }
    },
}))
