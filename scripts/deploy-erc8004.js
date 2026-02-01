/**
 * Deploy ERC-8004 Contracts to Base Mainnet
 * 
 * Run with: npx hardhat run scripts/deploy-erc8004.js --network base
 * 
 * Deploys:
 * 1. AgentIdentityRegistry (ERC-721)
 * 2. AgentReputationRegistry
 * 3. TechneAgentFactoryV4 (with identity minting)
 */

const hre = require("hardhat");

// Base Mainnet addresses
const TECHNE_IMPLEMENTATION_V3 = "0xde70b3300f5fe05F4D698FEFe231cf8d874a6575";
const TECHNE_SESSION_KEY = "0xa30A689ec0F9D717C5bA1098455B031b868B720f";

async function main() {
    const [deployer] = await hre.ethers.getSigners();
    console.log("Deploying ERC-8004 contracts with account:", deployer.address);
    console.log("Account balance:", (await hre.ethers.provider.getBalance(deployer.address)).toString());
    console.log("\n========================================");

    // 1. Deploy AgentIdentityRegistry
    console.log("\n📌 Deploying AgentIdentityRegistry...");
    const IdentityRegistry = await hre.ethers.getContractFactory("AgentIdentityRegistry");
    const identityRegistry = await IdentityRegistry.deploy();
    await identityRegistry.waitForDeployment();
    const identityAddress = await identityRegistry.getAddress();
    console.log("✅ AgentIdentityRegistry deployed to:", identityAddress);

    // 2. Deploy AgentReputationRegistry
    console.log("\n📌 Deploying AgentReputationRegistry...");
    const ReputationRegistry = await hre.ethers.getContractFactory("AgentReputationRegistry");
    const reputationRegistry = await ReputationRegistry.deploy(identityAddress);
    await reputationRegistry.waitForDeployment();
    const reputationAddress = await reputationRegistry.getAddress();
    console.log("✅ AgentReputationRegistry deployed to:", reputationAddress);

    // 3. Deploy TechneAgentFactoryV4
    console.log("\n📌 Deploying TechneAgentFactoryV4...");
    const FactoryV4 = await hre.ethers.getContractFactory("TechneAgentFactoryV4");
    const factoryV4 = await FactoryV4.deploy(
        TECHNE_IMPLEMENTATION_V3,
        TECHNE_SESSION_KEY,
        identityAddress
    );
    await factoryV4.waitForDeployment();
    const factoryAddress = await factoryV4.getAddress();
    console.log("✅ TechneAgentFactoryV4 deployed to:", factoryAddress);

    // 4. Configure contracts
    console.log("\n🔧 Configuring contracts...");

    // Set reputation registry on identity
    let tx = await identityRegistry.setReputationRegistry(reputationAddress);
    await tx.wait();
    console.log("  ✅ Identity → Reputation registry linked");

    // Authorize factory as identity minter
    tx = await identityRegistry.authorizeMinter(factoryAddress);
    await tx.wait();
    console.log("  ✅ Factory authorized as identity minter");

    // Set reputation registry on factory
    tx = await factoryV4.setReputationRegistry(reputationAddress);
    await tx.wait();
    console.log("  ✅ Factory → Reputation registry linked");

    // Authorize deployer as reporter (for testing)
    tx = await reputationRegistry.authorizeReporter(deployer.address);
    await tx.wait();
    console.log("  ✅ Deployer authorized as reputation reporter");

    // Summary
    console.log("\n========================================");
    console.log("🎉 ERC-8004 DEPLOYMENT COMPLETE!");
    console.log("========================================");
    console.log("\nDeployed Contracts:");
    console.log("  AgentIdentityRegistry:", identityAddress);
    console.log("  AgentReputationRegistry:", reputationAddress);
    console.log("  TechneAgentFactoryV4:", factoryAddress);
    console.log("\nAdd to .env:");
    console.log(`  IDENTITY_REGISTRY_ADDRESS=${identityAddress}`);
    console.log(`  REPUTATION_REGISTRY_ADDRESS=${reputationAddress}`);
    console.log(`  TECHNE_FACTORY_V4_ADDRESS=${factoryAddress}`);
    console.log("========================================\n");

    // Verify contracts (optional)
    if (process.env.BASESCAN_API_KEY) {
        console.log("\n🔍 Verifying contracts on BaseScan...");
        try {
            await hre.run("verify:verify", {
                address: identityAddress,
                constructorArguments: []
            });
            await hre.run("verify:verify", {
                address: reputationAddress,
                constructorArguments: [identityAddress]
            });
            await hre.run("verify:verify", {
                address: factoryAddress,
                constructorArguments: [TECHNE_IMPLEMENTATION_V3, TECHNE_SESSION_KEY, identityAddress]
            });
            console.log("✅ All contracts verified!");
        } catch (e) {
            console.log("⚠️ Verification failed:", e.message);
        }
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
