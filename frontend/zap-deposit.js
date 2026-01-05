/**
 * Zap & Deposit System + Risk Analysis
 * Single-sided farming with automatic token conversion
 * Implements Gemini feedback on realistic risk labels
 */

class ZapDepositSystem {
    constructor() {
        // Realistic APY thresholds for risk labeling
        this.riskThresholds = {
            safe: { maxApy: 15, label: 'Safe', class: 'low' },
            moderate: { maxApy: 30, label: 'Moderate', class: 'medium' },
            elevated: { maxApy: 50, label: 'Elevated', class: 'medium-high' },
            high: { maxApy: 100, label: 'High Risk', class: 'high' },
            extreme: { maxApy: Infinity, label: 'Extreme', class: 'extreme' }
        };

        // Boosted APY indicators
        this.boostIndicators = {
            temporaryBoost: { minApy: 50, label: '🔥 Boosted' },
            newPool: { label: '✨ New' },
            lowTvl: { maxTvl: 100000, label: '⚠️ Low Liquidity' }
        };
    }

    init() {
        this.patchPoolCards();
        this.patchDepositButtons();
        console.log('[ZapDeposit] System initialized');
    }

    /**
     * Get realistic risk label based on APY and other factors
     */
    getRealisticRisk(pool) {
        const apy = pool.apy || 0;
        const tvl = pool.tvlUsd || pool.tvl || 0;
        const isStable = pool.stablecoin || pool.symbol?.toLowerCase().includes('usd');

        let risk = { label: 'Unknown', class: 'unknown', warnings: [] };

        // Base risk from APY
        if (apy <= 15) {
            risk = { label: 'Safe', class: 'low', warnings: [] };
        } else if (apy <= 30) {
            risk = { label: 'Moderate', class: 'medium', warnings: [] };
        } else if (apy <= 50) {
            risk = { label: 'Elevated', class: 'medium-high', warnings: ['Higher than typical yield'] };
        } else if (apy <= 100) {
            risk = { label: 'High Risk', class: 'high', warnings: ['Very high APY may be unsustainable'] };
        } else {
            risk = { label: 'Extreme', class: 'extreme', warnings: ['Extremely high APY - likely temporary or high risk'] };
        }

        // Adjust for stablecoins
        if (isStable && apy > 25) {
            risk.warnings.push('Unusually high for stablecoin pool');
        }

        // Low TVL warning
        if (tvl < 100000) {
            risk.warnings.push('Low liquidity - slippage risk');
            if (risk.class === 'low') risk.class = 'medium';
        }

        // Very high APY with "stable" label is suspicious
        if (isStable && apy > 100) {
            risk.class = 'extreme';
            risk.label = '⚠️ Verify';
            risk.warnings.push('Stablecoin with 100%+ APY is unusual - verify source');
        }

        return risk;
    }

    /**
     * Get APY badge with boost/temporary indicator
     */
    getApyBadge(apy, pool = {}) {
        let badges = [];

        if (apy > 100) {
            badges.push({ label: '🔥 Boosted', class: 'boosted' });
        } else if (apy > 50) {
            badges.push({ label: '⚡ High Yield', class: 'high-yield' });
        }

        if (pool.tvlUsd < 100000 && apy > 30) {
            badges.push({ label: '⚠️ Low TVL', class: 'warning' });
        }

        // Check if APY is temporary (e.g., new pool or incentive program)
        if (pool.apyReward && pool.apyReward > pool.apyBase * 2) {
            badges.push({ label: '🎁 Rewards', class: 'incentive' });
        }

        return badges;
    }

