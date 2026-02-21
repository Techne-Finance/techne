/**
 * Toast Notification System
 * Replaces the vanilla JS Toast module with React + Framer Motion
 */


import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, AlertTriangle, Info, XCircle, X } from 'lucide-react'
import { create } from 'zustand'

type ToastType = 'success' | 'error' | 'warning' | 'info'

interface ToastItem {
    id: number
    message: string
    type: ToastType
}

interface ToastStore {
    toasts: ToastItem[]
    show: (message: string, type?: ToastType) => void
    dismiss: (id: number) => void
}

let nextId = 0

export const useToastStore = create<ToastStore>((set) => ({
    toasts: [],

    show: (message, type = 'info') => {
        const id = nextId++
        set((s) => ({ toasts: [...s.toasts, { id, message, type }] }))
        // Auto dismiss after 4s
        setTimeout(() => {
            set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
        }, 4000)
    },

    dismiss: (id) => {
        set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
    },
}))

// Convenience global function
export const toast = {
    show: (msg: string, type?: ToastType) => useToastStore.getState().show(msg, type),
    success: (msg: string) => useToastStore.getState().show(msg, 'success'),
    error: (msg: string) => useToastStore.getState().show(msg, 'error'),
    warning: (msg: string) => useToastStore.getState().show(msg, 'warning'),
    info: (msg: string) => useToastStore.getState().show(msg, 'info'),
}

const ICON_MAP = {
    success: CheckCircle2,
    error: XCircle,
    warning: AlertTriangle,
    info: Info,
}

const COLOR_MAP = {
    success: 'var(--color-green)',
    error: '#ff4466',
    warning: 'var(--color-gold)',
    info: '#6ca6ff',
}

export function ToastContainer() {
    const { toasts, dismiss } = useToastStore()

    return (
        <div
            style={{
                position: 'fixed',
                bottom: 20,
                right: 20,
                zIndex: 9999,
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
                maxWidth: 380,
            }}
        >
            <AnimatePresence>
                {toasts.map((t) => {
                    const Icon = ICON_MAP[t.type]
                    const color = COLOR_MAP[t.type]
                    return (
                        <motion.div
                            key={t.id}
                            initial={{ opacity: 0, x: 60, scale: 0.95 }}
                            animate={{ opacity: 1, x: 0, scale: 1 }}
                            exit={{ opacity: 0, x: 60, scale: 0.95 }}
                            transition={{ duration: 0.25 }}
                            style={{
                                background: 'rgba(10, 10, 15, 0.92)',
                                backdropFilter: 'blur(16px)',
                                border: `1px solid ${color}40`,
                                borderRadius: 12,
                                padding: '10px 14px',
                                display: 'flex',
                                alignItems: 'center',
                                gap: 10,
                                boxShadow: `0 4px 24px ${color}15`,
                            }}
                        >
                            <Icon style={{ width: 16, height: 16, color, flexShrink: 0 }} />
                            <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', flex: 1 }}>
                                {t.message}
                            </span>
                            <button
                                onClick={() => dismiss(t.id)}
                                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2 }}
                            >
                                <X style={{ width: 12, height: 12, color: 'var(--color-text-muted)' }} />
                            </button>
                        </motion.div>
                    )
                })}
            </AnimatePresence>
        </div>
    )
}
