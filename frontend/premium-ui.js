/**
 * Premium Subscription UI for Techne.finance
 * Handles subscription state, Telegram integration, and search limits
 */

// Constants
const PREMIUM_CONFIG = {
    TREASURY_ADDRESS: '0x742d35Cc6634C0532925a3b844Bc9e7595f8fE00', // Replace with actual treasury
    USDC_ADDRESS_BASE: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', // USDC on Base
    SUBSCRIPTION_PRICE: 10 * 1e6, // 10 USDC (6 decimals)
    CREDIT_PACK_PRICE: 0.1 * 1e6, // 0.10 USDC (6 decimals)
    CREDIT_PACK_SEARCHES: 15, // 15 searches per pack
    PREMIUM_DAILY_LIMIT: 200, // 200 searches/day for premium
    TELEGRAM_BOT: 'TechneAlertBot',
    SUBSCRIPTION_DAYS: 30
};

// State
let premiumState = {
    isPremium: false,
    subscriptionExpires: null,
    searchCredits: 0, // Pay-per-use credits
    searchesToday: 0, // For premium daily counter
    telegramConnected: false,
    telegramChatId: null,
    alertPreferences: {
        minApy: 10,
        minTvl: 100000,
        riskLevel: 'medium',
        protocols: [],
        chains: []
    }
};

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    loadPremiumState();
    initPremiumUI();
    updateSearchCounter();
});

/**
 * Load premium state from localStorage
 */
function loadPremiumState() {
    const saved = localStorage.getItem('techne_premium_state');
    if (saved) {
        try {
            const parsed = JSON.parse(saved);
            premiumState = { ...premiumState, ...parsed };

            // Reset daily search count if new day
            const lastSearchDate = localStorage.getItem('techne_last_search_date');
            const today = new Date().toDateString();
            if (lastSearchDate !== today) {
                premiumState.searchesToday = 0;
                localStorage.setItem('techne_last_search_date', today);
            }

            // Check if subscription expired
            if (premiumState.subscriptionExpires && new Date(premiumState.subscriptionExpires) < new Date()) {
                premiumState.isPremium = false;
                premiumState.subscriptionExpires = null;
            }
        } catch (e) {
            console.error('Failed to parse premium state:', e);
        }
    }
    savePremiumState();
}

/**
 * Save premium state to localStorage
 */
function savePremiumState() {
    localStorage.setItem('techne_premium_state', JSON.stringify(premiumState));
}

/**
 * Initialize Premium UI elements
 */
function initPremiumUI() {
    // Subscribe button
    const subscribeBtn = document.getElementById('subscribe-btn');
    if (subscribeBtn) {
        subscribeBtn.addEventListener('click', handleSubscribe);
    }

    // Buy credits button
    const buyCreditsBtn = document.getElementById('buy-credits-btn');
    if (buyCreditsBtn) {
        buyCreditsBtn.addEventListener('click', handleBuyCredits);
    }

    // Telegram connect button
    const telegramBtn = document.getElementById('connect-telegram-btn');
    if (telegramBtn) {
        telegramBtn.addEventListener('click', handleTelegramConnect);
    }

    // Update UI based on current state
    updatePremiumUI();
}

/**
 * Update all Premium UI elements
 */
