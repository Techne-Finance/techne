/**
 * Techne Protocol - Search History & Advanced Features
 */

// ============================================
// SEARCH HISTORY (24h localStorage)
// ============================================
const SearchHistory = {
    KEY: 'techne_search_history',
    MAX_ITEMS: 20,
    TTL_HOURS: 24,

    init() {
        this.cleanOldEntries();
        this.renderWidget();
    },

    getHistory() {
        try {
            const data = localStorage.getItem(this.KEY);
            return data ? JSON.parse(data) : [];
        } catch {
            return [];
        }
    },

    saveHistory(history) {
        localStorage.setItem(this.KEY, JSON.stringify(history));
    },

    cleanOldEntries() {
        const history = this.getHistory();
        const now = Date.now();
        const ttl = this.TTL_HOURS * 60 * 60 * 1000;

        const filtered = history.filter(entry => (now - entry.timestamp) < ttl);
        this.saveHistory(filtered);
    },

    addEntry(type, data) {
        const history = this.getHistory();

        const entry = {
            id: Date.now().toString(),
            type,  // 'filter', 'pool_view', 'unlock', 'deposit'
            data,
            timestamp: Date.now()
        };

        history.unshift(entry);

        // Keep only last MAX_ITEMS
        if (history.length > this.MAX_ITEMS) {
            history.pop();
        }

        this.saveHistory(history);
        this.renderWidget();

        return entry;
    },

    formatTimeAgo(timestamp) {
        const diff = Date.now() - timestamp;
        const mins = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);

        if (mins < 1) return 'Just now';
        if (mins < 60) return `${mins}m ago`;
        if (hours < 24) return `${hours}h ago`;
        return 'Yesterday';
    },

    renderWidget() {
        let widget = document.getElementById('paidPoolsHistory');

        // Only show unlock and deposit entries (paid pools)
        const history = this.getHistory().filter(e => e.type === 'unlock' || e.type === 'deposit');

        if (!widget) {
            widget = document.createElement('div');
            widget.id = 'paidPoolsHistory';
            widget.className = 'paid-history-dropdown';

            // Insert in header-right area
            const headerRight = document.querySelector('.header-right');
            if (headerRight) {
                headerRight.insertBefore(widget, headerRight.firstChild);
            }
        }

        if (history.length === 0) {
            widget.style.display = 'none';
            return;
        }

        widget.style.display = 'block';
        widget.innerHTML = `
            <button class="paid-history-btn" onclick="this.parentElement.classList.toggle('open')">
                🔓 <span>${history.length}</span>
            </button>
            <div class="paid-history-panel">
                <div class="paid-history-header">
                    <span>Unlocked Pools</span>
                    <button onclick="SearchHistory.clearAll()">Clear</button>
                </div>
                ${history.slice(0, 5).map(entry => `
                    <div class="paid-history-item">
                        <span class="icon">${this.getIcon(entry.type)}</span>
                        <span class="label">${this.getLabel(entry)}</span>
                        <span class="time">${this.formatTimeAgo(entry.timestamp)}</span>
                    </div>
                `).join('')}
            </div>
        `;
    },

    getIcon(type) {
        const icons = {
            'filter': '🔍',
            'pool_view': '💧',
            'unlock': '🔓',
            'deposit': '💰'
        };
        return icons[type] || '📋';
    },

    getLabel(entry) {
        switch (entry.type) {
            case 'filter':
                return `Filtered: ${entry.data.assetType || 'All'}`;
            case 'pool_view':
                return `Viewed: ${entry.data.project}`;
            case 'unlock':
                return `Unlocked ${entry.data.count} pools`;
            case 'deposit':
                return `Deposit: ${entry.data.project}`;
            default:
                return 'Activity';
        }
    },

    replayEntry(id) {
        const history = this.getHistory();
        const entry = history.find(e => e.id === id);

        if (entry && entry.type === 'filter') {
            // Replay filter settings
            Object.assign(filters, entry.data);
            loadPools();
        }
    },

    clearAll() {
        localStorage.removeItem(this.KEY);
        this.renderWidget();
    }
};

// ============================================
// ETH POOLS SUPPORT
// ============================================
const ETHPools = {
    // ETH staking and yield protocols
    PROTOCOLS: [
        'lido', 'rocketpool', 'frax-ether', 'swell', 'mantle-staked-ether',
        'eigenlayer', 'ether.fi', 'kelp-dao', 'renzo', 'puffer-finance'
    ],

    isETHPool(pool) {
        const symbol = (pool.symbol || '').toUpperCase();
        return symbol.includes('ETH') ||
            symbol.includes('STETH') ||
            symbol.includes('WETH') ||
            symbol.includes('RETH') ||
            symbol.includes('CBETH');
    },

    isSingleSided(pool) {
        const symbol = pool.symbol || '';
        // Single-sided = no separator, or staking derivative
        return !symbol.includes('-') &&
            !symbol.includes('/') ||
            symbol.match(/^(stETH|rETH|cbETH|wstETH|ezETH|weETH)$/i);
    }
};

