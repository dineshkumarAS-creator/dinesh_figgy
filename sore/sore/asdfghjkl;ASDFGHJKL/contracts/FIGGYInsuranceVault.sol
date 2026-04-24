// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./interfaces/IFIGGYPoWToken.sol";
import "./interfaces/IFIGGYOracle.sol";

/**
 * @title FIGGYInsuranceVault
 * @dev On-chain insurance pool for worker disruption payouts
 * 
 * This vault implements dual-condition payout logic:
 * 1. Worker PoW token verification (proof of disruption occurred)
 * 2. Chainlink oracle confirmation (environmental data validation)
 * 
 * Only when BOTH conditions pass does the vault release USDC to the worker.
 * This design prevents FIGGY from unilaterally manipulating payouts.
 * 
 * Chain: Polygon (mainnet or mumbai testnet)
 * Token: USDC (6 decimals)
 * Payouts: Condition-gated and time-locked (48h expiry for pending)
 */
contract FIGGYInsuranceVault is Ownable, Pausable, ReentrancyGuard, AccessControl {
    
    // ============ ACCESS CONTROL ============
    bytes32 public constant PAYOUT_REQUESTOR = keccak256("PAYOUT_REQUESTOR");
    bytes32 public constant ORACLE_FULFILLER = keccak256("ORACLE_FULFILLER");
    
    // ============ STATE ============
    
    /// @dev USDC token on Polygon (6 decimals)
    IERC20 public immutable usdcToken;
    
    /// @dev Reference to FIGGYPoWToken contract for verification
    IFIGGYPoWToken public powToken;
    
    /// @dev Reference to disruption oracle for on-chain verification
    IFIGGYOracle public disruptionOracle;
    
    /// @dev Total USDC reserves in vault
    uint256 public totalReserves;
    
    /// @dev Minimum time window for token verification (in seconds)
    /// Tokens must be minted within this window of payout request
    /// Default: 7 days (604800 seconds)
    uint256 public tokenVerificationWindow = 7 days;
    
    /// @dev Maximum time a payout request can remain pending
    /// After this time, any address can expire the claim (in seconds)
    /// Default: 48 hours (172800 seconds)
    uint256 public payoutExpiryTime = 48 hours;
    
    /// @dev Minimum vault reserves to maintain (safety threshold)
    uint256 public minReserveThreshold = 50_000e6; // $50,000 USDC
    
    // ============ STRUCTURES ============
    
    enum PayoutStatus {
        Pending,
        Released,
        Rejected,
        Expired
    }
    
    struct PayoutClaim {
        address workerAddress;                // Wallet to receive USDC
        uint256 tokenId;                      // PoW token ID
        uint256 requestedAmountUSDC;          // Amount in wei (6 decimals)
        uint256 releasedAmountUSDC;           // Actual amount released
        PayoutStatus status;                  // Current status
        uint64 requestedAt;                   // Timestamp of request
        uint64 releasedAt;                    // Timestamp of release (0 if not released)
        bytes32 claimRef;                     // FIGGY internal claim_id
        bytes32 oracleRequestId;              // Chainlink request ID (tracking)
    }
    
    // ============ MAPPINGS ============
    
    /// @dev Token ID → PayoutClaim details
    mapping(uint256 => PayoutClaim) public claims;
    
    /// @dev Worker address → sum of released payouts (audit trail)
    mapping(address => uint256) public workerPayoutTotals;
    
    /// @dev Claim reference (bytes32(claim_id)) → token ID (reverse lookup)
    mapping(bytes32 => uint256) public claimRefToTokenId;
    
    /// @dev Oracle request ID → token ID (for callback mapping)
    mapping(bytes32 => uint256) public oracleRequestIdToTokenId;
    
    // ============ EVENTS ============
    
    /// @notice Emitted when owner deposits USDC reserves
    event ReservesDeposited(
        uint256 indexed amount,
        uint256 indexed newTotalReserves,
        address indexed depositor,
        uint64 timestamp
    );
    
    /// @notice Emitted when backend requests a payout
    event PayoutRequested(
        uint256 indexed tokenId,
        bytes32 indexed claimRef,
        address indexed workerAddress,
        uint256 amountUSDC,
        uint64 timestamp
    );
    
    /// @notice Emitted when oracle confirms disruption and payout is released
    event PayoutReleased(
        uint256 indexed tokenId,
        bytes32 indexed claimRef,
        address indexed workerAddress,
        uint256 amountUSDC,
        uint256 vaultReservesAfter,
        uint64 timestamp
    );
    
    /// @notice Emitted when oracle rejects disruption claim
    event PayoutRejected(
        uint256 indexed tokenId,
        bytes32 indexed claimRef,
        string reason,
        uint64 timestamp
    );
    
    /// @notice Emitted when payout expires (pending > 48h)
    event PayoutExpired(
        uint256 indexed tokenId,
        bytes32 indexed claimRef,
        address indexed workerAddress,
        uint256 amountUSDC,
        uint64 timestamp
    );
    
    /// @notice Emitted when owner withdraws funds (emergency)
    event EmergencyWithdraw(
        address indexed to,
        uint256 amount,
        uint256 vaultReservesAfter,
        uint64 timestamp
    );
    
    /// @notice Emitted when configuration is updated
    event ConfigurationUpdated(
        string parameter,
        uint256 newValue,
        uint64 timestamp
    );
    
    // ============ ERRORS ============
    
    error InsufficientReserves(uint256 requested, uint256 available);
    error InvalidTokenId(uint256 tokenId);
    error ClaimAlreadyExists(uint256 tokenId);
    error ClaimNotFound(uint256 tokenId);
    error InvalidStatus(PayoutStatus current, PayoutStatus expected);
    error TokenNotMinted(bytes32 workerIdHash);
    error OracleNotVerified(uint256 tokenId);
    error NotTimeForExpiry(uint256 timeElapsed, uint256 required);
    error InvalidAmount(uint256 amount);
    error UnauthorizedCaller(address caller);
    error OracleVerificationFailed(string reason);
    
    // ============ CONSTRUCTOR ============
    
    /**
     * @param _usdcToken address of USDC token on Polygon
     * @param _powToken address of FIGGYPoWToken contract
     * @param _disruptionOracle address of disruption oracle (initially may be address(0))
     */
    constructor(
        address _usdcToken,
        address _powToken,
        address _disruptionOracle
    ) {
        require(_usdcToken != address(0), "Invalid USDC address");
        require(_powToken != address(0), "Invalid PoW token address");
        
        usdcToken = IERC20(_usdcToken);
        powToken = IFIGGYPoWToken(_powToken);
        disruptionOracle = IFIGGYOracle(_disruptionOracle);
        
        // Set up access control
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(PAYOUT_REQUESTOR, msg.sender); // Initially owner, can be transferred
        _grantRole(ORACLE_FULFILLER, msg.sender); // Initially owner
    }
    
    // ============ ADMIN FUNCTIONS ============
    
    /**
     * @dev Deposit USDC into vault reserves
     * 
     * Caller must approve vault contract to spend USDC first.
     * 
     * @param amount amount of USDC to deposit (in wei, 6 decimals)
     * @notice Only owner can deposit
     */
    function depositReserves(uint256 amount) 
        external 
        onlyOwner 
        nonReentrant 
    {
        require(amount > 0, "Amount must be > 0");
        
        bool success = usdcToken.transferFrom(msg.sender, address(this), amount);
        require(success, "USDC transfer failed");
        
        totalReserves += amount;
        
        emit ReservesDeposited(amount, totalReserves, msg.sender, uint64(block.timestamp));
    }
    
    /**
     * @dev Emergency withdraw of USDC (only owner when paused)
     * 
     * @param to recipient address
     * @param amount amount of USDC to withdraw
     * @notice Only owner, only when paused (safety measure)
     */
    function emergencyWithdraw(address to, uint256 amount) 
        external 
        onlyOwner 
        whenPaused 
        nonReentrant 
    {
        require(to != address(0), "Invalid recipient");
        require(amount > 0, "Amount must be > 0");
        require(amount <= totalReserves, "Insufficient reserves");
        
        totalReserves -= amount;
        
        bool success = usdcToken.transfer(to, amount);
        require(success, "USDC transfer failed");
        
        emit EmergencyWithdraw(to, amount, totalReserves, uint64(block.timestamp));
    }
    
    /**
     * @dev Pause vault (stops new payout requests)
     * @notice Only owner
     */
    function pause() external onlyOwner {
        _pause();
    }
    
    /**
     * @dev Unpause vault
     * @notice Only owner
     */
    function unpause() external onlyOwner {
        _unpause();
    }
    
    /**
     * @dev Update oracle contract address
     * @param newOracle new oracle contract address
     * @notice Only owner
     */
    function setDisruptionOracle(address newOracle) 
        external 
        onlyOwner 
    {
        require(newOracle != address(0), "Invalid oracle address");
        disruptionOracle = IFIGGYOracle(newOracle);
        emit ConfigurationUpdated("disruptionOracle", uint256(uint160(newOracle)), uint64(block.timestamp));
    }
    
    /**
     * @dev Update token verification window
     * @param newWindow new window in seconds
     * @notice Only owner
     */
    function setTokenVerificationWindow(uint256 newWindow) 
        external 
        onlyOwner 
    {
        require(newWindow > 0, "Window must be > 0");
        tokenVerificationWindow = newWindow;
        emit ConfigurationUpdated("tokenVerificationWindow", newWindow, uint64(block.timestamp));
    }
    
    /**
     * @dev Update payout expiry time
     * @param newExpiryTime new expiry duration in seconds
     * @notice Only owner
     */
    function setPayoutExpiryTime(uint256 newExpiryTime) 
        external 
        onlyOwner 
    {
        require(newExpiryTime > 0, "Expiry time must be > 0");
        payoutExpiryTime = newExpiryTime;
        emit ConfigurationUpdated("payoutExpiryTime", newExpiryTime, uint64(block.timestamp));
    }
    
    /**
     * @dev Update minimum reserve threshold
     * @param newThreshold new minimum in USDC (wei, 6 decimals)
     * @notice Only owner
     */
    function setMinReserveThreshold(uint256 newThreshold) 
        external 
        onlyOwner 
    {
        minReserveThreshold = newThreshold;
        emit ConfigurationUpdated("minReserveThreshold", newThreshold, uint64(block.timestamp));
    }
    
    // ============ PAYOUT REQUEST FLOW ============
    
    /**
     * @dev Request payout for a verified worker disruption claim
     * 
     * Triggers the oracle to verify disruption on-chain:
     * 1. Validates payout claim (amount, token, reserves)
     * 2. Creates PayoutClaim record (status=Pending)
     * 3. Calls oracle.requestDisruptionVerification(tokenId)
     * 4. Oracle will callback with fulfillPayout(tokenId, confirmed)
     * 
     * @param tokenId PoW token ID from FIGGYPoWToken
     * @param amountUSDC payout amount in USDC wei (6 decimals)
     * @param claimRef FIGGY internal claim_id (for tracking)
     * @param workerAddress wallet to receive USDC
     * 
     * @notice Only PAYOUT_REQUESTOR role (FIGGY backend)
     * @notice Vault must not be paused
     */
    function requestPayout(
        uint256 tokenId,
        uint256 amountUSDC,
        bytes32 claimRef,
        address workerAddress
    ) 
        external 
        onlyRole(PAYOUT_REQUESTOR) 
        whenNotPaused 
        nonReentrant 
    {
        // Validate inputs
        if (amountUSDC == 0) revert InvalidAmount(0);
        if (workerAddress == address(0)) revert UnauthorizedCaller(address(0));
        
        // Check if claim already exists
        if (claims[tokenId].requestedAt != 0) {
            revert ClaimAlreadyExists(tokenId);
        }
        
        // Check vault has sufficient reserves
        if (totalReserves < amountUSDC) {
            revert InsufficientReserves(amountUSDC, totalReserves);
        }
        
        // Create claim record (status=Pending)
        claims[tokenId] = PayoutClaim({
            workerAddress: workerAddress,
            tokenId: tokenId,
            requestedAmountUSDC: amountUSDC,
            releasedAmountUSDC: 0,
            status: PayoutStatus.Pending,
            requestedAt: uint64(block.timestamp),
            releasedAt: 0,
            claimRef: claimRef,
            oracleRequestId: bytes32(0)
        });
        
        // Record reverse lookup
        claimRefToTokenId[claimRef] = tokenId;
        
        // Request oracle verification
        // The oracle will call fulfillPayout(tokenId, confirmed) as callback
        bytes32 requestId = disruptionOracle.requestDisruptionVerification(tokenId);
        claims[tokenId].oracleRequestId = requestId;
        oracleRequestIdToTokenId[requestId] = tokenId;
        
        emit PayoutRequested(
            tokenId,
            claimRef,
            workerAddress,
            amountUSDC,
            uint64(block.timestamp)
        );
    }
    
    /**
     * @dev Fulfill payout after oracle verification (called by oracle contract)
     * 
     * This is the callback from Chainlink oracle after verifying disruption.
     * If BOTH conditions are met:
     *   1. Oracle confirms disruption (oracleConfirmed=true)
     *   2. PoW token is valid (verifyWorkerToken passes)
     * Then:
     *   - Transfer USDC to worker
     *   - Mark claim as Released
     *   - Mark PoW token as released (prevent double-pay)
     *   - Emit PayoutReleased event
     * 
     * If not confirmed:
     *   - Mark claim as Rejected
     *   - USDC stays in vault
     *   - Emit PayoutRejected event
     * 
     * @param tokenId the PoW token ID
     * @param oracleConfirmed whether oracle verified the disruption
     * @param reason optional rejection reason (for logging)
     * 
     * @notice Only callable by ORACLE_FULFILLER (oracle contract)
     */
    function fulfillPayout(
        uint256 tokenId,
        bool oracleConfirmed,
        string calldata reason
    ) 
        external 
        onlyRole(ORACLE_FULFILLER) 
        nonReentrant 
    {
        PayoutClaim storage claim = claims[tokenId];
        
        // Verify claim exists and is pending
        if (claim.requestedAt == 0) revert ClaimNotFound(tokenId);
        if (claim.status != PayoutStatus.Pending) {
            revert InvalidStatus(claim.status, PayoutStatus.Pending);
        }
        
        // If oracle rejected, mark as rejected
        if (!oracleConfirmed) {
            claim.status = PayoutStatus.Rejected;
            emit PayoutRejected(tokenId, claim.claimRef, reason, uint64(block.timestamp));
            return;
        }
        
        // Oracle confirmed, now verify PoW token
        // Get token data to extract worker ID hash and timestamp
        (
            bytes32 workerIdHash,
            ,
            ,
            ,
            uint64 sessionTimestamp,
            bool payoutReleased
        ) = powToken.getTokenData(tokenId);
        
        // Verify token hasn't been released already
        if (payoutReleased) {
            claim.status = PayoutStatus.Rejected;
            emit PayoutRejected(tokenId, claim.claimRef, "Token already released", uint64(block.timestamp));
            return;
        }
        
        // Verify token is valid within time window
        uint64 minTime = claim.requestedAt > tokenVerificationWindow 
            ? claim.requestedAt - uint64(tokenVerificationWindow)
            : 0;
        uint64 maxTime = claim.requestedAt + uint64(tokenVerificationWindow);
        
        (bool tokenValid, ) = powToken.verifyWorkerToken(workerIdHash, minTime, maxTime);
        
        if (!tokenValid) {
            claim.status = PayoutStatus.Rejected;
            emit PayoutRejected(tokenId, claim.claimRef, "Token verification failed", uint64(block.timestamp));
            return;
        }
        
        // All conditions passed: release payout
        uint256 amountToRelease = claim.requestedAmountUSDC;
        require(amountToRelease <= totalReserves, "Insufficient reserves at release time");
        
        // Update state BEFORE transfer (checks-effects-interactions)
        claim.status = PayoutStatus.Released;
        claim.releasedAmountUSDC = amountToRelease;
        claim.releasedAt = uint64(block.timestamp);
        totalReserves -= amountToRelease;
        workerPayoutTotals[claim.workerAddress] += amountToRelease;
        
        // Mark token as released (prevents double-pay)
        powToken.markPayoutReleased(tokenId);
        
        // Transfer USDC to worker
        bool success = usdcToken.transfer(claim.workerAddress, amountToRelease);
        require(success, "USDC transfer to worker failed");
        
        emit PayoutReleased(
            tokenId,
            claim.claimRef,
            claim.workerAddress,
            amountToRelease,
            totalReserves,
            uint64(block.timestamp)
        );
    }
    
    // ============ TIME-BASED OPERATIONS ============
    
    /**
     * @dev Expire a stale payout request (Pending > expiry time)
     * 
     * Anyone can expire a stale claim after payoutExpiryTime has passed.
     * This returns USDC to vault reserves.
     * 
     * @param tokenId the token ID with stale claim
     * @notice Can be called by anyone after expiry time
     */
    function expireStale(uint256 tokenId) 
        external 
        nonReentrant 
    {
        PayoutClaim storage claim = claims[tokenId];
        
        // Verify claim exists and is still pending
        if (claim.requestedAt == 0) revert ClaimNotFound(tokenId);
        if (claim.status != PayoutStatus.Pending) {
            revert InvalidStatus(claim.status, PayoutStatus.Pending);
        }
        
        // Check if enough time has passed
        uint256 timeElapsed = block.timestamp - claim.requestedAt;
        if (timeElapsed < payoutExpiryTime) {
            revert NotTimeForExpiry(timeElapsed, payoutExpiryTime);
        }
        
        // Mark as expired (USDC stays in vault)
        claim.status = PayoutStatus.Expired;
        
        emit PayoutExpired(
            tokenId,
            claim.claimRef,
            claim.workerAddress,
            claim.requestedAmountUSDC,
            uint64(block.timestamp)
        );
    }
    
    // ============ VIEW FUNCTIONS ============
    
    /**
     * @dev Get full claim details for a token ID
     * @param tokenId the PoW token ID
     * @return claim the PayoutClaim struct
     */
    function getClaim(uint256 tokenId) 
        external 
        view 
        returns (PayoutClaim memory claim) 
    {
        return claims[tokenId];
    }
    
    /**
     * @dev Get total payout amount for a worker address
     * @param workerAddress worker's wallet address
     * @return totalReleased sum of all released payouts
     */
    function getWorkerPayoutTotal(address workerAddress) 
        external 
        view 
        returns (uint256 totalReleased) 
    {
        return workerPayoutTotals[workerAddress];
    }
    
    /**
     * @dev Get vault health metrics
     * @return _totalReserves current USDC in vault
     * @return _reservesAboveThreshold true if above minimum threshold
     */
    function getVaultHealth() 
        external 
        view 
        returns (uint256 _totalReserves, bool _reservesAboveThreshold) 
    {
        _totalReserves = totalReserves;
        _reservesAboveThreshold = totalReserves >= minReserveThreshold;
    }
    
    /**
     * @dev Check if a claim is in a specific status
     * @param tokenId the token ID
     * @param status the status to check
     * @return isStatus true if claim has this status
     */
    function isClaimStatus(uint256 tokenId, PayoutStatus status) 
        external 
        view 
        returns (bool isStatus) 
    {
        return claims[tokenId].status == status;
    }
}
