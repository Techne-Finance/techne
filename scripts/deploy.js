const hre = require("hardhat");

async function main() {
    console.log("🚀 Deploying TechneAgentWallet to Base Mainnet...\n");

    // Base Mainnet addresses
    const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
    const AERODROME_ROUTER = "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43";
    const AERODROME_FACTORY = "0x420DD381b31aEf6683db6B902084cB0FFECe40Da";
    const AGENT = "0x542c3b6cb5c93c4e4b4c20de48ee87dd79efdfec";

    const [deployer] = await hre.ethers.getSigners();

    console.log("📍 Deployer:", deployer.address);

    const balance = await hre.ethers.provider.getBalance(deployer.address);
    console.log("💰 Balance:", hre.ethers.formatEther(balance), "ETH\n");

    console.log("📝 Constructor args:");
    console.log("   USDC:", USDC);
    console.log("   Router:", AERODROME_ROUTER);
    console.log("   Factory:", AERODROME_FACTORY);
    console.log("   Agent:", AGENT);

    // Deploy
    console.log("\n⏳ Deploying...");

    const TechneAgentWallet = await hre.ethers.getContractFactory("TechneAgentWallet");
    const wallet = await TechneAgentWallet.deploy(
        USDC,
        AERODROME_ROUTER,
        AERODROME_FACTORY,
        AGENT
    );

    await wallet.waitForDeployment();

    const address = await wallet.getAddress();

    console.log("\n================================");
    console.log("✅ DEPLOYMENT SUCCESSFUL!");
    console.log("================================");
    console.log("📍 Contract Address:", address);
    console.log("🔗 Basescan: https://basescan.org/address/" + address);
    console.log("================================\n");

    // Verify on Basescan
    console.log("⏳ Waiting 30s before verification...");
    await new Promise(r => setTimeout(r, 30000));

    console.log("📝 Verifying on Basescan...");
    try {
        await hre.run("verify:verify", {
            address: address,
            constructorArguments: [USDC, AERODROME_ROUTER, AERODROME_FACTORY, AGENT],
        });
        console.log("✅ Contract verified on Basescan!");
    } catch (e) {
        console.log("⚠️ Verification failed:", e.message);
    }
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
