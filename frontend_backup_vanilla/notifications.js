/**
 * Notifications & Toast System
 * Provides real-time toast notifications and notification history
 */

class NotificationSystem {
    constructor() {
        this.history = [];
        this.maxHistory = 50;
        this.container = null;
    }

    init() {
        this.createContainer();
        console.log('[Notifications] System initialized');
    }

    createContainer() {
        if (document.getElementById('toast-container')) return;

        const container = document.createElement('div');
        container.id = 'toast-container';
        container.innerHTML = `
            <style>
                #toast-container {
                    position: fixed;
                    top: 80px;
                    right: 20px;
                    z-index: 10000;
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                    max-width: 400px;
                }
                
                .toast {
                    display: flex;
                    align-items: flex-start;
                    gap: 12px;
                    padding: 14px 18px;
                    background: linear-gradient(135deg, rgba(26, 26, 46, 0.98) 0%, rgba(22, 33, 62, 0.95) 100%);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
                    backdrop-filter: blur(10px);
                    animation: slideIn 0.3s ease-out;
                    min-width: 300px;
                }
                
                .toast.info { border-color: rgba(59, 130, 246, 0.5); }
                .toast.success { border-color: rgba(16, 185, 129, 0.5); }
                .toast.warning { border-color: rgba(245, 158, 11, 0.5); }
                .toast.error { border-color: rgba(239, 68, 68, 0.5); }
                
                .toast-icon {
                    font-size: 1.3rem;
                    flex-shrink: 0;
                }
                
                .toast-content {
                    flex: 1;
                }
                
                .toast-title {
                    font-weight: 600;
                    color: #fff;
                    font-size: 0.9rem;
                    margin-bottom: 4px;
                }
                
                .toast-message {
                    color: #aaa;
                    font-size: 0.82rem;
                    line-height: 1.4;
                }
                
                .toast-close {
                    background: none;
                    border: none;
                    color: #666;
                    cursor: pointer;
                    padding: 0;
                    font-size: 1.2rem;
                    line-height: 1;
                }
                
                .toast-close:hover {
                    color: #fff;
                }
                
                .toast-progress {
                    position: absolute;
                    bottom: 0;
                    left: 0;
                    height: 3px;
                    background: var(--gold, #D4AF37);
                    border-radius: 0 0 12px 12px;
                    animation: progress linear forwards;
                }
                
                @keyframes slideIn {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                
                @keyframes slideOut {
                    from {
                        transform: translateX(0);
                        opacity: 1;
                    }
                    to {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                }
                
                @keyframes progress {
                    from { width: 100%; }
                    to { width: 0%; }
                }
            </style>
        `;
        document.body.appendChild(container);
        this.container = container;
    }

    /**
     * Show a toast notification
     */
    show(message, type = 'info', options = {}) {
        const {
            title = this.getDefaultTitle(type),
            duration = 5000,
            persistent = false,
            onClick = null
        } = options;

        const id = Date.now();
        const icon = this.getIcon(type);

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.id = `toast-${id}`;
        toast.style.position = 'relative';
        toast.innerHTML = `
            <span class="toast-icon">${icon}</span>
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close">&times;</button>
            ${!persistent ? `<div class="toast-progress" style="animation-duration: ${duration}ms"></div>` : ''}
        `;

        // Close button
        toast.querySelector('.toast-close').addEventListener('click', () => {
            this.dismiss(id);
        });

        // Click handler
        if (onClick) {
            toast.style.cursor = 'pointer';
            toast.addEventListener('click', (e) => {
                if (!e.target.classList.contains('toast-close')) {
                    onClick();
                    this.dismiss(id);
                }
            });
        }

        this.container.appendChild(toast);

        // Add to history
        this.addToHistory({ id, type, title, message, time: new Date() });

        // Auto dismiss
        if (!persistent) {
            setTimeout(() => this.dismiss(id), duration);
        }

        return id;
    }

    dismiss(id) {
        const toast = document.getElementById(`toast-${id}`);
        if (toast) {
            toast.style.animation = 'slideOut 0.3s ease-out forwards';
            setTimeout(() => toast.remove(), 300);
        }
    }

    /**
     * Convenience methods
     */
    info(message, options = {}) {
        return this.show(message, 'info', options);
    }

    success(message, options = {}) {
        return this.show(message, 'success', options);
    }

    warning(message, options = {}) {
        return this.show(message, 'warning', options);
    }

    error(message, options = {}) {
        return this.show(message, 'error', { duration: 8000, ...options });
    }

    /**
     * Agent-specific notifications
     */
    agentDeposit(vault, amount) {
        this.success(`Deposited $${amount.toFixed(2)} into ${vault}`, {
            title: '🤖 Agent Action'
        });
    }

    agentWithdraw(vault, amount) {
        this.info(`Withdrew $${amount.toFixed(2)} from ${vault}`, {
            title: '🤖 Agent Action'
        });
    }

    agentRebalance(changes) {
        this.success(`Portfolio rebalanced: ${changes} position(s) adjusted`, {
            title: '⚖️ Rebalance Complete'
        });
    }

    agentHarvest(vault, rewards) {
        this.success(`Harvested $${rewards.toFixed(2)} from ${vault}`, {
            title: '🌾 Rewards Claimed'
        });
    }

    apyAlert(vault, oldApy, newApy) {
        const direction = newApy > oldApy ? 'increased' : 'dropped';
        const type = newApy > oldApy ? 'success' : 'warning';
        this.show(
            `APY ${direction} from ${oldApy.toFixed(1)}% to ${newApy.toFixed(1)}%`,
            type,
            { title: `📊 ${vault}` }
        );
    }

    emergencyExit(reason) {
        this.error(`Emergency exit triggered: ${reason}`, {
            title: '🚨 Emergency Action',
            duration: 10000
        });
    }

    /**
     * History management
     */
    addToHistory(notification) {
        this.history.unshift(notification);
        if (this.history.length > this.maxHistory) {
            this.history.pop();
        }

        // Update notifications panel in portfolio
        this.updatePortfolioNotifications();
    }

    updatePortfolioNotifications() {
        const listEl = document.getElementById('notificationsList');
        const countEl = document.getElementById('notifCount');

        if (!listEl) return;

        countEl.textContent = this.history.length;

        if (this.history.length === 0) {
            listEl.innerHTML = '<div class="notif-empty"><p>No new notifications</p></div>';
            return;
        }

        listEl.innerHTML = this.history.slice(0, 8).map(n => `
            <div class="notif-item ${n.type}">
                <span class="notif-text">${n.message}</span>
                <span class="notif-time">${this.formatTime(n.time)}</span>
            </div>
        `).join('');
    }

    getHistory() {
        return this.history;
    }

    clearHistory() {
        this.history = [];
        this.updatePortfolioNotifications();
    }

    getDefaultTitle(type) {
        const titles = {
            info: 'Information',
            success: 'Success',
            warning: 'Warning',
            error: 'Error'
        };
        return titles[type] || 'Notification';
    }

    getIcon(type) {
        const icons = {
            info: 'ℹ️',
            success: '✅',
            warning: '⚠️',
            error: '❌'
        };
        return icons[type] || '📢';
    }

    formatTime(date) {
        const now = new Date();
        const diff = now - date;
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        return date.toLocaleDateString();
    }
}

// Initialize
const Notifications = new NotificationSystem();
document.addEventListener('DOMContentLoaded', () => Notifications.init());

// Global helpers
window.Notifications = Notifications;
window.showToast = (msg, type) => Notifications.show(msg, type);
window.toast = Notifications;
