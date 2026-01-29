/**
 * Agent Service API Client
 * Frontend client for the new scalable /api/agents/* endpoints
 * Uses Supabase-backed agent management system
 */

const AgentServiceAPI = {

    /**
     * Get all agents for a user
     * @param {string} userAddress - User's wallet address
     * @returns {Promise<object>} List of agents
     */
    async getUserAgents(userAddress) {
        try {
            const API_BASE = window.API_BASE || '';
            const response = await fetch(`${API_BASE}/api/agents/user/${userAddress}`);
            return await response.json();
        } catch (error) {
            console.error('[AgentService] Failed to get user agents:', error);
            return { success: false, error: error.message };
        }
    },

    /**
     * Get single agent details with balances and positions
     * @param {string} agentAddress - Agent's wallet address
     * @returns {Promise<object>} Agent details
     */
    async getAgentDetails(agentAddress) {
        try {
            const API_BASE = window.API_BASE || '';
            const response = await fetch(`${API_BASE}/api/agents/details/${agentAddress}`);
            return await response.json();
        } catch (error) {
            console.error('[AgentService] Failed to get agent details:', error);
            return { success: false, error: error.message };
        }
    },

    /**
     * Pause an agent
     * @param {string} agentAddress - Agent's wallet address
     */
    async pauseAgent(agentAddress) {
        try {
            const API_BASE = window.API_BASE || '';
            const response = await fetch(`${API_BASE}/api/agents/${agentAddress}/pause`, {
                method: 'POST'
            });
            return await response.json();
        } catch (error) {
            console.error('[AgentService] Failed to pause agent:', error);
            return { success: false, error: error.message };
        }
    },

    /**
     * Resume an agent
     * @param {string} agentAddress - Agent's wallet address
     */
    async resumeAgent(agentAddress) {
        try {
            const API_BASE = window.API_BASE || '';
            const response = await fetch(`${API_BASE}/api/agents/${agentAddress}/resume`, {
                method: 'POST'
            });
            return await response.json();
        } catch (error) {
            console.error('[AgentService] Failed to resume agent:', error);
            return { success: false, error: error.message };
        }
    },

    /**
     * Get agent balances
     * @param {string} agentAddress - Agent's wallet address
     */
    async getBalances(agentAddress) {
        try {
            const API_BASE = window.API_BASE || '';
            const response = await fetch(`${API_BASE}/api/agents/${agentAddress}/balances`);
            return await response.json();
        } catch (error) {
            console.error('[AgentService] Failed to get balances:', error);
            return { success: false, error: error.message };
        }
    },

    /**
     * Get agent positions
     * @param {string} agentAddress - Agent's wallet address
     * @param {string} status - Filter by status (active, closed, all)
     */
    async getPositions(agentAddress, status = 'active') {
        try {
            const API_BASE = window.API_BASE || '';
            const response = await fetch(`${API_BASE}/api/agents/${agentAddress}/positions?status=${status}`);
            return await response.json();
        } catch (error) {
            console.error('[AgentService] Failed to get positions:', error);
            return { success: false, error: error.message };
        }
    },

    /**
     * Get agent transaction history
     * @param {string} agentAddress - Agent's wallet address
     * @param {number} limit - Max transactions to return
     */
    async getTransactions(agentAddress, limit = 50) {
        try {
            const API_BASE = window.API_BASE || '';
            const response = await fetch(`${API_BASE}/api/agents/${agentAddress}/transactions?limit=${limit}`);
            return await response.json();
        } catch (error) {
            console.error('[AgentService] Failed to get transactions:', error);
            return { success: false, error: error.message };
        }
    },

    /**
     * Get audit trail for agent
     * @param {string} agentAddress - Agent's wallet address
     */
    async getAuditTrail(agentAddress) {
        try {
            const API_BASE = window.API_BASE || '';
            const response = await fetch(`${API_BASE}/api/agents/${agentAddress}/audit`);
            return await response.json();
        } catch (error) {
            console.error('[AgentService] Failed to get audit trail:', error);
            return { success: false, error: error.message };
        }
    },

    /**
     * Get portfolio summary for user (all agents combined)
     * @param {string} userAddress - User's wallet address
     */
    async getPortfolioSummary(userAddress) {
        try {
            const API_BASE = window.API_BASE || '';
            const response = await fetch(`${API_BASE}/api/agents/user/${userAddress}/summary`);
            return await response.json();
        } catch (error) {
            console.error('[AgentService] Failed to get portfolio summary:', error);
            return { success: false, error: error.message };
        }
    },

    /**
     * Update agent configuration
     * @param {string} agentAddress - Agent's wallet address
     * @param {object} updates - Fields to update
     */
    async updateAgent(agentAddress, updates) {
        try {
            const API_BASE = window.API_BASE || '';
            const response = await fetch(`${API_BASE}/api/agents/${agentAddress}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updates)
            });
            return await response.json();
        } catch (error) {
            console.error('[AgentService] Failed to update agent:', error);
            return { success: false, error: error.message };
        }
    }
};

// Export to window
window.AgentServiceAPI = AgentServiceAPI;

console.log('[AgentServiceAPI] Loaded - Scalable agent management client ready');
