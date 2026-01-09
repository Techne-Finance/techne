/**
 * TechneIcons - Unified SVG Icon System
 * Matches Verify section and modal gold theme
 */

const TechneIcons = {
    // Status Icons
    success: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="8" cy="8" r="7" stroke="#22c55e" stroke-width="1.5" fill="rgba(34, 197, 94, 0.15)"/>
        <path d="M5 8L7 10L11 6" stroke="#22c55e" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,

    error: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="8" cy="8" r="7" stroke="#ef4444" stroke-width="1.5" fill="rgba(239, 68, 68, 0.15)"/>
        <path d="M5.5 5.5L10.5 10.5M10.5 5.5L5.5 10.5" stroke="#ef4444" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`,

    warning: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 1L15 14H1L8 1Z" stroke="#eab308" stroke-width="1.5" fill="rgba(234, 179, 8, 0.15)" stroke-linejoin="round"/>
        <path d="M8 6V9M8 11.5V12" stroke="#eab308" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`,

    info: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="8" cy="8" r="7" stroke="#3b82f6" stroke-width="1.5" fill="rgba(59, 130, 246, 0.15)"/>
        <path d="M8 7V11M8 5V5.5" stroke="#3b82f6" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`,

    // Action Icons (Gold theme)
    robot: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="6" width="14" height="11" rx="2" stroke="#d4a853" stroke-width="1.5" fill="rgba(212, 168, 83, 0.1)"/>
        <circle cx="7" cy="10" r="1.5" fill="#d4a853"/>
        <circle cx="13" cy="10" r="1.5" fill="#d4a853"/>
        <path d="M7 14H13" stroke="#d4a853" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M10 3V6" stroke="#d4a853" stroke-width="1.5" stroke-linecap="round"/>
        <circle cx="10" cy="2" r="1" fill="#d4a853"/>
    </svg>`,

    lock: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="7" width="10" height="7" rx="1.5" stroke="#d4a853" stroke-width="1.5" fill="rgba(212, 168, 83, 0.1)"/>
        <path d="M5 7V5C5 3.34315 6.34315 2 8 2C9.65685 2 11 3.34315 11 5V7" stroke="#d4a853" stroke-width="1.5" stroke-linecap="round"/>
        <circle cx="8" cy="10.5" r="1" fill="#d4a853"/>
    </svg>`,

    coin: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="8" cy="8" r="6.5" stroke="#d4a853" stroke-width="1.5" fill="rgba(212, 168, 83, 0.1)"/>
        <path d="M8 4V12M6 6H10M6 10H10" stroke="#d4a853" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`,

    bolt: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M9 1L3 9H8L7 15L13 7H8L9 1Z" stroke="#d4a853" stroke-width="1.5" fill="rgba(212, 168, 83, 0.15)" stroke-linejoin="round"/>
    </svg>`,

    rocket: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M10 6C10 6 12 4 12 2C12 2 10 2 8 4C6 2 4 2 4 2C4 4 6 6 6 6" stroke="#d4a853" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M6 6L3 14L8 11L13 14L10 6" stroke="#d4a853" stroke-width="1.5" fill="rgba(212, 168, 83, 0.15)" stroke-linejoin="round"/>
    </svg>`,

    chart: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M2 14V8L6 5L10 8L14 2" stroke="#d4a853" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M2 14H14" stroke="#d4a853" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`,

    wallet: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="1.5" y="4" width="13" height="10" rx="1.5" stroke="#d4a853" stroke-width="1.5" fill="rgba(212, 168, 83, 0.1)"/>
        <path d="M1.5 7H14.5" stroke="#d4a853" stroke-width="1.5"/>
        <circle cx="11.5" cy="10" r="1" fill="#d4a853"/>
        <path d="M3 4V3C3 2.44772 3.44772 2 4 2H12C12.5523 2 13 2.44772 13 3V4" stroke="#d4a853" stroke-width="1.5"/>
    </svg>`,

    shield: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 1L2 3.5V7C2 11 5 14 8 15C11 14 14 11 14 7V3.5L8 1Z" stroke="#d4a853" stroke-width="1.5" fill="rgba(212, 168, 83, 0.1)" stroke-linejoin="round"/>
        <path d="M6 8L7.5 9.5L10 6.5" stroke="#d4a853" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,

    settings: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="8" cy="8" r="2.5" stroke="#d4a853" stroke-width="1.5"/>
        <path d="M8 1V3M8 13V15M15 8H13M3 8H1M13.5 2.5L11.5 4.5M4.5 11.5L2.5 13.5M13.5 13.5L11.5 11.5M4.5 4.5L2.5 2.5" stroke="#d4a853" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`,

    copy: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="5" y="5" width="9" height="9" rx="1.5" stroke="#d4a853" stroke-width="1.5" fill="rgba(212, 168, 83, 0.1)"/>
        <path d="M11 5V3C11 2.44772 10.5523 2 10 2H3C2.44772 2 2 2.44772 2 3V10C2 10.5523 2.44772 11 3 11H5" stroke="#d4a853" stroke-width="1.5"/>
    </svg>`,

    withdraw: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 10V2M8 2L5 5M8 2L11 5" stroke="#d4a853" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M2 11V13C2 13.5523 2.44772 14 3 14H13C13.5523 14 14 13.5523 14 13V11" stroke="#d4a853" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`,

    deposit: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 2V10M8 10L5 7M8 10L11 7" stroke="#d4a853" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M2 11V13C2 13.5523 2.44772 14 3 14H13C13.5523 14 14 13.5523 14 13V11" stroke="#d4a853" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`,

    fire: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 1C8 1 4 5 4 9C4 11.2091 5.79086 14 8 14C10.2091 14 12 11.2091 12 9C12 5 8 1 8 1Z" stroke="#d4a853" stroke-width="1.5" fill="rgba(212, 168, 83, 0.15)"/>
        <path d="M8 8C8 8 6.5 9.5 6.5 11C6.5 12 7.17 13 8 13C8.83 13 9.5 12 9.5 11C9.5 9.5 8 8 8 8Z" stroke="#d4a853" stroke-width="1.5" fill="rgba(212, 168, 83, 0.25)"/>
    </svg>`,

    emergency: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="8" cy="8" r="7" stroke="#ef4444" stroke-width="1.5" fill="rgba(239, 68, 68, 0.15)"/>
        <path d="M8 4V9" stroke="#ef4444" stroke-width="2" stroke-linecap="round"/>
        <circle cx="8" cy="11.5" r="1" fill="#ef4444"/>
    </svg>`,

    twofa: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="4" width="12" height="9" rx="1.5" stroke="#d4a853" stroke-width="1.5" fill="rgba(212, 168, 83, 0.1)"/>
        <path d="M5 8H6M8 8H8.5M10 8H11" stroke="#d4a853" stroke-width="2" stroke-linecap="round"/>
        <path d="M8 1L8 4" stroke="#d4a853" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`,

    // Wallet provider icons
    metamask: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M17.5 3L11 7.5L12 5L17.5 3Z" fill="#E2761B" stroke="#E2761B"/>
        <path d="M2.5 3L8.93 7.55L8 5L2.5 3Z" fill="#E4761B" stroke="#E4761B"/>
        <path d="M15 13.5L13.5 16L17 17L18 13.6L15 13.5Z" fill="#E4761B" stroke="#E4761B"/>
        <path d="M2 13.6L3 17L6.5 16L5 13.5L2 13.6Z" fill="#E4761B" stroke="#E4761B"/>
        <path d="M6.3 9.3L5.3 10.8L8.8 11L8.7 7.3L6.3 9.3Z" fill="#E4761B" stroke="#E4761B"/>
        <path d="M13.7 9.3L11.25 7.2L11.2 11L14.7 10.8L13.7 9.3Z" fill="#E4761B" stroke="#E4761B"/>
        <path d="M6.5 16L8.6 15L6.8 13.6L6.5 16Z" fill="#E4761B" stroke="#E4761B"/>
        <path d="M11.4 15L13.5 16L13.2 13.6L11.4 15Z" fill="#E4761B" stroke="#E4761B"/>
    </svg>`,

    coinbase: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="10" cy="10" r="9" fill="#0052FF"/>
        <circle cx="10" cy="10" r="4" fill="white"/>
    </svg>`,

    rabby: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="10" cy="10" r="9" fill="#7C3AED"/>
        <ellipse cx="7" cy="8" rx="2" ry="3" fill="white"/>
        <ellipse cx="13" cy="8" rx="2" ry="3" fill="white"/>
        <ellipse cx="10" cy="14" rx="3" ry="2" fill="white"/>
    </svg>`,

    // Navigation icons
    home: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M2 7L9 2L16 7V15C16 15.5523 15.5523 16 15 16H3C2.44772 16 2 15.5523 2 15V7Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
        <path d="M7 16V10H11V16" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,

    verify: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="9" cy="9" r="7" stroke="currentColor" stroke-width="1.5"/>
        <path d="M6 9L8 11L12 7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,

    build: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M10 2L8 4L10 6L12 4L10 2Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
        <path d="M4 8L2 10L4 12L6 10L4 8Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
        <path d="M12 10L10 12L12 14L14 12L12 10Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
        <path d="M6 10L10 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M10 12L12 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`,

    portfolio: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="4" width="14" height="12" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
        <path d="M6 4V2.5C6 2.22386 6.22386 2 6.5 2H11.5C11.7761 2 12 2.22386 12 2.5V4" stroke="currentColor" stroke-width="1.5"/>
        <path d="M2 9H16" stroke="currentColor" stroke-width="1.5"/>
    </svg>`,

    history: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="9" cy="9" r="7" stroke="currentColor" stroke-width="1.5"/>
        <path d="M9 5V9L12 11" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,

    bell: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M14 7C14 4.23858 11.7614 2 9 2C6.23858 2 4 4.23858 4 7V11L2 13V14H16V13L14 11V7Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
        <path d="M7.5 14C7.5 15.1046 8.17157 16 9 16C9.82843 16 10.5 15.1046 10.5 14" stroke="currentColor" stroke-width="1.5"/>
    </svg>`,

    // Pool icons
    trendUp: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M2 10L5.5 6.5L8 9L12 4" stroke="#22c55e" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M9 4H12V7" stroke="#22c55e" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,

    trendDown: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M2 4L5.5 7.5L8 5L12 10" stroke="#ef4444" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M9 10H12V7" stroke="#ef4444" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,

    // Pool Category Icons (for badges)
    bank: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 1L1 5V7H15V5L8 1Z" stroke="#d4a853" stroke-width="1.3" fill="rgba(212,168,83,0.1)" stroke-linejoin="round"/>
        <path d="M2 7V14H14V7" stroke="#d4a853" stroke-width="1.3"/>
        <path d="M6 14V10H10V14" stroke="#d4a853" stroke-width="1.3"/>
    </svg>`,

    vault: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="3" width="12" height="11" rx="1" stroke="#d4a853" stroke-width="1.3" fill="rgba(212,168,83,0.1)"/>
        <circle cx="8" cy="8.5" r="2.5" stroke="#d4a853" stroke-width="1.3"/>
        <path d="M8 7V10M6.5 8.5H9.5" stroke="#d4a853" stroke-width="1" stroke-linecap="round"/>
        <circle cx="12" cy="8.5" r="0.8" fill="#d4a853"/>
    </svg>`,

    diamond: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 2L3 6L8 14L13 6L8 2Z" stroke="#d4a853" stroke-width="1.3" fill="rgba(212,168,83,0.15)" stroke-linejoin="round"/>
        <path d="M3 6H13" stroke="#d4a853" stroke-width="1.3"/>
    </svg>`,

    amm: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M2 8C2 4.5 5 2 8 2C11 2 13.5 4.5 14 8M14 8L11 5M14 8L11 11" stroke="#d4a853" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M14 8C14 11.5 11 14 8 14C5 14 2.5 11.5 2 8M2 8L5 11M2 8L5 5" stroke="#d4a853" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,

    rewards: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="7" width="12" height="7" rx="1" stroke="#d4a853" stroke-width="1.3" fill="rgba(212,168,83,0.1)"/>
        <path d="M8 3V7M5 3C5 3 5 6 8 6C11 6 11 3 11 3" stroke="#d4a853" stroke-width="1.3" stroke-linecap="round"/>
    </svg>`,

    lp: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="6" cy="8" r="4" stroke="#d4a853" stroke-width="1.3" fill="rgba(212,168,83,0.1)"/>
        <circle cx="10" cy="8" r="4" stroke="#d4a853" stroke-width="1.3" fill="rgba(212,168,83,0.15)"/>
    </svg>`,

    defi: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="8" cy="8" r="6" stroke="#d4a853" stroke-width="1.3" fill="rgba(212,168,83,0.1)"/>
        <path d="M5.5 8H10.5M8 5.5V10.5" stroke="#d4a853" stroke-width="1.3" stroke-linecap="round"/>
    </svg>`,

    // Utility function to get icon with custom size
    get(name, size = 16) {
        const icon = this[name];
        if (!icon) return '';
        return icon.replace(/width="\d+"/, `width="${size}"`).replace(/height="\d+"/, `height="${size}"`);
    },

    // Wrapper with optional class
    wrap(name, className = '', size = 16) {
        return `<span class="techne-icon ${className}">${this.get(name, size)}</span>`;
    }
};

// Export for use
if (typeof window !== 'undefined') {
    window.TechneIcons = TechneIcons;
}