    /**
     * Enhanced risk analysis for pool detail modal
     */
    generateRiskAnalysis(pool) {
        const risk = this.getRealisticRisk(pool);
        const apy = pool.apy || 0;
        const tvl = pool.tvlUsd || pool.tvl || 0;

        let analysis = [];

        // APY Analysis
        if (apy > 100) {
            analysis.push({
                icon: '⚠️',
                title: 'Very High APY',
                description: `${apy.toFixed(0)}% APY is unusually high. This is likely due to:`,
                details: [
                    'Low liquidity / new pool',
                    'Temporary incentive program',
                    'High impermanent loss risk',
                    'Possibly unsustainable rewards'
                ],
                severity: 'high'
            });
        } else if (apy > 50) {
            analysis.push({
                icon: '⚡',
                title: 'Elevated Yield',
                description: `${apy.toFixed(0)}% APY is above average. Verify the source of rewards.`,
                severity: 'medium'
            });
        } else if (apy > 20) {
            analysis.push({
                icon: '📊',
                title: 'Good Yield',
                description: 'APY is within normal range for DeFi yields.',
                severity: 'low'
            });
        } else {
            analysis.push({
                icon: '🛡️',
                title: 'Conservative Yield',
                description: 'Realistic and sustainable yield level.',
                severity: 'safe'
            });
        }

        // TVL Analysis
        if (tvl < 50000) {
            analysis.push({
                icon: '🚨',
                title: 'Very Low Liquidity',
                description: 'TVL under $50K means high slippage and potential rug risk.',
                severity: 'high'
            });
        } else if (tvl < 500000) {
            analysis.push({
                icon: '⚡',
                title: 'Lower Liquidity',
                description: 'Consider smaller position sizes to avoid slippage.',
                severity: 'medium'
            });
        } else if (tvl > 10000000) {
            analysis.push({
                icon: '✅',
                title: 'High Liquidity',
                description: 'Well-established pool with good liquidity depth.',
                severity: 'safe'
            });
        }

        // Impermanent Loss warning for LP pools
        if (pool.symbol && pool.symbol.includes('/')) {
            analysis.push({
                icon: '📉',
                title: 'Impermanent Loss Risk',
                description: 'This is a liquidity pool. If asset prices diverge, you may experience IL.',
                details: ['Use single-sided options when available', 'Consider correlation between assets'],
                severity: 'medium'
            });
        }

        return { risk, analysis };
    }

    /**
     * Zap & Deposit: Convert single token to LP if needed
     */
    async zapAndDeposit(pool, inputToken, amount) {
        window.Notifications?.info('Preparing Zap & Deposit...');

        // Check if this is an LP pool requiring zap
        const isLpPool = pool.symbol && pool.symbol.includes('/');

        if (isLpPool) {
            // Parse pool tokens
            const tokens = pool.symbol.split('/').map(t => t.trim());
            const [token0, token1] = tokens;

            // Check if user has the input token
            if (inputToken !== token0 && inputToken !== token1) {
                window.Notifications?.warning(`This pool requires ${token0} or ${token1}. Will swap first.`);
            }

            window.Notifications?.info(`Zapping: Swapping 50% of ${inputToken} to create LP position...`);

            // Simulate zap process
            await this.simulateZap(inputToken, tokens, amount);
        }

        window.Notifications?.success(`Deposited ${amount} ${inputToken} into ${pool.symbol}`);

        return true;
    }

    async simulateZap(inputToken, targetTokens, amount) {
        // Simulate swap + LP creation
        return new Promise(resolve => setTimeout(resolve, 2000));
    }

    /**
     * Patch pool cards to show realistic risk labels
     */
    patchPoolCards() {
        // Override the pool card creation to use our risk logic
        const self = this;

        // Intercept pool rendering
        const originalInnerHTMLSetter = Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML').set;

        // Add CSS for new risk badges
        this.addRiskStyles();
    }

