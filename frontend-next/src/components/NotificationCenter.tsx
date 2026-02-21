/**
 * Notification Center — Porting notifications.js
 * Features: Toast notifications (via Toast.tsx) + notification history panel,
 * agent-specific notification types, persistent history in localStorage
 */
import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Bell, X, Trash2, Activity, ArrowDownToLine, Zap, AlertTriangle } from 'lucide-react'

// ─── Types ───
interface Notification {
    id: number
    type: 'info' | 'success' | 'warning' | 'error' | 'agent'
    title: string
    message: string
    timestamp: number
    read: boolean
}

const STORAGE_KEY = 'techne_notification_history'
const MAX_HISTORY = 50

// ─── Persistence ───
function loadHistory(): Notification[] {
    try {
        const raw = localStorage.getItem(STORAGE_KEY)
        if (!raw) return []
        return JSON.parse(raw).slice(0, MAX_HISTORY)
    } catch { return [] }
}

function saveHistory(items: Notification[]) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, MAX_HISTORY)))
}

let nextId = Date.now()

// ─── Global notification dispatcher ───
type Listener = (n: Notification) => void
const listeners: Set<Listener> = new Set()

export const notifications = {
    _history: loadHistory(),

    push(type: Notification['type'], title: string, message: string) {
        const n: Notification = { id: nextId++, type, title, message, timestamp: Date.now(), read: false }
        this._history = [n, ...this._history].slice(0, MAX_HISTORY)
        saveHistory(this._history)
        listeners.forEach(fn => fn(n))
    },

    // Agent-specific convenience methods
    agentDeposit(vault: string, amount: string) {
        this.push('agent', 'Agent Deposit', `Deposited ${amount} into ${vault}`)
    },
    agentWithdraw(vault: string, amount: string) {
        this.push('agent', 'Agent Withdraw', `Withdrew ${amount} from ${vault}`)
    },
    agentRebalance(changes: string) {
        this.push('agent', 'Rebalance', changes)
    },
    agentHarvest(vault: string, rewards: string) {
        this.push('agent', 'Harvest', `Harvested ${rewards} from ${vault}`)
    },
    apyAlert(vault: string, oldApy: number, newApy: number) {
        const direction = newApy > oldApy ? '▲' : '▼'
        this.push('warning', `${direction} APY Change`, `${vault}: ${oldApy.toFixed(1)}% → ${newApy.toFixed(1)}%`)
    },
    emergencyExit(reason: string) {
        this.push('error', 'Emergency Exit', reason)
    },

    getHistory(): Notification[] { return this._history },
    markAllRead() {
        this._history = this._history.map(n => ({ ...n, read: true }))
        saveHistory(this._history)
        listeners.forEach(() => { }) // trigger re-render
    },
    clearHistory() {
        this._history = []
        saveHistory([])
        listeners.forEach(() => { })
    },
}

// ─── Hook ───
function useNotifications() {
    const [items, setItems] = useState<Notification[]>(notifications.getHistory())

    useEffect(() => {
        const listener: Listener = () => {
            setItems([...notifications.getHistory()])
        }
        listeners.add(listener)
        return () => { listeners.delete(listener) }
    }, [])

    return items
}

// ─── Helper ───
function formatTimeAgo(ts: number): string {
    const diff = Math.floor((Date.now() - ts) / 1000)
    if (diff < 60) return 'just now'
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    return `${Math.floor(diff / 86400)}d ago`
}

function getTypeIcon(type: string) {
    switch (type) {
        case 'agent': return Activity
        case 'success': return ArrowDownToLine
        case 'warning': return AlertTriangle
        case 'error': return AlertTriangle
        default: return Zap
    }
}

