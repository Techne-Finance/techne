import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useState } from 'react'
import { motion } from 'framer-motion'
import { Wallet, Zap, ChevronDown } from 'lucide-react'
import { useWalletStore } from '@/stores/walletStore'
import { useCreditsStore } from '@/stores/creditsStore'
import { Sidebar } from './Sidebar'
import { NetworkSelectorModal } from './modals/NetworkSelectorModal'
import { WalletSelectorModal } from './WalletSelectorModal'
import { CreditBuyModal } from './CreditBuyModal'

// Pages that show the sidebar (matches live techne.finance)
const SIDEBAR_ROUTES = ['/explore', '/protocols']

// Nav icons — use local SVG/PNG from /icons/nav/
const NAV_ITEMS = [
    { to: '/verify', label: 'Verify', icon: '/icons/nav/verify.svg' },
    { to: '/explore', label: 'Explore', icon: '/icons/nav/explore.svg' },
    { to: '/protocols', label: 'Protocols', icon: '/icons/nav/vaults.svg' },
    { to: '/premium', label: 'Artisan', icon: '/icons/nav/premium.svg' },
    { to: '/strategies', label: 'Strategies', icon: '/icons/nav/strategies.svg' },
    { to: '/build', label: 'Build', icon: '/icons/nav/build.svg' },
    { to: '/portfolio', label: 'Portfolio', icon: '/icons/nav/portfolio.svg' },
    { to: '/referrals', label: 'Referrals', icon: '/icons/nav/dao.svg' },
]

export function Layout() {
    const { isConnected, address, disconnect } = useWalletStore()
    const credits = useCreditsStore(s => s.credits)
    const location = useLocation()
    const [networkOpen, setNetworkOpen] = useState(false)
    const [walletOpen, setWalletOpen] = useState(false)
    const [creditBuyOpen, setCreditBuyOpen] = useState(false)

    const showSidebar = SIDEBAR_ROUTES.some(r => location.pathname.startsWith(r))

    return (
        <div className="min-h-screen flex flex-col" style={{ background: 'var(--color-bg-primary)' }}>
            {/* Header */}
            <header
                className="sticky top-0 z-50 px-4 h-14 flex items-center justify-between"
                style={{
                    background: 'rgba(10, 10, 15, 0.85)',
                    backdropFilter: 'blur(16px)',
                    borderBottom: '1px solid var(--color-gold-border)',
                }}
            >
                {/* Logo — Techne SVG */}
                <NavLink to="/" className="flex items-center gap-2 flex-shrink-0">
                    <img
                        src="/icons/nav/logo.svg"
                        alt="Techne"
                        className="w-7 h-7"
                    />
                    <span
                        className="text-sm font-bold tracking-wider hidden sm:block"
                        style={{ fontFamily: 'Orbitron, sans-serif', color: 'var(--color-gold)' }}
                    >
                        TECHNE<span style={{ color: 'var(--color-text-primary)' }}>.finance</span>
                    </span>
                </NavLink>

                {/* Navigation */}
                <nav className="flex items-center gap-0.5 overflow-x-auto hide-scrollbar mx-4">
                    {NAV_ITEMS.map(({ to, label, icon }) => (
                        <NavLink
                            key={to}
                            to={to}
                            className="flex items-center gap-1.5 whitespace-nowrap transition-colors"
                            style={({ isActive }) => ({
                                padding: '6px 12px',
                                borderRadius: '8px',
                                fontSize: '0.8rem',
                                fontWeight: 500,
                                fontFamily: 'Outfit, sans-serif',
                                background: isActive ? 'var(--color-gold-dim)' : 'transparent',
                                color: isActive ? 'var(--color-gold)' : 'var(--color-text-muted)',
                                border: isActive ? '1px solid var(--color-gold-border)' : '1px solid transparent',
                            })}
                        >
                            <img
                                src={icon}
                                alt=""
                                className="w-3.5 h-3.5"
                                style={{ filter: 'grayscale(100%) brightness(1.5)' }}
                            />
                            <span className="hidden md:inline">{label}</span>
                        </NavLink>
                    ))}
                </nav>

                {/* Right side: Credits + Chain + Wallet */}
                <div className="flex items-center gap-2 flex-shrink-0">
                    {/* Credits — clickable to open buy modal */}
                    <button
                        onClick={() => setCreditBuyOpen(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs cursor-pointer transition-all"
                        style={{
                            background: 'var(--color-glass)',
                            border: '1px solid var(--color-glass-border)',
                            color: 'var(--color-gold)',
                        }}
                        onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--color-gold-border)')}
                        onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--color-glass-border)')}
                    >
                        <Zap className="w-3 h-3" />
                        <span className="font-heading font-semibold">{credits}</span>
                        <span style={{ color: 'var(--color-text-muted)' }}>credits</span>
                    </button>

                    {/* Chain Selector */}
                    <button
                        onClick={() => setNetworkOpen(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs cursor-pointer"
                        style={{
                            background: 'var(--color-glass)',
                            border: '1px solid var(--color-glass-border)',
                            color: 'var(--color-text-secondary)',
                        }}
                    >
                        <img src="/icons/base.png" alt="Base" className="w-4 h-4 rounded-full" />
                        <span className="font-medium hidden sm:inline">Base</span>
                        <ChevronDown className="w-3 h-3" />
                    </button>

                    {/* Wallet */}
                    <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.97 }}
                        onClick={() => isConnected ? disconnect() : setWalletOpen(true)}
                        className="px-4 py-1.5 rounded-lg text-xs font-heading font-semibold cursor-pointer"
                        style={{
                            background: isConnected ? 'var(--color-glass)' : 'linear-gradient(135deg, var(--color-gold), var(--color-gold-bright))',
                            color: isConnected ? 'var(--color-text-primary)' : '#0a0a0f',
                            border: isConnected ? '1px solid var(--color-glass-border)' : 'none',
                        }}
                    >
                        <Wallet className="w-3.5 h-3.5 inline mr-1.5" />
                        {isConnected
                            ? `${address?.slice(0, 6)}...${address?.slice(-4)}`
                            : 'Connect Wallet'}
                    </motion.button>
                </div>
            </header>

            {/* Body */}
            <div className="flex flex-1 overflow-hidden">
                {showSidebar && <Sidebar />}
                <main className="flex-1 overflow-y-auto p-5">
                    <Outlet />
                </main>
            </div>

            {/* Modals */}
            <NetworkSelectorModal isOpen={networkOpen} onClose={() => setNetworkOpen(false)} />
            <WalletSelectorModal isOpen={walletOpen} onClose={() => setWalletOpen(false)} />
            <CreditBuyModal isOpen={creditBuyOpen} onClose={() => setCreditBuyOpen(false)} />
        </div>
    )
}
