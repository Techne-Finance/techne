/**
 * AI Strategy System
 * Backtesting, recommendations, scheduled actions, alerts & triggers
 */

class AIStrategySystem {
    constructor() {
        this.scheduledActions = [];
        this.alerts = [];
        this.backtestHistory = [];
    }

    init() {
        this.startScheduler();
        this.startAlertMonitor();
        console.log('[AIStrategy] System initialized');
    }

    // =============================================
    // BACKTESTING
    // =============================================

    async backtest(config, days = 30) {
        const startDate = new Date();
        startDate.setDate(startDate.getDate() - days);

        window.Notifications?.info('Running backtest simulation...');

        try {
            // Get matching pools based on config
            const pools = await window.DefiApi?.getMatchingPools(config) || [];

            if (pools.length === 0) {
                return { error: 'No matching pools found' };
            }

            // Simulate portfolio over time
            const results = this.simulatePortfolio(pools, config, days);

            this.backtestHistory.push({
                config,
                results,
                timestamp: new Date()
            });

            window.Notifications?.success(`Backtest complete: ${results.totalReturn.toFixed(1)}% return over ${days} days`);

            return results;
        } catch (error) {
            console.error('[AIStrategy] Backtest failed:', error);
            return { error: error.message };
        }
    }

    simulatePortfolio(pools, config, days) {
        const initialValue = 1000;
        let currentValue = initialValue;
        const dailyReturns = [];
        const allocations = [];

        // Calculate allocation per pool
        const poolValue = initialValue / Math.min(pools.length, config.vaultCount || 5);

        // Simulate daily returns
        for (let day = 0; day < days; day++) {
            let dailyReturn = 0;

            pools.slice(0, config.vaultCount || 5).forEach((pool, i) => {
                const dailyApy = (pool.apy || 10) / 365;
                // Add some variance
                const variance = (Math.random() - 0.5) * 0.5;
                const dayReturn = (dailyApy + variance) / 100;
                dailyReturn += (poolValue / initialValue) * dayReturn;
            });

            currentValue *= (1 + dailyReturn);
            dailyReturns.push({
                day,
                value: currentValue,
                dailyReturn: dailyReturn * 100
            });
        }

        // Calculate metrics
        const totalReturn = ((currentValue - initialValue) / initialValue) * 100;
        const avgDailyReturn = dailyReturns.reduce((sum, d) => sum + d.dailyReturn, 0) / days;
        const annualizedReturn = totalReturn * (365 / days);

        // Calculate Sharpe ratio (simplified)
        const returns = dailyReturns.map(d => d.dailyReturn);
        const stdDev = this.standardDeviation(returns);
        const sharpeRatio = (avgDailyReturn * Math.sqrt(365)) / (stdDev || 1);

        // Max drawdown
        let peak = initialValue;
        let maxDrawdown = 0;
        dailyReturns.forEach(d => {
            if (d.value > peak) peak = d.value;
            const drawdown = (peak - d.value) / peak;
            if (drawdown > maxDrawdown) maxDrawdown = drawdown;
        });

        return {
            initialValue,
            finalValue: currentValue,
            totalReturn,
            annualizedReturn,
            avgDailyReturn,
            sharpeRatio,
            maxDrawdown: maxDrawdown * 100,
            dailyReturns,
            poolsUsed: pools.slice(0, config.vaultCount || 5).map(p => ({
                name: p.symbol || p.pool,
                apy: p.apy,
                protocol: p.project
            }))
        };
    }

    standardDeviation(values) {
        const n = values.length;
        if (n === 0) return 0;
        const mean = values.reduce((a, b) => a + b) / n;
        return Math.sqrt(values.map(x => Math.pow(x - mean, 2)).reduce((a, b) => a + b) / n);
    }

    // =============================================
    // AI RECOMMENDATIONS
    // =============================================

    async getRecommendations(currentPortfolio = []) {
        try {
            const pools = await window.DefiApi?.getTopPools(50, 'Base') || [];
            const stablePools = await window.DefiApi?.getStablePools('Base') || [];

            const recommendations = [];

            // High yield opportunities
            const highYield = pools.filter(p => p.apy > 20 && p.tvlUsd > 100000).slice(0, 3);
            if (highYield.length > 0) {
                recommendations.push({
                    type: 'opportunity',
                    title: 'High Yield Opportunities',
                    description: `${highYield.length} pools with >20% APY and good TVL`,
                    pools: highYield.map(p => ({
                        name: p.symbol,
                        apy: p.apy.toFixed(1) + '%',
                        protocol: p.project
                    })),
                    priority: 'high'
                });
            }

            // Safe stable yields
            const safeStables = stablePools.filter(p => p.apy > 5 && p.apy < 15).slice(0, 3);
            if (safeStables.length > 0) {
                recommendations.push({
                    type: 'safety',
                    title: 'Safe Stablecoin Yields',
                    description: 'Low-risk stablecoin opportunities',
                    pools: safeStables.map(p => ({
                        name: p.symbol,
                        apy: p.apy.toFixed(1) + '%',
                        protocol: p.project
                    })),
                    priority: 'medium'
                });
            }

            // Diversification recommendation
            if (currentPortfolio.length < 3) {
                recommendations.push({
                    type: 'diversification',
                    title: 'Diversify Your Portfolio',
                    description: 'Consider spreading across 3-5 vaults to reduce risk',
                    priority: 'medium'
                });
            }

            // APY drop alerts
            pools.filter(p => p.apyChange24h < -20).slice(0, 2).forEach(p => {
                recommendations.push({
                    type: 'warning',
                    title: 'APY Dropped',
                    description: `${p.symbol} dropped ${Math.abs(p.apyChange24h).toFixed(0)}% in 24h`,
                    priority: 'high'
                });
            });

            return recommendations;
        } catch (error) {
            console.error('[AIStrategy] Failed to get recommendations:', error);
            return [];
        }
    }

