/**
 * DeFi API Service
 * Real-time vault data from Beefy, DeFiLlama, and other protocols
 */

class DefiApiService {
    constructor() {
        this.apis = {
            defillama: 'https://yields.llama.fi',
            beefy: 'https://api.beefy.finance',
            coingecko: 'https://api.coingecko.com/api/v3'
        };

        this.cache = {
            pools: null,
            poolsTimestamp: 0,
            prices: null,
            pricesTimestamp: 0
        };

        this.cacheDuration = 60000; // 1 minute
    }

    /**
     * Get all yield pools from DeFiLlama
     */
    async getAllPools() {
        if (this.isCacheValid('pools')) {
            return this.cache.pools;
        }

        try {
            const response = await fetch(`${this.apis.defillama}/pools`);
            const data = await response.json();

            this.cache.pools = data.data;
            this.cache.poolsTimestamp = Date.now();

            console.log(`[DefiAPI] Loaded ${data.data.length} pools from DeFiLlama`);
            return data.data;
        } catch (error) {
            console.error('[DefiAPI] Failed to fetch pools:', error);
            return [];
        }
    }

    /**
     * Get pools filtered by chain
     */
    async getPoolsByChain(chain = 'Base') {
        const pools = await this.getAllPools();
        return pools.filter(p => p.chain?.toLowerCase() === chain.toLowerCase());
    }

    /**
     * Get pools by protocol
     */
    async getPoolsByProtocol(protocol) {
        const pools = await this.getAllPools();
        return pools.filter(p => p.project?.toLowerCase() === protocol.toLowerCase());
    }

    /**
     * Get top pools by APY
     */
    async getTopPools(limit = 20, chain = null) {
        let pools = await this.getAllPools();

        if (chain) {
            pools = pools.filter(p => p.chain?.toLowerCase() === chain.toLowerCase());
        }

        // Filter out suspicious pools
        pools = pools.filter(p =>
            p.apy > 0 &&
            p.apy < 1000 && // Filter out crazy APYs
            p.tvlUsd > 10000 // Minimum TVL
        );

        // Sort by APY
        pools.sort((a, b) => b.apy - a.apy);

        return pools.slice(0, limit);
    }

    /**
     * Get stablecoin pools
     */
    async getStablePools(chain = null) {
        let pools = await this.getAllPools();

        if (chain) {
            pools = pools.filter(p => p.chain?.toLowerCase() === chain.toLowerCase());
        }

        const stables = ['usdc', 'usdt', 'dai', 'frax', 'lusd', 'crvusd', 'gho', 'usd+'];

        return pools.filter(p => {
            const symbol = p.symbol?.toLowerCase() || '';
            return stables.some(s => symbol.includes(s)) && p.stablecoin === true;
        });
    }

    /**
     * Get Beefy vaults
     */
    async getBeefyVaults(chain = 'base') {
        try {
            const [vaultsRes, apyRes] = await Promise.all([
                fetch(`${this.apis.beefy}/vaults`),
                fetch(`${this.apis.beefy}/apy`)
            ]);

            const vaults = await vaultsRes.json();
            const apys = await apyRes.json();

            // Filter by chain and merge APY data
            const chainVaults = vaults
                .filter(v => v.chain === chain && v.status === 'active')
                .map(v => ({
                    ...v,
                    apy: (apys[v.id] || 0) * 100 // Convert to percentage
                }));

            console.log(`[DefiAPI] Loaded ${chainVaults.length} Beefy vaults on ${chain}`);
            return chainVaults;
        } catch (error) {
            console.error('[DefiAPI] Failed to fetch Beefy vaults:', error);
            return [];
        }
    }

    /**
     * Get token prices from CoinGecko
     */
    async getTokenPrices(tokens = ['ethereum', 'usd-coin', 'tether']) {
        if (this.isCacheValid('prices')) {
            return this.cache.prices;
        }

        try {
            const ids = tokens.join(',');
            const response = await fetch(
                `${this.apis.coingecko}/simple/price?ids=${ids}&vs_currencies=usd&include_24hr_change=true`
            );
            const data = await response.json();

            this.cache.prices = data;
            this.cache.pricesTimestamp = Date.now();

            return data;
        } catch (error) {
            console.error('[DefiAPI] Failed to fetch prices:', error);
            return {};
        }
    }

    /**
     * Get historical APY for a pool
     */
    async getPoolHistory(poolId) {
        try {
            const response = await fetch(`${this.apis.defillama}/chart/${poolId}`);
            const data = await response.json();
            return data.data;
        } catch (error) {
            console.error('[DefiAPI] Failed to fetch pool history:', error);
            return [];
        }
    }

    /**
     * Search pools
     */
    async searchPools(query, chain = null) {
        let pools = await this.getAllPools();

        if (chain) {
            pools = pools.filter(p => p.chain?.toLowerCase() === chain.toLowerCase());
        }

        const q = query.toLowerCase();
        return pools.filter(p =>
            p.symbol?.toLowerCase().includes(q) ||
            p.project?.toLowerCase().includes(q) ||
            p.pool?.toLowerCase().includes(q)
        );
    }

    /**
     * Get pools matching agent config
     */
    async getMatchingPools(config) {
        let pools = await this.getAllPools();

        // Filter by chain
        pools = pools.filter(p => p.chain?.toLowerCase() === 'base');

        // Filter by APY range
        pools = pools.filter(p =>
            p.apy >= config.minApy &&
            p.apy <= config.maxApy
        );

        // Filter by protocol
        if (config.protocols?.length > 0) {
            pools = pools.filter(p =>
                config.protocols.some(proto =>
                    p.project?.toLowerCase().includes(proto.toLowerCase())
                )
            );
        }

        // Filter by assets
        if (config.preferredAssets?.length > 0) {
            pools = pools.filter(p =>
                config.preferredAssets.some(asset =>
                    p.symbol?.toLowerCase().includes(asset.toLowerCase())
                )
            );
        }

        // Filter stablecoins only if configured
        if (config.avoidIL) {
            pools = pools.filter(p => p.stablecoin === true || p.ilRisk === 'no');
        }

        // Sort by TVL (higher = safer)
        pools.sort((a, b) => b.tvlUsd - a.tvlUsd);

        return pools.slice(0, config.vaultCount || 10);
    }

    /**
     * Get protocol TVL stats
     */
    async getProtocolStats() {
        try {
            const response = await fetch('https://api.llama.fi/protocols');
            const protocols = await response.json();

            // Get Base protocol stats
            const baseProtocols = protocols.filter(p =>
                p.chains?.includes('Base')
            ).slice(0, 20);

            return baseProtocols.map(p => ({
                name: p.name,
                tvl: p.tvl,
                change24h: p.change_1d,
                category: p.category,
                logo: p.logo
            }));
        } catch (error) {
            console.error('[DefiAPI] Failed to fetch protocol stats:', error);
            return [];
        }
    }

    isCacheValid(key) {
        const cacheTime = this.cache[`${key}Timestamp`];
        return cacheTime && (Date.now() - cacheTime) < this.cacheDuration;
    }

    clearCache() {
        this.cache = {
            pools: null,
            poolsTimestamp: 0,
            prices: null,
            pricesTimestamp: 0
        };
    }
}

// Singleton
const defiApi = new DefiApiService();
window.DefiApi = defiApi;

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = defiApi;
}
