/**
 * Beefy Vault Integration Service
 * Integrates with Beefy Finance vaults on Base chain
 */

const BEEFY_API = 'https://api.beefy.finance';
const BASE_CHAIN_ID = 8453;

// Standard ERC-4626 / Beefy Vault ABI
const VAULT_ABI = [
    // Read functions
    "function balanceOf(address) view returns (uint256)",
    "function totalSupply() view returns (uint256)",
    "function getPricePerFullShare() view returns (uint256)",
    "function want() view returns (address)",
    "function balance() view returns (uint256)",

    // Write functions
    "function deposit(uint256 _amount) external",
    "function depositAll() external",
    "function withdraw(uint256 _shares) external",
    "function withdrawAll() external",

    // ERC20 functions for moo tokens
    "function approve(address spender, uint256 amount) returns (bool)",
    "function allowance(address owner, address spender) view returns (uint256)"
];

// ERC20 ABI for underlying tokens
const ERC20_ABI = [
    "function approve(address spender, uint256 amount) returns (bool)",
    "function allowance(address owner, address spender) view returns (uint256)",
    "function balanceOf(address) view returns (uint256)",
    "function decimals() view returns (uint8)",
    "function symbol() view returns (string)"
];

class BeefyVaultService {
    constructor() {
        this.vaults = [];
        this.baseVaults = [];
        this.provider = null;
        this.signer = null;
    }

    /**
     * Initialize service with ethers provider/signer
     */
    init(provider, signer) {
        this.provider = provider;
        this.signer = signer;
    }

    /**
     * Fetch all Beefy vaults and filter for Base chain
     */
    async fetchBaseVaults() {
        try {
            const [vaultsRes, apyRes, tvlRes] = await Promise.all([
                fetch(`${BEEFY_API}/vaults`),
                fetch(`${BEEFY_API}/apy`),
                fetch(`${BEEFY_API}/tvl`)
            ]);

            const vaults = await vaultsRes.json();
            const apys = await apyRes.json();
            const tvls = await tvlRes.json();

            // Filter for Base chain, active vaults only
            this.baseVaults = vaults
                .filter(v => v.chain === 'base' && v.status === 'active')
                .map(v => ({
                    id: v.id,
                    name: v.name,
                    token: v.token,
                    tokenAddress: v.tokenAddress,
                    vaultAddress: v.earnContractAddress,
                    earnedToken: v.earnedToken,
                    platform: v.platformId,
                    assets: v.assets || [],
                    strategyType: v.strategyTypeId,
                    addLiquidityUrl: v.addLiquidityUrl,
                    apy: apys[v.id] ? (apys[v.id] * 100).toFixed(2) : null,
                    tvl: tvls[v.chain]?.[v.id] || null,
                    pricePerShare: v.pricePerFullShare
                }))
                .filter(v => v.apy && parseFloat(v.apy) > 0)
                .sort((a, b) => parseFloat(b.apy) - parseFloat(a.apy));

            console.log(`[Beefy] Loaded ${this.baseVaults.length} active Base vaults`);
            return this.baseVaults;
        } catch (error) {
            console.error('[Beefy] Failed to fetch vaults:', error);
            throw error;
        }
    }

    /**
     * Get top performing vaults by category
     */
    getTopVaults(category = 'all', limit = 10) {
        let filtered = [...this.baseVaults];

        switch (category) {
            case 'stablecoin':
                filtered = filtered.filter(v =>
                    v.assets.some(a => ['USDC', 'USDT', 'DAI', 'USDbC'].includes(a))
                );
                break;
            case 'eth':
                filtered = filtered.filter(v =>
                    v.assets.some(a => ['WETH', 'ETH', 'cbETH', 'wstETH'].includes(a))
                );
                break;
            case 'bluechip':
                filtered = filtered.filter(v =>
                    v.assets.some(a => ['WBTC', 'cbBTC', 'WETH', 'ETH'].includes(a))
                );
                break;
        }

        return filtered.slice(0, limit);
    }