function updatePremiumUI() {
    // Update plan name
    const planName = document.getElementById('current-plan-name');
    if (planName) {
        if (premiumState.isPremium) {
            planName.innerHTML = '<span style="color: #d4af37;">⭐ Premium Plus</span>';
        } else if (premiumState.searchCredits > 0) {
            planName.textContent = 'Pay-per-use';
        } else {
            planName.textContent = 'No Credits';
        }
    }

    // Update credits display
    const creditsEl = document.getElementById('search-credits');
    if (creditsEl) {
        creditsEl.textContent = premiumState.searchCredits;
    }

    // Update search count display
    updateSearchCounter();

    // Update subscribe button
    const subscribeBtn = document.getElementById('subscribe-btn');
    if (subscribeBtn) {
        if (premiumState.isPremium) {
            subscribeBtn.textContent = '✓ Subscribed';
            subscribeBtn.disabled = true;
            subscribeBtn.style.opacity = '0.7';
        } else {
            subscribeBtn.innerHTML = '💳 Subscribe with USDC';
            subscribeBtn.disabled = false;
            subscribeBtn.style.opacity = '1';
        }
    }

    // Update Telegram status
    const tgStatus = document.getElementById('tg-status');
    const tgBtn = document.getElementById('connect-telegram-btn');
    if (tgStatus && tgBtn) {
        if (premiumState.isPremium) {
            if (premiumState.telegramConnected) {
                tgStatus.innerHTML = '<span style="color: #10b981;">✓ Connected to Telegram</span>';
                tgBtn.innerHTML = '<span style="font-size: 18px;">✓</span> Telegram Connected';
                tgBtn.style.background = '#10b981';
            } else {
                tgStatus.textContent = 'Click to connect your Telegram for alerts';
                tgBtn.innerHTML = '<span style="font-size: 18px;">📲</span> Connect @TechneAlertBot';
            }
        } else {
            tgStatus.textContent = 'Premium subscription required for Telegram alerts';
            tgBtn.innerHTML = '<span style="font-size: 18px;">🔒</span> Premium Required';
        }
    }

    // Update subscription status banner
    const banner = document.getElementById('subscription-status-banner');
    if (banner && premiumState.isPremium) {
        banner.style.borderColor = '#d4af37';
        banner.style.background = 'linear-gradient(135deg, #1a1d29 0%, #2d2331 100%)';
    }
}

/**
 * Update search counter display
 */
function updateSearchCounter() {
    const countEl = document.getElementById('search-count');
    const limitEl = document.getElementById('search-limit');
    const displayEl = document.getElementById('search-count-display');

    if (premiumState.isPremium) {
        // Premium: show daily usage
        if (countEl) countEl.textContent = premiumState.searchesToday;
        if (limitEl) limitEl.textContent = PREMIUM_CONFIG.PREMIUM_DAILY_LIMIT;
        if (displayEl) displayEl.style.color = '#d4af37';
    } else {
        // Pay-per-use: show remaining credits
        if (countEl) countEl.textContent = premiumState.searchCredits;
        if (limitEl) limitEl.textContent = 'credits';

        if (displayEl) {
            displayEl.style.color = premiumState.searchCredits > 0 ? '#10b981' : '#ef4444';
        }
    }
}

/**
 * Check if user can perform a search (called from app.js)
 */
function canPerformSearch() {
    if (premiumState.isPremium) {
        return premiumState.searchesToday < PREMIUM_CONFIG.PREMIUM_DAILY_LIMIT;
    }
    return premiumState.searchCredits > 0;
}

/**
 * Increment search counter (called from app.js)
 */
function incrementSearchCount() {
    if (premiumState.isPremium) {
        premiumState.searchesToday++;
        // Show warning near daily limit
        const remaining = PREMIUM_CONFIG.PREMIUM_DAILY_LIMIT - premiumState.searchesToday;
        if (remaining === 20) {
            Toast?.show('⚠️ 20 searches remaining today', 'warning');
        }
    } else {
        // Deduct from credits
        if (premiumState.searchCredits > 0) {
            premiumState.searchCredits--;
            if (premiumState.searchCredits === 2) {
                Toast?.show('⚠️ Only 2 credits left! Buy more or subscribe.', 'warning');
            } else if (premiumState.searchCredits <= 0) {
                showUpgradeModal();
            }
        }
    }
    savePremiumState();
    updateSearchCounter();
    updatePremiumUI();
}

/**
 * Handle buy credits button click ($0.10 for 12 searches)
 */
/**
 * Handle buy credits button click - Redirect to Explore
 */
async function handleBuyCredits() {
    // Navigate to explore section
    const exploreNav = document.querySelector('[data-section="explore"]');
    if (exploreNav) {
        exploreNav.click();
        window.scrollTo({ top: 0, behavior: 'smooth' });
        Toast?.show('View pools in Explore to unlock', 'info');
    } else if (typeof navigateToSection === 'function') {
        navigateToSection('explore');
        window.scrollTo({ top: 0, behavior: 'smooth' });
        Toast?.show('View pools in Explore to unlock', 'info');
    } else {
        console.error('Navigation not found');
        Toast?.show('Please go to Explore page', 'info');
    }
}

/**
 * Handle subscribe button click
 */
