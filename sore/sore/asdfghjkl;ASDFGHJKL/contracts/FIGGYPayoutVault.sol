// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface IFIGGYPoWToken {
    struct WorkerActivityRecord {
        bytes32 workerIdHash;
        string deliveryZoneId;
        uint32 activeMinutes;
        uint16 deliveryAttempts;
        string triggerType;
        uint8 disruptionSeverity;
        uint8 compositeClaimScore;
        uint64 sessionTimestamp;
        bool payoutReleased;
        bytes32 featureVectorHash;
    }
    
    function verifyWorkerToken(
        bytes32 workerIdHash,
        uint64 minTimestamp,
        uint64 maxTimestamp
    ) external view returns (bool exists, uint256 tokenId);
    
    function getTokenData(uint256 tokenId)
        external
        view
        returns (WorkerActivityRecord memory);
    
    function markPayoutReleased(uint256 tokenId) external;
}

/**
 * @title FIGGYPayoutVault
 * @dev Holds MATIC/USDC insurance funds, releases payouts on condition
 * 
 * Purpose:
 * - Accept deposits (insurance funds from FIGGY/reinsurers)
 * - Release payouts only if valid PoW token exists
 * - Track all payout history on-chain
 * - Only FIGGY backend (minter role) can initiate payouts
 * 
 * Security:
 * - AccessControl for role-based authorization
 * - ReentrancyGuard to prevent reentrancy attacks
 * - Pausable for emergency stop
 * - Balance checks to prevent over-withdrawal
 */

