const { ethers } = require("hardhat");

/**
 * Deploy TechneAgentFactory v2 with 1-agent-1-wallet support
 * 
 * This script deploys:
 * 1. TechneAgentAccount implementation (singleton)
 * 2. TechneAgentFactory with salt support
 */
async function main() {
    console.log("=== Deploying TechneAgentFactory v2 (1 Agent = 1 Wallet) ===\n");

    const [deployer] = await ethers.getSigners();
    console.log("Deployer:", deployer.address);

    const balance = await ethers.provider.getBalance(deployer.address);
    console.log("Balance:", ethers.formatEther(balance), "ETH\n");

    // Step 1: Deploy Implementation (TechneAgentAccount)
    console.log("1. Deploying TechneAgentAccount implementation...");
    const Account = await ethers.getContractFactory("TechneAgentAccount");
    const implementation = await Account.deploy({
        gasLimit: 3000000
    });

    const implTx = implementation.deploymentTransaction();
    await implTx.wait(2);

    const implAddress = await implementation.getAddress();
    console.log("   Implementation deployed to:", implAddress);

    // Step 2: Deploy Factory
    console.log("\n2. Deploying TechneAgentFactory...");

    // Default session key = deployer (Techne backend)
    const defaultSessionKey = deployer.address;
    console.log("   Default Session Key:", defaultSessionKey);

    const Factory = await ethers.getContractFactory("TechneAgentFactory");
    const factory = await Factory.deploy(
        implAddress,       // implementation address
        defaultSessionKey, // Techne backend as default session key
        { gasLimit: 2000000 }
    );

    const factoryTx = factory.deploymentTransaction();
    await factoryTx.wait(2);

    const factoryAddress = await factory.getAddress();
    console.log("   Factory deployed to:", factoryAddress);

    // Verify bytecode
    const factoryCode = await ethers.provider.getCode(factoryAddress);
    const implCode = await ethers.provider.getCode(implAddress);
    console.log("\n3. Verification:");
    console.log("   Factory bytecode length:", factoryCode.length);
    console.log("   Implementation bytecode length:", implCode.length);

    // Test: get counterfactual address
    console.log("\n4. Testing getAddress...");
    const testOwner = "0xbA9D6947C0aD6eA2AaA99507355cf83B4D098058";
    const testSalt = 0; // Default agent
    const predictedAddress = await factory.getAddress(testOwner, testSalt);
    console.log(`   Predicted address for ${testOwner.slice(0, 10)}... (salt=0):`, predictedAddress);

    // Summary
    console.log("\n========================================");
    console.log("=== DEPLOYMENT COMPLETE ===");
    console.log("========================================");
    console.log("\nFactory Address:", factoryAddress);
    console.log("Implementation:", implAddress);
    console.log("Default Session Key:", defaultSessionKey);
    console.log("\n.env update:");
    console.log(`TECHNE_FACTORY_ADDRESS=${factoryAddress}`);
    console.log(`TECHNE_IMPLEMENTATION_ADDRESS=${implAddress}`);
    console.log("\n========================================");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