function getTypeColor(type: string) {
    switch (type) {
        case 'success': return 'var(--color-green)'
        case 'warning': return 'var(--color-gold)'
        case 'error': return 'var(--color-red)'
        case 'agent': return '#3b82f6'
        default: return 'var(--color-text-muted)'
    }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// NOTIFICATION CENTER COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export function NotificationCenter() {
    const [open, setOpen] = useState(false)
    const items = useNotifications()
    const unreadCount = items.filter(n => !n.read).length

    const handleOpen = useCallback(() => {
        setOpen(prev => !prev)
        if (!open) notifications.markAllRead()
    }, [open])

    return (
        <div className="relative">
            {/* Bell button */}
            <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleOpen}
                className="relative p-2 rounded-lg cursor-pointer"
                style={{
                    background: 'var(--color-glass)',
                    border: '1px solid var(--color-glass-border)',
                }}
            >
                <Bell className="w-4 h-4" style={{ color: 'var(--color-text-secondary)' }} />
                {unreadCount > 0 && (
                    <span
                        className="absolute -top-1 -right-1 w-4 h-4 rounded-full text-[10px] font-bold flex items-center justify-center"
                        style={{ background: 'var(--color-red)', color: '#fff' }}
                    >
                        {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                )}
            </motion.button>

            {/* Dropdown panel */}
            <AnimatePresence>
                {open && (
                    <>
                        {/* Backdrop */}
                        <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
                        <motion.div
                            initial={{ opacity: 0, y: -8, scale: 0.95 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: -8, scale: 0.95 }}
                            transition={{ duration: 0.15 }}
                            className="absolute right-0 top-full mt-2 w-80 max-h-96 rounded-xl overflow-hidden z-50"
                            style={{
                                background: 'var(--color-bg-secondary)',
                                border: '1px solid var(--color-glass-border)',
                                boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
                            }}
                        >
                            {/* Header */}
                            <div
                                className="flex items-center justify-between px-4 py-3"
                                style={{ borderBottom: '1px solid var(--color-glass-border)' }}
                            >
                                <h3 className="text-sm font-heading font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                                    Notifications
                                </h3>
                                <div className="flex items-center gap-2">
                                    {items.length > 0 && (
                                        <button
                                            onClick={() => { notifications.clearHistory(); setOpen(false) }}
                                            className="text-xs flex items-center gap-1 cursor-pointer"
                                            style={{ color: 'var(--color-text-muted)' }}
                                        >
                                            <Trash2 className="w-3 h-3" /> Clear
                                        </button>
                                    )}
                                    <button onClick={() => setOpen(false)} className="cursor-pointer">
                                        <X className="w-4 h-4" style={{ color: 'var(--color-text-muted)' }} />
                                    </button>
                                </div>
                            </div>

                            {/* Items */}
                            <div className="overflow-y-auto max-h-72">
                                {items.length === 0 ? (
                                    <div className="p-6 text-center">
                                        <Bell className="w-8 h-8 mx-auto mb-2" style={{ color: 'var(--color-text-muted)', opacity: 0.4 }} />
                                        <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>No notifications yet</p>
                                    </div>
                                ) : (
                                    items.map((n) => {
                                        const Icon = getTypeIcon(n.type)
                                        return (
                                            <div
                                                key={n.id}
                                                className="px-4 py-3 flex items-start gap-3"
                                                style={{
                                                    borderBottom: '1px solid var(--color-glass-border)',
                                                    background: n.read ? 'transparent' : 'rgba(212, 168, 83, 0.03)',
                                                }}
                                            >
                                                <div
                                                    className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                                                    style={{ background: `${getTypeColor(n.type)}20` }}
                                                >
                                                    <Icon className="w-3.5 h-3.5" style={{ color: getTypeColor(n.type) }} />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-xs font-semibold truncate" style={{ color: 'var(--color-text-primary)' }}>
                                                            {n.title}
                                                        </span>
                                                        <span className="text-[10px] flex-shrink-0 ml-2" style={{ color: 'var(--color-text-muted)' }}>
                                                            {formatTimeAgo(n.timestamp)}
                                                        </span>
                                                    </div>
                                                    <p className="text-xs mt-0.5 leading-snug" style={{ color: 'var(--color-text-secondary)' }}>
                                                        {n.message}
                                                    </p>
                                                </div>
                                            </div>
                                        )
                                    })
                                )}
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </div>
    )
}