contract FIGGYPayoutVault is AccessControl, ReentrancyGuard, Pausable {
    
    // ========================================================================
    // TYPES
    // ========================================================================
    
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    
    struct PayoutRecord {
        uint256 tokenId;
        bytes32 workerIdHash;
        address recipient;
        uint256 amountWei;
        uint256 timestamp;
        string txReason; // "claim_payout" | "appeal_reversal" etc
    }
    
    // ========================================================================
    // STATE
    // ========================================================================
    
    IFIGGYPoWToken public powTokenContract;
    
    /// @dev NATIVE currency (MATIC) balance per worker
    mapping(address => uint256) public nativeBalance;
    
    /// @dev USDC token contract (optional ERC-20 payments)
    IERC20 public usdcToken;
    mapping(address => uint256) public usdcBalance;
    
    /// @dev History of all payouts for audit trail
    PayoutRecord[] public payoutHistory;
    
    /// @dev Total MATIC deposited (for accounting)
    uint256 public totalNativeDeposited;
    
    /// @dev Total USDC deposited (for accounting)
    uint256 public totalUsdcDeposited;
    
    // ========================================================================
    // EVENTS
    // ========================================================================
    
    event Deposit(address indexed depositor, uint256 amount, string currency);
    
    event PayoutExecuted(
        uint256 indexed tokenId,
        bytes32 indexed workerIdHash,
        address indexed recipient,
        uint256 amountWei,
        string currency
    );
    
    event PayoutFailed(
        uint256 indexed tokenId,
        bytes32 indexed workerIdHash,
        string reason
    );
    
    event PoWTokenContractSet(address indexed powTokenAddress);
    event USDCTokenSet(address indexed usdcAddress);
    
    // ========================================================================
    // CONSTRUCTOR
    // ========================================================================
    
    constructor(address _powTokenAddress) {
        require(_powTokenAddress != address(0), "Invalid PoW token address");
        
        powTokenContract = IFIGGYPoWToken(_powTokenAddress);
        
        // Grant deployer the MINTER_ROLE (FIGGY backend)
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
    }
    
    // ========================================================================
    // DEPOSIT: Accept insurance funds
    // ========================================================================
    
    /**
     * @dev Deposit native MATIC into vault
     * 
     * @notice Anyone can deposit, but only MINTER_ROLE can withdraw
     */
    function depositNative() external payable whenNotPaused {
        require(msg.value > 0, "Deposit amount must be > 0");
        
        nativeBalance[msg.sender] += msg.value;
        totalNativeDeposited += msg.value;
        
        emit Deposit(msg.sender, msg.value, "MATIC");
    }
    
    /**
     * @dev Deposit USDC ERC-20 tokens
     * @param amount Amount of USDC to deposit (in wei, 6 decimals)
     */
    function depositUsdc(uint256 amount) external whenNotPaused {
        require(address(usdcToken) != address(0), "USDC not configured");
        require(amount > 0, "Deposit amount must be > 0");
        
        // Transfer USDC from caller to vault
        require(
            usdcToken.transferFrom(msg.sender, address(this), amount),
            "USDC transfer failed"
        );
        
        usdcBalance[msg.sender] += amount;
        totalUsdcDeposited += amount;
        
        emit Deposit(msg.sender, amount, "USDC");
    }
    
    // ========================================================================
    // WITHDRAWAL: Release payouts (condition-gated)
    // ========================================================================
    
    /**
     * @dev Release payout in MATIC to worker
     * 
     * @param tokenId PoW token ID (proof of work)
     * @param workerIdHash Hashed worker ID (from PoW token)
     * @param recipient Worker's address to receive funds
     * @param amountWei Amount to pay (in wei)
     * @param minTimestamp Minimum session timestamp (for verification window)
     * @param maxTimestamp Maximum session timestamp (for verification window)
     * 
     * Requirements:
     * - Only MINTER_ROLE (FIGGY backend) can call
     * - PoW token must exist and be valid (not already paid)
     * - Vault must have sufficient MATIC balance
     * - Transaction must not reenter
     * 
     * Effects:
     * - Transfers MATIC to recipient
     * - Marks PoW token as payoutReleased=true
     * - Records payout in history
     */
    function releasePayoutNative(
        uint256 tokenId,
        bytes32 workerIdHash,
        address recipient,
        uint256 amountWei,
        uint64 minTimestamp,
        uint64 maxTimestamp
    ) external onlyRole(MINTER_ROLE) nonReentrant whenNotPaused {
        require(recipient != address(0), "Invalid recipient");
        require(amountWei > 0, "Amount must be > 0");
        require(amountWei <= address(this).balance, "Insufficient vault balance");
        
        // Verify PoW token (condition-gated payout)
        (bool exists, uint256 verifiedTokenId) = powTokenContract.verifyWorkerToken(
            workerIdHash,
            minTimestamp,
            maxTimestamp
        );
        require(exists, "No valid PoW token found");
        
        // Double-check token ID matches
        require(verifiedTokenId == tokenId, "Token ID mismatch");
        
        // Transfer funds
        (bool success, ) = payable(recipient).call{value: amountWei}("");
        require(success, "Transfer failed");
        
        // Mark token as released on-chain
        powTokenContract.markPayoutReleased(tokenId);
        
        // Record in history
        payoutHistory.push(PayoutRecord({
            tokenId: tokenId,
            workerIdHash: workerIdHash,
            recipient: recipient,
            amountWei: amountWei,
            timestamp: block.timestamp,
            txReason: "claim_payout"
        }));
        
        emit PayoutExecuted(
            tokenId,
            workerIdHash,
            recipient,
            amountWei,
            "MATIC"
        );
    }
    
    /**
     * @dev Release payout in USDC to worker
     * 
     * @param tokenId PoW token ID (proof of work)
     * @param workerIdHash Hashed worker ID
     * @param recipient Recipient address
     * @param amountUsdc Amount in USDC (with 6 decimals)
     * @param minTimestamp Session timestamp window minimum
     * @param maxTimestamp Session timestamp window maximum
     */
    function releasePayoutUsdc(
        uint256 tokenId,
        bytes32 workerIdHash,
        address recipient,
        uint256 amountUsdc,
        uint64 minTimestamp,
        uint64 maxTimestamp
    ) external onlyRole(MINTER_ROLE) nonReentrant whenNotPaused {
        require(address(usdcToken) != address(0), "USDC not configured");
        require(recipient != address(0), "Invalid recipient");
        require(amountUsdc > 0, "Amount must be > 0");
        require(amountUsdc <= usdcToken.balanceOf(address(this)), "Insufficient USDC");
        
        // Verify PoW token
        (bool exists, uint256 verifiedTokenId) = powTokenContract.verifyWorkerToken(
            workerIdHash,
            minTimestamp,
            maxTimestamp
        );
        require(exists, "No valid PoW token found");
        require(verifiedTokenId == tokenId, "Token ID mismatch");
        
        // Transfer USDC
        require(
            usdcToken.transfer(recipient, amountUsdc),
            "USDC transfer failed"
        );
        
        // Mark token as released
        powTokenContract.markPayoutReleased(tokenId);
        
        // Record in history
        payoutHistory.push(PayoutRecord({
            tokenId: tokenId,
            workerIdHash: workerIdHash,
            recipient: recipient,
            amountWei: amountUsdc,
            timestamp: block.timestamp,
            txReason: "claim_payout"
        }));
        
        emit PayoutExecuted(
            tokenId,
            workerIdHash,
            recipient,
            amountUsdc,
            "USDC"
        );
    }
    
    // ========================================================================
    // QUERIES
    // ========================================================================
    
    /**
     * @dev Get payout history
     * @return Array of all PayoutRecords
     */
    function getPayoutHistory() external view returns (PayoutRecord[] memory) {
        return payoutHistory;
    }
    
    /**
     * @dev Get payout count
     */
    function getPayoutCount() external view returns (uint256) {
        return payoutHistory.length;
    }
    
    /**
     * @dev Get vault balance (MATIC)
     */
    function getNativeBalance() external view returns (uint256) {
        return address(this).balance;
    }
    
    /**
     * @dev Get USDC balance
     */
    function getUsdcBalance() external view returns (uint256) {
        if (address(usdcToken) == address(0)) return 0;
        return usdcToken.balanceOf(address(this));
    }
    
    // ========================================================================
    // ADMIN: Configuration
    // ========================================================================
    
    /**
     * @dev Set USDC token contract address
     * @param _usdcAddress ERC-20 USDC contract
     */
    function setUsdcToken(address _usdcAddress) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_usdcAddress != address(0), "Invalid address");
        usdcToken = IERC20(_usdcAddress);
        emit USDCTokenSet(_usdcAddress);
    }
    
    /**
     * @dev Grant MINTER_ROLE to address (FIGGY backend)
     */
    function grantMinterRole(address account) external onlyRole(DEFAULT_ADMIN_ROLE) {
        grantRole(MINTER_ROLE, account);
    }
    
    /**
     * @dev Revoke MINTER_ROLE from address
     */
    function revokeMinterRole(address account) external onlyRole(DEFAULT_ADMIN_ROLE) {
        revokeRole(MINTER_ROLE, account);
    }
    
    /**
     * @dev Emergency pause
     */
    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }
    
    /**
     * @dev Resume from pause
     */
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }
    
    // ========================================================================
    // RECEIVE: Allow contract to receive MATIC
    // ========================================================================
    
    receive() external payable {
        totalNativeDeposited += msg.value;
    }
}
