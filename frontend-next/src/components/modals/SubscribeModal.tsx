/**
 * Subscribe Modal — Artisan Bot $99/mo subscription
 * Opens when clicking "SUBSCRIBE WITH USDC" on Premium page.
 * Shows confirmation with price, features, then handles x402 payment flow.
 */
import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Bot, Shield, Loader2, Copy, Check, MessageSquare, Clock, Zap, ExternalLink } from 'lucide-react'
import { useWalletStore } from '@/stores/walletStore'
import { toast } from '@/components/Toast'
import { fetchPremiumRequirements, subscribePremium } from '@/lib/api'

const TELEGRAM_BOT = 'TechneArtisanBot'

interface SubscribeModalProps {
    isOpen: boolean
    onClose: () => void
    onSuccess?: (code: string) => void
}

type PaymentStep = 'confirm' | 'signing' | 'confirming' | 'activating' | 'success' | 'error'

const FEATURES = [
    'Personal AI Trading Agent',
    'Autonomous Trade Execution',
    'Telegram AI Assistant',
    '$10K/trade Session Key Limits',
    'AI Strategy Optimization',
    'Emergency Exit Controls',
]

export function SubscribeModal({ isOpen, onClose, onSuccess }: SubscribeModalProps) {
    const { address } = useWalletStore()
    const [step, setStep] = useState<PaymentStep>('confirm')
    const [activationCode, setActivationCode] = useState<string | null>(null)
    const [codeCopied, setCodeCopied] = useState(false)
    const [errorMsg, setErrorMsg] = useState('')

    const resetAndClose = useCallback(() => {
        setStep('confirm')
        setActivationCode(null)
        setCodeCopied(false)
        setErrorMsg('')
        onClose()
    }, [onClose])

    const copyCode = useCallback(() => {
        if (activationCode) {
            navigator.clipboard.writeText(activationCode)
            setCodeCopied(true)
            setTimeout(() => setCodeCopied(false), 2000)
        }
    }, [activationCode])

    const handleSubscribe = async () => {
        if (!address) {
            toast.error('Connect your wallet first')
            return
        }

        const ethereum = (window as any).ethereum
        if (!ethereum) {
            toast.error('No wallet detected')
            return
        }

        setStep('signing')
        try {
            // Step 1: Fetch premium requirements from backend
            const requirements = await fetchPremiumRequirements()

            // Step 2: Construct EIP-712 typed data for TransferWithAuthorization
            const domain = {
                name: 'USD Coin',
                version: '2',
                chainId: 8453, // Base mainnet
                verifyingContract: requirements.usdcAddress
            }

            const types = {
                TransferWithAuthorization: [
                    { name: 'from', type: 'address' },
                    { name: 'to', type: 'address' },
                    { name: 'value', type: 'uint256' },
                    { name: 'validAfter', type: 'uint256' },
                    { name: 'validBefore', type: 'uint256' },
                    { name: 'nonce', type: 'bytes32' },
                ]
            }

            const now = Math.floor(Date.now() / 1000)
            const nonce = '0x' + Array.from(crypto.getRandomValues(new Uint8Array(32)))
                .map(b => b.toString(16).padStart(2, '0')).join('')

            const message = {
                from: address,
                to: requirements.recipientAddress,
                value: requirements.amount,
                validAfter: 0,
                validBefore: now + 3600,
                nonce,
            }

            // Step 3: Request EIP-712 signature from wallet
            const signature = await ethereum.request({
                method: 'eth_signTypedData_v4',
                params: [address, JSON.stringify({ types, domain, primaryType: 'TransferWithAuthorization', message })]
            })

            setStep('confirming')

            // Step 4: Build x402 payment payload
            const paymentPayload = {
                x402Version: 1,
                scheme: 'exact',
                network: 'base',
                payload: {
                    signature,
                    authorization: {
                        from: address,
                        to: requirements.recipientAddress,
                        value: requirements.amount,
                        validAfter: 0,
                        validBefore: now + 3600,
                        nonce,
                    }
                }
            }

            setStep('activating')

            // Step 5: Subscribe via backend
            const result = await subscribePremium({
                wallet_address: address,
                paymentPayload,
            })

            if (result.success || result.activation_code) {
                const code = result.activation_code || result.code || 'CHECK-TELEGRAM'
                setActivationCode(code)
                setStep('success')
                onSuccess?.(code)
                toast.success('Artisan Access activated!')
            } else {
                throw new Error(result.error || 'Subscription failed')
            }
        } catch (err: any) {
            if (err.code === 4001 || err.code === 'ACTION_REJECTED') {
                toast.warning('Transaction cancelled')
                setStep('confirm')
                return
            }
            setErrorMsg(err.message || 'Unknown error')
            setStep('error')
        }
    }

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50"
                        style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
                        onClick={resetAndClose}
                    />
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        className="fixed inset-0 z-50 flex items-center justify-center p-4"
                        onClick={e => e.stopPropagation()}
                    >
                        <div
                            className="w-full max-w-md rounded-2xl overflow-hidden"
                            style={{
                                background: 'var(--color-bg-secondary)',
                                border: '1px solid var(--color-gold-border)',
                                boxShadow: '0 32px 100px rgba(0,0,0,0.5)',
                            }}
                        >
                            {/* Header */}
                            <div
                                className="flex items-center justify-between p-5"
                                style={{
                                    borderBottom: '1px solid var(--color-glass-border)',
                                    background: 'linear-gradient(135deg, rgba(212,168,83,0.08), transparent)',
                                }}
                            >
                                <div className="flex items-center gap-3">
                                    <div
                                        className="w-10 h-10 rounded-xl flex items-center justify-center"
                                        style={{ background: 'var(--color-gold-dim)', border: '1px solid var(--color-gold-border)' }}
                                    >
                                        <Bot className="w-5 h-5" style={{ color: 'var(--color-gold)' }} />
                                    </div>
                                    <div>
                                        <h3 className="text-sm font-heading font-bold" style={{ color: 'var(--color-text-primary)' }}>
                                            Artisan Bot Subscription
                                        </h3>
                                        <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                                            AI Trading Agent — 30 days
                                        </p>
                                    </div>
                                </div>
                                <button
                                    onClick={resetAndClose}
                                    className="p-1.5 rounded-lg cursor-pointer"
                                    style={{ background: 'var(--color-glass)', border: 'none', color: 'var(--color-text-muted)' }}
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            </div>

                            {/* Body */}
                            <div className="p-5">
                                {step === 'confirm' && (
                                    <div>
                                        {/* Price */}
                                        <div className="text-center mb-5">
                                            <div className="flex items-baseline justify-center gap-1">
                                                <span className="font-heading text-4xl font-bold" style={{ color: 'var(--color-gold)' }}>99</span>
                                                <span className="text-base" style={{ color: 'var(--color-text-muted)' }}>USDC</span>
                                            </div>
                                            <p className="text-xs mt-1 flex items-center justify-center gap-1" style={{ color: 'var(--color-text-muted)' }}>
                                                <Clock className="w-3 h-3" /> Valid for 30 days · Base network
                                            </p>
                                        </div>

                                        {/* Features */}
                                        <div
                                            className="p-4 rounded-xl mb-5"
                                            style={{ background: 'var(--color-glass)', border: '1px solid var(--color-glass-border)' }}
                                        >
                                            <p className="text-xs font-semibold mb-3" style={{ color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                                Included
                                            </p>
                                            <div className="space-y-2">
                                                {FEATURES.map((f, i) => (
                                                    <div key={i} className="flex items-center gap-2">
                                                        <Zap className="w-3 h-3 flex-shrink-0" style={{ color: 'var(--color-gold)' }} />
                                                        <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>{f}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>

                                        {/* How it works */}
                                        <div
                                            className="p-3 rounded-xl mb-5"
                                            style={{ background: 'rgba(212,168,83,0.05)', border: '1px solid var(--color-gold-border)' }}
                                        >
                                            <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                                                <Shield className="w-3 h-3 inline mr-1" style={{ color: 'var(--color-gold)' }} />
                                                Payment generates an <strong style={{ color: 'var(--color-gold)' }}>activation code</strong>. Enter it in{' '}
                                                <a
                                                    href={`https://t.me/${TELEGRAM_BOT}`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    style={{ color: 'var(--color-gold)' }}
                                                >
                                                    @{TELEGRAM_BOT}
                                                </a>{' '}
                                                to activate your AI agent.
                                            </p>
                                        </div>

                                        {/* Subscribe button */}
                                        <motion.button
                                            whileHover={{ scale: 1.02 }}
                                            whileTap={{ scale: 0.97 }}
                                            onClick={handleSubscribe}
                                            className="w-full py-3.5 rounded-xl text-sm font-heading font-bold cursor-pointer flex items-center justify-center gap-2"
                                            style={{
                                                background: 'linear-gradient(135deg, var(--color-gold), var(--color-gold-bright))',
                                                color: '#0a0a0f',
                                                border: 'none',
                                            }}
                                        >
                                            <MessageSquare className="w-4 h-4" />
                                            Pay 99 USDC & Get Activation Code
                                        </motion.button>

                                        <p className="text-center text-xs mt-3" style={{ color: 'var(--color-text-muted)' }}>
                                            Paid via x402 on Base · Non-refundable
                                        </p>
                                    </div>
                                )}

                                {(step === 'signing' || step === 'confirming' || step === 'activating') && (
                                    <div className="text-center py-8">
                                        <Loader2 className="w-10 h-10 animate-spin mx-auto mb-4" style={{ color: 'var(--color-gold)' }} />
                                        <p className="text-sm font-heading font-semibold mb-1" style={{ color: 'var(--color-text-primary)' }}>
                                            {step === 'signing' && 'Approve in Wallet...'}
                                            {step === 'confirming' && 'Confirming Payment...'}
                                            {step === 'activating' && 'Generating Activation Code...'}
                                        </p>
                                        <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                                            {step === 'signing' && 'Sign the EIP-712 authorization in your wallet'}
                                            {step === 'confirming' && 'Verifying payment with Meridian...'}
                                            {step === 'activating' && 'Almost there! Creating your premium access...'}
                                        </p>
                                    </div>
                                )}

                                {step === 'success' && activationCode && (
                                    <div className="text-center py-4">
                                        <div
                                            className="w-14 h-14 rounded-full mx-auto mb-4 flex items-center justify-center"
                                            style={{ background: 'var(--color-gold-dim)', border: '2px solid var(--color-gold)' }}
                                        >
                                            <Check className="w-7 h-7" style={{ color: 'var(--color-gold)' }} />
                                        </div>
                                        <h3 className="text-lg font-heading font-bold mb-1" style={{ color: 'var(--color-gold)' }}>
                                            Payment Confirmed!
                                        </h3>
                                        <p className="text-xs mb-5" style={{ color: 'var(--color-text-muted)' }}>
                                            Click below to activate your Artisan Bot instantly.
                                        </p>

                                        {/* Primary: Telegram deep link (auto-sends code) */}
                                        <a
                                            href={`https://t.me/${TELEGRAM_BOT}?start=${activationCode}`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="w-full py-3.5 rounded-xl text-sm font-heading font-bold flex items-center justify-center gap-2"
                                            style={{
                                                background: 'linear-gradient(135deg, var(--color-gold), var(--color-gold-bright))',
                                                color: '#0a0a0f',
                                                textDecoration: 'none',
                                                display: 'flex',
                                            }}
                                        >
                                            <ExternalLink className="w-4 h-4" />
                                            🚀 Activate on Telegram
                                        </a>

                                        <p className="text-xs mt-4 mb-2" style={{ color: 'var(--color-text-muted)' }}>
                                            Or enter code manually:
                                        </p>

                                        {/* Fallback: code display + copy */}
                                        <div
                                            className="p-3 rounded-xl flex items-center justify-between"
                                            style={{ background: 'var(--color-glass)', border: '1px solid var(--color-glass-border)' }}
                                        >
                                            <code
                                                className="font-heading text-sm font-bold tracking-widest"
                                                style={{ color: 'var(--color-gold)' }}
                                            >
                                                {activationCode}
                                            </code>
                                            <button
                                                onClick={copyCode}
                                                className="p-1.5 rounded-lg cursor-pointer"
                                                style={{
                                                    background: codeCopied ? 'var(--color-gold-dim)' : 'var(--color-glass)',
                                                    border: '1px solid var(--color-glass-border)',
                                                    color: codeCopied ? 'var(--color-gold)' : 'var(--color-text-muted)',
                                                }}
                                            >
                                                {codeCopied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                                            </button>
                                        </div>
                                    </div>
                                )}

                                {step === 'error' && (
                                    <div className="text-center py-8">
                                        <div
                                            className="w-14 h-14 rounded-full mx-auto mb-4 flex items-center justify-center"
                                            style={{ background: 'rgba(239,68,68,0.1)', border: '2px solid rgba(239,68,68,0.3)' }}
                                        >
                                            <X className="w-7 h-7" style={{ color: '#ef4444' }} />
                                        </div>
                                        <h3 className="text-base font-heading font-bold mb-2" style={{ color: '#ef4444' }}>
                                            Payment Failed
                                        </h3>
                                        <p className="text-xs mb-5" style={{ color: 'var(--color-text-muted)' }}>
                                            {errorMsg || 'An unexpected error occurred'}
                                        </p>
                                        <motion.button
                                            whileHover={{ scale: 1.02 }}
                                            whileTap={{ scale: 0.97 }}
                                            onClick={() => setStep('confirm')}
                                            className="px-6 py-2.5 rounded-xl text-sm font-heading font-semibold cursor-pointer"
                                            style={{
                                                background: 'var(--color-glass)',
                                                border: '1px solid var(--color-glass-border)',
                                                color: 'var(--color-text-primary)',
                                            }}
                                        >
                                            Try Again
                                        </motion.button>
                                    </div>
                                )}
                            </div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    )
}