    // =============================================
    // SCHEDULED ACTIONS
    // =============================================

    scheduleAction(action, interval, options = {}) {
        const id = Date.now();
        const scheduled = {
            id,
            action,
            interval, // in hours
            options,
            lastRun: null,
            nextRun: new Date(Date.now() + interval * 3600000),
            enabled: true
        };

        this.scheduledActions.push(scheduled);
        window.Notifications?.success(`Scheduled: ${action} every ${interval}h`);

        return id;
    }

    cancelScheduledAction(id) {
        this.scheduledActions = this.scheduledActions.filter(a => a.id !== id);
    }

    startScheduler() {
        setInterval(() => this.checkScheduledActions(), 60000); // Check every minute
    }

    async checkScheduledActions() {
        const now = new Date();

        for (const action of this.scheduledActions) {
            if (!action.enabled) continue;
            if (action.nextRun > now) continue;

            // Execute action
            await this.executeScheduledAction(action);

            // Update next run
            action.lastRun = now;
            action.nextRun = new Date(now.getTime() + action.interval * 3600000);
        }
    }

    async executeScheduledAction(action) {
        console.log(`[AIStrategy] Executing scheduled: ${action.action}`);

        switch (action.action) {
            case 'harvest':
                window.Notifications?.agentHarvest?.('All Vaults', 0);
                break;
            case 'rebalance':
                window.Notifications?.agentRebalance?.(0);
                break;
            case 'compound':
                window.Notifications?.info('Auto-compounding rewards...');
                break;
            case 'check-apy':
                await this.checkApyChanges();
                break;
        }
    }

    // =============================================
    // ALERTS & TRIGGERS
    // =============================================

    addAlert(name, condition, action, options = {}) {
        const id = Date.now();
        const alert = {
            id,
            name,
            condition, // Function that returns true when triggered
            action,    // Function to execute when triggered
            options,
            triggered: false,
            createdAt: new Date()
        };

        this.alerts.push(alert);
        window.Notifications?.success(`Alert created: ${name}`);

        return id;
    }

    removeAlert(id) {
        this.alerts = this.alerts.filter(a => a.id !== id);
    }

    startAlertMonitor() {
        setInterval(() => this.checkAlerts(), 30000); // Check every 30 seconds
    }

    async checkAlerts() {
        for (const alert of this.alerts) {
            if (alert.triggered && !alert.options.repeatable) continue;

            try {
                const shouldTrigger = await alert.condition();
                if (shouldTrigger) {
                    alert.triggered = true;
                    alert.lastTriggered = new Date();

                    window.Notifications?.warning(`Alert triggered: ${alert.name}`);

                    if (typeof alert.action === 'function') {
                        await alert.action();
                    }
                }
            } catch (error) {
                console.error(`[AIStrategy] Alert check failed: ${alert.name}`, error);
            }
        }
    }

    async checkApyChanges() {
        // Check if any monitored pools had significant APY changes
        const pools = await window.DefiApi?.getTopPools(20, 'Base') || [];

        pools.forEach(pool => {
            if (pool.apyChange24h && Math.abs(pool.apyChange24h) > 20) {
                window.Notifications?.apyAlert?.(
                    pool.symbol,
                    pool.apy + pool.apyChange24h,
                    pool.apy
                );
            }
        });
    }

    // Preset alerts
    addApyDropAlert(poolSymbol, threshold = -20) {
        return this.addAlert(
            `APY Drop: ${poolSymbol}`,
            async () => {
                const pools = await window.DefiApi?.searchPools(poolSymbol, 'Base') || [];
                return pools.some(p => p.apyChange24h < threshold);
            },
            () => window.Notifications?.warning(`${poolSymbol} APY dropped significantly`),
            { repeatable: false }
        );
    }

    addValueDropAlert(threshold = -10) {
        return this.addAlert(
            `Portfolio value drop > ${Math.abs(threshold)}%`,
            () => {
                const change = parseFloat(document.getElementById('portfolioChange')?.textContent) || 0;
                return change < threshold;
            },
            () => window.Notifications?.emergencyExit?.('Portfolio value dropped below threshold'),
            { repeatable: false }
        );
    }

    // UI Helper: Get summary for display
    getSummary() {
        return {
            scheduledActions: this.scheduledActions.length,
            activeAlerts: this.alerts.filter(a => !a.triggered).length,
            backtestsRun: this.backtestHistory.length
        };
    }
}

// Initialize
const AIStrategy = new AIStrategySystem();
document.addEventListener('DOMContentLoaded', () => AIStrategy.init());

// Export
window.AIStrategy = AIStrategy;
