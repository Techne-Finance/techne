/**
 * Protocol & Chain Icon Utilities
 * Ported from frontend/protocol-icons.js — uses local /icons/ assets
 */

// Protocol name → icon key mappings for versioned/chain-suffixed names
const EXPLICIT_MAPPINGS: Record<string, string> = {
    'aerodrome slipstream': 'aerodrome',
    'aerodrome-slipstream': 'aerodrome',
    'aerodrome-slipstream-2': 'aerodrome',
    'aave v3': 'aave', 'aave-v3': 'aave',
    'compound v3': 'compound', 'compound-v3': 'compound',
    'uniswap v2': 'uniswap', 'uniswap v3': 'uniswap', 'uniswap v4': 'uniswap',
    'uniswap-v2': 'uniswap', 'uniswap-v3': 'uniswap', 'uniswap-v4': 'uniswap',
    'uniswap-v2-base': 'uniswap', 'uniswap-v3-base': 'uniswap', 'uniswap-v4-base': 'uniswap',
    'beefy-base': 'beefy', 'beefy-arbitrum': 'beefy', 'beefy-optimism': 'beefy',
    'morpho blue': 'morpho', 'morpho-blue': 'morpho',
    // New protocols — explicit name → icon file mappings
    'ether.fi': 'ether.fi',
    'etherfi': 'ether.fi',
    'extra finance': 'extra',
    'marginfi': 'marginfi',
    'margin-fi': 'marginfi',
    'memedollar': 'meme-dollar',
    'meme dollar': 'meme-dollar',
    'infinifi': 'infinifi',
    'infini-fi': 'infinifi',
}

// Icons in root /icons/ folder (originally bundled)
const ROOT_ICONS = new Set([
    'aave', 'aerodrome', 'balancer', 'beefy', 'compound', 'convex', 'curve',
    'gmx', 'lido', 'morpho', 'pendle', 'spark', 'uniswap', 'yearn',
])

// Icons in /icons/protocols/ subfolder (all 40 techne.finance protocols)
const PROTOCOLS_SUBFOLDER = new Set([
    'aave', 'aerodrome', 'aerodromebase', 'avantis', 'balancer', 'beefy',
    'compound', 'convex', 'curve', 'drift', 'eigenlayer', 'exactly', 'extra',
    'gmx', 'infinifi', 'jito', 'jupiter', 'kamino', 'lido', 'marginfi',
    'marinade', 'meme-dollar', 'merkl', 'meteora', 'moonwell', 'morpho',
    'orca', 'origin', 'peapods', 'pendle', 'radiant', 'raydium', 'sanctum',
    'seamless', 'solend', 'sonne', 'spark', 'uniswap', 'yearn', 'ether.fi',
    'lyra', 'synthetix',
])

// Protocol brand colors
export const PROTOCOL_COLORS: Record<string, string> = {
    aave: '#B6509E', compound: '#00D395', uniswap: '#FF007A', curve: '#FF0000',
    lido: '#00A3FF', convex: '#3A3A3A', yearn: '#006AE3', aerodrome: '#0052FF',
    velodrome: '#FF0420', gmx: '#1E90FF', morpho: '#2470FF', pendle: '#15BDB6',
    beefy: '#6DCB56', moonwell: '#5A67D8', balancer: '#1E1E1E', spark: '#EB8C00',
    radiant: '#00D9FF', jito: '#9945FF', jupiter: '#9945FF', meteora: '#7C3AED',
    kamino: '#06B6D4', raydium: '#58D5C7', sanctum: '#9945FF', drift: '#9945FF',
    'ether.fi': '#627EEA', synthetix: '#00D1FF', lyra: '#00D1FF', marginfi: '#9945FF',
    merkl: '#F59E0B', origin: '#0074F0', seamless: '#0052FF', solend: '#9945FF',
    exactly: '#627EEA', sonne: '#0052FF', avantis: '#0052FF',
}

// Chain data with icon URLs and colors
export const CHAINS: Record<string, { name: string; icon: string; color: string; chainId: number }> = {
    ethereum: { name: 'Ethereum', icon: '/icons/ethereum.png', color: '#627EEA', chainId: 1 },
    base: { name: 'Base', icon: '/icons/base.png', color: '#0052FF', chainId: 8453 },
    arbitrum: { name: 'Arbitrum', icon: '/icons/arbitrum.png', color: '#28A0F0', chainId: 42161 },
    optimism: { name: 'Optimism', icon: '/icons/optimism.png', color: '#FF0420', chainId: 10 },
    polygon: { name: 'Polygon', icon: '/icons/polygon.png', color: '#8247E5', chainId: 137 },
    solana: { name: 'Solana', icon: '/icons/solana.png', color: '#9945FF', chainId: 0 },
    bsc: { name: 'BSC', icon: '/icons/bsc.png', color: '#F3BA2F', chainId: 56 },
    avalanche: { name: 'Avalanche', icon: '/icons/avalanche.png', color: '#E84142', chainId: 43114 },
    blast: { name: 'Blast', icon: '/icons/blast.png', color: '#FCFC03', chainId: 81457 },
}

/**
 * Get icon URL for a protocol.
 * Checks: explicit mappings → /icons/protocols/ subfolder → root /icons/ → fallback to /icons/protocols/
 */
export function getProtocolIconUrl(protocolName?: string): string {
    if (!protocolName) return '/icons/default.svg'

    const lower = protocolName.toLowerCase().trim()

    // Check explicit mappings first
    if (EXPLICIT_MAPPINGS[lower]) {
        const key = EXPLICIT_MAPPINGS[lower]
        if (PROTOCOLS_SUBFOLDER.has(key)) return `/icons/protocols/${key}.png`
        if (ROOT_ICONS.has(key)) return `/icons/${key}.png`
        return `/icons/protocols/${key}.png`
    }

    // Normalize: strip chain suffix, version, common words
    const key = lower
        .replace(/-(?:base|arbitrum|optimism|polygon|ethereum|mainnet)$/gi, '')
        .replace(/\s+slipstream/gi, '')
        .replace(/\s+finance/gi, '')
        .replace(/\s+protocol/gi, '')
        .replace(/\s+v[234]/gi, '')
        .replace(/-v[234]/gi, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '')
        .trim()

    // Prefer protocols subfolder (has all 40 protocol icons)
    if (PROTOCOLS_SUBFOLDER.has(key)) return `/icons/protocols/${key}.png`
    // Fall back to root icons
    if (ROOT_ICONS.has(key)) return `/icons/${key}.png`
    // Default: try protocols subfolder
    return `/icons/protocols/${key}.png`
}

/**
 * Get icon URL for a chain (e.g., "Base" → "/icons/base.png")
 */
export function getChainIconUrl(chainName?: string): string {
    if (!chainName) return ''
    const chain = CHAINS[chainName.toLowerCase()]
    if (chain) return chain.icon
    return `/icons/${chainName.toLowerCase()}.png`
}

/**
 * Get chain brand color
 */
export function getChainColor(chainName?: string): string {
    if (!chainName) return '#666'
    return CHAINS[chainName.toLowerCase()]?.color || '#666'
}

/**
 * Get protocol brand color
 */
export function getProtocolColor(protocolName?: string): string {
    if (!protocolName) return '#666'
    const lower = protocolName.toLowerCase().trim()
    const key = EXPLICIT_MAPPINGS[lower] || lower
        .replace(/-(?:base|arbitrum|optimism|polygon|ethereum|mainnet)$/gi, '')
        .replace(/-v[234]/gi, '')
        .replace(/\s+/g, '-')
    return PROTOCOL_COLORS[key] || '#D4AF37'
}
