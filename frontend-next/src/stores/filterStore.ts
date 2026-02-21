import { create } from 'zustand'

interface FilterValues {
    chain: string
    riskLevel: string
    assetType: string
    poolType: string
    stablecoin: string
    protocols: string[]
    tvlRange: [number, number]
    apyRange: [number, number]
}

interface FilterState extends FilterValues {
    appliedFilters: FilterValues
    setChain: (chain: string) => void
    setRiskLevel: (level: string) => void
    setAssetType: (type: string) => void
    setPoolType: (type: string) => void
    setStablecoin: (stable: string) => void
    setProtocols: (protocols: string[]) => void
    setTvlRange: (range: [number, number]) => void
    setApyRange: (range: [number, number]) => void
    applyFilters: () => void
    resetFilters: () => void
}

const defaultFilterValues: FilterValues = {
    chain: 'all',
    riskLevel: 'all',
    assetType: 'all',
    poolType: 'all',
    stablecoin: 'all',
    protocols: [] as string[],
    tvlRange: [0, 9] as [number, number],
    apyRange: [0, 100] as [number, number],
}

export const useFilterStore = create<FilterState>((set, get) => ({
    ...defaultFilterValues,
    appliedFilters: { ...defaultFilterValues },
    setChain: (chain) => set({ chain }),
    setRiskLevel: (riskLevel) => set({ riskLevel }),
    setAssetType: (assetType) => set({ assetType }),
    setPoolType: (poolType) => set({ poolType }),
    setStablecoin: (stablecoin) => set({ stablecoin }),
    setProtocols: (protocols) => set({ protocols }),
    setTvlRange: (tvlRange) => set({ tvlRange }),
    setApyRange: (apyRange) => set({ apyRange }),
    applyFilters: () => {
        const s = get()
        set({
            appliedFilters: {
                chain: s.chain,
                riskLevel: s.riskLevel,
                assetType: s.assetType,
                poolType: s.poolType,
                stablecoin: s.stablecoin,
                protocols: s.protocols,
                tvlRange: s.tvlRange,
                apyRange: s.apyRange,
            },
        })
    },
    resetFilters: () => set({ ...defaultFilterValues, appliedFilters: { ...defaultFilterValues } }),
}))