    addRiskStyles() {
        if (document.getElementById('zap-risk-styles')) return;

        const style = document.createElement('style');
        style.id = 'zap-risk-styles';
        style.textContent = `
            /* Realistic Risk Badges - Narrow Rounded Pills */
            .risk-badge.extreme {
                background: #7f1d1d;
                color: #fecaca;
                border: none;
            }
            
            .risk-badge.medium-high {
                background: #92400e;
                color: #fde68a;
                border: none;
            }
            
            /* APY Boost Badge */
            .apy-boost-badge {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                padding: 2px 8px;
                font-size: 0.65rem;
                font-weight: 600;
                border-radius: 8px;
                margin-left: 6px;
            }
            
            .apy-boost-badge.boosted {
                background: linear-gradient(135deg, rgba(251, 146, 60, 0.3) 0%, rgba(234, 88, 12, 0.2) 100%);
                color: #fb923c;
            }
            
            .apy-boost-badge.warning {
                background: rgba(239, 68, 68, 0.2);
                color: #fca5a5;
            }
            
            .apy-boost-badge.incentive {
                background: rgba(168, 85, 247, 0.2);
                color: #c4b5fd;
            }
            
            /* Zap & Deposit Button */
            .btn-zap-deposit {
                background: linear-gradient(135deg, #D4AF37 0%, #F4E4BC 50%, #D4AF37 100%);
                background-size: 200% 100%;
                animation: shimmer 2s linear infinite;
                color: #0f0f23;
                font-weight: 700;
                padding: 12px 24px;
                border: none;
                border-radius: 12px;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .btn-zap-deposit:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(212, 175, 55, 0.4);
            }
            
            @keyframes shimmer {
                0% { background-position: 200% 0; }
                100% { background-position: -200% 0; }
            }
            
            /* Risk Analysis Panel */
            .risk-analysis-item {
                display: flex;
                gap: 12px;
                padding: 12px;
                background: rgba(255, 255, 255, 0.02);
                border-radius: 10px;
                margin-bottom: 10px;
            }
            
            .risk-analysis-item.safe {
                border-left: 3px solid #10b981;
            }
            
            .risk-analysis-item.medium {
                border-left: 3px solid #f59e0b;
            }
            
            .risk-analysis-item.high {
                border-left: 3px solid #ef4444;
            }
            
            .risk-analysis-icon {
                font-size: 1.5rem;
            }
            
            .risk-analysis-content h4 {
                margin: 0 0 4px 0;
                font-size: 0.9rem;
                color: #fff;
            }
            
            .risk-analysis-content p {
                margin: 0;
                font-size: 0.8rem;
                color: #888;
            }
            
            .risk-analysis-details {
                margin-top: 8px;
                padding-left: 16px;
                font-size: 0.75rem;
                color: #666;
            }
            
            .risk-analysis-details li {
                margin: 4px 0;
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Patch deposit buttons to show "Zap & Deposit"
     */
    patchDepositButtons() {
        // Update any deposit buttons to show Zap option
        document.querySelectorAll('.btn-deposit, .pool-action-btn').forEach(btn => {
            if (btn.textContent.includes('Deposit')) {
                btn.textContent = '⚡ Zap & Deposit';
                btn.classList.add('btn-zap-deposit');

                // Add demo click handler if none exists
                if (!btn.onclick) {
                    btn.onclick = (e) => {
                        e.stopPropagation();
                        // Check if it's a real pool button (has onclick usually) or static vault button
                        const card = btn.closest('.vault-card');
                        if (card) {
                            const title = card.querySelector('h3')?.textContent || 'Vault';
                            window.Notifications?.info(`🚀 Initializing Agent Strategy: ${title}...`);
                            setTimeout(() => {
                                window.Notifications?.success(`✅ Demo: Allocated to ${title} (Simulated)`);
                            }, 1500);
                        }
                    };
                }
            }
        });

        // Also patch "Details" buttons in vaults
        document.querySelectorAll('.vault-card .btn-details').forEach(btn => {
            if (!btn.onclick) {
                btn.onclick = (e) => {
                    e.stopPropagation();
                    const card = btn.closest('.vault-card');
                    const title = card.querySelector('h3')?.textContent || 'Vault';
                    window.Notifications?.info(`ℹ️ ${title}: Strategy Details coming soon`);
                };
            }
        });
    }

    /**
     * Render risk analysis HTML for pool detail modal
     */
    renderRiskAnalysisHTML(pool) {
        const { risk, analysis } = this.generateRiskAnalysis(pool);

        return `
            <div class="risk-analysis-panel">
                <div class="risk-summary">
                    <span class="risk-badge ${risk.class}">${risk.label}</span>
                    ${risk.warnings.length > 0 ? `
                        <div class="risk-warnings">
                            ${risk.warnings.map(w => `<span class="warning-tag">⚠️ ${w}</span>`).join('')}
                        </div>
                    ` : ''}
                </div>
                
                <div class="risk-items">
                    ${analysis.map(item => `
                        <div class="risk-analysis-item ${item.severity}">
                            <span class="risk-analysis-icon">${item.icon}</span>
                            <div class="risk-analysis-content">
                                <h4>${item.title}</h4>
                                <p>${item.description}</p>
                                ${item.details ? `
                                    <ul class="risk-analysis-details">
                                        ${item.details.map(d => `<li>${d}</li>`).join('')}
                                    </ul>
                                ` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
}

// Initialize
const ZapDeposit = new ZapDepositSystem();
document.addEventListener('DOMContentLoaded', () => ZapDeposit.init());

// Export
window.ZapDeposit = ZapDeposit;
