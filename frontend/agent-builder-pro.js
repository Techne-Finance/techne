/**
 * Agent Builder Pro Mode - Helper Class
 * Reads values from Pro Mode DOM controls (leverage, ALM, exit targets)
 */

class AgentBuilderPro {
    constructor() {
        this.warnings = [];
    }

    /**
     * Check if Pro Mode is currently active
     */
    isProModeActive() {
        return document.body.classList.contains('builder-pro');
    }

    /**
     * Get the current pool type (single/dual/all)
     */
    getPoolType() {
        const activeBtn = document.querySelector('.pool-type-btn-build.active');
        return activeBtn?.dataset.poolType || 'single';
    }

    /**
     * Read all Pro Mode configuration values from DOM
     */
    getProConfig() {
        if (!this.isProModeActive()) {
            return null; // Not in Pro Mode
        }

        const config = {
            // Leverage (Smart Loop Engine)
            leverage: this.getLeverageLevel(),

            // Liquidity Strategy (for dual-sided)
            liquidityStrategy: this.getLiquidityStrategy(),
            rebalanceThreshold: this.getRebalanceThreshold(),

            // Precision Duration
            duration: this.getDuration(),

            // Exit Targets
            takeProfitEnabled: this.isTakeProfitEnabled(),
            takeProfitAmount: this.getTakeProfitAmount(),  // Legacy $ value
            takeProfitPercent: this.getTakeProfitPercent(),  // % profit target
            takeProfitUsd: this.getTakeProfitUsd(),  // $ profit target
            stopLossEnabled: this.isStopLossEnabled(),
            stopLossPercent: this.getStopLossPercent(),
            apyTargetEnabled: this.isApyTargetEnabled(),
            apyTargetValue: this.getApyTargetValue(),

            // Safety & Gas
            volatilityGuard: this.isVolatilityGuardEnabled(),
            mevProtection: this.isMevProtectionEnabled(),
            gasStrategy: this.getGasStrategy(),

            // Custom Instructions
            customInstructions: this.getCustomInstructions()
        };

        return config;
    }

    // ==========================================
    // LEVERAGE (Smart Loop Engine)
    // ==========================================

    getLeverageLevel() {
        const slider = document.getElementById('leverageSlider');
        return slider ? slider.value / 100 : 1.0;
    }

    // ==========================================
    // LIQUIDITY STRATEGY (Dual-Sided)
    // ==========================================

    getLiquidityStrategy() {
        const activeBtn = document.querySelector('.liq-btn.active');
        return activeBtn?.dataset.strategy || 'passive';
    }

    getRebalanceThreshold() {
        const input = document.getElementById('rebalancePercent');
        return input ? parseInt(input.value) || 5 : 5;
    }

    // ==========================================
    // PRECISION DURATION
    // ==========================================

    getDuration() {
        const valueInput = document.getElementById('durationValue');
        const unitSelect = document.getElementById('durationUnit');

        const value = valueInput ? parseInt(valueInput.value) || 24 : 24;
        const unit = unitSelect ? unitSelect.value : 'hours';

        // Convert to hours for backend
        const multipliers = {
            hours: 1,
            days: 24,
            weeks: 168,
            months: 720
        };

        return {
            value: value,
            unit: unit,
            totalHours: value * (multipliers[unit] || 1)
        };
    }

    // ==========================================
    // EXIT TARGETS
    // ==========================================

    isTakeProfitEnabled() {
        const check = document.getElementById('takeProfitEnabled');
        return check?.checked || false;
    }

    getTakeProfitAmount() {
        // For backwards compatibility - returns USD value
        const input = document.getElementById('takeProfitAmount');
        return input ? parseFloat(input.value) || 500 : 500;
    }

    getTakeProfitPercent() {
        const input = document.getElementById('takeProfitPercent');
        return input ? parseFloat(input.value) || 0 : 0;
    }

    getTakeProfitUsd() {
        const input = document.getElementById('takeProfitUsd');
        return input ? parseFloat(input.value) || 0 : 0;
    }

    isStopLossEnabled() {
        const check = document.getElementById('stopLossEnabled');
        return check?.checked || true;
    }

    getStopLossPercent() {
        const input = document.getElementById('stopLossPercent');
        return input ? parseInt(input.value) || 15 : 15;
    }

