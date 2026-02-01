// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/proxy/Clones.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title TechneAgentFactoryV4
 * @notice Factory for deploying TechneAgentAccount smart accounts WITH ERC-8004 identity
 * @dev Upgrades V3 Factory with Identity Registry integration
 * 
 * NEW in V4 (ERC-8004 Compliance):
 * - Auto-mints Agent NFT on account creation
 * - Links Smart Account to Identity Registry
 * - Records agent type and model hash
 * - Full ERC-8004 compliance for trustless agents
 */
contract TechneAgentFactoryV4 is Ownable {
    using Clones for address;

    // ============ State ============
    address public immutable implementation;
    
    // ERC-8004 Registries
    address public identityRegistry;
    address public reputationRegistry;
    
    // Owner -> AgentSalt -> Smart Account (1 agent = 1 wallet)
    mapping(address => mapping(uint256 => address)) public accounts;
    
    // Owner -> All their agent accounts
    mapping(address => address[]) public ownerAccounts;
    
    // All deployed accounts (for iteration)
    address[] public allAccounts;
    
    // Default session key to add (Techne backend)
    address public defaultSessionKey;
    uint48 public defaultSessionKeyValidity = 365 days;
    uint256 public defaultDailyLimitUSD = 1_000_000 * 1e8; // $1M/day
    
    // Default protocols to whitelist
    address[] public defaultProtocols;
    bytes4[][] public defaultSelectors;
    
    // Default agent type for identity
    string public defaultAgentType = "yield_optimizer";

    // ============ Events ============
    event AccountCreated(
        address indexed owner,
        address indexed account,
        uint256 indexed agentSalt,
        uint256 identityTokenId  // NEW: ERC-8004 token ID
    );
    event DefaultSessionKeySet(address indexed key, uint48 validity, uint256 dailyLimit);
    event DefaultProtocolsUpdated(uint256 count);
    event IdentityRegistrySet(address indexed registry);
    event ReputationRegistrySet(address indexed registry);

    // ============ Errors ============
    error InvalidOwner();
    error ZeroAddress();
    error IdentityMintFailed();

    // ============ Constructor ============
    constructor(
        address _implementation,
        address _defaultSessionKey,
        address _identityRegistry
    ) Ownable(msg.sender) {
        if (_implementation == address(0)) revert ZeroAddress();
        implementation = _implementation;
        defaultSessionKey = _defaultSessionKey;
        identityRegistry = _identityRegistry;
    }

    // ============ Factory Functions ============

    /**
     * @notice Create a new smart account for a specific agent WITH ERC-8004 identity
     * @param owner The owner of the new account (user's EOA)
     * @param agentSalt Unique salt per agent (e.g., keccak256(agentId))
     * @param modelHash Hash of the agent's config/model for identity
     * @param agentType Type of agent (e.g., "yield_optimizer", "trading_bot")
     * @return account The deployed smart account address
     * @return tokenId The ERC-8004 identity NFT token ID
     */
    function createAccountWithIdentity(
        address owner, 
        uint256 agentSalt,
        bytes32 modelHash,
        string calldata agentType
    ) external returns (address account, uint256 tokenId) {
        if (owner == address(0)) revert InvalidOwner();
        
        // Check if this specific agent already has account
        if (accounts[owner][agentSalt] != address(0)) {
            account = accounts[owner][agentSalt];
            // Get existing token ID
            if (identityRegistry != address(0)) {
                tokenId = IAgentIdentityRegistry(identityRegistry).getTokenId(account);
            }
            return (account, tokenId);
        }

        // Deploy deterministic clone with combined salt
        bytes32 salt = keccak256(abi.encodePacked(owner, agentSalt));
        account = implementation.cloneDeterministic(salt);

        // Initialize the account
        ITechneAgentAccount(account).initialize(owner);

        // Add default session key if configured
        if (defaultSessionKey != address(0)) {
            ITechneAgentAccount(account).addSessionKey(
                defaultSessionKey,
                uint48(block.timestamp) + defaultSessionKeyValidity,
                defaultDailyLimitUSD
            );
        }

        // Whitelist default protocols
        if (defaultProtocols.length > 0) {
            ITechneAgentAccount(account).batchWhitelist(
                defaultProtocols,
                defaultSelectors
            );
        }

        // Register account
        accounts[owner][agentSalt] = account;
        ownerAccounts[owner].push(account);
        allAccounts.push(account);

        // ============ ERC-8004: Mint Identity NFT ============
        if (identityRegistry != address(0)) {
            try IAgentIdentityRegistry(identityRegistry).registerAgent(
                account,
                owner,
                modelHash,
                agentType
            ) returns (uint256 _tokenId) {
                tokenId = _tokenId;
            } catch {
                // Don't revert - account is still usable without identity
                tokenId = 0;
            }
        }

        emit AccountCreated(owner, account, agentSalt, tokenId);
    }

    /**
     * @notice Create account with default parameters (backward compatible)
     * @param owner The owner of the new account
     * @param agentSalt The agent's unique salt
     * @return account The deployed smart account address
     */
    function createAccount(address owner, uint256 agentSalt) external returns (address account) {
        // Use default model hash and agent type
        bytes32 modelHash = keccak256(abi.encodePacked(owner, agentSalt, block.timestamp));
        (account, ) = this.createAccountWithIdentity(owner, agentSalt, modelHash, defaultAgentType);
    }

    /**
     * @notice Legacy: Create account with default salt (0)
     * @param owner The owner of the new account
     */
    function createAccount(address owner) external returns (address) {
        return this.createAccount(owner, 0);
    }

    /**
     * @notice Get deterministic address for owner + agent (without deploying)
     * @param owner The owner address
     * @param agentSalt The agent's unique salt
     */
    function getAddress(address owner, uint256 agentSalt) external view returns (address) {
        bytes32 salt = keccak256(abi.encodePacked(owner, agentSalt));
        return implementation.predictDeterministicAddress(salt, address(this));
    }

    /**
     * @notice Legacy: Get address with default salt
     */
    function getAddress(address owner) external view returns (address) {
        return this.getAddress(owner, 0);
    }

    /**
     * @notice Check if specific agent account exists
     */
    function hasAccount(address owner, uint256 agentSalt) external view returns (bool) {
        return accounts[owner][agentSalt] != address(0);
    }

    /**
     * @notice Get all accounts for an owner
     */
    function getAccountsForOwner(address owner) external view returns (address[] memory) {
        return ownerAccounts[owner];
    }

    /**
     * @notice Get account count for an owner
     */
    function getAccountCount(address owner) external view returns (uint256) {
        return ownerAccounts[owner].length;
    }

    /**
     * @notice Get total number of accounts created
     */
    function totalAccounts() external view returns (uint256) {
        return allAccounts.length;
    }

    // ============ Admin Functions ============

    /**
     * @notice Set ERC-8004 Identity Registry
     */
    function setIdentityRegistry(address _registry) external onlyOwner {
        identityRegistry = _registry;
        emit IdentityRegistrySet(_registry);
    }

    /**
     * @notice Set ERC-8004 Reputation Registry
     */
    function setReputationRegistry(address _registry) external onlyOwner {
        reputationRegistry = _registry;
        emit ReputationRegistrySet(_registry);
    }

    /**
     * @notice Set default agent type for auto-created identities
     */
    function setDefaultAgentType(string calldata _type) external onlyOwner {
        defaultAgentType = _type;
    }

    /**
     * @notice Set default session key for new accounts
     */
    function setDefaultSessionKey(
        address key,
        uint48 validity,
        uint256 dailyLimitUSD
    ) external onlyOwner {
        defaultSessionKey = key;
        defaultSessionKeyValidity = validity;
        defaultDailyLimitUSD = dailyLimitUSD;
        emit DefaultSessionKeySet(key, validity, dailyLimitUSD);
    }

    /**
     * @notice Set default protocols to whitelist for new accounts
     */
    function setDefaultProtocols(
        address[] calldata protocols,
        bytes4[][] calldata selectors
    ) external onlyOwner {
        require(protocols.length == selectors.length, "Length mismatch");
        
        delete defaultProtocols;
        delete defaultSelectors;
        
        for (uint256 i = 0; i < protocols.length; i++) {
            defaultProtocols.push(protocols[i]);
            defaultSelectors.push(selectors[i]);
        }
        
        emit DefaultProtocolsUpdated(protocols.length);
    }
}

// ============ Interfaces ============

interface ITechneAgentAccount {
    function initialize(address owner) external;
    function addSessionKey(address key, uint48 validUntil, uint256 dailyLimitUSD) external;
    function batchWhitelist(address[] calldata protocols, bytes4[][] calldata selectors) external;
}

interface IAgentIdentityRegistry {
    function registerAgent(
        address smartAccount,
        address agentOwner,
        bytes32 modelHash,
        string calldata agentType
    ) external returns (uint256);
    
    function getTokenId(address smartAccount) external view returns (uint256);
}
