import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { ToastContainer } from '@/components/Toast'
import { useCreditsStore } from '@/stores/creditsStore'
import { initWalletAutoConnect, useWalletStore } from '@/stores/walletStore'
import { VerifyPage } from '@/pages/VerifyPage'
import { ExplorePage } from '@/pages/ExplorePage'
import { ProtocolsPage } from '@/pages/ProtocolsPage'
import { PoolDetailPage } from '@/pages/PoolDetailPage'
import { PortfolioPage } from '@/pages/PortfolioPage'
import { PremiumPage } from '@/pages/PremiumPage'
import { BuildPage } from '@/pages/BuildPage'
import { StrategiesPage } from '@/pages/StrategiesPage'
import { ReferralsPage } from '@/pages/ReferralsPage'

export default function App() {
  const { isConnected, address } = useWalletStore()

  useEffect(() => {
    // Auto-reconnect wallet if previously connected
    initWalletAutoConnect()
  }, [])

  // Sync credits with Supabase when wallet connects/changes
  useEffect(() => {
    if (isConnected && address) {
      useCreditsStore.getState().initCredits(address)
    } else {
      useCreditsStore.getState().initCredits()
    }
  }, [isConnected, address])

  return (
    <>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<VerifyPage />} />
          <Route path="/verify" element={<VerifyPage />} />
          <Route path="/explore" element={<ExplorePage />} />
          <Route path="/protocols" element={<ProtocolsPage />} />
          <Route path="/pool/:poolId" element={<PoolDetailPage />} />
          <Route path="/premium" element={<PremiumPage />} />
          <Route path="/strategies" element={<StrategiesPage />} />
          <Route path="/build" element={<BuildPage />} />
          <Route path="/portfolio" element={<PortfolioPage />} />
          <Route path="/referrals" element={<ReferralsPage />} />
        </Route>
      </Routes>
      <ToastContainer />
    </>
  )
}
