// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title AgentReputationRegistry
 * @notice ERC-8004 Reputation Registry - Tracks execution outcomes and builds trust scores
 * @dev Portable reputation that follows the agent NFT
 * 
 * Reputation is calculated based on:
 * 1. Total executions
 * 2. Success rate
 * 3. Value managed
 * 4. Time active
 * 5. Protocol endorsements
 */
contract AgentReputationRegistry is Ownable, ReentrancyGuard {
    
    // ============ State ============
    
    // Identity registry reference
    address public identityRegistry;
    
    // Mapping from tokenId to reputation data
    mapping(uint256 => AgentReputation) public reputations;
    
    // Authorized reporters (e.g., StrategyExecutor, Backend)
    mapping(address => bool) public authorizedReporters;
    
    // Protocol endorsements (protocol address => endorsement weight)
    mapping(address => uint256) public protocolWeights;
    
    // ============ Structs ============
    
    struct AgentReputation {
        // Execution metrics
        uint256 totalExecutions;
        uint256 successfulExecutions;
        uint256 failedExecutions;
        
        // Financial metrics
        uint256 totalValueManaged;     // Cumulative USD value (8 decimals)
        uint256 currentValueManaged;   // Current AUM
        uint256 totalProfitGenerated;  // Cumulative profit (8 decimals)
        
        // Time metrics
        uint256 firstExecutionAt;
        uint256 lastExecutionAt;
        uint256 uptimeDays;
        
        // Trust score (0-10000 = 0-100.00%)
        uint256 trustScore;
        
        // Endorsements
        uint256 endorsementScore;
        mapping(address => bool) endorsedBy;
    }
    
    struct ExecutionReport {
        uint256 tokenId;
        bool success;
        uint256 valueUSD;        // 8 decimals
        int256 profitUSD;        // Can be negative
        string executionType;    // "deposit", "withdraw", "rebalance", etc.
    }
    
    // ============ Events ============
    
    event ExecutionRecorded(
        uint256 indexed tokenId,
        bool success,
        uint256 valueUSD,
        int256 profitUSD,
        string executionType
    );
    
    event TrustScoreUpdated(
        uint256 indexed tokenId,
        uint256 oldScore,
        uint256 newScore
    );
    
    event ProtocolEndorsement(
        uint256 indexed tokenId,
        address indexed protocol,
        uint256 weight
    );
    
    event ReporterAuthorized(address indexed reporter);
    event ReporterRevoked(address indexed reporter);
    
    // ============ Constructor ============
    
    constructor(address _identityRegistry) Ownable(msg.sender) {
        identityRegistry = _identityRegistry;
    }
    
    // ============ Modifiers ============
    
    modifier onlyAuthorizedReporter() {
        require(
            authorizedReporters[msg.sender] || msg.sender == owner(),
            "Reputation: not authorized reporter"
        );
        _;
    }
    
    // ============ Admin Functions ============
    
    function authorizeReporter(address reporter) external onlyOwner {
        authorizedReporters[reporter] = true;
        emit ReporterAuthorized(reporter);
    }
    
    function revokeReporter(address reporter) external onlyOwner {
        authorizedReporters[reporter] = false;
        emit ReporterRevoked(reporter);
    }
    
    function setProtocolWeight(address protocol, uint256 weight) external onlyOwner {
        protocolWeights[protocol] = weight;
    }
    
    function setIdentityRegistry(address _registry) external onlyOwner {
        identityRegistry = _registry;
    }
    
    // ============ Core Functions ============
    
    /**
     * @notice Record an execution outcome
     * @param report The execution report
     */
    function recordExecution(ExecutionReport calldata report) 
        external 
        onlyAuthorizedReporter 
        nonReentrant 
    {
        AgentReputation storage rep = reputations[report.tokenId];
        
        // Update execution counts
        rep.totalExecutions++;
        if (report.success) {
            rep.successfulExecutions++;
        } else {
            rep.failedExecutions++;
        }
        
        // Update value metrics
        rep.totalValueManaged += report.valueUSD;
        
        if (report.profitUSD > 0) {
            rep.totalProfitGenerated += uint256(report.profitUSD);
        }
        
        // Update time metrics
        if (rep.firstExecutionAt == 0) {
            rep.firstExecutionAt = block.timestamp;
        }
        rep.lastExecutionAt = block.timestamp;
        
        // Calculate uptime days
        if (rep.firstExecutionAt > 0) {
            rep.uptimeDays = (block.timestamp - rep.firstExecutionAt) / 1 days;
        }
        
        // Update trust score
        uint256 oldScore = rep.trustScore;
        rep.trustScore = _calculateTrustScore(report.tokenId);
        
        emit ExecutionRecorded(
            report.tokenId,
            report.success,
            report.valueUSD,
            report.profitUSD,
            report.executionType
        );
        
        if (oldScore != rep.trustScore) {
            emit TrustScoreUpdated(report.tokenId, oldScore, rep.trustScore);
        }
    }
    
    /**
     * @notice Batch record multiple executions (gas efficient)
     * @param reports Array of execution reports
     */
    function batchRecordExecutions(ExecutionReport[] calldata reports) 
        external 
        onlyAuthorizedReporter 
        nonReentrant 
    {
        for (uint256 i = 0; i < reports.length; i++) {
            _recordExecutionInternal(reports[i]);
        }
    }
    
    function _recordExecutionInternal(ExecutionReport calldata report) internal {
        AgentReputation storage rep = reputations[report.tokenId];
        
        rep.totalExecutions++;
        if (report.success) {
            rep.successfulExecutions++;
        } else {
            rep.failedExecutions++;
        }
        
        rep.totalValueManaged += report.valueUSD;
        
        if (report.profitUSD > 0) {
            rep.totalProfitGenerated += uint256(report.profitUSD);
        }
        
        if (rep.firstExecutionAt == 0) {
            rep.firstExecutionAt = block.timestamp;
        }
        rep.lastExecutionAt = block.timestamp;
        
        emit ExecutionRecorded(
            report.tokenId,
            report.success,
            report.valueUSD,
            report.profitUSD,
            report.executionType
        );
    }
    
    /**
     * @notice Update current AUM for an agent
     * @param tokenId The agent token ID
     * @param currentAUM Current assets under management (8 decimals)
     */
    function updateCurrentAUM(uint256 tokenId, uint256 currentAUM) 
        external 
        onlyAuthorizedReporter 
    {
        reputations[tokenId].currentValueManaged = currentAUM;
    }
    
    /**
     * @notice Protocol endorses an agent
     * @param tokenId The agent token ID
     */
    function endorseAgent(uint256 tokenId) external {
        require(protocolWeights[msg.sender] > 0, "Reputation: not endorsed protocol");
        require(!reputations[tokenId].endorsedBy[msg.sender], "Reputation: already endorsed");
        
        reputations[tokenId].endorsedBy[msg.sender] = true;
        reputations[tokenId].endorsementScore += protocolWeights[msg.sender];
        
        // Recalculate trust score
        reputations[tokenId].trustScore = _calculateTrustScore(tokenId);
        
        emit ProtocolEndorsement(tokenId, msg.sender, protocolWeights[msg.sender]);
    }
    
    // ============ View Functions ============
    
    /**
     * @notice Get full reputation for an agent
     * @param tokenId The agent token ID
     */
    function getReputation(uint256 tokenId) external view returns (
        uint256 totalExecutions,
        uint256 successfulExecutions,
        uint256 failedExecutions,
        uint256 totalValueManaged,
        uint256 currentValueManaged,
        uint256 totalProfitGenerated,
        uint256 trustScore,
        uint256 endorsementScore,
        uint256 uptimeDays
    ) {
        AgentReputation storage rep = reputations[tokenId];
        return (
            rep.totalExecutions,
            rep.successfulExecutions,
            rep.failedExecutions,
            rep.totalValueManaged,
            rep.currentValueManaged,
            rep.totalProfitGenerated,
            rep.trustScore,
            rep.endorsementScore,
            rep.uptimeDays
        );
    }
    
    /**
     * @notice Get trust score for an agent
     * @param tokenId The agent token ID
     */
    function getTrustScore(uint256 tokenId) external view returns (uint256) {
        return reputations[tokenId].trustScore;
    }
    
    /**
     * @notice Get success rate for an agent
     * @param tokenId The agent token ID
     */
    function getSuccessRate(uint256 tokenId) external view returns (uint256) {
        AgentReputation storage rep = reputations[tokenId];
        if (rep.totalExecutions == 0) return 0;
        return (rep.successfulExecutions * 10000) / rep.totalExecutions;
    }
    
    /**
     * @notice Check if protocol has endorsed an agent
     * @param tokenId The agent token ID
     * @param protocol The protocol address
     */
    function hasEndorsed(uint256 tokenId, address protocol) external view returns (bool) {
        return reputations[tokenId].endorsedBy[protocol];
    }
    
    // ============ Internal Functions ============
    
    /**
     * @notice Calculate trust score based on multiple factors
     * @dev Score = (successRate * 40) + (volumeFactor * 30) + (timeFactor * 20) + (endorsements * 10)
     * @param tokenId The agent token ID
     */
    function _calculateTrustScore(uint256 tokenId) internal view returns (uint256) {
        AgentReputation storage rep = reputations[tokenId];
        
        if (rep.totalExecutions == 0) return 0;
        
        // Success rate component (40% weight)
        uint256 successRate = (rep.successfulExecutions * 10000) / rep.totalExecutions;
        uint256 successComponent = (successRate * 40) / 100;
        
        // Volume component (30% weight) - logarithmic scale
        // $100k+ = max score
        uint256 volumeScore;
        if (rep.totalValueManaged >= 100000 * 10**8) {
            volumeScore = 10000;
        } else if (rep.totalValueManaged >= 10000 * 10**8) {
            volumeScore = 7500;
        } else if (rep.totalValueManaged >= 1000 * 10**8) {
            volumeScore = 5000;
        } else if (rep.totalValueManaged >= 100 * 10**8) {
            volumeScore = 2500;
        } else {
            volumeScore = 1000;
        }
        uint256 volumeComponent = (volumeScore * 30) / 100;
        
        // Time component (20% weight) - more uptime = more trust
        // 30+ days = max score
        uint256 timeScore;
        if (rep.uptimeDays >= 30) {
            timeScore = 10000;
        } else if (rep.uptimeDays >= 7) {
            timeScore = 7000;
        } else if (rep.uptimeDays >= 1) {
            timeScore = 4000;
        } else {
            timeScore = 1000;
        }
        uint256 timeComponent = (timeScore * 20) / 100;
        
        // Endorsement component (10% weight)
        // Cap at 1000 endorsement points for max score
        uint256 endorsementScore = rep.endorsementScore > 1000 ? 1000 : rep.endorsementScore;
        uint256 endorsementComponent = (endorsementScore * 10) / 100;
        
        return successComponent + volumeComponent + timeComponent + endorsementComponent;
    }
}
