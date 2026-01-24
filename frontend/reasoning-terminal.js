/**
 * Reasoning Terminal v2.0
 * Displays Agent decision logs in cyberpunk style
 * 
 * Usage:
 *   const terminal = new ReasoningTerminal('reasoning-terminal-container');
 *   terminal.start();  // Starts auto-refresh
 *   terminal.stop();   // Stops auto-refresh
 */

class ReasoningTerminal {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            refreshInterval: options.refreshInterval || 5000,
            maxLogs: options.maxLogs || 10,
            apiUrl: options.apiUrl || '/api/audit/reasoning-logs',
            userAddress: options.userAddress || null
        };
        this.intervalId = null;
        this.logs = [];

        if (this.container) {
            this.render();
        }
    }

    render() {
        this.container.innerHTML = `
            <div class="reasoning-terminal">
                <div class="terminal-header">
                    <span class="terminal-icon">🧠</span>
                    <span class="terminal-title">Neural Terminal v2.0</span>
                    <span class="terminal-status" id="terminal-status">● LIVE</span>
                </div>
                <div class="terminal-body" id="terminal-logs">
                    <div class="terminal-loading">
                        <span class="loading-cursor">▋</span> Initializing neural network...
                    </div>
                </div>
                <div class="terminal-footer">
                    <span class="terminal-hint">Agent reasoning logs • Auto-refresh 5s</span>
                </div>
            </div>
        `;

        this.logsContainer = document.getElementById('terminal-logs');
        this.statusIndicator = document.getElementById('terminal-status');
    }

    async fetchLogs() {
        try {
            let url = `${this.options.apiUrl}?limit=${this.options.maxLogs}`;
            if (this.options.userAddress) {
                url += `&user_address=${this.options.userAddress}`;
            }

            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to fetch');

            const data = await response.json();
            this.logs = data.logs || [];
            this.updateStatus('online');
            this.renderLogs();

        } catch (error) {
            console.error('Reasoning Terminal error:', error);
            this.updateStatus('offline');
            this.renderError();
        }
    }

    renderLogs() {
        if (!this.logsContainer) return;

        if (this.logs.length === 0) {
            this.logsContainer.innerHTML = `
                <div class="terminal-empty">
                    <span class="empty-icon">📭</span>
                    <span class="empty-text">No reasoning logs yet. Agent is waiting...</span>
                </div>
            `;
            return;
        }

        const logsHtml = this.logs.map(log => this.renderLogEntry(log)).join('');
        this.logsContainer.innerHTML = logsHtml;

        // Auto-scroll to bottom
        this.logsContainer.scrollTop = this.logsContainer.scrollHeight;
    }

    renderLogEntry(log) {
        const time = this.formatTime(log.timestamp);
        const colorClass = `log-${log.color || 'green'}`;

        return `
            <div class="terminal-log ${colorClass}" data-severity="${log.severity}">
                <span class="log-time">${time}</span>
                <span class="log-category">${log.category}</span>
                <span class="log-icon">${log.icon}</span>
                <span class="log-message">${log.message}</span>
            </div>
        `;
    }

    renderError() {
        if (!this.logsContainer) return;
        this.logsContainer.innerHTML = `
            <div class="terminal-error">
                <span class="error-icon">⚠️</span>
                <span class="error-text">Connection lost. Retrying...</span>
            </div>
        `;
    }

    updateStatus(status) {
        if (!this.statusIndicator) return;

        if (status === 'online') {
            this.statusIndicator.textContent = '● LIVE';
            this.statusIndicator.className = 'terminal-status status-online';
        } else {
            this.statusIndicator.textContent = '○ OFFLINE';
            this.statusIndicator.className = 'terminal-status status-offline';
        }
    }

    formatTime(timestamp) {
        if (!timestamp) return '--:--';
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
    }

    start() {
        this.fetchLogs();
        this.intervalId = setInterval(() => this.fetchLogs(), this.options.refreshInterval);
        console.log('🧠 Reasoning Terminal started');
    }

    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
        this.updateStatus('offline');
        console.log('🧠 Reasoning Terminal stopped');
    }

    // Add demo logs for testing
    addDemoLogs() {
        this.logs = [
            {
                timestamp: new Date().toISOString(),
                category: '[GUARD]',
                icon: '⛔',
                message: 'Rotation aborted. Costs ($11.50) > Profit ($8.20)',
                color: 'yellow',
                severity: 'warning'
            },
            {
                timestamp: new Date(Date.now() - 60000).toISOString(),
                category: '[SECURITY]',
                icon: '🚨',
                message: 'Security Alert: Contract flagged as scam (score: 85)',
                color: 'red',
                severity: 'critical'
            },
            {
                timestamp: new Date(Date.now() - 120000).toISOString(),
                category: '[PARK]',
                icon: '🅿️',
                message: 'Capital parked in Aave V3. Earning 3.5% APY while waiting.',
                color: 'cyan',
                severity: 'info'
            },
            {
                timestamp: new Date(Date.now() - 180000).toISOString(),
                category: '[ORACLE]',
                icon: '📊',
                message: 'Price deviation 2.3% detected. Monitoring.',
                color: 'green',
                severity: 'info'
            }
        ];
        this.renderLogs();
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ReasoningTerminal;
}
