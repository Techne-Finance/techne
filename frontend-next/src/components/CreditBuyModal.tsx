/**
 * Credit Buy Modal — Porting credits.js showBuyModal()
 * Opens when clicking the credits counter in the header.
 * Features: Buy 100 credits for 0.10 USDC via x402, or go Premium.
 */
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Zap, Coins, Loader2 } from 'lucide-react'
import { useCreditsStore, CREDIT_COSTS } from '@/stores/creditsStore'
import { useWalletStore } from '@/stores/walletStore'
import { toast } from '@/components/Toast'
import { fetchPaymentRequirements, settlePayment } from '@/lib/api'

interface CreditBuyModalProps {
    isOpen: boolean
    onClose: () => void
}

export function CreditBuyModal({ isOpen, onClose }: CreditBuyModalProps) {
    const { credits, addCredits } = useCreditsStore()
    const { address } = useWalletStore()
    const [buying, setBuying] = useState(false)
    const [quantity, setQuantity] = useState(1)

    const totalCredits = quantity * CREDIT_COSTS.PURCHASE_AMOUNT
    const totalCost = (quantity * CREDIT_COSTS.PRICE_USDC).toFixed(2)

    const handleBuy = async () => {
        if (!address) {
            toast.error('Connect wallet first')
            return
        }

        const ethereum = (window as any).ethereum
        if (!ethereum) {
            toast.error('No wallet detected')
            return
        }

        setBuying(true)
        try {
            // Step 1: Get payment requirements from backend (Meridian x402)
            toast.info('Fetching payment details...')
            const requirements = await fetchPaymentRequirements()

            // Step 2: Construct EIP-712 typed data for x402 authorization
            // Domain MUST match USDC contract's EIP-712 domain (not generic x402)
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
                ],
            }

            // Scale amount by quantity
            const totalAmount = BigInt(requirements.amount) * BigInt(quantity)
            const nonce = '0x' + Array.from(crypto.getRandomValues(new Uint8Array(32))).map(b => b.toString(16).padStart(2, '0')).join('')
            const now = Math.floor(Date.now() / 1000)
            const validAfter = now - 3600 // 1 hour ago (required by Meridian)
            const validBefore = now + 3600

            const value = {
                from: address,
                to: requirements.recipientAddress,
                value: totalAmount.toString(),
                validAfter: validAfter,
                validBefore: validBefore,
                nonce: nonce,
            }

            // Step 3: Request EIP-712 signature from wallet
            toast.info('Sign the payment in your wallet...')
            const msgParams = JSON.stringify({
                types: {
                    EIP712Domain: [
                        { name: 'name', type: 'string' },
                        { name: 'version', type: 'string' },
                        { name: 'chainId', type: 'uint256' },
                        { name: 'verifyingContract', type: 'address' }
                    ],
                    ...types
                },
                primaryType: 'TransferWithAuthorization',
                domain,
                message: value,
            })

            const signature = await ethereum.request({
                method: 'eth_signTypedData_v4',
                params: [address, msgParams],
            })

            // Step 4: Send signed payload to backend for settlement
            // authorization values must be strings (Meridian API requirement)
            toast.info('Processing payment...')
            const paymentPayload = {
                x402Version: 1,
                scheme: 'exact',
                network: 'base',
                payload: {
                    signature,
                    authorization: {
                        from: address,
                        to: requirements.recipientAddress,
                        value: totalAmount.toString(),
                        validAfter: validAfter.toString(),
                        validBefore: validBefore.toString(),
                        nonce: nonce,
                    },
                    token: requirements.usdcAddress,
                },
            }

            const result = await settlePayment(paymentPayload)

            if (result.success) {
                addCredits(totalCredits)
                toast.success(`Purchased ${totalCredits} credits! Tx: ${result.tx_hash?.slice(0, 10)}...`)
                onClose()
            } else {
                toast.error(result.error || 'Payment settlement failed')
            }
        } catch (err: any) {
            if (err?.code === 4001) {
                toast.warning('Payment cancelled')
            } else {
                toast.error(err?.message || 'Purchase failed')
            }
        } finally {
            setBuying(false)
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
                        onClick={onClose}
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
                                    background: 'linear-gradient(135deg, rgba(212,168,83,0.05), transparent)',
                                }}
                            >
                                <div className="flex items-center gap-3">
                                    <div
                                        className="w-10 h-10 rounded-xl flex items-center justify-center"
                                        style={{ background: 'var(--color-gold-dim)' }}
                                    >
                                        <Zap className="w-5 h-5" style={{ color: 'var(--color-gold)' }} />
                                    </div>
                                    <div>
                                        <h2 className="text-base font-heading font-bold" style={{ color: 'var(--color-text-primary)' }}>
                                            Buy Filter Credits
                                        </h2>
                                        <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                                            Current: {credits} credits
                                        </p>
                                    </div>
                                </div>
                                <button onClick={onClose} className="cursor-pointer p-1">
                                    <X className="w-5 h-5" style={{ color: 'var(--color-text-muted)' }} />
                                </button>
                            </div>

                            {/* Content */}
                            <div className="p-5 space-y-4">
                                {/* Quick Buy */}
                                <div
                                    className="p-4 rounded-xl"
                                    style={{
                                        background: 'var(--color-glass)',
                                        border: '1px solid var(--color-glass-border)',
                                    }}
                                >
                                    <div className="flex items-center justify-between mb-3">
                                        <span className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                                            Credit Pack
                                        </span>
                                        <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                                            via x402 Protocol
                                        </span>
                                    </div>

                                    {/* Quantity selector */}
                                    <div className="flex items-center gap-3 mb-3">
                                        {[1, 3, 5, 10].map(q => (
                                            <button
                                                key={q}
                                                onClick={() => setQuantity(q)}
                                                className="flex-1 py-2 rounded-lg text-xs font-semibold cursor-pointer transition-all"
                                                style={{
                                                    background: quantity === q ? 'var(--color-gold-dim)' : 'var(--color-glass)',
                                                    border: `1px solid ${quantity === q ? 'var(--color-gold-border)' : 'var(--color-glass-border)'}`,
                                                    color: quantity === q ? 'var(--color-gold)' : 'var(--color-text-secondary)',
                                                }}
                                            >
                                                {q * CREDIT_COSTS.PURCHASE_AMOUNT}
                                            </button>
                                        ))}
                                    </div>

                                    {/* Summary */}
                                    <div className="flex items-center justify-between py-2" style={{ borderTop: '1px solid var(--color-glass-border)' }}>
                                        <div className="flex items-center gap-2">
                                            <Coins className="w-4 h-4" style={{ color: 'var(--color-gold)' }} />
                                            <span className="text-sm" style={{ color: 'var(--color-text-primary)' }}>
                                                {totalCredits} credits
                                            </span>
                                        </div>
                                        <span className="text-sm font-semibold" style={{ color: 'var(--color-gold)' }}>
                                            {totalCost} USDC
                                        </span>
                                    </div>
                                </div>

                                {/* Buy button */}
                                <motion.button
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.97 }}
                                    onClick={handleBuy}
                                    disabled={buying}
                                    className="w-full py-3 rounded-xl text-sm font-heading font-bold cursor-pointer flex items-center justify-center gap-2"
                                    style={{
                                        background: 'linear-gradient(135deg, var(--color-gold), var(--color-gold-bright))',
                                        color: '#0a0a0f',
                                        opacity: buying ? 0.7 : 1,
                                    }}
                                >
                                    {buying ? (
                                        <>
                                            <Loader2 className="w-4 h-4 animate-spin" /> Processing...
                                        </>
                                    ) : (
                                        <>
                                            <Zap className="w-4 h-4" /> Buy {totalCredits} Credits
                                        </>
                                    )}
                                </motion.button>

                                {/* Meridian x402 branding */}
                                <div
                                    className="p-3 rounded-xl flex items-center justify-between"
                                    style={{
                                        background: 'linear-gradient(135deg, rgba(212,168,83,0.04), transparent)',
                                        border: '1px solid var(--color-glass-border)',
                                    }}
                                >
                                    <div className="flex items-center gap-2.5">
                                        <img src="/icons/meridian.png" alt="Meridian" className="w-5 h-5 rounded-full" />
                                        <div>
                                            <span className="text-[10px] font-medium block" style={{ color: 'var(--color-text-muted)' }}>
                                                Powered by
                                            </span>
                                            <a
                                                href="https://mrdn.finance"
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-xs font-semibold hover:underline"
                                                style={{ color: 'var(--color-text-secondary)' }}
                                            >
                                                mrdn.finance
                                            </a>
                                        </div>
                                    </div>
                                    <span className="text-[10px] font-medium px-2 py-0.5 rounded-full"
                                        style={{ background: 'var(--color-glass)', color: 'var(--color-text-muted)', border: '1px solid var(--color-glass-border)' }}>
                                        x402 Protocol
                                    </span>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    )
}
