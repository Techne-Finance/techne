/**
 * Telegram Alert Service
 * Premium feature for $10/month subscription
 * "Killer Feature" - Real-time opportunity alerts
 */

class TelegramAlertService {
    constructor() {
        this.apiEndpoint = '/api/telegram';
        this.isSubscribed = false;
        this.chatId = null;
        this.alertTypes = {
            newPool: { enabled: true, emoji: '🚀' },
            highApy: { enabled: true, minApy: 20, emoji: '💰' },
            tvlSpike: { enabled: true, minTvlChange: 50, emoji: '📈' },
            whaleActivity: { enabled: true, minAmount: 100000, emoji: '🐋' },
            apyDrop: { enabled: true, minDrop: 20, emoji: '📉' },
            newProtocol: { enabled: true, emoji: '✨' }
        };
        this.lastCheck = null;
    }

    init() {
        this.loadSettings();
        console.log('[TelegramAlerts] Service initialized');
    }

    loadSettings() {
        const saved = localStorage.getItem('telegramAlertSettings');
        if (saved) {
            const settings = JSON.parse(saved);
            this.isSubscribed = settings.isSubscribed;
            this.chatId = settings.chatId;
            Object.assign(this.alertTypes, settings.alertTypes);
        }
    }

    saveSettings() {
        localStorage.setItem('telegramAlertSettings', JSON.stringify({
            isSubscribed: this.isSubscribed,
            chatId: this.chatId,
            alertTypes: this.alertTypes
        }));
    }

    /**
     * Connect Telegram bot
     */
    async connect(chatId) {
        try {
            // Verify chat ID and send test message
            await this.sendAlert({
                type: 'test',
                title: '🤖 Techne Protocol Connected!',
                message: 'You will now receive real-time DeFi opportunity alerts.',
                chatId
            });

            this.chatId = chatId;
            this.isSubscribed = true;
            this.saveSettings();

            window.Notifications?.success('Telegram connected! Check your messages.');
            return true;
        } catch (error) {
            console.error('[TelegramAlerts] Connection failed:', error);
            window.Notifications?.error('Failed to connect Telegram');
            return false;
        }
    }

    disconnect() {
        this.isSubscribed = false;
        this.chatId = null;
        this.saveSettings();
        window.Notifications?.info('Telegram alerts disconnected');
    }

    /**
     * Send alert to Telegram
     */
    async sendAlert(alert) {
        if (!this.chatId && !alert.chatId) {
            throw new Error('No chat ID configured');
        }

        const message = this.formatMessage(alert);

        // In production, this would call your backend which sends to Telegram API
        // For now, log and show notification
        console.log('[TelegramAlerts] Would send:', message);

        // Mock success
        return { success: true, messageId: Date.now() };
    }

    /**
     * Format alert message for Telegram
     */
    formatMessage(alert) {
        const emoji = this.alertTypes[alert.type]?.emoji || '📢';

        switch (alert.type) {
            case 'newPool':
                return `${emoji} *New Pool Alert*\n\n` +
                    `*${alert.poolName}*\n` +
                    `Protocol: ${alert.protocol}\n` +
                    `APY: ${alert.apy}%\n` +
                    `TVL: $${this.formatNumber(alert.tvl)}\n\n` +
                    `🔗 [View on Techne](${alert.link})`;

            case 'highApy':
                return `${emoji} *High Yield Opportunity*\n\n` +
                    `*${alert.poolName}*\n` +
                    `APY: ${alert.apy}% 🔥\n` +
                    `TVL: $${this.formatNumber(alert.tvl)}\n` +
                    `Risk: ${alert.risk}\n\n` +
                    `⚡ Be the first - ${alert.earlyBirdNote || 'Low TVL = Higher Rewards'}`;

            case 'whaleActivity':
                return `${emoji} *Whale Alert*\n\n` +
                    `Large ${alert.action} detected:\n` +
                    `Amount: $${this.formatNumber(alert.amount)}\n` +
                    `Pool: ${alert.poolName}\n` +
                    `Wallet: ${alert.wallet?.slice(0, 10)}...`;

            case 'apyDrop':
                return `${emoji} *APY Change Alert*\n\n` +
                    `*${alert.poolName}*\n` +
                    `APY dropped: ${alert.oldApy}% → ${alert.newApy}%\n` +
                    `Consider rebalancing your position.`;

            case 'tvlSpike':
                return `${emoji} *TVL Spike Detected*\n\n` +
                    `*${alert.poolName}*\n` +
                    `TVL increased ${alert.tvlChange}%\n` +
                    `New TVL: $${this.formatNumber(alert.newTvl)}\n\n` +
                    `Growing confidence in this pool!`;

            default:
                return `${emoji} *${alert.title}*\n\n${alert.message}`;
        }
    }

    formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toFixed(0);
    }

    /**
     * Monitor pools for alert triggers
     */
    async checkForAlerts() {
        if (!this.isSubscribed) return;

        try {
            const pools = await window.DefiApi?.getTopPools(50, 'Base') || [];

            for (const pool of pools) {
                // New high APY pool
                if (this.alertTypes.highApy.enabled && pool.apy >= this.alertTypes.highApy.minApy) {
                    if (!this.isPoolAlerted(pool.pool)) {
                        await this.sendAlert({
                            type: 'highApy',
                            poolName: pool.symbol,
                            protocol: pool.project,
                            apy: pool.apy.toFixed(1),
                            tvl: pool.tvlUsd,
                            risk: pool.ilRisk
                        });
                        this.markPoolAlerted(pool.pool);
                    }
                }

                // APY drop
                if (this.alertTypes.apyDrop.enabled && pool.apyChange24h < -this.alertTypes.apyDrop.minDrop) {
                    await this.sendAlert({
                        type: 'apyDrop',
                        poolName: pool.symbol,
                        oldApy: (pool.apy - pool.apyChange24h).toFixed(1),
                        newApy: pool.apy.toFixed(1)
                    });
                }
            }

            this.lastCheck = new Date();
        } catch (error) {
            console.error('[TelegramAlerts] Check failed:', error);
        }
    }

    isPoolAlerted(poolId) {
        const alerted = JSON.parse(localStorage.getItem('alertedPools') || '[]');
        return alerted.includes(poolId);
    }

    markPoolAlerted(poolId) {
        const alerted = JSON.parse(localStorage.getItem('alertedPools') || '[]');
        alerted.push(poolId);
        // Keep only last 100
        if (alerted.length > 100) alerted.shift();
        localStorage.setItem('alertedPools', JSON.stringify(alerted));
    }

    /**
     * Start monitoring loop
     */
    startMonitoring(intervalMinutes = 5) {
        this.checkForAlerts();
        setInterval(() => this.checkForAlerts(), intervalMinutes * 60 * 1000);
        console.log(`[TelegramAlerts] Monitoring every ${intervalMinutes} minutes`);
    }

    /**
     * Generate subscription modal HTML
     */
    getSubscriptionModalHTML() {
        return `
            <div class="telegram-subscription-modal">
                <h2>🤖 Telegram Alerts</h2>
                <p class="modal-subtitle">Get real-time DeFi opportunities sent to Telegram</p>
                
                <div class="subscription-tiers">
                    <div class="tier free">
                        <h3>Free</h3>
                        <div class="price">$0</div>
                        <ul>
                            <li>✓ Daily digest</li>
                            <li>✓ Top 3 opportunities</li>
                            <li>✗ Real-time alerts</li>
                            <li>✗ Whale activity</li>
                        </ul>
                    </div>
                    
                    <div class="tier pro active">
                        <div class="popular-badge">Most Popular</div>
                        <h3>Pro</h3>
                        <div class="price">$10<span>/month</span></div>
                        <ul>
                            <li>✓ Real-time alerts</li>
                            <li>✓ New pool notifications</li>
                            <li>✓ High APY opportunities</li>
                            <li>✓ Whale activity alerts</li>
                            <li>✓ APY drop warnings</li>
                            <li>✓ Custom thresholds</li>
                        </ul>
                        <button class="btn-subscribe" onclick="TelegramAlerts.showConnectFlow()">
                            Subscribe Now
                        </button>
                    </div>
                </div>
                
                <div class="connect-section" id="telegramConnectSection" style="display: none;">
                    <h4>Connect Your Telegram</h4>
                    <ol>
                        <li>Open Telegram and search for <code>@TechneProtocolBot</code></li>
                        <li>Send <code>/start</code> to the bot</li>
                        <li>Copy your Chat ID and paste below</li>
                    </ol>
                    <div class="input-group">
                        <input type="text" id="telegramChatId" placeholder="Your Telegram Chat ID">
                        <button onclick="TelegramAlerts.connect(document.getElementById('telegramChatId').value)">
                            Connect
                        </button>
                    </div>
                </div>
                
                <div class="alert-settings" ${this.isSubscribed ? '' : 'style="display:none"'}>
                    <h4>Alert Settings</h4>
                    ${Object.entries(this.alertTypes).map(([key, config]) => `
                        <label class="alert-toggle">
                            <input type="checkbox" ${config.enabled ? 'checked' : ''} 
                                   onchange="TelegramAlerts.toggleAlert('${key}', this.checked)">
                            <span>${this.getAlertLabel(key)}</span>
                        </label>
                    `).join('')}
                </div>
            </div>
        `;
    }

    getAlertLabel(key) {
        const labels = {
            newPool: '🚀 New Pool Alerts',
            highApy: '💰 High APY Opportunities (>20%)',
            tvlSpike: '📈 TVL Spike Detection',
            whaleActivity: '🐋 Whale Activity Alerts',
            apyDrop: '📉 APY Drop Warnings',
            newProtocol: '✨ New Protocol Launches'
        };
        return labels[key] || key;
    }

    showConnectFlow() {
        document.getElementById('telegramConnectSection').style.display = 'block';
    }

    toggleAlert(key, enabled) {
        this.alertTypes[key].enabled = enabled;
        this.saveSettings();
    }
}

// Initialize
const TelegramAlerts = new TelegramAlertService();
document.addEventListener('DOMContentLoaded', () => {
    TelegramAlerts.init();
    // Start monitoring if subscribed
    if (TelegramAlerts.isSubscribed) {
        TelegramAlerts.startMonitoring();
    }
});

// Export
window.TelegramAlerts = TelegramAlerts;