async function handleSubscribe() {
    if (!window.connectedWallet) {
        Toast?.show('Please connect your wallet first', 'warning');
        return;
    }

    try {
        Toast?.show('Initiating USDC payment...', 'info');

        // Check if on Base network
        const chainId = await window.ethereum.request({ method: 'eth_chainId' });
        if (chainId !== '0x2105') { // Base mainnet
            Toast?.show('Please switch to Base network', 'warning');
            try {
                await window.ethereum.request({
                    method: 'wallet_switchEthereumChain',
                    params: [{ chainId: '0x2105' }]
                });
            } catch (e) {
                console.error('Failed to switch network:', e);
                return;
            }
        }

        // USDC transfer (ERC20)
        const usdcInterface = new ethers.Interface([
            'function transfer(address to, uint256 amount) returns (bool)'
        ]);

        const data = usdcInterface.encodeFunctionData('transfer', [
            PREMIUM_CONFIG.TREASURY_ADDRESS,
            PREMIUM_CONFIG.SUBSCRIPTION_PRICE
        ]);

        const tx = await window.ethereum.request({
            method: 'eth_sendTransaction',
            params: [{
                from: window.connectedWallet,
                to: PREMIUM_CONFIG.USDC_ADDRESS_BASE,
                data: data
            }]
        });

        Toast?.show('Payment submitted! Activating subscription...', 'info');

        // Activate subscription
        premiumState.isPremium = true;
        premiumState.subscriptionExpires = new Date(Date.now() + PREMIUM_CONFIG.SUBSCRIPTION_DAYS * 24 * 60 * 60 * 1000).toISOString();
        savePremiumState();
        updatePremiumUI();

        Toast?.show('🎉 Premium Plus activated! Welcome to unlimited access.', 'success');

    } catch (error) {
        console.error('Subscription error:', error);
        if (error.code === 4001) {
            Toast?.show('Transaction cancelled', 'info');
        } else {
            Toast?.show('Payment failed: ' + (error.message || 'Unknown error'), 'error');
        }
    }
}

/**
 * Handle Telegram connect button click
 */
function handleTelegramConnect() {
    if (!premiumState.isPremium) {
        Toast?.show('Premium subscription required for Telegram alerts', 'warning');
        // Scroll to subscribe button
        document.getElementById('subscribe-btn')?.scrollIntoView({ behavior: 'smooth' });
        return;
    }

    // Open Telegram bot with deep link containing wallet address
    const walletParam = window.connectedWallet ? `?start=${window.connectedWallet}` : '';
    const botUrl = `https://t.me/${PREMIUM_CONFIG.TELEGRAM_BOT}${walletParam}`;
    window.open(botUrl, '_blank');

    // Mark as connected (in real app, verify via backend)
    setTimeout(() => {
        premiumState.telegramConnected = true;
        savePremiumState();
        updatePremiumUI();
        Toast?.show('Telegram bot opened! Complete setup in the app.', 'success');
    }, 2000);
}

/**
 * Show upgrade modal when no credits
 */
function showUpgradeModal() {
    const existing = document.querySelector('.upgrade-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.className = 'upgrade-modal upgrade-modal-greek';
    modal.innerHTML = `
        <div class="upgrade-content-greek">
            <div class="upgrade-icon">🔒</div>
            <h2>No Search Credits</h2>
            <p>You need credits to search pools. Choose an option:</p>
            
            <button onclick="document.querySelector('.upgrade-modal').remove(); handleBuyCredits();" class="btn-greek-option">
                <div class="option-info">
                    <span class="option-title">💳 Buy 15 Searches</span>
                </div>
                <span class="option-price">$0.10</span>
            </button>
            
            <button onclick="document.querySelector('.upgrade-modal').remove(); document.querySelector('[data-section=premium]')?.click();" class="btn-greek-option premium">
                <div class="option-info">
                    <span class="option-title">⭐ Premium Plus</span>
                    <span class="option-sub">200/day + TG Signals</span>
                </div>
                <span class="option-price">$10/mo</span>
            </button>
            
            <button onclick="document.querySelector('.upgrade-modal').remove();" class="btn-greek-cancel">
                Maybe later
            </button>
        </div>
    `;
    document.body.appendChild(modal);
}

// Expose functions globally
window.PremiumUI = {
    canPerformSearch,
    incrementSearchCount,
    isPremium: () => premiumState.isPremium,
    getState: () => ({ ...premiumState })
};
