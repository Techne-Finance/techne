// Type declaration for ethers - used via dynamic import() in DepositModal, WithdrawModal, PremiumPage
declare module 'ethers' {
    export const ethers: any
    export function parseEther(value: string): bigint
    export function formatEther(value: bigint): string
    export function parseUnits(value: string, decimals: number): bigint
    export function formatUnits(value: bigint, decimals: number): string
}
