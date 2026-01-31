/**
 * Sentry Utility Functions for Techne Finance Frontend
 * Provides helpers for user context, breadcrumbs, and error capturing
 */

const SentryUtils = {
    /**
     * Check if Sentry is available
     */
    isAvailable() {
        return typeof Sentry !== 'undefined';
    },

    /**
     * Set user context when wallet connects
     */
    setWalletContext(walletAddress) {
        if (!this.isAvailable()) return;

        Sentry.setUser({
            id: walletAddress ? walletAddress.slice(0, 10) + '...' : null,
        });
        Sentry.setContext('wallet', {
            address: walletAddress?.slice(0, 10) + '...',
            connected: !!walletAddress,
            network: 'base',
            chainId: 8453,
        });
    },

    /**
     * Clear user context on disconnect
     */
    clearWalletContext() {
        if (!this.isAvailable()) return;
        Sentry.setUser(null);
    },

    /**
     * Add breadcrumb for agent deployment
     */
    trackAgentDeploy(agentId, strategy) {
        if (!this.isAvailable()) return;

        Sentry.addBreadcrumb({
            category: 'agent',
            message: 'Agent deployment initiated',
            level: 'info',
            data: { agentId, strategy }
        });
    },

    /**
     * Track agent deployment success
     */
    trackAgentDeploySuccess(agentId, smartAccountAddress) {
        if (!this.isAvailable()) return;

        Sentry.addBreadcrumb({
            category: 'agent',
            message: 'Agent deployed successfully',
            level: 'info',
            data: {
                agentId,
                smartAccount: smartAccountAddress?.slice(0, 10) + '...'
            }
        });
    },

    /**
     * Add breadcrumb for transactions
     */
    trackTransaction(type, amount, token) {
        if (!this.isAvailable()) return;

        Sentry.addBreadcrumb({
            category: 'transaction',
            message: `${type} ${amount} ${token}`,
            level: 'info',
            data: { type, amount, token }
        });
    },

    /**
     * Track blockchain interactions
     */
    trackBlockchain(action, details = {}) {
        if (!this.isAvailable()) return;

        Sentry.addBreadcrumb({
            category: 'blockchain',
            message: action,
            level: 'info',
            data: { network: 'base', ...details }
        });
    },

    /**
     * Capture and report an error with context
     */
    captureError(error, context = {}) {
        if (!this.isAvailable()) {
            console.error('[Error]', error, context);
            return;
        }

        Sentry.withScope((scope) => {
            Object.entries(context).forEach(([key, value]) => {
                scope.setExtra(key, value);
            });
            Sentry.captureException(error);
        });
    },

    /**
     * Capture a message (non-error event)
     */
    captureMessage(message, level = 'info', context = {}) {
        if (!this.isAvailable()) {
            console.log('[Sentry]', message, context);
            return;
        }

        Sentry.withScope((scope) => {
            Object.entries(context).forEach(([key, value]) => {
                scope.setExtra(key, value);
            });
            Sentry.captureMessage(message, level);
        });
    },

    /**
     * Track page navigation
     */
    trackNavigation(section) {
        if (!this.isAvailable()) return;

        Sentry.addBreadcrumb({
            category: 'navigation',
            message: `Navigated to ${section}`,
            level: 'info',
        });
    },

    /**
     * Track API calls
     */
    trackApiCall(endpoint, method = 'GET', status = null) {
        if (!this.isAvailable()) return;

        Sentry.addBreadcrumb({
            category: 'api',
            message: `${method} ${endpoint}`,
            level: status >= 400 ? 'error' : 'info',
            data: { endpoint, method, status }
        });
    },

    /**
     * Start a performance transaction
     */
    startTransaction(name, op = 'function') {
        if (!this.isAvailable()) return null;

        return Sentry.startTransaction({
            name: name,
            op: op,
        });
    },

    /**
     * Finish a transaction
     */
    finishTransaction(transaction) {
        if (transaction && typeof transaction.finish === 'function') {
            transaction.finish();
        }
    }
};

// Export for global use
window.SentryUtils = SentryUtils;

// Log initialization
console.log('[SentryUtils] Utility functions loaded');