// ============================================
// SOL POOLS SUPPORT
// ============================================
const SOLPools = {
    // SOL staking and yield protocols
    PROTOCOLS: [
        'marinade', 'jito', 'blazestake', 'socean', 'lido-solana',
        'sanctum', 'eversol', 'laine-stake'
    ],

    isSOLPool(pool) {
        const symbol = (pool.symbol || '').toUpperCase();
        const chain = (pool.chain || '').toLowerCase();
        return chain === 'solana' ||
            symbol.includes('SOL') ||
            symbol.includes('MSOL') ||
            symbol.includes('JITOSOL');
    },

    isSingleSided(pool) {
        const symbol = pool.symbol || '';
        return !symbol.includes('-') &&
            !symbol.includes('/') ||
            symbol.match(/^(mSOL|jitoSOL|bSOL|scnSOL|stSOL)$/i);
    }
};

// ============================================
// NICHE PROTOCOLS
// ============================================
const NicheProtocols = {
    // Lesser-known but solid protocols
    LIST: [
        { name: 'Notional Finance', chain: 'Ethereum', category: 'lending' },
        { name: 'Idle Finance', chain: 'Ethereum', category: 'yield' },
        { name: 'Ribbon Finance', chain: 'Ethereum', category: 'options' },
        { name: 'Sturdy Finance', chain: 'Ethereum', category: 'lending' },
        { name: 'Exactly Protocol', chain: 'Ethereum', category: 'lending' },
        { name: 'Silo Finance', chain: 'Ethereum', category: 'lending' },
        { name: 'Fluid', chain: 'Ethereum', category: 'lending' },
        { name: 'Seamless Protocol', chain: 'Base', category: 'lending' },
        { name: 'Moonwell', chain: 'Base', category: 'lending' },
        { name: 'Ionic Protocol', chain: 'Base', category: 'lending' },
        { name: 'Extra Finance', chain: 'Base', category: 'leveraged' },
        { name: 'Tarot Finance', chain: 'Base', category: 'leveraged' },
        { name: 'Marginfi', chain: 'Solana', category: 'lending' },
        { name: 'Drift Protocol', chain: 'Solana', category: 'perps' },
        { name: 'Tulip Protocol', chain: 'Solana', category: 'yield' }
    ],

    isNiche(protocol) {
        const name = (protocol || '').toLowerCase();
        return this.LIST.some(p => name.includes(p.name.toLowerCase()));
    },

    getCategory(protocol) {
        const name = (protocol || '').toLowerCase();
        const found = this.LIST.find(p => name.includes(p.name.toLowerCase()));
        return found?.category || 'other';
    }
};

// ============================================
// ENHANCED POOL FILTERING
// ============================================
function filterPoolsByAssetType(pools, assetType, stablecoinType = 'all') {
    if (assetType === 'all') return pools;

    return pools.filter(pool => {
        const symbol = (pool.symbol || '').toUpperCase();

        switch (assetType) {
            case 'stablecoin':
                const isStable = pool.stablecoin ||
                    ['USDC', 'USDT', 'DAI', 'FRAX', 'LUSD', 'TUSD', 'BUSD', 'GUSD'].some(s => symbol.includes(s));

                // Filter by specific stablecoin if selected
                if (stablecoinType !== 'all') {
                    return isStable && symbol.includes(stablecoinType);
                }
                return isStable;

            case 'eth':
                return ETHPools.isETHPool(pool);

            case 'sol':
                return SOLPools.isSOLPool(pool);

            default:
                return true;
        }
    });
}

// ============================================
// CSS FOR PAID POOLS HISTORY (header dropdown)
// ============================================
const historyStyles = document.createElement('style');
historyStyles.textContent = `
    .paid-history-dropdown {
        position: relative;
        margin-right: 8px;
    }
    
    .paid-history-btn {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 8px 12px;
        background: rgba(212, 175, 55, 0.1);
        border: 1px solid rgba(212, 175, 55, 0.3);
        border-radius: 8px;
        color: #D4AF37;
        font-size: 0.8rem;
        cursor: pointer;
    }
    
    .paid-history-btn span {
        background: #D4AF37;
        color: #0f0f23;
        padding: 2px 6px;
        border-radius: 10px;
        font-size: 0.7rem;
        font-weight: 700;
    }
    
    .paid-history-panel {
        display: none;
        position: absolute;
        top: 100%;
        right: 0;
        margin-top: 8px;
        width: 280px;
        background: #1a1a2e;
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.4);
        z-index: 1000;
        overflow: hidden;
    }
    
    .paid-history-dropdown.open .paid-history-panel {
        display: block;
    }
    
    .paid-history-header {
        display: flex;
        justify-content: space-between;
        padding: 12px;
        background: rgba(255,255,255,0.03);
        border-bottom: 1px solid rgba(255,255,255,0.08);
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .paid-history-header button {
        background: transparent;
        border: none;
        color: #888;
        font-size: 0.7rem;
        cursor: pointer;
    }
    
    .paid-history-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 12px;
        border-bottom: 1px solid rgba(255,255,255,0.05);
    }
    
    .paid-history-item:last-child {
        border-bottom: none;
    }
    
    .paid-history-item .icon {
        font-size: 1rem;
    }
    
    .paid-history-item .label {
        flex: 1;
        font-size: 0.8rem;
    }
    
    .paid-history-item .time {
        font-size: 0.7rem;
        color: #888;
    }
`;
document.head.appendChild(historyStyles);

// ============================================
// INITIALIZE
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        SearchHistory.init();
    }, 600);
});

// Export
window.SearchHistory = SearchHistory;
window.ETHPools = ETHPools;
window.SOLPools = SOLPools;
window.NicheProtocols = NicheProtocols;
window.filterPoolsByAssetType = filterPoolsByAssetType;
