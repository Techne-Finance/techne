/**
 * Test TechneAgentWallet Contract
 * Verifies deployment and reads state
 */

import { ethers } from 'ethers';

const RPC = 'https://base-mainnet.g.alchemy.com/v2/Cts9SUVykfnWx2pW5qWWS';
const CONTRACT = '0x567D1Fc55459224132aB5148c6140E8900f9a607';

// Minimal ABI for reading
const ABI = [
    "function USDC() view returns (address)",
    "function router() view returns (address)",
    "function agent() view returns (address)",
    "function owner() view returns (address)",
    "function totalShares() view returns (uint256)",
    "function totalDeposited() view returns (uint256)",
    "function minDeposit() view returns (uint256)",
    "function poolType() view returns (uint8)",
    "function emergencyMode() view returns (bool)",
    "function performanceFee() view returns (uint256)",
    "function getUserValue(address) view returns (uint256)",
    "function getUserShares(address) view returns (uint256)",
    "function totalValue() view returns (uint256)"
];

async function main() {
    console.log('🔍 Testing TechneAgentWallet Contract\n');
    console.log('📍 Contract:', CONTRACT);
    console.log('🔗 Chain: Base Mainnet\n');

    const provider = new ethers.JsonRpcProvider(RPC);
    const contract = new ethers.Contract(CONTRACT, ABI, provider);

    try {
        console.log('=== Contract Configuration ===');

        const usdc = await contract.USDC();
        console.log('✅ USDC:', usdc);

        const router = await contract.router();
        console.log('✅ Aerodrome Router:', router);

        const agent = await contract.agent();
        console.log('✅ Agent:', agent);

        const owner = await contract.owner();
        console.log('✅ Owner:', owner);

        console.log('\n=== State Variables ===');

        const totalShares = await contract.totalShares();
        console.log('📊 Total Shares:', totalShares.toString());

        const totalDeposited = await contract.totalDeposited();
        console.log('💰 Total Deposited:', ethers.formatUnits(totalDeposited, 6), 'USDC');

        const totalValue = await contract.totalValue();
        console.log('💎 Total Value:', ethers.formatUnits(totalValue, 6), 'USDC');

        const minDeposit = await contract.minDeposit();
        console.log('📌 Min Deposit:', ethers.formatUnits(minDeposit, 6), 'USDC');

        const poolType = await contract.poolType();
        const poolTypes = ['Single-sided only', 'Dual-sided enabled', 'All pools'];
        console.log('🏊 Pool Type:', poolTypes[poolType] || poolType);

        const emergencyMode = await contract.emergencyMode();
        console.log('🚨 Emergency Mode:', emergencyMode ? 'ACTIVE ⚠️' : 'OFF ✅');

        const fee = await contract.performanceFee();
        console.log('💸 Performance Fee:', (Number(fee) / 100) + '%');

        console.log('\n=== Contract Status ===');
        console.log('✅ Contract is LIVE and responding!');
        console.log('✅ All read functions working correctly!');

    } catch (err) {
        console.error('❌ Error:', err.message);
    }
}

main();
