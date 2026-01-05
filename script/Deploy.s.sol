// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../contracts/TechneAgentWallet.sol";

/**
 * @title Deploy TechneAgentWallet to Base Mainnet
 * @dev Run with: forge script script/Deploy.s.sol --rpc-url base --broadcast --verify
 */
contract DeployScript is Script {
    // Base Mainnet addresses
    address constant USDC = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    address constant AERODROME_ROUTER = 0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43;
    address constant AERODROME_FACTORY = 0x420DD381b31aEf6683db6B902084cB0FFECe40Da;
    
    // Agent/Owner address (Techne treasury - receives fees, can trigger rebalance)
    address constant AGENT = 0x542c3b6cb5c93c4e4b4c20de48ee87dd79efdfec;

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        
        vm.startBroadcast(deployerPrivateKey);
        
        TechneAgentWallet wallet = new TechneAgentWallet(
            USDC,
            AERODROME_ROUTER,
            AERODROME_FACTORY,
            AGENT
        );
        
        console.log("=================================");
        console.log("TechneAgentWallet deployed!");
        console.log("=================================");
        console.log("Contract:", address(wallet));
        console.log("Owner:", wallet.owner());
        console.log("Agent:", wallet.agent());
        console.log("USDC:", address(wallet.USDC()));
        console.log("Router:", address(wallet.router()));
        console.log("=================================");
        
        vm.stopBroadcast();
    }
}
