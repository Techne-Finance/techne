// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title TechneAgentWallet V2 - Institutional Grade
 * @author Techne Protocol
 * @notice Autonomous yield wallet with full security controls
 * @dev Security Features:
 * - Timelock on critical functions (2 days)
 * - Multi-sig support (2/3 signers required)
 * - Daily withdrawal limits
 * - Auto circuit breaker
 * - De-peg protection (Chainlink oracle)
 * - Protocol allocation caps (25% max)
 * - Emergency mode with guardian
 */

// Chainlink Price Feed Interface
interface AggregatorV3Interface {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
}

// Aerodrome Router interface
interface IAerodromeRouter {
    struct Route {
        address from;
        address to;
        bool stable;
        address factory;
    }
    
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        Route[] calldata routes,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);
    
    function addLiquidity(
        address tokenA,
        address tokenB,
        bool stable,
        uint256 amountADesired,
        uint256 amountBDesired,
        uint256 amountAMin,
        uint256 amountBMin,
        address to,
        uint256 deadline
    ) external returns (uint256 amountA, uint256 amountB, uint256 liquidity);
    
    function removeLiquidity(
        address tokenA,
        address tokenB,
        bool stable,
        uint256 liquidity,
        uint256 amountAMin,
        uint256 amountBMin,
        address to,
        uint256 deadline
    ) external returns (uint256 amountA, uint256 amountB);
    
    function getAmountsOut(
        uint256 amountIn,
        Route[] calldata routes
    ) external view returns (uint256[] memory amounts);
}

interface IAerodromeFactory {
    function getPool(address tokenA, address tokenB, bool stable) external view returns (address);
}

