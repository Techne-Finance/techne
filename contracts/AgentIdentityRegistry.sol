// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";
import "@openzeppelin/contracts/utils/Base64.sol";

/**
 * @title AgentIdentityRegistry
 * @notice ERC-8004 Identity Registry - Portable, censorship-resistant AI agent identities
 * @dev Each agent gets an NFT linking their Smart Account to an on-chain identity
 * 
 * ERC-8004 Standard Components:
 * 1. ✅ Identity Registry (this contract) - ERC-721 for agent identity
 * 2. Reputation Registry - tracks execution outcomes (separate contract)
 * 3. Validation Registry - TEE/ZK attestations (future)
 */
contract AgentIdentityRegistry is ERC721, ERC721Enumerable, ERC721URIStorage, Ownable {
    using Strings for uint256;
    
    // ============ State ============
    
    uint256 private _nextTokenId;
    
    // Mapping from tokenId to agent data
    mapping(uint256 => AgentIdentity) public agents;
    
    // Mapping from smartAccount to tokenId (reverse lookup)
    mapping(address => uint256) public accountToToken;
    
    // Mapping from smartAccount to whether it has an identity
    mapping(address => bool) public hasIdentity;
    
    // Authorized minters (e.g., TechneAgentFactory)
    mapping(address => bool) public authorizedMinters;
    
    // Reputation registry address (for cross-contract calls)
    address public reputationRegistry;
    
    // ============ Structs ============
    
    struct AgentIdentity {
        address smartAccount;      // TechneAgentAccount address
        address owner;             // User who owns this agent
        bytes32 modelHash;         // Hash of agent config/model
        string agentType;          // e.g., "yield_optimizer", "trading_bot"
        uint256 createdAt;
        uint256 lastActiveAt;
        bool active;
    }
    
    // ============ Events ============
    
    event AgentRegistered(
        uint256 indexed tokenId,
        address indexed smartAccount,
        address indexed owner,
        bytes32 modelHash,
        string agentType
    );
    
    event AgentUpdated(
        uint256 indexed tokenId,
        bytes32 newModelHash
    );
    
    event AgentDeactivated(uint256 indexed tokenId);
    event AgentReactivated(uint256 indexed tokenId);
    event MinterAuthorized(address indexed minter);
    event MinterRevoked(address indexed minter);
    
    // ============ Constructor ============
    
    constructor() ERC721("Techne Agent Identity", "TAGENT") Ownable(msg.sender) {
        _nextTokenId = 1; // Start from 1
    }
    
    // ============ Modifiers ============
    
    modifier onlyAuthorizedMinter() {
        require(
            authorizedMinters[msg.sender] || msg.sender == owner(),
            "AgentIdentity: not authorized minter"
        );
        _;
    }
    
    modifier onlyAgentOwner(uint256 tokenId) {
        require(ownerOf(tokenId) == msg.sender, "AgentIdentity: not owner");
        _;
    }
    
    // ============ Admin Functions ============
    
    function authorizeMinter(address minter) external onlyOwner {
        authorizedMinters[minter] = true;
        emit MinterAuthorized(minter);
    }
    
    function revokeMinter(address minter) external onlyOwner {
        authorizedMinters[minter] = false;
        emit MinterRevoked(minter);
    }
    
    function setReputationRegistry(address _registry) external onlyOwner {
        reputationRegistry = _registry;
    }
    
    // ============ Core Functions ============
    
    /**
     * @notice Register a new agent identity
     * @param smartAccount The TechneAgentAccount address
     * @param agentOwner The user who owns this agent
     * @param modelHash Hash of the agent's config/model
     * @param agentType Type of agent (e.g., "yield_optimizer")
     * @return tokenId The NFT token ID
     */
    function registerAgent(
        address smartAccount,
        address agentOwner,
        bytes32 modelHash,
        string calldata agentType
    ) external onlyAuthorizedMinter returns (uint256) {
        require(smartAccount != address(0), "AgentIdentity: zero address");
        require(!hasIdentity[smartAccount], "AgentIdentity: already registered");
        
        uint256 tokenId = _nextTokenId++;
        
        agents[tokenId] = AgentIdentity({
            smartAccount: smartAccount,
            owner: agentOwner,
            modelHash: modelHash,
            agentType: agentType,
            createdAt: block.timestamp,
            lastActiveAt: block.timestamp,
            active: true
        });
        
        accountToToken[smartAccount] = tokenId;
        hasIdentity[smartAccount] = true;
        
        _safeMint(agentOwner, tokenId);
        
        emit AgentRegistered(tokenId, smartAccount, agentOwner, modelHash, agentType);
        
        return tokenId;
    }
    
    /**
     * @notice Update agent's model hash (e.g., after config change)
     * @param tokenId The agent token ID
     * @param newModelHash New hash of agent config
     */
    function updateModelHash(
        uint256 tokenId,
        bytes32 newModelHash
    ) external onlyAgentOwner(tokenId) {
        agents[tokenId].modelHash = newModelHash;
        agents[tokenId].lastActiveAt = block.timestamp;
        
        emit AgentUpdated(tokenId, newModelHash);
    }
    
    /**
     * @notice Record agent activity (called by execution systems)
     * @param smartAccount The agent's smart account
     */
    function recordActivity(address smartAccount) external {
        if (hasIdentity[smartAccount]) {
            uint256 tokenId = accountToToken[smartAccount];
            agents[tokenId].lastActiveAt = block.timestamp;
        }
    }
    
    /**
     * @notice Deactivate an agent (owner only)
     * @param tokenId The agent token ID
     */
    function deactivateAgent(uint256 tokenId) external onlyAgentOwner(tokenId) {
        agents[tokenId].active = false;
        emit AgentDeactivated(tokenId);
    }
    
    /**
     * @notice Reactivate an agent (owner only)
     * @param tokenId The agent token ID
     */
    function reactivateAgent(uint256 tokenId) external onlyAgentOwner(tokenId) {
        agents[tokenId].active = true;
        emit AgentReactivated(tokenId);
    }
    
    // ============ View Functions ============
    
    /**
     * @notice Get agent identity by smart account
     * @param smartAccount The agent's smart account address
     * @return identity The agent identity struct
     */
    function getAgentByAccount(address smartAccount) 
        external 
        view 
        returns (AgentIdentity memory) 
    {
        require(hasIdentity[smartAccount], "AgentIdentity: not found");
        return agents[accountToToken[smartAccount]];
    }
    
    /**
     * @notice Get agent identity by token ID
     * @param tokenId The NFT token ID
     * @return identity The agent identity struct
     */
    function getAgent(uint256 tokenId) external view returns (AgentIdentity memory) {
        require(_ownerOf(tokenId) != address(0), "AgentIdentity: nonexistent");
        return agents[tokenId];
    }
    
    /**
     * @notice Check if a smart account has a registered identity
     * @param smartAccount The address to check
     * @return bool Whether the account is registered
     */
    function isRegistered(address smartAccount) external view returns (bool) {
        return hasIdentity[smartAccount];
    }
    
    /**
     * @notice Get token ID for a smart account
     * @param smartAccount The agent's smart account
     * @return tokenId The NFT token ID
     */
    function getTokenId(address smartAccount) external view returns (uint256) {
        require(hasIdentity[smartAccount], "AgentIdentity: not found");
        return accountToToken[smartAccount];
    }
    
    // ============ Metadata (On-chain SVG) ============
    
    function tokenURI(uint256 tokenId) 
        public 
        view 
        override(ERC721, ERC721URIStorage) 
        returns (string memory) 
    {
        require(_ownerOf(tokenId) != address(0), "AgentIdentity: nonexistent");
        
        AgentIdentity memory agent = agents[tokenId];
        
        string memory svg = _generateSVG(tokenId, agent);
        string memory json = _generateJSON(tokenId, agent, svg);
        
        return string(abi.encodePacked(
            "data:application/json;base64,",
            Base64.encode(bytes(json))
        ));
    }
    
    function _generateSVG(uint256 tokenId, AgentIdentity memory agent) 
        internal 
        pure 
        returns (string memory) 
    {
        string memory statusColor = agent.active ? "#00ff88" : "#ff4444";
        
        return string(abi.encodePacked(
            '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400">',
            '<rect width="100%" height="100%" fill="#1a1a2e"/>',
            '<text x="200" y="50" text-anchor="middle" fill="#fff" font-size="24" font-family="monospace">TECHNE AGENT</text>',
            '<text x="200" y="90" text-anchor="middle" fill="#888" font-size="14">#', tokenId.toString(), '</text>',
            '<circle cx="200" cy="180" r="60" fill="none" stroke="', statusColor, '" stroke-width="3"/>',
            '<text x="200" y="190" text-anchor="middle" fill="', statusColor, '" font-size="40">&#x1F916;</text>',
            '<text x="200" y="280" text-anchor="middle" fill="#fff" font-size="16">', agent.agentType, '</text>',
            '<text x="200" y="320" text-anchor="middle" fill="#666" font-size="12">ERC-8004 Verified</text>',
            '</svg>'
        ));
    }
    
    function _generateJSON(
        uint256 tokenId, 
        AgentIdentity memory agent,
        string memory svg
    ) internal pure returns (string memory) {
        return string(abi.encodePacked(
            '{"name":"Techne Agent #', tokenId.toString(), '",',
            '"description":"ERC-8004 Verified AI Agent Identity",',
            '"image":"data:image/svg+xml;base64,', Base64.encode(bytes(svg)), '",',
            '"attributes":[',
            '{"trait_type":"Agent Type","value":"', agent.agentType, '"},',
            '{"trait_type":"Status","value":"', agent.active ? "Active" : "Inactive", '"},',
            '{"display_type":"number","trait_type":"Created","value":', uint256(agent.createdAt).toString(), '}',
            ']}'
        ));
    }
    
    // ============ Required Overrides ============
    
    function _update(address to, uint256 tokenId, address auth)
        internal
        override(ERC721, ERC721Enumerable)
        returns (address)
    {
        return super._update(to, tokenId, auth);
    }
    
    function _increaseBalance(address account, uint128 value)
        internal
        override(ERC721, ERC721Enumerable)
    {
        super._increaseBalance(account, value);
    }
    
    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC721Enumerable, ERC721URIStorage)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