    isApyTargetEnabled() {
        const check = document.getElementById('apyTargetEnabled');
        return check?.checked || false;
    }

    getApyTargetValue() {
        const input = document.getElementById('apyTargetValue');
        return input ? parseInt(input.value) || 5 : 5;
    }

    // ==========================================
    // SAFETY & GAS
    // ==========================================

    isVolatilityGuardEnabled() {
        const check = document.getElementById('volatilityGuard');
        return check?.checked ?? true;
    }

    isMevProtectionEnabled() {
        const check = document.getElementById('mevProtection');
        return check?.checked ?? true;
    }

    getGasStrategy() {
        const select = document.getElementById('gasStrategy');
        return select?.value || 'smart';
    }

    // ==========================================
    // CUSTOM INSTRUCTIONS
    // ==========================================

    getCustomInstructions() {
        const textarea = document.getElementById('customInstructions');
        return textarea?.value?.trim() || '';
    }

    // ==========================================
    // 🔥 DEGEN MODE SETTINGS
    // ==========================================

    /**
     * Get all Degen mode configuration from DOM
     * @returns {Object|null} Degen config or null if no degen settings enabled
     */
    getDegenConfig() {
        const config = {
            // Flash Leverage Engine
            flashLoanEnabled: document.getElementById('flashLoanLoops')?.checked || false,
            maxLeverage: this.getSelectedLeverage(),
            deleverageThreshold: parseInt(document.getElementById('deleverageThreshold')?.value) || 15,

            // Volatility Hunter
            chaseVolatility: document.getElementById('chaseVolatility')?.checked || false,
            minVolatilityThreshold: parseInt(document.getElementById('minVolatility')?.value) || 25,
            ilFarmingMode: document.getElementById('ilFarmingMode')?.checked || false,

            // Auto-Snipe New Pools
            snipeNewPools: document.getElementById('snipeNewPools')?.checked || false,
            snipeMinApy: parseInt(document.getElementById('snipeMinApy')?.value) || 100,
            snipeMaxPosition: parseInt(document.getElementById('snipeMaxPosition')?.value) || 500,
            snipeExitHours: parseInt(document.getElementById('snipeExitTime')?.value) || 24,

            // Delta Neutral
            autoHedge: document.getElementById('autoHedge')?.checked || false,
            hedgeProtocol: document.getElementById('hedgeProtocol')?.value || 'synthetix',
            deltaThreshold: parseInt(document.getElementById('deltaThreshold')?.value) || 5,
            fundingFarming: document.getElementById('fundingFarming')?.checked ?? true
        };

        // Check if any degen mode is active
        const hasDegenEnabled = config.flashLoanEnabled ||
            config.chaseVolatility ||
            config.snipeNewPools ||
            config.autoHedge;

        if (hasDegenEnabled) {
            console.log('[AgentBuilderPro] Degen modes enabled:', {
                flash: config.flashLoanEnabled ? `${config.maxLeverage}x` : false,
                volatility: config.chaseVolatility ? `${config.minVolatilityThreshold}%` : false,
                snipe: config.snipeNewPools ? `${config.snipeMinApy}% APY` : false,
                hedge: config.autoHedge ? config.hedgeProtocol : false
            });
        }

        return hasDegenEnabled ? config : null;
    }

    /**
     * Get selected leverage from leverage buttons
     */
    getSelectedLeverage() {
        const activeBtn = document.querySelector('.lev-btn.active');
        return activeBtn ? parseInt(activeBtn.dataset.lev) || 3 : 3;
    }

