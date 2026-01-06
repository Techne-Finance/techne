/**
 * Oracle Console - Unified Command Center
 * Combines chat + terminal + deployment logs
 */

(function () {
    'use strict';

    const OracleConsole = {
        console: null,
        logs: null,
        input: null,
        chatMessages: null,
        isVisible: false,

        init() {
            this.console = document.getElementById('oracleConsole');
            this.logs = document.getElementById('oracleLogs');
            this.input = document.getElementById('oracleInput');
            this.chatMessages = document.getElementById('oracleChatMessages');

            if (!this.console) return;

            this.bindEvents();
            console.log('[Oracle] Console initialized');
        },

        bindEvents() {
            // Toggle button
            const toggleBtn = document.getElementById('oracleToggle');
            if (toggleBtn) {
                toggleBtn.addEventListener('click', () => this.toggle());
            }

            // Close button
            const closeBtn = document.getElementById('oracleClose');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => this.hide());
            }

            // Minimize button
            const minimizeBtn = document.getElementById('oracleMinimize');
            if (minimizeBtn) {
                minimizeBtn.addEventListener('click', () => this.minimize());
            }

            // Clear button
            const clearBtn = document.getElementById('oracleClear');
            if (clearBtn) {
                clearBtn.addEventListener('click', () => this.clearLogs());
            }

            // Input handling
            if (this.input) {
                this.input.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        this.handleCommand(this.input.value);
                        this.input.value = '';
                    }
                });
            }

            // Auto-show on Build section
            document.addEventListener('sectionChange', (e) => {
                if (e.detail?.section === 'build') {
                    this.show();
                }
            });
        },

        toggle() {
            this.isVisible ? this.hide() : this.show();
        },

        show() {
            if (this.console) {
                this.console.style.display = 'flex';
                this.isVisible = true;
                document.body.classList.add('oracle-visible');
                this.log('[SYS] Oracle Console activated', 'system');
            }
        },

        hide() {
            if (this.console) {
                this.console.style.display = 'none';
                this.isVisible = false;
                document.body.classList.remove('oracle-visible');
            }
        },

        minimize() {
            if (this.console) {
                this.console.classList.toggle('minimized');
            }
        },

        clearLogs() {
            if (this.logs) {
                this.logs.innerHTML = '<div class="oracle-log system">[SYS] Logs cleared</div>';
            }
        },

        log(message, type = 'info') {
            if (!this.logs) return;

            const time = new Date().toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });

            const logEl = document.createElement('div');
            logEl.className = `oracle-log ${type}`;
            logEl.innerHTML = `<span class="time">[${time}]</span> ${message}`;

            this.logs.appendChild(logEl);
            this.logs.scrollTop = this.logs.scrollHeight;
        },

        addChatMessage(sender, message) {
            if (!this.chatMessages) return;

            const msgEl = document.createElement('div');
            msgEl.className = `oracle-message ${sender === 'user' ? 'user' : ''}`;
            msgEl.innerHTML = `
                <div class="sender">${sender.toUpperCase()}</div>
                <div class="content">${message}</div>
            `;

            this.chatMessages.appendChild(msgEl);
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        },

        handleCommand(cmd) {
            if (!cmd.trim()) return;

            this.log(`Ω> ${cmd}`, 'command');
            this.addChatMessage('user', cmd);

            // Parse command
            const parts = cmd.toLowerCase().trim().split(' ');
            const action = parts[0];

            switch (action) {
                case 'help':
                    this.showHelp();
                    break;
                case 'status':
                    this.showStatus();
                    break;
                case 'deploy':
                    this.simulateDeploy();
                    break;
                case 'clear':
                    this.clearLogs();
                    break;
                case 'harvest':
                    this.log('[CMD] Triggering harvest...', 'info');
                    this.addChatMessage('oracle', 'Harvesting rewards from all active positions...');
                    break;
                case 'exit':
                    this.log('[CMD] Emergency exit initiated', 'warning');
                    this.addChatMessage('oracle', '⚠️ Emergency exit: Converting all positions to USDC...');
                    break;
                default:
                    // Natural language - forward to AI
                    this.processNaturalLanguage(cmd);
            }
        },

        showHelp() {
            const helpText = `
Available commands:
  help     - Show this help
  status   - Show agent status
  deploy   - Deploy agent
  harvest  - Trigger reward harvest
  exit     - Emergency exit to stable
  clear    - Clear logs

Or type natural language instructions.
            `.trim();

            this.log(helpText.replace(/\n/g, '<br>'), 'system');
            this.addChatMessage('oracle', 'Commands: help, status, deploy, harvest, exit, clear. Or just tell me what you want in plain English.');
        },

        showStatus() {
            const status = {
                agent: 'STANDBY',
                positions: 0,
                totalValue: '$0.00',
                pendingRewards: '$0.00'
            };

            this.log(`[STATUS] Agent: ${status.agent} | Positions: ${status.positions} | Value: ${status.totalValue}`, 'info');
            this.addChatMessage('oracle', `Current status:\n• Agent: ${status.agent}\n• Positions: ${status.positions}\n• Value: ${status.totalValue}\n• Pending rewards: ${status.pendingRewards}`);
        },

        async simulateDeploy() {
            this.log('[DEPLOY] Initializing deployment sequence...', 'info');

            const steps = [
                { msg: '[DEPLOY] Validating configuration...', delay: 500 },
                { msg: '[DEPLOY] Checking wallet balance...', delay: 800 },
                { msg: '[DEPLOY] Compiling strategy parameters...', delay: 600 },
                { msg: '[DEPLOY] Connecting to Base network...', delay: 700 },
                { msg: '[DEPLOY] Creating agent wallet...', delay: 1000 },
                { msg: '[DEPLOY] ✓ Agent deployed successfully!', delay: 500, type: 'success' }
            ];

            for (const step of steps) {
                await this.sleep(step.delay);
                this.log(step.msg, step.type || 'info');
            }

            this.addChatMessage('oracle', '🚀 Agent deployed successfully! Send funds to the agent wallet to begin farming.');
        },

        processNaturalLanguage(text) {
            this.log(`[NLP] Processing: "${text}"`, 'info');

            // Simple pattern matching for demo
            if (text.includes('harvest') || text.includes('collect')) {
                this.addChatMessage('oracle', 'I\'ll configure the agent to harvest rewards. Would you like auto-compound or cash-out?');
            } else if (text.includes('stop') || text.includes('exit')) {
                this.addChatMessage('oracle', '⚠️ Understood. I\'ll prepare an exit strategy. Confirm by typing "exit".');
            } else if (text.includes('apy') || text.includes('yield')) {
                this.addChatMessage('oracle', 'Current best yields on Base:\n• Morpho USDC: 12.4%\n• Aave USDC: 8.2%\n• Moonwell: 15.1%');
            } else {
                this.addChatMessage('oracle', `Received: "${text}". I\'ll incorporate this into the agent\'s strategy.`);
            }
        },

        sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }
    };

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => OracleConsole.init());
    } else {
        OracleConsole.init();
    }

    // Export
    window.OracleConsole = OracleConsole;
})();