    /**
     * Get vault details by ID
     */
    getVault(vaultId) {
        return this.baseVaults.find(v => v.id === vaultId);
    }

    /**
     * Deposit into a Beefy vault
     */
    async deposit(vaultId, amount) {
        if (!this.signer) throw new Error('Wallet not connected');

        const vault = this.getVault(vaultId);
        if (!vault) throw new Error(`Vault ${vaultId} not found`);

        const vaultContract = new ethers.Contract(vault.vaultAddress, VAULT_ABI, this.signer);
        const tokenContract = new ethers.Contract(vault.tokenAddress, ERC20_ABI, this.signer);
        const userAddress = await this.signer.getAddress();

        // Check allowance
        const allowance = await tokenContract.allowance(userAddress, vault.vaultAddress);
        if (allowance.lt(amount)) {
            console.log('[Beefy] Approving token spend...');
            const approveTx = await tokenContract.approve(vault.vaultAddress, ethers.constants.MaxUint256);
            await approveTx.wait();
            console.log('[Beefy] Approval confirmed');
        }

        // Deposit
        console.log(`[Beefy] Depositing ${amount} into ${vault.name}...`);
        const tx = await vaultContract.deposit(amount);
        const receipt = await tx.wait();

        console.log(`[Beefy] Deposit confirmed: ${receipt.transactionHash}`);
        return receipt;
    }

    /**
     * Withdraw from a Beefy vault
     */
    async withdraw(vaultId, shares) {
        if (!this.signer) throw new Error('Wallet not connected');

        const vault = this.getVault(vaultId);
        if (!vault) throw new Error(`Vault ${vaultId} not found`);

        const vaultContract = new ethers.Contract(vault.vaultAddress, VAULT_ABI, this.signer);

        console.log(`[Beefy] Withdrawing ${shares} shares from ${vault.name}...`);
        const tx = await vaultContract.withdraw(shares);
        const receipt = await tx.wait();

        console.log(`[Beefy] Withdrawal confirmed: ${receipt.transactionHash}`);
        return receipt;
    }

    /**
     * Withdraw all from a vault
     */
    async withdrawAll(vaultId) {
        if (!this.signer) throw new Error('Wallet not connected');

        const vault = this.getVault(vaultId);
        if (!vault) throw new Error(`Vault ${vaultId} not found`);

        const vaultContract = new ethers.Contract(vault.vaultAddress, VAULT_ABI, this.signer);

        console.log(`[Beefy] Withdrawing all from ${vault.name}...`);
        const tx = await vaultContract.withdrawAll();
        const receipt = await tx.wait();

        console.log(`[Beefy] Full withdrawal confirmed: ${receipt.transactionHash}`);
        return receipt;
    }

    /**
     * Get user's vault balance
     */
    async getUserBalance(vaultId, userAddress) {
        const vault = this.getVault(vaultId);
        if (!vault) throw new Error(`Vault ${vaultId} not found`);

        const vaultContract = new ethers.Contract(vault.vaultAddress, VAULT_ABI, this.provider);

        const shares = await vaultContract.balanceOf(userAddress);
        const pricePerShare = await vaultContract.getPricePerFullShare();

        // Calculate underlying value
        const underlyingValue = shares.mul(pricePerShare).div(ethers.utils.parseEther('1'));

        return {
            shares: shares.toString(),
            underlyingValue: underlyingValue.toString(),
            pricePerShare: pricePerShare.toString()
        };
    }

    /**
     * Get all user positions across vaults
     */
    async getUserPositions(userAddress) {
        const positions = [];

        for (const vault of this.baseVaults.slice(0, 20)) { // Limit to avoid rate limits
            try {
                const balance = await this.getUserBalance(vault.id, userAddress);
                if (balance.shares !== '0') {
                    positions.push({
                        vault,
                        ...balance
                    });
                }
            } catch (e) {
                // Skip erroring vaults
            }
        }

        return positions;
    }
}

// Export singleton instance
const beefyService = new BeefyVaultService();
window.BeefyVaultService = beefyService;

export default beefyService;
