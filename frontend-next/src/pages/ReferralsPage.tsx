import { motion } from 'framer-motion'
import { Users, Gift, Copy, Check, Link2, TrendingUp } from 'lucide-react'
import { useState } from 'react'
import { useWalletStore } from '@/stores/walletStore'

export function ReferralsPage() {
    const { isConnected, address } = useWalletStore()
    const [copied, setCopied] = useState(false)

    const referralLink = `https://techne.finance?ref=${address?.slice(0, 8) || 'connect'}`
    const handleCopy = () => {
        navigator.clipboard.writeText(referralLink)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    return (
        <div className="max-w-3xl mx-auto">
            <div className="flex items-center gap-3 mb-6">
                <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center"
                    style={{ background: 'var(--color-gold-dim)', border: '1px solid var(--color-gold-border)' }}
                >
                    <Users className="w-6 h-6" style={{ color: 'var(--color-gold)' }} />
                </div>
                <div>
                    <h1 className="font-heading text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
                        Referrals
                    </h1>
                    <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                        Invite friends, earn rewards
                    </p>
                </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-3 mb-5">
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="glass-card p-4 text-center"
                >
                    <Users className="w-5 h-5 mx-auto mb-1.5" style={{ color: 'var(--color-gold)' }} />
                    <div className="text-2xl font-heading font-bold" style={{ color: 'var(--color-text-primary)' }}>0</div>
                    <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Referrals</div>
                </motion.div>
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.05 }}
                    className="glass-card p-4 text-center"
                >
                    <Gift className="w-5 h-5 mx-auto mb-1.5" style={{ color: 'var(--color-green)' }} />
                    <div className="text-2xl font-heading font-bold" style={{ color: 'var(--color-text-primary)' }}>0</div>
                    <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Credits Earned</div>
                </motion.div>
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="glass-card p-4 text-center"
                >
                    <TrendingUp className="w-5 h-5 mx-auto mb-1.5" style={{ color: 'var(--color-gold)' }} />
                    <div className="text-2xl font-heading font-bold" style={{ color: 'var(--color-text-primary)' }}>10%</div>
                    <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Commission</div>
                </motion.div>
            </div>

            {/* Referral Link */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
                className="glass-card-gold p-5 mb-5"
            >
                <h3 className="font-heading text-sm font-semibold mb-3" style={{ color: 'var(--color-text-primary)' }}>
                    <Link2 className="w-4 h-4 inline mr-1.5" style={{ color: 'var(--color-gold)' }} />
                    Your Referral Link
                </h3>
                <div className="flex gap-2">
                    <div
                        className="flex-1 px-4 py-2.5 rounded-xl text-sm font-mono truncate"
                        style={{
                            background: 'var(--color-bg-primary)',
                            border: '1px solid var(--color-glass-border)',
                            color: 'var(--color-text-secondary)',
                        }}
                    >
                        {isConnected ? referralLink : 'Connect wallet to generate link'}
                    </div>
                    <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.97 }}
                        onClick={handleCopy}
                        disabled={!isConnected}
                        className="px-4 py-2.5 rounded-xl text-sm font-heading font-semibold cursor-pointer flex items-center gap-1.5"
                        style={{
                            background: 'linear-gradient(135deg, var(--color-gold), var(--color-gold-bright))',
                            color: 'var(--color-bg-primary)',
                            opacity: isConnected ? 1 : 0.5,
                        }}
                    >
                        {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                        {copied ? 'Copied!' : 'Copy'}
                    </motion.button>
                </div>
            </motion.div>

            {/* How It Works */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="glass-card p-5"
            >
                <h3 className="font-heading text-sm font-semibold mb-4" style={{ color: 'var(--color-text-primary)' }}>
                    How It Works
                </h3>
                <div className="space-y-4">
                    {[
                        { step: '1', title: 'Share your link', desc: 'Send your unique referral link to friends and community members' },
                        { step: '2', title: 'They sign up', desc: 'When someone uses your link and makes their first purchase' },
                        { step: '3', title: 'Earn rewards', desc: 'Receive 10% of their credit purchases as bonus credits' },
                    ].map((item) => (
                        <div key={item.step} className="flex items-start gap-3">
                            <div
                                className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-heading font-bold flex-shrink-0"
                                style={{
                                    background: 'var(--color-gold-dim)',
                                    color: 'var(--color-gold)',
                                    border: '1px solid var(--color-gold-border)',
                                }}
                            >
                                {item.step}
                            </div>
                            <div>
                                <h4 className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>{item.title}</h4>
                                <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{item.desc}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </motion.div>
        </div>
    )
}