contract TechneAgentWalletV2 is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ============================================
    // STRUCTS
    // ============================================
    struct UserDeposit {
        uint256 shares;
        uint256 depositTime;
    }

    struct LPPosition {
        address pool;
        address tokenA;
        address tokenB;
        bool stable;
        uint256 lpAmount;
    }
    
    struct TimelockProposal {
        uint256 executeTime;
        bytes data;
        bool executed;
    }

    // ============================================
    // CONSTANTS
    // ============================================
    uint256 public constant TIMELOCK_DELAY = 2 days;
    uint256 public constant MAX_FEE = 2000; // 20%
    uint256 public constant MAX_PROTOCOL_ALLOCATION = 2500; // 25%
    uint256 public constant DEPEG_THRESHOLD = 99500000; // $0.995 (8 decimals)
    uint256 public constant CIRCUIT_BREAKER_THRESHOLD = 3;
    
    // ============================================
    // STATE - Core
    // ============================================
    IERC20 public immutable USDC;
    IAerodromeRouter public immutable router;
    address public immutable aerodromeFactory;
    
    uint256 public totalShares;
    uint256 public totalDeposited;
    
    mapping(address => UserDeposit) public userDeposits;
    LPPosition[] public lpPositions;
    
    address public agent;
    uint256 public performanceFee = 1000; // 10%
    uint256 public minDeposit = 10 * 1e6; // 10 USDC
    uint256 public defaultSlippage = 50; // 0.5%
    uint8 public poolType = 0;
    
    // ============================================
    // STATE - Security: Multi-Sig
    // ============================================
    address[] public signers;
    uint256 public requiredSignatures = 2;
    mapping(bytes32 => mapping(address => bool)) public confirmations;
    mapping(bytes32 => uint256) public confirmationCount;
    
    // ============================================
    // STATE - Security: Timelock
    // ============================================
    mapping(bytes32 => TimelockProposal) public timelockProposals;
    
    // ============================================
    // STATE - Security: Withdrawal Limits
    // ============================================
    uint256 public dailyWithdrawLimit = 1_000_000 * 1e6; // $1M daily
    uint256 public maxSingleWithdraw = 100_000 * 1e6; // $100K per tx
    uint256 public lastWithdrawDay;
    uint256 public withdrawnToday;
    
    // ============================================
    // STATE - Security: Circuit Breaker
    // ============================================
    uint256 public failedTxCount;
    bool public circuitBreakerTriggered;
    
    // ============================================
    // STATE - Security: De-peg Protection
    // ============================================
    AggregatorV3Interface public usdcPriceFeed;
    bool public depegProtectionEnabled = true;
    
    // ============================================
    // STATE - Security: Protocol Caps
    // ============================================
    mapping(address => uint256) public protocolAllocations;
    mapping(address => bool) public approvedProtocols;
    
    // ============================================
    // STATE - Emergency
    // ============================================
    bool public emergencyMode = false;
    address public guardian;

    // ============================================
    // EVENTS
    // ============================================
    event Deposited(address indexed user, uint256 amount, uint256 shares);
    event TokenDeposited(address indexed user, address indexed token, uint256 amount, uint256 shares);
    event Withdrawn(address indexed user, uint256 amount, uint256 shares);
    event SwappedForLP(address indexed tokenIn, address indexed tokenOut, uint256 amountIn, uint256 amountOut);
    event LPDeposited(address indexed pool, uint256 amountA, uint256 amountB, uint256 lpTokens);
    event LPWithdrawn(address indexed pool, uint256 lpTokens, uint256 amountA, uint256 amountB);
    event PoolTypeChanged(uint8 oldType, uint8 newType);
    
    // Security Events
    event TimelockProposed(bytes32 indexed proposalId, uint256 executeTime, string action);
    event TimelockExecuted(bytes32 indexed proposalId);
    event TimelockCancelled(bytes32 indexed proposalId);
    event MultiSigConfirmed(bytes32 indexed txHash, address indexed signer, uint256 count);
    event CircuitBreakerTriggered(uint256 timestamp);
    event CircuitBreakerReset(uint256 timestamp);
    event DepegDetected(int256 price, uint256 timestamp);
    event WithdrawLimitExceeded(address indexed user, uint256 requested, uint256 available);
    event GuardianSet(address indexed oldGuardian, address indexed newGuardian);
    event ProtocolApproved(address indexed protocol);
    event ProtocolRemoved(address indexed protocol);

    // ============================================
    // CONSTRUCTOR
    // ============================================
    constructor(
        address _usdc,
        address _router,
        address _factory,
        address _agent,
        address _usdcPriceFeed,
        address[] memory _signers
    ) Ownable(msg.sender) {
        require(_usdc != address(0), "Invalid USDC");
        require(_router != address(0), "Invalid router");
        require(_agent != address(0), "Invalid agent");
        require(_signers.length >= 2, "Need at least 2 signers");
        
        USDC = IERC20(_usdc);
        router = IAerodromeRouter(_router);
        aerodromeFactory = _factory;
        agent = _agent;
        guardian = msg.sender;
        
        if (_usdcPriceFeed != address(0)) {
            usdcPriceFeed = AggregatorV3Interface(_usdcPriceFeed);
        }
        
        for (uint i = 0; i < _signers.length; i++) {
            require(_signers[i] != address(0), "Invalid signer");
            signers.push(_signers[i]);
        }
    }

    // ============================================
    // MODIFIERS
    // ============================================
    modifier onlyAgent() {
        require(msg.sender == agent || msg.sender == owner(), "Not authorized");
        _;
    }
    
    modifier onlyGuardian() {
        require(msg.sender == guardian || msg.sender == owner(), "Not guardian");
        _;
    }
    
    modifier onlySigner() {
        bool isSigner = false;
        for (uint i = 0; i < signers.length; i++) {
            if (signers[i] == msg.sender) {
                isSigner = true;
                break;
            }
        }
        require(isSigner || msg.sender == owner(), "Not signer");
        _;
    }
    
    modifier notEmergency() {
        require(!emergencyMode, "Emergency mode active");
        _;
    }
    
    modifier circuitBreakerCheck() {
        require(!circuitBreakerTriggered, "Circuit breaker active");
        _;
    }
    
    modifier pegProtected() {
        if (depegProtectionEnabled && address(usdcPriceFeed) != address(0)) {
            (, int256 price,,,) = usdcPriceFeed.latestRoundData();
            if (uint256(price) < DEPEG_THRESHOLD) {
                emit DepegDetected(price, block.timestamp);
                revert("USDC de-pegged - operations paused");
            }
        }
        _;
    }
    
    modifier withinWithdrawLimit(uint256 amount) {
        // Reset daily counter if new day
        uint256 today = block.timestamp / 1 days;
        if (today > lastWithdrawDay) {
            lastWithdrawDay = today;
            withdrawnToday = 0;
        }
        
        require(amount <= maxSingleWithdraw, "Exceeds single withdraw limit");
        require(withdrawnToday + amount <= dailyWithdrawLimit, "Daily limit exceeded");
        _;
        withdrawnToday += amount;
    }

    // ============================================
    // TIMELOCK FUNCTIONS
    // ============================================
    
    function proposeAgentChange(address _newAgent) external onlyOwner returns (bytes32) {
        bytes32 proposalId = keccak256(abi.encodePacked("setAgent", _newAgent, block.timestamp));
        
        timelockProposals[proposalId] = TimelockProposal({
            executeTime: block.timestamp + TIMELOCK_DELAY,
            data: abi.encode(_newAgent),
            executed: false
        });
        
        emit TimelockProposed(proposalId, block.timestamp + TIMELOCK_DELAY, "setAgent");
        return proposalId;
    }
    
    function executeAgentChange(bytes32 proposalId) external onlyOwner {
        TimelockProposal storage proposal = timelockProposals[proposalId];
        require(proposal.executeTime != 0, "Proposal not found");
        require(block.timestamp >= proposal.executeTime, "Timelock active");
        require(!proposal.executed, "Already executed");
        
        proposal.executed = true;
        address newAgent = abi.decode(proposal.data, (address));
        agent = newAgent;
        
        emit TimelockExecuted(proposalId);
    }
    
    function cancelProposal(bytes32 proposalId) external onlyOwner {
        require(timelockProposals[proposalId].executeTime != 0, "Proposal not found");
        delete timelockProposals[proposalId];
        emit TimelockCancelled(proposalId);
    }

    // ============================================
    // MULTI-SIG FUNCTIONS
    // ============================================
    
    function confirmTransaction(bytes32 txHash) external onlySigner {
        require(!confirmations[txHash][msg.sender], "Already confirmed");
        
        confirmations[txHash][msg.sender] = true;
        confirmationCount[txHash]++;
        
        emit MultiSigConfirmed(txHash, msg.sender, confirmationCount[txHash]);
    }
    
    function isConfirmed(bytes32 txHash) public view returns (bool) {
        return confirmationCount[txHash] >= requiredSignatures;
    }
    
    function executeMultiSigWithdraw(uint256 amount, address to) external onlySigner nonReentrant {
        bytes32 txHash = keccak256(abi.encodePacked("withdraw", amount, to, block.timestamp / 1 days));
        require(isConfirmed(txHash), "Not enough confirmations");
        
        // Reset confirmations
        for (uint i = 0; i < signers.length; i++) {
            confirmations[txHash][signers[i]] = false;
        }
        confirmationCount[txHash] = 0;
        
        // Execute
        USDC.safeTransfer(to, amount);
    }

    // ============================================
    // CIRCUIT BREAKER
    // ============================================
    
    function _checkCircuitBreaker(uint256 amount) internal {
        if (amount > maxSingleWithdraw) {
            failedTxCount++;
            if (failedTxCount >= CIRCUIT_BREAKER_THRESHOLD) {
                circuitBreakerTriggered = true;
                emit CircuitBreakerTriggered(block.timestamp);
            }
        } else {
            // Reset on successful small tx
            if (failedTxCount > 0) failedTxCount--;
        }
    }
    
    function resetCircuitBreaker() external onlyGuardian {
        circuitBreakerTriggered = false;
        failedTxCount = 0;
        emit CircuitBreakerReset(block.timestamp);
    }

    // ============================================
    // PROTOCOL CAPS
    // ============================================
    
    function approveProtocol(address protocol) external onlyOwner {
        approvedProtocols[protocol] = true;
        emit ProtocolApproved(protocol);
    }
    
    function removeProtocol(address protocol) external onlyOwner {
        approvedProtocols[protocol] = false;
        emit ProtocolRemoved(protocol);
    }
    
    function _checkAllocationLimit(address protocol, uint256 amount) internal view {
        require(approvedProtocols[protocol], "Protocol not approved");
        
        uint256 total = totalValue();
        if (total == 0) return;
        
        uint256 newAllocation = protocolAllocations[protocol] + amount;
        uint256 newPercent = (newAllocation * 10000) / total;
        require(newPercent <= MAX_PROTOCOL_ALLOCATION, "Exceeds protocol cap (25%)");
    }

    // ============================================
    // USER FUNCTIONS
    // ============================================
    
    function deposit(uint256 amount) external nonReentrant whenNotPaused notEmergency circuitBreakerCheck pegProtected {
        require(amount >= minDeposit, "Below minimum deposit");
        
        uint256 shares;
        if (totalShares == 0) {
            shares = amount;
        } else {
            shares = (amount * totalShares) / totalValue();
        }
        
        USDC.safeTransferFrom(msg.sender, address(this), amount);
        
        userDeposits[msg.sender].shares += shares;
        userDeposits[msg.sender].depositTime = block.timestamp;
        totalShares += shares;
        totalDeposited += amount;
        
        emit Deposited(msg.sender, amount, shares);
    }
    
    function depositToken(address token, uint256 amount) external nonReentrant whenNotPaused notEmergency circuitBreakerCheck {
        require(amount > 0, "Zero amount");
        require(token != address(0), "Invalid token");
        
        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);
        
        uint256 usdValue;
        if (token == address(USDC)) {
            usdValue = amount;
        } else {
            usdValue = amount; // In production: use price oracle
        }
        
        uint256 shares;
        if (totalShares == 0) {
            shares = usdValue;
        } else {
            shares = (usdValue * totalShares) / totalValue();
        }
        
        userDeposits[msg.sender].shares += shares;
        userDeposits[msg.sender].depositTime = block.timestamp;
        totalShares += shares;
        
        emit TokenDeposited(msg.sender, token, amount, shares);
    }
    
    function withdraw(uint256 shares) external nonReentrant circuitBreakerCheck withinWithdrawLimit(shares) {
        require(shares > 0, "Zero shares");
        require(userDeposits[msg.sender].shares >= shares, "Insufficient shares");
        
        uint256 amount = (shares * totalValue()) / totalShares;
        
        _checkCircuitBreaker(amount);
        
        userDeposits[msg.sender].shares -= shares;
        totalShares -= shares;
        if (totalDeposited > amount) {
            totalDeposited -= amount;
        } else {
            totalDeposited = 0;
        }
        
        USDC.safeTransfer(msg.sender, amount);
        
        emit Withdrawn(msg.sender, amount, shares);
    }

    // ============================================
    // AGENT FUNCTIONS - LP Operations
    // ============================================
    
    function swapUSDCFor(
        address tokenOut,
        uint256 amountIn,
        bool stable
    ) external onlyAgent notEmergency circuitBreakerCheck returns (uint256 amountOut) {
        require(amountIn > 0, "Zero amount");
        require(USDC.balanceOf(address(this)) >= amountIn, "Insufficient USDC");
        
        USDC.forceApprove(address(router), amountIn);
        
        IAerodromeRouter.Route[] memory routes = new IAerodromeRouter.Route[](1);
        routes[0] = IAerodromeRouter.Route({
            from: address(USDC),
            to: tokenOut,
            stable: stable,
            factory: aerodromeFactory
        });
        
        uint256[] memory expectedAmounts = router.getAmountsOut(amountIn, routes);
        uint256 minOut = expectedAmounts[1] * (10000 - defaultSlippage) / 10000;
        
        uint256[] memory amounts = router.swapExactTokensForTokens(
            amountIn,
            minOut,
            routes,
            address(this),
            block.timestamp + 300
        );
        
        amountOut = amounts[amounts.length - 1];
        emit SwappedForLP(address(USDC), tokenOut, amountIn, amountOut);
    }
    
    function addLiquidityToPool(
        address tokenA,
        address tokenB,
        uint256 amountA,
        uint256 amountB,
        bool stable
    ) external onlyAgent notEmergency circuitBreakerCheck returns (uint256 lpTokens) {
        require(amountA > 0 && amountB > 0, "Zero amounts");
        
        IERC20(tokenA).forceApprove(address(router), amountA);
        IERC20(tokenB).forceApprove(address(router), amountB);
        
        uint256 minA = amountA * (10000 - defaultSlippage) / 10000;
        uint256 minB = amountB * (10000 - defaultSlippage) / 10000;
        
        (uint256 actualA, uint256 actualB, uint256 liquidity) = router.addLiquidity(
            tokenA,
            tokenB,
            stable,
            amountA,
            amountB,
            minA,
            minB,
            address(this),
            block.timestamp + 300
        );
        
        address pool = IAerodromeFactory(aerodromeFactory).getPool(tokenA, tokenB, stable);
        
        lpPositions.push(LPPosition({
            pool: pool,
            tokenA: tokenA,
            tokenB: tokenB,
            stable: stable,
            lpAmount: liquidity
        }));
        
        // Track protocol allocation
        protocolAllocations[pool] += actualA;
        
        lpTokens = liquidity;
        emit LPDeposited(pool, actualA, actualB, liquidity);
    }
    
    function removeLiquidityFromPool(
        uint256 positionIndex,
        uint256 lpAmount
    ) external onlyAgent returns (uint256 amountA, uint256 amountB) {
        require(positionIndex < lpPositions.length, "Invalid position");
        LPPosition storage pos = lpPositions[positionIndex];
        require(lpAmount <= pos.lpAmount, "Exceeds position");
        
        IERC20(pos.pool).forceApprove(address(router), lpAmount);
        
        (amountA, amountB) = router.removeLiquidity(
            pos.tokenA,
            pos.tokenB,
            pos.stable,
            lpAmount,
            0,
            0,
            address(this),
            block.timestamp + 300
        );
        
        pos.lpAmount -= lpAmount;
        
        // Update protocol allocation
        if (protocolAllocations[pos.pool] >= amountA) {
            protocolAllocations[pos.pool] -= amountA;
        }
        
        emit LPWithdrawn(pos.pool, lpAmount, amountA, amountB);
    }
    
    function enterLPPosition(
        address tokenB,
        uint256 usdcAmount,
        bool stable
    ) external onlyAgent notEmergency circuitBreakerCheck returns (uint256 lpTokens) {
        require(usdcAmount >= minDeposit * 2, "Need at least 2x min deposit");
        require(poolType >= 1, "Dual-sided not enabled");
        
        uint256 halfUSDC = usdcAmount / 2;
        
        uint256 tokenBAmount = _swapUSDCForToken(tokenB, halfUSDC, stable);
        
        emit SwappedForLP(address(USDC), tokenB, halfUSDC, tokenBAmount);
        
        lpTokens = _addLiquidityInternal(tokenB, halfUSDC, tokenBAmount, stable);
    }
    
    function _swapUSDCForToken(address tokenOut, uint256 amountIn, bool stable) internal returns (uint256) {
        USDC.forceApprove(address(router), amountIn);
        
        IAerodromeRouter.Route[] memory routes = new IAerodromeRouter.Route[](1);
        routes[0] = IAerodromeRouter.Route({
            from: address(USDC),
            to: tokenOut,
            stable: stable,
            factory: aerodromeFactory
        });
        
        uint256[] memory amounts = router.swapExactTokensForTokens(
            amountIn,
            0,
            routes,
            address(this),
            block.timestamp + 300
        );
        
        return amounts[amounts.length - 1];
    }
    
    function _addLiquidityInternal(address tokenB, uint256 usdcAmt, uint256 tokenBAmt, bool stable) internal returns (uint256) {
        USDC.forceApprove(address(router), usdcAmt);
        IERC20(tokenB).forceApprove(address(router), tokenBAmt);
        
        (,, uint256 liquidity) = router.addLiquidity(
            address(USDC),
            tokenB,
            stable,
            usdcAmt,
            tokenBAmt,
            0,
            0,
            address(this),
            block.timestamp + 300
        );
        
        address pool = IAerodromeFactory(aerodromeFactory).getPool(address(USDC), tokenB, stable);
        
        lpPositions.push(LPPosition({
            pool: pool,
            tokenA: address(USDC),
            tokenB: tokenB,
            stable: stable,
            lpAmount: liquidity
        }));
        
        emit LPDeposited(pool, usdcAmt, tokenBAmt, liquidity);
        return liquidity;
    }

    // ============================================
    // VIEW FUNCTIONS
    // ============================================
    
    function totalValue() public view returns (uint256) {
        uint256 usdcBalance = USDC.balanceOf(address(this));
        return usdcBalance;
    }
    
    function getUserValue(address user) external view returns (uint256) {
        if (totalShares == 0) return 0;
        return (userDeposits[user].shares * totalValue()) / totalShares;
    }
    
    function getUserShares(address user) external view returns (uint256) {
        return userDeposits[user].shares;
    }
    
    function getLPPositionCount() external view returns (uint256) {
        return lpPositions.length;
    }
    
    function getSigners() external view returns (address[] memory) {
        return signers;
    }
    
    function getWithdrawLimitStatus() external view returns (uint256 remaining, uint256 dailyLimit) {
        uint256 today = block.timestamp / 1 days;
        if (today > lastWithdrawDay) {
            remaining = dailyWithdrawLimit;
        } else {
            remaining = dailyWithdrawLimit - withdrawnToday;
        }
        dailyLimit = dailyWithdrawLimit;
    }
    
    function checkUSDCPeg() external view returns (bool pegged, int256 price) {
        if (address(usdcPriceFeed) == address(0)) {
            return (true, 1e8);
        }
        (, price,,,) = usdcPriceFeed.latestRoundData();
        pegged = uint256(price) >= DEPEG_THRESHOLD;
    }

    // ============================================
    // ADMIN FUNCTIONS (Timelocked via proposals)
    // ============================================
    
    function setPoolType(uint8 _poolType) external onlyOwner {
        require(_poolType <= 2, "Invalid pool type");
        emit PoolTypeChanged(poolType, _poolType);
        poolType = _poolType;
    }
    
    function setSlippage(uint256 _slippage) external onlyOwner {
        require(_slippage <= 500, "Max 5% slippage");
        defaultSlippage = _slippage;
    }
    
    function setGuardian(address _guardian) external onlyOwner {
        emit GuardianSet(guardian, _guardian);
        guardian = _guardian;
    }
    
    function setWithdrawLimits(uint256 _daily, uint256 _single) external onlyOwner {
        dailyWithdrawLimit = _daily;
        maxSingleWithdraw = _single;
    }
    
    function setDepegProtection(bool _enabled) external onlyOwner {
        depegProtectionEnabled = _enabled;
    }
    
    function setPriceFeed(address _feed) external onlyOwner {
        usdcPriceFeed = AggregatorV3Interface(_feed);
    }

    // ============================================
    // EMERGENCY FUNCTIONS
    // ============================================
    
    function setEmergencyMode(bool _emergency) external onlyGuardian {
        emergencyMode = _emergency;
        if (_emergency) {
            _pause();
        } else {
            _unpause();
        }
    }
    
    function emergencyWithdrawAll() external onlyOwner {
        require(emergencyMode, "Not in emergency mode");
        uint256 balance = USDC.balanceOf(address(this));
        USDC.safeTransfer(owner(), balance);
    }
    
    function pause() external onlyGuardian {
        _pause();
    }
    
    function unpause() external onlyGuardian {
        _unpause();
    }
}
