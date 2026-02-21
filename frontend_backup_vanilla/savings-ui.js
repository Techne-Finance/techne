/**
 * Savings Account UI - Simplified "Smart Savings" Interface
 * MVP: Focus on USDT single-sided pools only
 */

const SavingsUI = {

    /**
     * Initialize the savings interface
     */
    async init() {
        await this.loadRecommendedPools();
        await this.updateGasPrice();
        this.setupEventListeners();

        // Update gas price every 30 seconds
        setInterval(() => this.updateGasPrice(), 30000);
    },

    /**
     * Load recommended USDT pools
     */
    async loadRecommendedPools() {
        const container = document.getElementById('savings-pools');
        if (!container) return;

        container.innerHTML = '<div class="loading">Loading safe USDT pools...</div>';

        try {
            const data = await EngineerClient.getRecommendedVaults();

            if (!data.vaults || data.vaults.length === 0) {
                container.innerHTML = '<div class="empty-state">No pools available</div>';
                return;
            }

            container.innerHTML = data.vaults.map(vault => this.createPoolCard(vault)).join('');

        } catch (error) {
            console.error('Load pools error:', error);
            container.innerHTML = '<div class="error-state">Failed to load pools</div>';
        }
    },

    /**
     * Create a simplified pool card
     */
    createPoolCard(vault) {
        const riskColors = {
            'safe': '#10b981',
            'low': '#3b82f6',
            'moderate': '#f59e0b'
        };

        const riskColor = riskColors[vault.risk_level] || '#6b7280';

        return `
            <div class="savings-pool-card ${vault.recommended ? 'recommended' : ''}" 
                 data-vault="${vault.address}">
                
                ${vault.recommended ? '<div class="recommended-badge">⭐ Recommended</div>' : ''}
                
                <div class="pool-header">
                    <h4>${vault.name}</h4>
                    <span class="protocol-badge">${vault.protocol}</span>
                </div>
                
                <div class="pool-stats-grid">
                    <div class="stat">
                        <div class="stat-value apy">${vault.current_apy.toFixed(2)}%</div>
                        <div class="stat-label">APY</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">${this.formatTVL(vault.tvl_usd)}</div>
                        <div class="stat-label">TVL</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" style="color: ${riskColor}">${vault.risk_level}</div>
                        <div class="stat-label">Risk</div>
                    </div>
                </div>
                
                <div class="pool-utilization">
                    <div class="utilization-label">Utilization: ${(vault.utilization_rate * 100).toFixed(1)}%</div>
                    <div class="utilization-bar">
                        <div class="utilization-fill" style="width: ${vault.utilization_rate * 100}%"></div>
                    </div>
                </div>
                
                <div class="pool-actions">
                    <input type="number" 
                           class="deposit-input" 
                           placeholder="Amount USDT" 
                           min="1" 
                           step="0.01"
                           data-vault="${vault.address}">
                    <button class="btn-deposit-savings" 
                            onclick="SavingsUI.handleDeposit('${vault.address}', '${vault.name}')">
                        Deposit USDT
                    </button>
                </div>
            </div>
        `;
    },

    /**
     * Handle deposit button click
     */
    async handleDeposit(vaultAddress, vaultName) {
        // Check wallet connection
        if (!window.connectedWallet) {
            Toast?.show('Please connect wallet first', 'warning');
            return;
        }

        // Get amount from input
        const input = document.querySelector(`input[data-vault="${vaultAddress}"]`);
        const amount = parseFloat(input.value);

        if (!amount || amount <= 0) {
            Toast?.show('Please enter a valid amount', 'warning');
            return;
        }

        // Confirm with user
        const confirmed = confirm(
            `Deposit ${amount} USDT to ${vaultName}?\n\n` +
            `The Engineer Agent will:\n` +
            `1. Wait for optimal gas price\n` +
            `2. Approve USDT\n` +
            `3. Execute deposit\n\n` +
            `You can track progress in your dashboard.`
        );

        if (!confirmed) return;

        try {
            // Disable button
            const btn = document.querySelector(`button[onclick*="${vaultAddress}"]`);
            btn.disabled = true;
            btn.textContent = 'Creating task...';

            // Create deposit task
            const task = await EngineerClient.createDeposit(
                window.connectedWallet,
                vaultAddress,
                amount
            );

            btn.textContent = 'Executing...';

            // Wait for completion (or timeout)
            await EngineerClient.waitForTaskCompletion(task.task_id, 120000);

            // Success!
            Toast?.show(`✅ Deposited ${amount} USDT successfully!`, 'success');

            // Clear input
            input.value = '';
            btn.textContent = 'Deposit USDT';
            btn.disabled = false;

            // Refresh user balance
            this.loadUserBalance();

        } catch (error) {
            console.error('Deposit error:', error);
            Toast?.show(`❌ Deposit failed: ${error.message}`, 'error');

            // Re-enable button
            const btn = document.querySelector(`button[onclick*="${vaultAddress}"]`);
            btn.textContent = 'Deposit USDT';
            btn.disabled = false;
        }
    },

    /**
     * Update gas price display
     */
    async updateGasPrice() {
        try {
            const gas = await EngineerClient.getGasPrice();

            const gasElement = document.getElementById('current-gas-price');
            if (gasElement) {
                gasElement.textContent = `${gas.current_gwei.toFixed(2)} gwei`;

                // Color code: green if <1, yellow if <5, red if >5
                if (gas.current_gwei < 1) {
                    gasElement.style.color = '#10b981';
                } else if (gas.current_gwei < 5) {
                    gasElement.style.color = '#f59e0b';
                } else {
                    gasElement.style.color = '#ef4444';
                }
            }
        } catch (error) {
            console.error('Gas price update error:', error);
        }
    },

    /**
     * Load user balance and positions
     */
    async loadUserBalance() {
        if (!window.connectedWallet) return;

        const balanceElement = document.getElementById('user-usdt-balance');
        if (balanceElement) {
            // TODO: Integrate with actual wallet balance
            balanceElement.textContent = '0.00 USDT';
        }

        // Load active tasks
        this.loadUserTasks();
    },

    /**
     * Load and display user's tasks
     */
    async loadUserTasks() {
        if (!window.connectedWallet) return;

        const tasksContainer = document.getElementById('user-tasks');
        if (!tasksContainer) return;

        try {
            const tasks = await EngineerClient.getUserTasks(window.connectedWallet);

            if (tasks.length === 0) {
                tasksContainer.innerHTML = '<div class="empty-tasks">No active tasks</div>';
                return;
            }

            tasksContainer.innerHTML = tasks.map(task => `
                <div class="task-item ${task.status}">
                    <div class="task-type">${this.getTaskEmoji(task.type)} ${task.type}</div>
                    <div class="task-status">${task.status}</div>
                    <div class="task-time">${new Date(task.created_at).toLocaleTimeString()}</div>
                </div>
            `).join('');

        } catch (error) {
            console.error('Load tasks error:', error);
        }
    },

    /**
     * Helper: Format TVL
     */
    formatTVL(tvl) {
        if (tvl >= 1e9) return `$${(tvl / 1e9).toFixed(2)}B`;
        if (tvl >= 1e6) return `$${(tvl / 1e6).toFixed(2)}M`;
        if (tvl >= 1e3) return `$${(tvl / 1e3).toFixed(2)}K`;
        return `$${tvl.toFixed(2)}`;
    },

    /**
     * Helper: Get task emoji
     */
    getTaskEmoji(type) {
        const emojis = {
            'simple_deposit': '💰',
            'simple_withdraw': '💸',
            'compound': '🔄',
            'rebalance': '⚖️'
        };
        return emojis[type] || '📋';
    },

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Wallet connection
        const connectBtn = document.getElementById('connect-wallet-btn');
        if (connectBtn) {
            connectBtn.addEventListener('click', async () => {
                await this.connectWallet();
            });
        }

        // Refresh button
        const refreshBtn = document.getElementById('refresh-pools-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadRecommendedPools();
            });
        }
    },

    /**
     * Connect wallet (simplified)
     */
    async connectWallet() {
        try {
            if (typeof window.ethereum !== 'undefined') {
                const accounts = await window.ethereum.request({
                    method: 'eth_requestAccounts'
                });

                window.connectedWallet = accounts[0];

                Toast?.show('✅ Wallet connected!', 'success');

                // Update UI
                document.getElementById('connect-wallet-btn').textContent =
                    `${accounts[0].substring(0, 6)}...${accounts[0].substring(38)}`;

                // Load balance
                this.loadUserBalance();

            } else {
                Toast?.show('Please install MetaMask', 'error');
            }
        } catch (error) {
            console.error('Connect wallet error:', error);
            Toast?.show('Failed to connect wallet', 'error');
        }
    }
};

// Auto-init when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => SavingsUI.init());
} else {
    SavingsUI.init();
}

// Export to window
window.SavingsUI = SavingsUI;
