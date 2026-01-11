/**
 * Pool Detail Modal - Enhanced pool information view
 */

const PoolIcons = {
    close: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`,
    tvl: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>`,
    risk: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`,
    shield: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>`,
    coins: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6"></circle><path d="M18.09 10.37A6 6 0 1 1 10.34 18"></path><path d="M7 6h1v4"></path><path d="m16.71 13.88.7.71-2.82 2.82"></path></svg>`,
    trendUp: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>`,
    trendDown: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"></polyline><polyline points="17 18 23 18 23 12"></polyline></svg>`,
    check: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`,
    activity: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>`,
    bot: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="16" r="4"></circle><path d="M7 6h10"></path><line x1="8" y1="6" x2="8" y2="2"></line><line x1="16" y1="6" x2="16" y2="2"></line></svg>`,
    externalLink: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>`,
    fileText: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>`
};

// Known token address to symbol mapping (Base mainnet)
const TOKEN_ADDRESS_MAP = {
    '0x194f7cd4da3514c7fb38f079d79e4b7200e98bf4': 'MERKL',
    '0x940181a94a35a4569e4529a3cdfb74e38fd98631': 'AERO',
    '0x4200000000000000000000000000000000000006': 'WETH',
    '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913': 'USDC',
    '0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca': 'USDbC',
    '0x50c5725949a6f0c72e6c4a641f24049a917db0cb': 'DAI',
    '0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22': 'cbETH',
    '0xc1cba3fcea344f92d9239c08c0568f6f2f0ee452': 'wstETH',
    '0xb6fe221fe9eef5aba221c348ba20a1bf5e73624c': 'rETH',
    '0x0578d8a44db98b23bf096a382e016e29a5ce0ffe': 'COMP',
    '0x4f604735c1cf31399c6e711d5962b2b3e0225ad3': 'MORPHO',
    '0x78a087d713be963bf3f1c1a8e73af1a31d9eb08d': 'ARB',
};

// Format reward token name - resolve addresses to symbols
function formatRewardTokenName(name) {
    if (!name) return 'TOKEN';

    // Check if it's a hex address (starts with 0x and has 42 chars)
    const addressMatch = name.match(/0x[a-fA-F0-9]{40}/i);
    if (addressMatch) {
        const address = addressMatch[0].toLowerCase();
        // Check mapping first
        if (TOKEN_ADDRESS_MAP[address]) {
            return TOKEN_ADDRESS_MAP[address];
        }
        // Return shortened address
        return `${address.slice(0, 6)}...${address.slice(-4)}`;
    }

    // Check if it's in format "Reward (0x...):" or similar
    if (name.match(/\(0x[a-fA-F0-9]+\)/)) {
        const innerMatch = name.match(/0x[a-fA-F0-9]{40}/i);
        if (innerMatch) {
            const addr = innerMatch[0].toLowerCase();
            if (TOKEN_ADDRESS_MAP[addr]) {
                return TOKEN_ADDRESS_MAP[addr];
            }
            return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
        }
    }

    return name;
}

// Get protocol website URL
function getProtocolWebsite(project) {
    const websites = {
        'aerodrome': 'https://aerodrome.finance',
        'velodrome': 'https://velodrome.finance',
        'aave': 'https://aave.com',
        'aave-v3': 'https://aave.com',
        'compound': 'https://compound.finance',
        'compound-v3': 'https://compound.finance',
        'morpho': 'https://morpho.org',
        'moonwell': 'https://moonwell.fi',
        'curve-dex': 'https://curve.fi',
        'curve': 'https://curve.fi',
        'uniswap': 'https://uniswap.org',
        'uniswap-v3': 'https://uniswap.org',
        'beefy': 'https://beefy.finance',
        'yearn': 'https://yearn.fi',
        'yearn-finance': 'https://yearn.fi',
        'seamless': 'https://seamlessprotocol.com',
        'seamless-protocol': 'https://seamlessprotocol.com',
        'sonne': 'https://sonne.finance',
        'sonne-finance': 'https://sonne.finance',
        'exactly': 'https://exactly.finance',
        'extra-finance': 'https://extra.finance',
        'merkl': 'https://merkl.angle.money',
        'pendle': 'https://pendle.finance',
        'radiant': 'https://radiant.capital',
        'radiant-v2': 'https://radiant.capital',
        'spark': 'https://spark.fi',
        'convex': 'https://convexfinance.com',
        'convex-finance': 'https://convexfinance.com',
        'lido': 'https://lido.fi',
        'gmx': 'https://gmx.io',
        'balancer': 'https://balancer.fi',
        'balancer-v2': 'https://balancer.fi',
        'stargate': 'https://stargate.finance',
        'origin': 'https://originprotocol.com',
        'origin-ether': 'https://originprotocol.com',
        'avantis': 'https://avantis.finance',
        'infinifi': 'https://infinifi.xyz'
    };
    const key = (project || '').toLowerCase().replace(/[^a-z0-9-]/g, '');
    return websites[key] || null;
}

// Get explorer URL for contract
function getExplorerUrl(pool) {
    const chain = (pool.chain || 'base').toLowerCase();
    const explorers = {
        'base': 'https://basescan.org/address/',
        'ethereum': 'https://etherscan.io/address/',
        'arbitrum': 'https://arbiscan.io/address/',
        'optimism': 'https://optimistic.etherscan.io/address/',
        'polygon': 'https://polygonscan.com/address/'
    };
    const baseUrl = explorers[chain] || explorers['base'];
    const contractAddress = pool.pool_address || pool.contract || pool.id;
    if (contractAddress && contractAddress.startsWith('0x')) {
        return `${baseUrl}${contractAddress}`;
    }
    return null;
}

const PoolDetailModal = {
    currentPool: null,

    // Calculate time until next Aerodrome/Velodrome epoch (Wednesday 00:00 UTC)
    getEpochCountdown() {
        const now = new Date();
        const nextWed = new Date(now);
        nextWed.setUTCHours(0, 0, 0, 0);
        const currentDay = now.getUTCDay();
        const daysUntilWed = (3 - currentDay + 7) % 7 || 7;
        nextWed.setUTCDate(now.getUTCDate() + daysUntilWed);
        const diff = nextWed - now;
        const days = Math.floor(diff / 86400000);
        const hours = Math.floor((diff % 86400000) / 3600000);
        const minutes = Math.floor((diff % 3600000) / 60000);
        return { days, hours, minutes, display: `${days}d ${hours}h ${minutes}m` };
    },

    // Check if protocol has epoch-based rewards
    isEpochProtocol(project) {
        const ep = (project || '').toLowerCase();
        return ep.includes('aerodrome') || ep.includes('velodrome');
    },

    // Keydown handler
    handleKeydown(e) {
        if (e.key === 'Escape') {
            PoolDetailModal.close();
        }
    },

    // =========================================
    // SECURITY ASSESSMENT (Safety Guard)
    // =========================================

    /**
     * Assess pool security from backend data
     * Returns { isCritical, isWarning, warnings, canDeposit }
     */
    assessSecurity(pool) {
        const security = pool.security || {};
        const riskScore = pool.risk_score || pool.riskScore || 50;
        const riskAnalysis = pool.risk_analysis || {};

        const result = {
            isCritical: false,
            isWarning: false,
            warnings: [],
            canDeposit: true,
            honeypot: false,
            unverified: false,
            highTax: false,
            depeg: false
        };

        // Check 1: Honeypot detection (CRITICAL)
        if (security.is_honeypot || riskAnalysis.is_honeypot) {
            result.isCritical = true;
            result.canDeposit = false;
            result.honeypot = true;
            result.warnings.push('🚨 HONEYPOT DETECTED - Cannot sell tokens!');
        }

        // Check 2: Risk score below 30 (CRITICAL)
        if (riskScore < 30 && !result.isCritical) {
            result.isCritical = true;
            result.canDeposit = false;
            result.warnings.push(`🚨 Critical risk level (Score: ${riskScore}/100)`);
        }

        // Check 3: Unverified contract (WARNING)
        if (security.tokens) {
            for (const [addr, info] of Object.entries(security.tokens)) {
                if (info && info.is_verified === false) {
                    result.isWarning = true;
                    result.unverified = true;
                    result.warnings.push('⚠️ Unverified contract - not open source');
                    break;
                }
            }
        }

        // Check 4: High tax detection (WARNING)
        if (security.tokens) {
            for (const [addr, info] of Object.entries(security.tokens)) {
                if (info) {
                    const sellTax = parseFloat(info.sell_tax || 0) * 100;
                    const buyTax = parseFloat(info.buy_tax || 0) * 100;
                    if (sellTax > 10 || buyTax > 10) {
                        result.isWarning = true;
                        result.highTax = true;
                        result.warnings.push(`⚠️ High tax detected: Buy ${buyTax.toFixed(1)}% / Sell ${sellTax.toFixed(1)}%`);
                        break;
                    }
                }
            }
        }

        // Check 5: Stablecoin depeg (WARNING)
        const pegStatus = security.peg_status || {};
        if (pegStatus.depeg_risk) {
            result.isWarning = true;
            result.depeg = true;
            const depegged = pegStatus.depegged_tokens || [];
            depegged.forEach(t => {
                result.warnings.push(`⚠️ ${t.symbol} DEPEG: $${t.price?.toFixed(4)} (${t.deviation?.toFixed(2)}% off peg)`);
            });
        }

        return result;
    },

    /**
     * Format reward token name - prefer backend symbols over addresses
     */
    formatRewardSymbol(token) {
        // If backend provides symbol, use it
        if (token.symbol && !token.symbol.startsWith('0x')) {
            return token.symbol;
        }
        // Fallback to address mapping
        if (token.address && TOKEN_ADDRESS_MAP[token.address.toLowerCase()]) {
            return TOKEN_ADDRESS_MAP[token.address.toLowerCase()];
        }
        // Last resort: truncate address
        if (token.address) {
            return `${token.address.slice(0, 6)}...`;
        }
        return token.symbol || '???';
    },

    /**
     * Render deposit button based on security assessment
     */
    renderDepositButton(pool, security) {
        const project = (pool.project || '').toUpperCase();
        const poolUrl = pool.pool_link || (window.getPoolUrl ? getPoolUrl(pool) : '#');

        if (security.isCritical) {
            // BLOCKED: Critical risk
            return `
                <button class="pd-btn-danger" disabled onclick="alert('⚠️ Deposit blocked: ${security.warnings[0]}')">
                    🚫 DEPOSIT BLOCKED - CRITICAL RISK
                </button>
            `;
        } else if (security.isWarning) {
            // WARNING: Show caution but allow
            return `
                <a href="${poolUrl}" target="_blank" class="pd-btn-warning" onclick="return confirm('⚠️ Warning:\\n${security.warnings.join('\\n')}\\n\\nDo you want to proceed?');">
                    ⚠️ DEPOSIT ON ${project} (CAUTION)
                </a>
            `;
        } else {
            // SAFE: Normal deposit
            return `
                <a href="${poolUrl}" target="_blank" class="pd-btn-primary" onclick="event.stopPropagation();">
                    💰 DEPOSIT ON ${project}
                </a>
            `;
        }
    },

    // =========================================
    // APY EXPLAINER - Source and Confidence
    // =========================================

    /**
     * Render APY source explanation
     * Shows user where APY comes from and any caveats
     */
    renderApyExplainer(pool) {
        const apySource = pool.apy_source || 'unknown';
        const hasGauge = pool.gauge_address || pool.has_gauge;
        const isEpoch = this.isEpochProtocol(pool.project);
        const isCL = (pool.pool_type === 'cl') || (pool.project || '').toLowerCase().includes('slipstream');

        // Determine source label and explanation
        let sourceLabel, sourceIcon, explanation, confidence;

        if (apySource.includes('gauge') || apySource.includes('v2_onchain')) {
            sourceLabel = 'Gauge Emissions';
            sourceIcon = '🎯';
            explanation = 'APY from AERO token rewards distributed to stakers';
            confidence = 'high';
        } else if (apySource.includes('cl_calculated')) {
            sourceLabel = 'Gauge + Total TVL';
            sourceIcon = '📊';
            explanation = 'Emissions ÷ total pool TVL. Actual staker APR may be higher if not all liquidity is staked.';
            confidence = 'medium';
        } else if (apySource.includes('defillama')) {
            sourceLabel = 'DefiLlama Aggregate';
            sourceIcon = '📈';
            explanation = 'Historical yield data from aggregator';
            confidence = 'medium';
        } else if (apySource.includes('geckoterminal')) {
            sourceLabel = 'GeckoTerminal';
            sourceIcon = '🦎';
            explanation = 'Market-derived APY estimate';
            confidence = 'medium';
        } else {
            sourceLabel = 'Estimated';
            sourceIcon = '⚙️';
            explanation = 'Calculated from available data';
            confidence = 'low';
        }

        // Build caveats based on pool characteristics
        const caveats = [];
        if (isEpoch) caveats.push('Epoch-based: changes weekly');
        if (isCL) caveats.push('CL pool: gauge APR may differ');
        if (hasGauge) caveats.push('Requires gauge staking');
        if (pool.apy > 100) caveats.push('High APY: verify sustainability');

        // If APY is N/A, explain why
        if (!pool.apy || pool.apy === 0) {
            const reason = pool.apy_reason || pool.apy_status || 'Data unavailable';
            return `
                <div class="pd-apy-explainer unavailable">
                    <div class="pd-apy-source">
                        <span class="pd-source-icon">❓</span>
                        <span class="pd-source-label">APY Unavailable</span>
                    </div>
                    <div class="pd-apy-reason">${this.formatApyReason(reason)}</div>
                </div>
            `;
        }

        return `
            <div class="pd-apy-explainer">
                <div class="pd-apy-source">
                    <span class="pd-source-icon">${sourceIcon}</span>
                    <span class="pd-source-label">Source: ${sourceLabel}</span>
                    <span class="pd-confidence ${confidence}">${confidence.toUpperCase()}</span>
                </div>
                <div class="pd-apy-explanation">${explanation}</div>
                ${caveats.length > 0 ? `
                    <div class="pd-apy-caveats">
                        ${caveats.map(c => `<span class="pd-caveat">• ${c}</span>`).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    },

    /**
     * Render "Why this APY can change" expandable section
     * Educates user about volatility factors
     */
    renderApyChangeExplainer(pool) {
        const isCL = (pool.pool_type === 'cl') || (pool.project || '').toLowerCase().includes('slipstream');
        const isEpoch = this.isEpochProtocol(pool.project);
        const hasGauge = pool.gauge_address || pool.has_gauge;

        const reasons = [];

        // Epoch-based emissions
        if (isEpoch) {
            reasons.push({
                icon: '⏰',
                title: 'Epoch-based emissions',
                desc: 'Rewards reset each epoch (typically weekly). New votes determine emission levels.'
            });
        }

        // CL liquidity dependency
        if (isCL) {
            reasons.push({
                icon: '🎯',
                title: 'Active liquidity dependency',
                desc: 'CL pool APY depends on your position range. Out-of-range = 0 rewards.'
            });
        }

        // Gauge re-weighting
        if (hasGauge) {
            reasons.push({
                icon: '🗳️',
                title: 'Gauge can be re-weighted',
                desc: 'veAERO/veVELO voters decide emissions. Gauge weight changes weekly.'
            });
        }

        // TVL changes
        reasons.push({
            icon: '💧',
            title: 'TVL fluctuations',
            desc: 'Same rewards ÷ more TVL = lower APY. Large deposits dilute returns.'
        });

        // Token price
        if (pool.apy_reward > 0 || hasGauge) {
            reasons.push({
                icon: '📉',
                title: 'Reward token price',
                desc: 'APY is calculated at current token prices. Token value changes affect real returns.'
            });
        }

        if (reasons.length === 0) return '';

        return `
            <details class="pd-apy-change-section">
                <summary class="pd-apy-change-header">
                    <span class="pd-change-icon">⚡</span>
                    <span>Why this APY can change</span>
                    <span class="pd-expand-arrow">▶</span>
                </summary>
                <div class="pd-apy-change-content">
                    ${reasons.map(r => `
                        <div class="pd-change-reason">
                            <span class="pd-reason-icon">${r.icon}</span>
                            <div class="pd-reason-text">
                                <strong>${r.title}</strong>
                                <span>${r.desc}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </details>
        `;
    },

    /**
     * Render Liquidity Stress Indicator
     * Simulates impact of TVL drops since we don't have historical data
     */
    renderLiquidityStress(pool) {
        const tvl = pool.tvl || pool.tvlUsd || 0;
        if (!tvl || tvl <= 0) return '';

        // Format TVL helper
        const formatTvl = (val) => {
            if (val >= 1e9) return `$${(val / 1e9).toFixed(1)}B`;
            if (val >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
            if (val >= 1e3) return `$${(val / 1e3).toFixed(0)}K`;
            return `$${val.toFixed(0)}`;
        };

        // Calculate stress scenarios
        const scenarios = [
            { drop: 10, level: 'low', label: 'Low impact', color: '#22C55E' },
            { drop: 30, level: 'medium', label: 'Medium impact', color: '#F59E0B' },
            { drop: 50, level: 'high', label: 'High slippage risk', color: '#EF4444' }
        ];

        // Determine current stress level based on absolute TVL
        let currentStress = 'healthy';
        let stressColor = '#22C55E';
        if (tvl < 100000) {
            currentStress = 'critical';
            stressColor = '#EF4444';
        } else if (tvl < 500000) {
            currentStress = 'stressed';
            stressColor = '#F59E0B';
        } else if (tvl < 2000000) {
            currentStress = 'moderate';
            stressColor = '#84CC16';
        }

        return `
            <div class="pd-liquidity-stress">
                <div class="pd-stress-header">
                    <span class="pd-stress-icon">💧</span>
                    <span class="pd-stress-title">Liquidity Stress Test</span>
                    <span class="pd-stress-current" style="color: ${stressColor}">
                        ${currentStress.charAt(0).toUpperCase() + currentStress.slice(1)}
                    </span>
                </div>
                <div class="pd-stress-scenarios">
                    ${scenarios.map(s => {
            const newTvl = tvl * (1 - s.drop / 100);
            return `
                            <div class="pd-stress-row ${s.level}">
                                <div class="pd-stress-drop">-${s.drop}% TVL</div>
                                <div class="pd-stress-bar-container">
                                    <div class="pd-stress-bar" style="width: ${100 - s.drop}%; background: ${s.color}"></div>
                                </div>
                                <div class="pd-stress-result">
                                    <span class="pd-stress-tvl">${formatTvl(newTvl)}</span>
                                    <span class="pd-stress-impact" style="color: ${s.color}">${s.label}</span>
                                </div>
                            </div>
                        `;
        }).join('')}
                </div>
                <div class="pd-stress-footer">
                    Simulated impact if liquidity exits. Current: ${formatTvl(tvl)}
                </div>
            </div>
        `;
    },

    formatApyReason(reason) {
        const reasons = {
            'CL_POOL_NO_ONCHAIN_TVL': 'Concentrated liquidity - TVL data unavailable',
            'NO_GAUGE': 'No gauge - no emission rewards',
            'GAUGE_METHODS_FAILED': 'Unable to read gauge contract',
            'LP_PRICE_ZERO': 'Could not determine LP token value',
            'requires_external_tvl': 'Waiting for external TVL data',
            'unsupported': 'Pool type not supported for APY calculation',
            'error': 'Error during calculation'
        };
        return reasons[reason] || reason || 'Calculation not available';
    },

    // =========================================
    // DATA COVERAGE - Transparency Section
    // =========================================

    /**
     * Render data coverage section
     * Shows what data is available vs unavailable
     */
    renderDataCoverage(pool) {
        const coverage = [];

        // On-chain state - green if we have gauge verification
        const hasGaugeVerification = pool.has_gauge || pool.gauge_address;
        const hasAddress = pool.pool_address || pool.address;

        coverage.push({
            label: 'On-chain State',
            status: hasGaugeVerification ? 'available' : (hasAddress ? 'partial' : 'unavailable'),
            detail: hasGaugeVerification ? 'Gauge verified' : (hasAddress ? 'Address found' : 'Not verified')
        });

        // APY
        if (pool.apy && pool.apy > 0) {
            const source = (pool.apy_source || '').toLowerCase();
            // Gauge, V2 on-chain, CL calculated, and Merkl are all "our" calculations
            const isOnchain = source.includes('gauge') ||
                source.includes('onchain') ||
                source.includes('v2_') ||
                source.includes('cl_calculated') ||
                source.includes('merkl') ||
                source.includes('aerodrome');
            // External = defillama, geckoterminal, etc
            const isExternal = source.includes('defillama') ||
                source.includes('gecko') ||
                source.includes('external');

            let status, detail;
            if (isOnchain) {
                status = 'available';
                detail = 'On-chain verified';
            } else if (isExternal) {
                status = 'partial';
                detail = 'Aggregator data';
            } else {
                status = 'partial';
                detail = 'Calculated estimate';
            }

            coverage.push({
                label: 'APY Calculation',
                status: status,
                detail: detail
            });
        } else {
            coverage.push({
                label: 'APY Calculation',
                status: 'unavailable',
                detail: this.formatApyReason(pool.apy_reason || pool.apy_status)
            });
        }

        // TVL
        coverage.push({
            label: 'TVL',
            status: pool.tvl > 0 ? 'available' : 'unavailable',
            detail: pool.tvl > 0 ? 'Real-time data' : 'No data'
        });

        // Volume
        coverage.push({
            label: '24h Volume',
            status: pool.volume_24h || pool.volume_24h_formatted !== 'N/A' ? 'available' : 'unavailable',
            detail: pool.volume_24h ? 'Market data' : 'Not tracked'
        });

        // Historical
        coverage.push({
            label: 'TVL History',
            status: typeof pool.tvl_change_7d === 'number' ? 'available' : 'unavailable',
            detail: typeof pool.tvl_change_7d === 'number' ? '7-day trend' : 'No history'
        });

        const availableCount = coverage.filter(c => c.status === 'available').length;
        const totalCount = coverage.length;
        const coveragePercent = Math.round((availableCount / totalCount) * 100);

        return `
            <div class="pd-data-coverage">
                <div class="pd-coverage-header">
                    <span class="pd-coverage-title">📋 Data Coverage</span>
                    <span class="pd-coverage-score">${availableCount}/${totalCount} (${coveragePercent}%)</span>
                </div>
                <div class="pd-coverage-grid">
                    ${coverage.map(c => `
                        <div class="pd-coverage-item ${c.status}">
                            <span class="pd-coverage-dot ${c.status}"></span>
                            <span class="pd-coverage-label">${c.label}</span>
                            <span class="pd-coverage-detail">${c.detail}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    },

    // =========================================
    // CONFIDENCE LEVEL - How Certain Are We?
    // =========================================

    // Render confidence level based on data completeness
    // Shows user how reliable our estimates are
    renderConfidenceLevel(pool) {
        // Calculate confidence score based on available data
        let confidencePoints = 0;
        let maxPoints = 0;
        const factors = [];

        // APY Source (most important)
        maxPoints += 40;
        const apySource = (pool.apy_source || '').toLowerCase();

        // Tier 1: On-chain verified sources (gauge data used for APY)
        if (apySource.includes('onchain') || apySource.includes('gauge') ||
            apySource.includes('aerodrome') || apySource.includes('velodrome') ||
            apySource.includes('v2_onchain') || apySource.includes('staker') ||
            apySource.includes('tvl_fallback')) {
            confidencePoints += 40;
            factors.push({ label: 'APY', status: 'high', text: 'On-chain verified' });
        }
        // Tier 2: Calculated from emissions/rewards
        else if (apySource.includes('merkl') || apySource.includes('cl_calculated') ||
            apySource.includes('cl_staker') || apySource.includes('reward')) {
            confidencePoints += 35;
            factors.push({ label: 'APY', status: 'high', text: 'Calculated from rewards' });
        }
        // Tier 3: Verified API sources (known protocols with reliable APY data)
        else if (apySource.includes('beefy') || apySource.includes('moonwell') ||
            apySource.includes('aave') || apySource.includes('compound') ||
            apySource.includes('morpho') || apySource.includes('curve') ||
            apySource.includes('sushi') || apySource.includes('uniswap')) {
            confidencePoints += 30;
            factors.push({ label: 'APY', status: 'high', text: 'Protocol API verified' });
        }
        // Tier 4: Aggregator data
        else if (apySource.includes('defillama') || apySource.includes('gecko') ||
            apySource.includes('llama')) {
            confidencePoints += 25;
            factors.push({ label: 'APY', status: 'medium', text: 'Third-party aggregator' });
        }
        // Tier 5: Has APY but unknown source
        else if (pool.apy > 0) {
            confidencePoints += 15;
            factors.push({ label: 'APY', status: 'low', text: 'Source unverified' });
        }
        // No APY
        else {
            factors.push({ label: 'APY', status: 'unavailable', text: 'Unknown source' });
        }

        // TVL Data
        maxPoints += 25;
        if (pool.tvl > 0) {
            confidencePoints += 25;
            factors.push({ label: 'TVL', status: 'high', text: `$${(pool.tvl / 1e6).toFixed(2)}M verified` });
        } else {
            factors.push({ label: 'TVL', status: 'unavailable', text: 'Not available' });
        }

        // Historical Data
        maxPoints += 20;
        if (pool.tvl_change_7d !== undefined && pool.tvl_change_7d !== 0) {
            confidencePoints += 20;
            factors.push({ label: 'History', status: 'high', text: '7-day data available' });
        } else {
            factors.push({ label: 'History', status: 'unavailable', text: 'No historical data' });
        }

        // Protocol Recognition
        maxPoints += 15;
        const knownProtocols = ['aerodrome', 'velodrome', 'uniswap', 'aave', 'compound', 'moonwell', 'beefy', 'morpho', 'curve', 'sushiswap', 'sushi'];
        const projectLower = (pool.project || '').toLowerCase();
        if (knownProtocols.some(p => projectLower.includes(p))) {
            confidencePoints += 15;
            factors.push({ label: 'Protocol', status: 'high', text: 'Verified protocol' });
        } else {
            confidencePoints += 5;
            factors.push({ label: 'Protocol', status: 'medium', text: 'Less known' });
        }

        const confidencePercent = Math.round((confidencePoints / maxPoints) * 100);
        let confidenceLabel, confidenceColor, confidenceEmoji;

        if (confidencePercent >= 80) {
            confidenceLabel = 'High';
            confidenceColor = '#22C55E';
            confidenceEmoji = '🟢';
        } else if (confidencePercent >= 50) {
            confidenceLabel = 'Medium';
            confidenceColor = '#F59E0B';
            confidenceEmoji = '🟡';
        } else {
            confidenceLabel = 'Low';
            confidenceColor = '#EF4444';
            confidenceEmoji = '🔴';
        }

        return `
            <div class="pd-confidence-section">
                <div class="pd-confidence-header">
                    <span class="pd-confidence-title">🔍 Data Confidence</span>
                    <span class="pd-confidence-badge" style="background: ${confidenceColor}20; color: ${confidenceColor}">
                        ${confidenceEmoji} ${confidenceLabel} (${confidencePercent}%)
                    </span>
                </div>
                <div class="pd-confidence-subtitle">How reliable are our estimates?</div>
                <div class="pd-confidence-factors">
                    ${factors.map(f => `
                        <div class="pd-confidence-factor ${f.status}">
                            <span class="pd-conf-label">${f.label}</span>
                            <span class="pd-conf-status ${f.status}">
                                ${f.status === 'high' ? '✓' : f.status === 'medium' ? '~' : '?'}
                            </span>
                            <span class="pd-conf-text">${f.text}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    },

    // =========================================
    // DECISION GUIDANCE - Is This Right For Me?
    // =========================================

    // Render decision guidance based on pool characteristics
    // Helps user understand if pool matches their profile
    renderDecisionGuidance(pool) {
        const recommendations = [];
        const warnings = [];

        // Analyze APY sustainability
        const apy = pool.apy || 0;
        const apyReward = pool.apy_reward || 0;
        const rewardPercent = apy > 0 ? (apyReward / apy) * 100 : 0;

        if (rewardPercent > 80) {
            warnings.push({
                icon: '⚠️',
                text: 'APY heavily depends on token emissions',
                detail: 'May decrease as incentives are reduced'
            });
        }

        if (apy > 50) {
            warnings.push({
                icon: '🔥',
                text: `High APY (${apy.toFixed(0)}%) is likely temporary`,
                detail: 'Based on current incentive rates'
            });
        }

        // Analyze TVL
        const tvl = pool.tvl || 0;
        if (tvl < 500000) {
            warnings.push({
                icon: '💧',
                text: 'Lower liquidity pool',
                detail: 'May have slippage on larger positions'
            });
        } else if (tvl > 10000000) {
            recommendations.push({
                icon: '✓',
                text: 'Deep liquidity',
                detail: 'Suitable for larger positions'
            });
        }

        // Analyze pool type
        const poolType = pool.pool_type || '';
        const isConcentrated = poolType === 'cl' || (pool.protocol || '').includes('slipstream');

        if (isConcentrated) {
            warnings.push({
                icon: '📊',
                text: 'Requires active management',
                detail: 'Concentrated liquidity - rebalance needed'
            });
        }

        // Stable vs volatile
        if (pool.il_risk === 'yes') {
            warnings.push({
                icon: '📉',
                text: 'Impermanent loss risk',
                detail: 'One asset may depreciate vs the other'
            });
        } else if (pool.pool_type === 'stable') {
            recommendations.push({
                icon: '✓',
                text: 'Stablecoin pair',
                detail: 'Minimal IL risk'
            });
        }

        // Good for scenarios
        const goodFor = [];
        if (apy < 15 && tvl > 5000000 && pool.il_risk !== 'yes') {
            goodFor.push('Conservative yield farming');
        }
        if (apy > 30 && tvl > 1000000) {
            goodFor.push('Short-term yield optimization');
        }
        if (pool.pool_type === 'stable') {
            goodFor.push('Stable yield with low IL');
        }
        if (rewardPercent < 50 && apy > 5) {
            goodFor.push('Sustainable long-term holding');
        }

        return `
            <div class="pd-decision-section">
                <div class="pd-decision-header">
                    <span class="pd-decision-title">💡 Decision Guidance</span>
                </div>
                
                ${warnings.length > 0 ? `
                    <div class="pd-decision-warnings">
                        <div class="pd-decision-subtitle">⚠️ Consider Before Depositing</div>
                        ${warnings.map(w => `
                            <div class="pd-decision-item warning">
                                <span class="pd-decision-icon">${w.icon}</span>
                                <div class="pd-decision-content">
                                    <span class="pd-decision-text">${w.text}</span>
                                    <span class="pd-decision-detail">${w.detail}</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
                
                ${recommendations.length > 0 ? `
                    <div class="pd-decision-recs">
                        <div class="pd-decision-subtitle">✅ Positive Factors</div>
                        ${recommendations.map(r => `
                            <div class="pd-decision-item positive">
                                <span class="pd-decision-icon">${r.icon}</span>
                                <div class="pd-decision-content">
                                    <span class="pd-decision-text">${r.text}</span>
                                    <span class="pd-decision-detail">${r.detail}</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
                
                ${goodFor.length > 0 ? `
                    <div class="pd-decision-goodfor">
                        <span class="pd-goodfor-label">Good for:</span>
                        ${goodFor.map(g => `<span class="pd-goodfor-tag">${g}</span>`).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    },

    // =========================================
    // EXIT STRATEGY - How Do I Withdraw?
    // =========================================

    // Render exit strategy section
    // Shows user how to withdraw and any constraints
    renderExitStrategy(pool) {
        const exitInfo = [];
        const projectLower = (pool.project || '').toLowerCase();
        const poolType = pool.pool_type || 'lp';

        // Determine withdrawal method based on protocol
        if (projectLower.includes('aerodrome') || projectLower.includes('velodrome')) {
            exitInfo.push({
                icon: '🏊',
                label: 'Withdraw at',
                value: `${pool.project || 'Protocol'} app`,
                link: pool.pool_link || `https://${projectLower.includes('aero') ? 'aerodrome.finance' : 'velodrome.finance'}`
            });
            if (pool.has_gauge) {
                exitInfo.push({
                    icon: '🎯',
                    label: 'Claim rewards',
                    value: 'Unstake from gauge first',
                    link: null
                });
            }
        } else if (projectLower.includes('moonwell')) {
            exitInfo.push({
                icon: '🌙',
                label: 'Redeem at',
                value: 'Moonwell app',
                link: pool.pool_link || 'https://moonwell.fi'
            });
            exitInfo.push({
                icon: '📊',
                label: 'Availability',
                value: `${100 - (pool.utilization_rate || 0)}% available for withdrawal`,
                link: null
            });
        } else if (projectLower.includes('beefy')) {
            exitInfo.push({
                icon: '🐄',
                label: 'Withdraw at',
                value: 'Beefy vault page',
                link: pool.pool_link || 'https://app.beefy.com'
            });
            if (pool.vault_withdrawal_fee) {
                exitInfo.push({
                    icon: '💸',
                    label: 'Withdrawal fee',
                    value: `${pool.vault_withdrawal_fee}%`,
                    link: null
                });
            }
        } else {
            exitInfo.push({
                icon: '🔗',
                label: 'Withdraw via',
                value: pool.project || 'Protocol app',
                link: pool.pool_link || null
            });
        }

        // Epoch-based rewards
        if (this.isEpochProtocol(pool.project)) {
            const epoch = this.getEpochCountdown();
            exitInfo.push({
                icon: '⏰',
                label: 'Claim before',
                value: `Epoch ends in ${epoch.display}`,
                link: null
            });
        }

        // Slippage warning for low TVL
        const tvl = pool.tvl || 0;
        if (tvl < 500000) {
            exitInfo.push({
                icon: '⚠️',
                label: 'Slippage warning',
                value: 'Exit in smaller chunks for large positions',
                link: null
            });
        }

        return `
            <div class="pd-exit-section">
                <div class="pd-exit-header">
                    <span class="pd-exit-title">🚪 Exit Strategy</span>
                </div>
                <div class="pd-exit-items">
                    ${exitInfo.map(e => `
                        <div class="pd-exit-item">
                            <span class="pd-exit-icon">${e.icon}</span>
                            <span class="pd-exit-label">${e.label}:</span>
                            ${e.link ?
                `<a href="${e.link}" target="_blank" class="pd-exit-value link">${e.value}</a>` :
                `<span class="pd-exit-value">${e.value}</span>`
            }
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    },

    // =========================================
    // VERIFY FLAGS - Concrete Risk Indicators
    // =========================================


    /**
     * Render concrete risk flags (not generic "Medium")
     * Uses backend risk_flags when available, falls back to frontend detection
     */
    renderVerifyFlags(pool) {
        let flags = [];

        // PRIORITY: Use backend risk_flags if available (from SmartRouter)
        if (pool.risk_flags && pool.risk_flags.length > 0) {
            flags = pool.risk_flags.map(rf => ({
                icon: rf.icon || '⚠️',
                text: rf.label,
                type: rf.severity === 'high' ? 'warning' : (rf.severity === 'medium' ? 'caution' : 'info'),
                tooltip: rf.description
            }));
        } else {
            // FALLBACK: Frontend detection (for pools without backend flags)
            const isCL = (pool.pool_type === 'cl') || (pool.project || '').toLowerCase().includes('slipstream');
            const isStable = pool.pool_type === 'stable' || pool.stablecoin;

            // Pool type flags
            if (isCL) {
                flags.push({ icon: '🎯', text: 'Concentrated Liquidity', type: 'info', tooltip: 'Active liquidity mgmt required' });
            }
            if (pool.gauge_address) {
                flags.push({ icon: '⚡', text: 'Emissions-based yield', type: 'info', tooltip: 'APY from token rewards' });
            }
            if (this.isEpochProtocol(pool.project)) {
                flags.push({ icon: '⏰', text: 'Epoch-based rewards', type: 'info', tooltip: 'Rewards reset weekly' });
            }

            // Risk flags
            if (!isStable && (pool.il_risk === 'yes' || pool.il_risk !== 'no')) {
                flags.push({ icon: '📉', text: 'Impermanent Loss risk', type: 'warning', tooltip: 'Volatile token pair' });
            }
            if (pool.apy > 200) {
                flags.push({ icon: '🔥', text: 'Very high APY', type: 'warning', tooltip: 'Verify sustainability' });
            }
            if (pool.tvl < 100000) {
                flags.push({ icon: '💧', text: 'Low liquidity', type: 'warning', tooltip: 'May have slippage issues' });
            }

            // External dependency
            if (pool.apy_source && (pool.apy_source.includes('external') || pool.apy_source.includes('cl_calculated'))) {
                flags.push({ icon: '🔗', text: 'External data dependency', type: 'info', tooltip: 'APY uses off-chain data' });
            }
        }

        if (flags.length === 0) {
            return ''; // No flags to show
        }

        return `
            <div class="pd-verify-flags">
                <div class="pd-flags-title">🚩 Risk Flags</div>
                <div class="pd-flags-grid">
                    ${flags.map(f => `
                        <div class="pd-flag ${f.type}" title="${f.tooltip}">
                            <span class="pd-flag-icon">${f.icon}</span>
                            <span class="pd-flag-text">${f.text}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    },

    // Render Artisan Agent verdict banner for verified pools
    // Greek Gold Gaming Matrix style - elegant circular score
    renderVerdictBanner(pool) {
        const riskScore = pool.riskScore || pool.risk_score || 50;
        const riskLevel = pool.riskLevel || pool.risk_level || 'Medium';
        const dataSource = pool.dataSource || 'defillama';

        let verdict, scoreColor, glowColor, bgGradient, verdictDesc;

        if (riskScore >= 70 || riskLevel === 'Low') {
            verdict = 'SAFE';
            scoreColor = '#10B981';
            glowColor = 'rgba(16, 185, 129, 0.4)';
            bgGradient = 'linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(16, 185, 129, 0.02))';
            verdictDesc = 'Pool has passed Artisan Agent risk assessment';
        } else if (riskScore >= 40 || riskLevel === 'Medium') {
            verdict = 'CAUTION';
            scoreColor = '#D4A853';
            glowColor = 'rgba(212, 168, 83, 0.4)';
            bgGradient = 'linear-gradient(135deg, rgba(212, 168, 83, 0.08), rgba(212, 168, 83, 0.02))';
            verdictDesc = 'Careful consideration recommended before investing';
        } else {
            verdict = 'HIGH RISK';
            scoreColor = '#EF4444';
            glowColor = 'rgba(239, 68, 68, 0.4)';
            bgGradient = 'linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(239, 68, 68, 0.02))';
            verdictDesc = 'Significant risk factors detected - proceed with caution';
        }

        // Calculate circle progress (stroke-dasharray for 100% = 251.2)
        const circumference = 251.2;
        const progress = (riskScore / 100) * circumference;
        const dashOffset = circumference - progress;

        // Data source badge
        let sourceBadge;
        if (dataSource.includes('geckoterminal')) {
            sourceBadge = '🦎 GeckoTerminal';
        } else if (dataSource.includes('defillama')) {
            sourceBadge = '📊 DefiLlama';
        } else if (dataSource.includes('aerodrome')) {
            sourceBadge = '🛩️ Aerodrome';
        } else {
            sourceBadge = '⛓️ On-chain';
        }

        return `
            <div class="matrix-verdict" style="background: ${bgGradient}; border-color: ${scoreColor}30;">
                <div class="matrix-score-ring" style="--score-color: ${scoreColor}; --glow-color: ${glowColor};">
                    <svg viewBox="0 0 100 100">
                        <circle class="ring-bg" cx="50" cy="50" r="40" />
                        <circle class="ring-progress" cx="50" cy="50" r="40" 
                            style="stroke: ${scoreColor}; stroke-dasharray: ${circumference}; stroke-dashoffset: ${dashOffset};" />
                    </svg>
                    <div class="score-value" style="color: ${scoreColor};">${riskScore}</div>
                </div>
                <div class="matrix-info">
                    <div class="matrix-verdict-label" style="color: ${scoreColor};">${verdict}</div>
                    <div class="matrix-desc">${verdictDesc}</div>
                    <div class="matrix-meta">
                        <span class="matrix-source-badge">${sourceBadge}</span>
                        <span class="matrix-score-text">Score: ${riskScore}/100</span>
                    </div>
                </div>
            </div>
        `;
    },

    show(pool) {
        this.currentPool = pool;

        // Add to history
        if (window.SearchHistory) {
            SearchHistory.addEntry('pool_view', {
                project: pool.project,
                symbol: pool.symbol,
                apy: pool.apy
            });
        }

        // Add ESC listener
        document.addEventListener('keydown', this.handleKeydown);

        // Create modal if not exists
        let modal = document.getElementById('poolDetailModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'poolDetailModal';
            modal.className = 'pool-detail-overlay';
            // Click outside to close
            modal.onclick = (e) => {
                if (e.target === modal) PoolDetailModal.close();
            };
            document.body.appendChild(modal);
        } else {
            modal.style.display = 'flex';
        }

        const protocolIcon = window.getProtocolIconUrl ? getProtocolIconUrl(pool.project) :
            `https://icons.llama.fi/${(pool.project || '').toLowerCase()}.png`;
        const chainIcon = window.getChainIconUrl ? getChainIconUrl(pool.chain) :
            `https://icons.llama.fi/chains/rsz_${(pool.chain || 'base').toLowerCase()}.jpg`;

        const isNiche = window.NicheProtocols?.isNiche(pool.project);
        const nicheCategory = isNiche ? NicheProtocols.getCategory(pool.project) : null;

        const epoch = this.getEpochCountdown();

        // ========================================
        // SECURITY ASSESSMENT (Safety Guard)
        // ========================================
        const securityAssessment = this.assessSecurity(pool);

        // Build security warnings banner if needed
        const securityBanner = securityAssessment.warnings.length > 0 ? `
            <div class="pd-security-banner ${securityAssessment.isCritical ? 'critical' : 'warning'}">
                <div class="pd-security-icon">${securityAssessment.isCritical ? '🚨' : '⚠️'}</div>
                <div class="pd-security-content">
                    <div class="pd-security-title">${securityAssessment.isCritical ? 'CRITICAL RISK DETECTED' : 'Security Warnings'}</div>
                    <ul class="pd-security-list">
                        ${securityAssessment.warnings.map(w => `<li>${w}</li>`).join('')}
                    </ul>
                </div>
            </div>
        ` : '';

        modal.innerHTML = `
            <div class="pool-detail-modal">
                <button class="modal-close-pro" onclick="PoolDetailModal.close()" title="Close (ESC)">${PoolIcons.close}</button>
                
                ${pool.isVerified ? this.renderVerdictBanner(pool) : ''}
                
                ${securityBanner}
                
                <!-- Header Section -->
                <div class="pd-header">
                    <div class="pd-header-main">
                        <div class="pd-logo">
                            <img src="${protocolIcon}" alt="${pool.project || 'Protocol'}" onerror="this.style.display='none'">
                        </div>
                        <div class="pd-title-block">
                            <h2 class="pd-protocol">${pool.project || pool.name?.split('/')[0]?.trim() || 'Unknown Protocol'}</h2>
                            <div class="pd-pair">
                                <span class="pd-symbol">${pool.symbol}</span>
                                <img src="${chainIcon}" alt="${pool.chain}" class="pd-chain-icon">
                                <span class="pd-chain">${pool.chain || 'Base'}</span>
                                ${isNiche ? `<span class="pd-niche-tag">🔮 ${nicheCategory}</span>` : ''}
                            </div>
                        </div>
                    </div>
                    <div class="pd-apy-block" ${pool.apy_optimal ? `title="Up to ${pool.apy_optimal.toFixed(0)}% for narrow tick ranges (Aerodrome-style). Displayed APY is realistic average."` : ''}>
                        <span class="pd-apy-value">${pool.apy > 0 ? pool.apy.toFixed(2) + '%' : (pool.trading_fee ? `~${(pool.trading_fee * 365).toFixed(0)}%*` : 'N/A')}</span>
                        <span class="pd-apy-label">${pool.apy > 0 ? (pool.apy_optimal ? 'APY ℹ️' : 'APY') : (pool.trading_fee ? 'Est. APR' : 'APY')}</span>
                    </div>
                </div>
                
                <!-- APY Source Explainer (Verified pools only) -->
                ${pool.isVerified ? this.renderApyExplainer(pool) : ''}
                
                <!-- Metrics Grid (tread.fi style) -->
                <div class="pd-metrics-row">
                    <div class="pd-metric-card">
                        <div class="pd-metric-icon">${PoolIcons.tvl}</div>
                        <div class="pd-metric-value">${formatTvl ? formatTvl(pool.tvl) : '$' + (pool.tvl / 1000000).toFixed(2) + 'M'}</div>
                        <div class="pd-metric-label">TVL</div>
                    </div>
                    <div class="pd-metric-card">
                        <div class="pd-metric-icon">${PoolIcons.risk}</div>
                        <span class="pd-risk-badge ${(pool.risk_level || 'medium').toLowerCase()}">${pool.risk_level || 'Medium'}</span>
                        <div class="pd-metric-label">Risk Level</div>
                    </div>
                    <div class="pd-metric-card ${pool.il_risk === 'yes' ? 'pd-il-high' : 'pd-il-none'}">
                        <div class="pd-metric-icon">${PoolIcons.shield}</div>
                        <div class="pd-metric-value ${pool.il_risk === 'yes' ? 'pd-danger' : 'pd-safe'}">
                            ${pool.il_risk === 'yes' ? '⚠️ High' : '🛡️ None'}
                        </div>
                        <div class="pd-metric-label">IL Risk</div>
                    </div>
                    <div class="pd-metric-card">
                        <div class="pd-metric-icon">${PoolIcons.coins}</div>
                        <div class="pd-metric-value">${pool.pool_type === 'stable' ? '🟢 Stable' : '🟠 Volatile'}</div>
                        <div class="pd-metric-label">Type</div>
                    </div>
                </div>
                
                <!-- Pool Characteristics Flags (Verified pools only) -->
                ${pool.isVerified ? this.renderVerifyFlags(pool) : ''}
                
                <!-- Why APY Can Change (expandable) -->
                ${this.renderApyChangeExplainer(pool)}
                
                <!-- Liquidity Stress Test -->
                ${this.renderLiquidityStress(pool)}
                
                <!-- Data Coverage Section (Verified pools only) -->
                ${pool.isVerified ? this.renderDataCoverage(pool) : ''}
                
                <!-- Confidence Level - How Certain Are We? -->
                ${pool.isVerified ? this.renderConfidenceLevel(pool) : ''}
                
                <!-- Decision Guidance - Is This Right For Me? -->
                ${pool.isVerified ? this.renderDecisionGuidance(pool) : ''}
                
                <!-- Exit Strategy - How Do I Withdraw? -->
                ${pool.isVerified ? this.renderExitStrategy(pool) : ''}
                
                <!-- Market Dynamics Section -->
                <div class="pd-section">
                    <div class="pd-section-header">
                        <h3>📊 Market Dynamics</h3>
                        ${this.isEpochProtocol(pool.project) ? `
                            <div class="pd-epoch-badge">⏳ Epoch ends in: ${epoch.display}</div>
                        ` : ''}
                    </div>
                    
                    ${pool.premium_insights?.length > 0 ? `
                        <div class="pd-insights-box">
                            ${pool.premium_insights.map(insight => `
                                <div class="pd-insight ${insight.type}">
                                    <span class="pd-insight-bar"></span>
                                    <span class="pd-insight-text">${insight.text}</span>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}

                    <div class="pd-data-grid">
                        ${(typeof pool.apy_base === 'number') ? `
                            <div class="pd-data-card">
                                <div class="pd-data-label">APY COMPOSITION</div>
                                <div class="pd-apy-breakdown">
                                    <div class="pd-apy-row">
                                        <span class="pd-dot base"></span>
                                        <span>Base: ${Number(pool.apy_base || 0).toFixed(2)}%</span>
                                    </div>
                                    <div class="pd-apy-row">
                                        <span class="pd-dot reward"></span>
                                        <span>Reward (${formatRewardTokenName(pool.reward_token)}): ${Number(pool.apy_reward || 0).toFixed(2)}%</span>
                                        ${pool.pool_type !== 'stable' ? '<span class="pd-warn-icon" title="Volatile token">⚠️</span>' : ''}
                                    </div>
                                </div>
                            </div>
                        ` : ''}
                        
                        <div class="pd-data-card">
                            <div class="pd-data-label">TVL STABILITY</div>
                            ${pool.tvl_change_7d !== undefined && pool.tvl_change_7d !== null && pool.tvl_change_7d !== 0 ? `
                                <div class="pd-trend-value ${pool.tvl_change_7d >= 0 ? 'up' : 'down'}">
                                    ${pool.tvl_change_7d >= 0 ? PoolIcons.trendUp : PoolIcons.trendDown}
                                    ${pool.tvl_change_7d >= 0 ? '+' : ''}${pool.tvl_change_7d.toFixed(1)}% 7d
                                </div>
                            ` : `
                                <div class="pd-trend-value unknown" title="No historical pool-level data available">
                                    <span style="opacity: 0.5">📊</span> Unknown
                                </div>
                            `}
                        </div>
                        
                        <div class="pd-data-card">
                            <div class="pd-data-label">24H VOLUME</div>
                            <div class="pd-data-value">${pool.volume_24h_formatted || 'N/A'}</div>
                        </div>
                        
                        ${pool.trading_fee ? `
                        <div class="pd-data-card">
                            <div class="pd-data-label">TRADING FEE</div>
                            <div class="pd-data-value">${pool.trading_fee}%</div>
                        </div>
                        ` : ''}
                    </div>

                    ${pool.risk_reasons?.length > 0 ? `
                        <div class="pd-risk-section">
                            <div class="pd-risk-title">Risk Factors:</div>
                            <ul class="pd-risk-list">
                                ${pool.risk_reasons.map(r => `<li>• ${r}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
                
                <!-- Trust Links -->
                <div class="pd-trust-row">
                    ${getExplorerUrl(pool) ? `<a href="${getExplorerUrl(pool)}" target="_blank">${PoolIcons.fileText} Contract</a>` : ''}
                    ${getProtocolWebsite(pool.project) ? `<a href="${getProtocolWebsite(pool.project)}" target="_blank">${PoolIcons.externalLink} Protocol</a>` : ''}
                    ${pool.pool_link ? `<a href="${pool.pool_link}" target="_blank">🏊 Pool</a>` : ''}
                </div>
                
                <!-- Action Buttons -->
                <div class="pd-actions">
                    ${this.renderDepositButton(pool, securityAssessment)}
                    <button class="pd-btn-secondary" onclick="PoolDetailModal.addToStrategy()">
                        + Add to Strategy
                    </button>
                    <button class="pd-btn-outline" onclick="YieldComparison?.addPool(PoolDetailModal.currentPool)">
                        📊 Compare
                    </button>
                </div>
            </div>
        `;

        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    },

    close() {
        const modal = document.getElementById('poolDetailModal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }
    },

    addToStrategy() {
        if (this.currentPool && window.addToStrategy) {
            addToStrategy(this.currentPool.id || this.currentPool.pool);
        }
        this.close();
    }
};

// ============================================
// CSS FOR POOL DETAIL MODAL - PROFESSIONAL MATRIX GOLD THEME
// ============================================
const detailStyles = document.createElement('style');
detailStyles.textContent = `
    /* Modal Overlay */
    .pool-detail-overlay {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.85);
        backdrop-filter: blur(12px);
        z-index: 2000;
        justify-content: center;
        align-items: center;
        padding: var(--space-4);
    }
    
    /* Modal Container */
    .pool-detail-modal {
        background: linear-gradient(180deg, rgba(20, 20, 20, 0.98), rgba(10, 10, 10, 0.98));
        border: 1px solid rgba(212, 168, 83, 0.3);
        border-radius: 14px;
        max-width: 580px;
        width: 100%;
        max-height: 90vh;
        overflow-y: auto;
        padding: 18px;
        position: relative;
        box-shadow: 0 0 60px rgba(212, 168, 83, 0.1), 0 0 1px rgba(212, 168, 83, 0.5);
    }
    
    /* Matrix Verdict Banner - Greek Gold Gaming Style */
    .matrix-verdict {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 12px 16px;
        border-radius: 10px;
        border: 1px solid;
        margin-bottom: 14px;
    }
    
    .matrix-score-ring {
        position: relative;
        width: 56px;
        height: 56px;
        flex-shrink: 0;
    }
    
    .matrix-score-ring svg {
        width: 100%;
        height: 100%;
        transform: rotate(-90deg);
        filter: drop-shadow(0 0 8px var(--glow-color));
    }
    
    .matrix-score-ring .ring-bg {
        fill: none;
        stroke: rgba(255, 255, 255, 0.08);
        stroke-width: 6;
    }
    
    .matrix-score-ring .ring-progress {
        fill: none;
        stroke-width: 6;
        stroke-linecap: round;
        transition: stroke-dashoffset 0.8s ease-out;
    }
    
    .matrix-score-ring .score-value {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 1.1rem;
        font-weight: 800;
        text-shadow: 0 0 10px currentColor;
    }
    
    .matrix-info {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    
    .matrix-verdict-label {
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    
    .matrix-desc {
        font-size: 0.7rem;
        color: var(--text-muted);
        font-weight: 400;
        margin-bottom: 4px;
    }
    
    .matrix-meta {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .matrix-source-badge {
        display: inline-block;
        font-size: 0.6rem;
        color: var(--text-muted);
        background: rgba(255, 255, 255, 0.05);
        padding: 2px 6px;
        border-radius: 4px;
    }
    
    .matrix-score-text {
        font-size: 0.6rem;
        color: var(--text-muted);
        opacity: 0.7;
    }
    
    /* Close Button */
    .modal-close-pro {
        position: absolute;
        top: 10px;
        right: 10px;
        width: 28px;
        height: 28px;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 6px;
        color: var(--text-muted);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s;
        z-index: 10;
    }
    
    .modal-close-pro:hover {
        background: rgba(212, 168, 83, 0.2);
        border-color: var(--gold);
        color: var(--gold);
    }
    
    .modal-close-pro svg {
        width: 18px;
        height: 18px;
    }
    
    /* Header Section */
    .pd-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 14px;
        margin-bottom: 14px;
        border-bottom: 1px solid rgba(212, 168, 83, 0.2);
    }
    
    .pd-header-main {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .pd-logo img {
        width: 44px;
        height: 44px;
        border-radius: 10px;
        border: 2px solid rgba(212, 168, 83, 0.3);
    }
    
    .pd-protocol {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--text);
        margin: 0 0 4px 0;
    }
    
    .pd-pair {
        display: flex;
        align-items: center;
        gap: 6px;
        color: var(--text-muted);
        font-size: 0.75rem;
    }
    
    .pd-symbol {
        font-weight: 500;
        color: var(--text-secondary);
    }
    
    .pd-chain-icon {
        width: 18px;
        height: 18px;
        border-radius: 50%;
    }
    
    .pd-niche-tag {
        background: rgba(139, 92, 246, 0.15);
        color: #A78BFA;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 600;
    }
    
    .pd-apy-block {
        text-align: right;
    }
    
    .pd-apy-value {
        display: block;
        font-size: 1.6rem;
        font-weight: 800;
        background: linear-gradient(135deg, #D4A853, #F5D78E);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.1;
    }
    
    .pd-apy-label {
        font-size: 0.65rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    
    /* Metrics Row - compact style */
    .pd-metrics-row {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
        margin-bottom: 14px;
    }
    
    .pd-metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 8px;
        padding: 10px 8px;
        text-align: center;
        transition: all 0.2s;
    }
    
    .pd-metric-card:hover {
        background: rgba(255, 255, 255, 0.05);
        border-color: rgba(212, 168, 83, 0.3);
    }
    
    .pd-metric-card.pd-il-high {
        border-color: rgba(239, 68, 68, 0.4);
        background: rgba(239, 68, 68, 0.05);
    }
    
    .pd-metric-card.pd-il-none {
        border-color: rgba(16, 185, 129, 0.4);
        background: rgba(16, 185, 129, 0.05);
    }
    
    .pd-metric-icon {
        display: flex;
        justify-content: center;
        margin-bottom: 4px;
        color: var(--gold);
        opacity: 0.6;
    }
    
    .pd-metric-icon svg {
        width: 18px;
        height: 18px;
    }
    
    .pd-metric-value {
        font-size: 0.85rem;
        font-weight: 700;
        color: var(--text);
        margin-bottom: 2px;
    }
    
    .pd-metric-value.pd-danger { color: #EF4444; }
    .pd-metric-value.pd-safe { color: #10B981; }
    
    .pd-metric-label {
        font-size: 0.6rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.2px;
    }
    
    .pd-risk-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 4px;
    }
    
    .pd-risk-badge.low { background: rgba(16, 185, 129, 0.15); color: #10B981; }
    .pd-risk-badge.medium { background: rgba(251, 191, 36, 0.15); color: #FBBF24; }
    .pd-risk-badge.high { background: rgba(239, 68, 68, 0.15); color: #EF4444; }
    .pd-risk-badge.critical { background: rgba(239, 68, 68, 0.25); color: #EF4444; animation: pulse-danger 1.5s infinite; }
    
    /* Security Banner - Safety Guard Warnings */
    .pd-security-banner {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 12px 14px;
        border-radius: 10px;
        margin-bottom: 12px;
        animation: fadeIn 0.3s ease;
    }
    
    .pd-security-banner.warning {
        background: rgba(251, 191, 36, 0.1);
        border: 1px solid rgba(251, 191, 36, 0.4);
    }
    
    .pd-security-banner.critical {
        background: rgba(239, 68, 68, 0.15);
        border: 2px solid rgba(239, 68, 68, 0.6);
        animation: pulse-danger 2s infinite;
    }
    
    .pd-security-icon {
        font-size: 1.5rem;
        flex-shrink: 0;
    }
    
    .pd-security-content {
        flex: 1;
    }
    
    .pd-security-title {
        font-weight: 700;
        font-size: 0.85rem;
        margin-bottom: 6px;
    }
    
    .pd-security-banner.warning .pd-security-title { color: #FBBF24; }
    .pd-security-banner.critical .pd-security-title { color: #EF4444; }
    
    .pd-security-list {
        list-style: none;
        padding: 0;
        margin: 0;
        font-size: 0.75rem;
        color: var(--text-secondary);
    }
    
    .pd-security-list li {
        margin-bottom: 4px;
    }
    
    /* Danger/Warning Button Variants */
    .pd-btn-danger {
        flex: 1;
        padding: 12px 16px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.85rem;
        text-align: center;
        cursor: not-allowed;
        background: rgba(239, 68, 68, 0.2);
        border: 2px solid rgba(239, 68, 68, 0.5);
        color: #EF4444;
        opacity: 0.8;
    }
    
    .pd-btn-warning {
        flex: 1;
        padding: 12px 16px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.85rem;
        text-decoration: none;
        text-align: center;
        display: block;
        background: linear-gradient(135deg, rgba(251, 191, 36, 0.3), rgba(212, 168, 83, 0.3));
        border: 1px solid rgba(251, 191, 36, 0.5);
        color: #FBBF24;
        transition: all 0.2s;
    }
    
    .pd-btn-warning:hover {
        background: linear-gradient(135deg, rgba(251, 191, 36, 0.4), rgba(212, 168, 83, 0.4));
        box-shadow: 0 0 15px rgba(251, 191, 36, 0.3);
    }
    
    @keyframes pulse-danger {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    
    /* Section Container */
    .pd-section {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 12px;
    }
    
    .pd-section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
    }
    
    .pd-section-header h3 {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--text);
        margin: 0;
    }
    
    .pd-epoch-badge {
        font-size: 0.75rem;
        color: #FBBF24;
        background: rgba(251, 191, 36, 0.12);
        padding: 4px 12px;
        border-radius: 20px;
        border: 1px solid rgba(251, 191, 36, 0.3);
    }
    
    /* Insights Box */
    .pd-insights-box {
        background: rgba(212, 168, 83, 0.05);
        border-left: 3px solid var(--gold);
        padding: 12px 16px;
        margin-bottom: 16px;
        border-radius: 0 8px 8px 0;
    }
    
    .pd-insight {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 6px 0;
        font-size: 0.85rem;
        color: var(--text-secondary);
    }
    
    .pd-insight-bar {
        width: 4px;
        height: 16px;
        background: var(--gold);
        border-radius: 2px;
    }
    
    .pd-insight.warning .pd-insight-bar { background: #EF4444; }
    .pd-insight.positive .pd-insight-bar { background: #10B981; }
    
    /* Data Grid */
    .pd-data-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
    }
    
    .pd-data-card {
        background: rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 14px;
    }
    
    .pd-data-label {
        font-size: 0.65rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }
    
    .pd-data-value {
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--text);
    }
    
    .pd-apy-breakdown {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    
    .pd-apy-row {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.85rem;
        color: var(--text-secondary);
    }
    
    .pd-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
    }
    
    .pd-dot.base { background: #10B981; }
    .pd-dot.reward { background: #FBBF24; }
    
    .pd-warn-icon {
        margin-left: 4px;
        cursor: help;
    }
    
    .pd-trend-value {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1.1rem;
        font-weight: 600;
    }
    
    .pd-trend-value.up { color: #10B981; }
    .pd-trend-value.down { color: #EF4444; }
    
    .pd-trend-value svg {
        width: 20px;
        height: 20px;
    }
    
    /* Risk Section */
    .pd-risk-section {
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .pd-risk-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--text-secondary);
        margin-bottom: 8px;
    }
    
    .pd-risk-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }
    
    .pd-risk-list li {
        font-size: 0.8rem;
        color: var(--text-muted);
        padding: 4px 0;
    }
    
    /* Trust Links Row */
    .pd-trust-row {
        display: flex;
        justify-content: center;
        gap: 16px;
        margin-bottom: 16px;
    }
    
    .pd-trust-row a {
        font-size: 0.75rem;
        color: var(--text-muted);
        text-decoration: none;
        padding: 8px 14px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
        transition: all 0.2s;
    }
    
    .pd-trust-row a:hover {
        color: var(--gold);
        border-color: rgba(212, 168, 83, 0.4);
        background: rgba(212, 168, 83, 0.1);
    }
    
    .pd-trust-row a svg {
        width: 14px;
        height: 14px;
    }
    
    /* Action Buttons */
    .pd-actions {
        display: flex;
        gap: 10px;
    }
    
    .pd-btn-primary {
        flex: 2;
        padding: 14px 20px;
        background: linear-gradient(135deg, #D4A853, #C49A47);
        border: none;
        border-radius: 10px;
        color: #000;
        font-weight: 700;
        font-size: 0.9rem;
        text-decoration: none;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .pd-btn-primary:hover {
        background: linear-gradient(135deg, #E5B95F, #D4A853);
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(212, 168, 83, 0.3);
    }
    
    .pd-btn-secondary,
    .pd-btn-outline {
        flex: 1;
        padding: 14px 16px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        color: var(--text-secondary);
        font-weight: 600;
        font-size: 0.85rem;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .pd-btn-secondary:hover,
    .pd-btn-outline:hover {
        border-color: var(--gold);
        color: var(--gold);
        background: rgba(212, 168, 83, 0.1);
    }
    
    /* Responsive */
    @media (max-width: 600px) {
        .pd-metrics-row {
            grid-template-columns: repeat(2, 1fr);
        }
        
        .pd-data-grid {
            grid-template-columns: 1fr;
        }
        
        .pd-actions {
            flex-direction: column;
        }
        
        .pd-header {
            flex-direction: column;
            text-align: center;
            gap: 16px;
        }
        
        .pd-header-main {
            flex-direction: column;
        }
    }
    
    /* ========================================= */
    /* APY EXPLAINER - Source and Confidence    */
    /* ========================================= */
    
    .pd-apy-explainer {
        background: rgba(212, 168, 83, 0.05);
        border: 1px solid rgba(212, 168, 83, 0.15);
        border-radius: 8px;
        padding: 10px 12px;
        margin-bottom: 12px;
    }
    
    .pd-apy-explainer.unavailable {
        background: rgba(239, 68, 68, 0.05);
        border-color: rgba(239, 68, 68, 0.2);
    }
    
    .pd-apy-source {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;
    }
    
    .pd-source-icon {
        font-size: 0.9rem;
    }
    
    .pd-source-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text);
    }
    
    .pd-confidence {
        font-size: 0.6rem;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 4px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .pd-confidence.high {
        background: rgba(16, 185, 129, 0.15);
        color: #10B981;
    }
    
    .pd-confidence.medium {
        background: rgba(251, 191, 36, 0.15);
        color: #FBBF24;
    }
    
    .pd-confidence.low {
        background: rgba(239, 68, 68, 0.15);
        color: #EF4444;
    }
    
    .pd-apy-explanation {
        font-size: 0.7rem;
        color: var(--text-muted);
        margin-bottom: 4px;
    }
    
    .pd-apy-reason {
        font-size: 0.7rem;
        color: #EF4444;
    }
    
    .pd-apy-caveats {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }
    
    .pd-caveat {
        font-size: 0.65rem;
        color: var(--text-muted);
        background: rgba(255, 255, 255, 0.03);
        padding: 2px 6px;
        border-radius: 4px;
    }
    
    /* ========================================= */
    /* WHY APY CAN CHANGE - Expandable Section  */
    /* ========================================= */
    
    .pd-apy-change-section {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        margin-bottom: 14px;
        overflow: hidden;
    }
    
    .pd-apy-change-section[open] {
        background: rgba(255, 255, 255, 0.03);
    }
    
    .pd-apy-change-header {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 10px 12px;
        cursor: pointer;
        font-size: 0.85rem;
        font-weight: 600;
        color: var(--text-secondary);
        list-style: none;
    }
    
    .pd-apy-change-header::-webkit-details-marker {
        display: none;
    }
    
    .pd-apy-change-header:hover {
        color: var(--gold);
    }
    
    .pd-change-icon {
        font-size: 1rem;
    }
    
    .pd-expand-arrow {
        margin-left: auto;
        font-size: 0.7rem;
        transition: transform 0.2s;
    }
    
    .pd-apy-change-section[open] .pd-expand-arrow {
        transform: rotate(90deg);
    }
    
    .pd-apy-change-content {
        padding: 0 12px 12px;
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    
    .pd-change-reason {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 8px;
        background: rgba(0, 0, 0, 0.2);
        border-radius: 6px;
    }
    
    .pd-reason-icon {
        font-size: 1rem;
        flex-shrink: 0;
    }
    
    .pd-reason-text {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    
    .pd-reason-text strong {
        font-size: 0.8rem;
        color: var(--text);
    }
    
    .pd-reason-text span {
        font-size: 0.7rem;
        color: var(--text-muted);
        line-height: 1.3;
    }
    
    /* ========================================= */
    /* LIQUIDITY STRESS TEST                    */
    /* ========================================= */
    
    .pd-liquidity-stress {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 14px;
    }
    
    .pd-stress-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 10px;
    }
    
    .pd-stress-icon {
        font-size: 1rem;
    }
    
    .pd-stress-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: var(--text);
    }
    
    .pd-stress-current {
        margin-left: auto;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .pd-stress-scenarios {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    
    .pd-stress-row {
        display: grid;
        grid-template-columns: 70px 1fr 100px;
        align-items: center;
        gap: 10px;
    }
    
    .pd-stress-drop {
        font-size: 0.75rem;
        color: var(--text-muted);
        font-weight: 500;
    }
    
    .pd-stress-bar-container {
        height: 6px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 3px;
        overflow: hidden;
    }
    
    .pd-stress-bar {
        height: 100%;
        border-radius: 3px;
        transition: width 0.3s ease;
    }
    
    .pd-stress-result {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 2px;
    }
    
    .pd-stress-tvl {
        font-size: 0.7rem;
        color: var(--text-muted);
    }
    
    .pd-stress-impact {
        font-size: 0.65rem;
        font-weight: 600;
    }
    
    .pd-stress-footer {
        margin-top: 8px;
        font-size: 0.65rem;
        color: var(--text-muted);
        text-align: center;
        font-style: italic;
    }
    
    /* ========================================= */
    /* DATA COVERAGE - Transparency Section     */
    /* ========================================= */
    
    .pd-data-coverage {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 14px;
    }
    
    .pd-coverage-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    
    .pd-coverage-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--text);
    }
    
    .pd-coverage-score {
        font-size: 0.7rem;
        color: var(--gold);
        font-weight: 600;
    }
    
    .pd-coverage-grid {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    
    .pd-coverage-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.7rem;
    }
    
    .pd-coverage-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
    }
    
    .pd-coverage-dot.available {
        background: #10B981;
        box-shadow: 0 0 6px rgba(16, 185, 129, 0.5);
    }
    
    .pd-coverage-dot.partial {
        background: #FBBF24;
        box-shadow: 0 0 6px rgba(251, 191, 36, 0.5);
    }
    
    .pd-coverage-dot.unavailable {
        background: rgba(255, 255, 255, 0.2);
    }
    
    .pd-coverage-label {
        color: var(--text);
        font-weight: 500;
        min-width: 100px;
    }
    
    .pd-coverage-detail {
        color: var(--text-muted);
        font-size: 0.65rem;
    }
    
    .pd-coverage-item.unavailable .pd-coverage-label,
    .pd-coverage-item.unavailable .pd-coverage-detail {
        opacity: 0.5;
    }
    
    /* ========================================= */
    /* VERIFY FLAGS - Pool Characteristics      */
    /* ========================================= */
    
    .pd-verify-flags {
        margin-bottom: 14px;
    }
    
    .pd-flags-title {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text);
        margin-bottom: 8px;
    }
    
    .pd-flags-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }
    
    .pd-flag {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 500;
        cursor: help;
        transition: all 0.2s;
    }
    
    .pd-flag.info {
        background: rgba(212, 168, 83, 0.1);
        border: 1px solid rgba(212, 168, 83, 0.2);
        color: var(--gold);
    }
    
    .pd-flag.warning {
        background: rgba(251, 191, 36, 0.1);
        border: 1px solid rgba(251, 191, 36, 0.3);
        color: #FBBF24;
    }
    
    .pd-flag:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }
    
    .pd-flag-icon {
        font-size: 0.8rem;
    }
    
    .pd-flag-text {
        white-space: nowrap;
    }
    
    /* =========================================
       CONFIDENCE LEVEL SECTION
       ========================================= */
    
    .pd-confidence-section {
        background: rgba(30, 30, 35, 0.6);
        border: 1px solid rgba(212, 168, 83, 0.15);
        border-radius: 12px;
        padding: 16px;
        margin-top: 16px;
    }
    
    .pd-confidence-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
    }
    
    .pd-confidence-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--gold);
    }
    
    .pd-confidence-badge {
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .pd-confidence-subtitle {
        font-size: 0.75rem;
        color: rgba(255, 255, 255, 0.5);
        margin-bottom: 12px;
    }
    
    .pd-confidence-factors {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    
    .pd-confidence-factor {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 12px;
        background: rgba(0, 0, 0, 0.2);
        border-radius: 8px;
    }
    
    .pd-conf-label {
        font-size: 0.8rem;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.7);
        width: 60px;
    }
    
    .pd-conf-status {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.7rem;
        font-weight: bold;
    }
    
    .pd-conf-status.high { background: #22C55E; color: white; }
    .pd-conf-status.medium { background: #F59E0B; color: white; }
    .pd-conf-status.low { background: #EF4444; color: white; }
    .pd-conf-status.unavailable { background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.5); }
    
    .pd-conf-text {
        font-size: 0.8rem;
        color: rgba(255, 255, 255, 0.9);
    }
    
    /* =========================================
       DECISION GUIDANCE SECTION
       ========================================= */
    
    .pd-decision-section {
        background: rgba(30, 30, 35, 0.6);
        border: 1px solid rgba(212, 168, 83, 0.15);
        border-radius: 12px;
        padding: 16px;
        margin-top: 16px;
    }
    
    .pd-decision-header {
        margin-bottom: 12px;
    }
    
    .pd-decision-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--gold);
    }
    
    .pd-decision-subtitle {
        font-size: 0.8rem;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.6);
        margin-bottom: 8px;
    }
    
    .pd-decision-warnings, .pd-decision-recs {
        margin-bottom: 12px;
    }
    
    .pd-decision-item {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 10px 12px;
        border-radius: 8px;
        margin-bottom: 6px;
    }
    
    .pd-decision-item.warning {
        background: rgba(239, 68, 68, 0.08);
        border-left: 3px solid #EF4444;
    }
    
    .pd-decision-item.positive {
        background: rgba(34, 197, 94, 0.08);
        border-left: 3px solid #22C55E;
    }
    
    .pd-decision-icon {
        font-size: 1rem;
        flex-shrink: 0;
    }
    
    .pd-decision-content {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    
    .pd-decision-text {
        font-size: 0.85rem;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.9);
    }
    
    .pd-decision-detail {
        font-size: 0.75rem;
        color: rgba(255, 255, 255, 0.5);
    }
    
    .pd-decision-goodfor {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 8px;
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .pd-goodfor-label {
        font-size: 0.8rem;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.6);
    }
    
    .pd-goodfor-tag {
        background: rgba(212, 168, 83, 0.15);
        color: var(--gold);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 500;
    }
    
    /* =========================================
       EXIT STRATEGY SECTION
       ========================================= */
    
    .pd-exit-section {
        background: rgba(30, 30, 35, 0.6);
        border: 1px solid rgba(212, 168, 83, 0.15);
        border-radius: 12px;
        padding: 16px;
        margin-top: 16px;
    }
    
    .pd-exit-header {
        margin-bottom: 12px;
    }
    
    .pd-exit-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--gold);
    }
    
    .pd-exit-items {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    
    .pd-exit-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 12px;
        background: rgba(0, 0, 0, 0.2);
        border-radius: 8px;
    }
    
    .pd-exit-icon {
        font-size: 1rem;
        flex-shrink: 0;
    }
    
    .pd-exit-label {
        font-size: 0.8rem;
        color: rgba(255, 255, 255, 0.6);
        flex-shrink: 0;
    }
    
    .pd-exit-value {
        font-size: 0.85rem;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.9);
    }
    
    .pd-exit-value.link {
        color: var(--gold);
        text-decoration: none;
    }
    
    .pd-exit-value.link:hover {
        text-decoration: underline;
    }
`;
document.head.appendChild(detailStyles);

// Export
window.PoolDetailModal = PoolDetailModal;