    /**
     * Send degen config to backend
     */
    async deployDegenConfig(userAddress) {
        const config = this.getDegenConfig();
        if (!config) return { success: true, message: 'No degen modes enabled' };

        try {
            const response = await fetch('/api/agent/degen/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_address: userAddress,
                    flash_loan_enabled: config.flashLoanEnabled,
                    max_leverage: config.maxLeverage,
                    deleverage_threshold: config.deleverageThreshold,
                    chase_volatility: config.chaseVolatility,
                    min_volatility_threshold: config.minVolatilityThreshold,
                    il_farming_mode: config.ilFarmingMode,
                    snipe_new_pools: config.snipeNewPools,
                    snipe_min_apy: config.snipeMinApy,
                    snipe_max_position: config.snipeMaxPosition,
                    snipe_exit_hours: config.snipeExitHours,
                    auto_hedge: config.autoHedge,
                    hedge_protocol: config.hedgeProtocol,
                    delta_threshold: config.deltaThreshold,
                    funding_farming: config.fundingFarming
                })
            });

            const result = await response.json();
            console.log('[AgentBuilderPro] Degen config deployed:', result);
            return result;
        } catch (error) {
            console.error('[AgentBuilderPro] Failed to deploy degen config:', error);
            return { success: false, error: error.message };
        }
    }


    // ==========================================
    // VALIDATION
    // ==========================================

    /**
     * Validate Pro Mode configuration
     * @returns {Object} { valid: boolean, warnings: string[], errors: string[] }
     */
    validate() {
        const result = {
            valid: true,
            warnings: [],
            errors: []
        };

        const config = this.getProConfig();
        if (!config) return result; // Not in Pro Mode, no validation needed

        const poolType = this.getPoolType();

        // Leverage validation for single-sided
        if (poolType === 'single') {
            if (config.leverage > 2.5) {
                result.warnings.push('⚠️ High leverage (>2.5x) significantly increases liquidation risk');
            }
            if (config.leverage > 3.0) {
                result.errors.push('❌ Maximum leverage is 3.0x');
                result.valid = false;
            }
        }

        // Dual-sided validation
        if (poolType === 'dual') {
            if (config.liquidityStrategy === 'jit') {
                result.warnings.push('⚡ JIT Liquidity requires constant monitoring and fast execution');
            }
            if (config.rebalanceThreshold < 2) {
                result.warnings.push('⚠️ Low rebalance threshold may result in high gas costs');
            }
        }

        // Duration validation
        if (config.duration.totalHours < 1) {
            result.errors.push('❌ Minimum duration is 1 hour');
            result.valid = false;
        }

        // Stop Loss validation
        if (config.stopLossEnabled && config.stopLossPercent > 50) {
            result.warnings.push('⚠️ Stop loss above 50% may not provide effective protection');
        }

        // Take Profit validation
        if (config.takeProfitEnabled && config.takeProfitAmount < 10) {
            result.warnings.push('⚠️ Take profit below $10 may trigger frequently');
        }

        return result;
    }

    /**
     * Calculate estimated APY based on leverage
     * @param {number} baseApy - Base APY percentage
     * @returns {number} Leveraged APY
     */
    calculateLeveragedApy(baseApy) {
        const leverage = this.getLeverageLevel();
        // Simple model: APY scales with leverage (minus borrow costs ~2%)
        const borrowCost = (leverage - 1) * 2; // Approximate borrow cost
        return baseApy * leverage - borrowCost;
    }

    /**
     * Calculate liquidation threshold
     * @returns {string} Human-readable liquidation info
     */
    calculateLiquidationInfo() {
        const leverage = this.getLeverageLevel();
        if (leverage <= 1) return 'No liquidation risk';

        // LTV threshold typically around 80%
        const ltv = 0.8;
        const liquidationDrop = ((1 - (1 / (leverage * ltv))) * 100).toFixed(1);

        return `Liquidation at -${liquidationDrop}% price drop`;
    }

    /**
     * Get a summary of Pro Mode configuration for display
     */
    getSummary() {
        const config = this.getProConfig();
        if (!config) return 'Basic Mode';

        const poolType = this.getPoolType();
        const lines = [];

        if (poolType === 'single') {
            lines.push(`Leverage: ${config.leverage.toFixed(1)}x`);
        } else if (poolType === 'dual') {
            lines.push(`Strategy: ${config.liquidityStrategy}`);
            if (config.liquidityStrategy === 'active') {
                lines.push(`Rebalance at ${config.rebalanceThreshold}%`);
            }
        }

        lines.push(`Duration: ${config.duration.value} ${config.duration.unit}`);

        if (config.stopLossEnabled) {
            lines.push(`Stop Loss: ${config.stopLossPercent}%`);
        }
        if (config.takeProfitEnabled) {
            lines.push(`Take Profit: $${config.takeProfitAmount}`);
        }

        return lines.join('\n');
    }
}

// Export
window.AgentBuilderPro = new AgentBuilderPro();
