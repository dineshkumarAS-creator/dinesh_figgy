// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

/**
 * @title FIGGYPoWToken
 * @dev ERC-721 NFT representing a verified worker proof-of-work activity claim
 * 
 * Each token encodes:
 * - Worker ID (hashed for privacy)
 * - Delivery zone
 * - Active working hours
 * - Delivery attempt count
 * - Environmental disruption conditions
 * - Composite claim fraud score
 * - Session timestamp (immutable proof-of-work)
 * 
 * Tokens are minted by FIGGY backend when a claim is verified.
 * Tokens are marked as "payoutReleased" when insurance payout is disbursed.
 * 
 * Purpose: Create immutable on-chain record of all verified worker sessions.
 * Network: Polygon (low gas fees, high throughput)
 */

contract FIGGYPoWToken is ERC721, ERC721URIStorage, Ownable, Pausable {
    using Counters for Counters.Counter;
    
    // ========================================================================
    // TYPES
    // ========================================================================
    
    struct WorkerActivityRecord {
        bytes32 workerIdHash;           // keccak256(worker_id) - privacy
        string deliveryZoneId;          // e.g., "Chennai_Zone_7"
        uint32 activeMinutes;           // Duration of active work (minutes)
        uint16 deliveryAttempts;        // Number of delivery attempts
        string triggerType;             // "rainfall" | "aqi" | "curfew_strike" | "composite"
        uint8 disruptionSeverity;       // 0-100 (composite_disruption_index * 100)
        uint8 compositeClaimScore;      // 0-100 (ML fraud likelihood)
        uint64 sessionTimestamp;        // Unix timestamp of disruption session START
        bool payoutReleased;            // True when payout disbursed
        bytes32 featureVectorHash;      // SHA-256(off-chain FeatureVector JSON) for integrity
    }
    
    // ========================================================================
    // STATE
    // ========================================================================
    
    Counters.Counter private _tokenIdCounter;
    
    /// @dev Mapping from tokenId to WorkerActivityRecord (immutable once minted)
    mapping(uint256 => WorkerActivityRecord) public tokenData;
    
    /// @dev Mapping from workerIdHash to array of tokenIds (for efficient lookup)
    mapping(bytes32 => uint256[]) public workerTokens;
    
    /// @dev FIGGYPayoutVault authorized to call markPayoutReleased (set at deployment)
    address public payoutVaultAddress;
    
    // ========================================================================
    // EVENTS
    // ========================================================================
    
    event PoWTokenMinted(
        uint256 indexed tokenId,
        bytes32 indexed workerIdHash,
        uint64 sessionTimestamp,
        string deliveryZoneId,
        uint8 disruptionSeverity
    );
    
    event PayoutReleased(
        uint256 indexed tokenId,
        bytes32 indexed workerIdHash,
        uint256 timestamp
    );
    
    event PayoutVaultSet(address indexed vaultAddress);
    
    // ========================================================================
    // CONSTRUCTOR
    // ========================================================================
    
    constructor() ERC721("FIGGY Proof of Work Token", "FIGGY-PoW") {
        _tokenIdCounter.increment(); // Start tokenIds at 1
    }
    
    // ========================================================================
    // PUBLIC: MINTING (onlyOwner)
    // ========================================================================
    
    /**
     * @dev Mint a new PoW token
     * 
     * @param to Recipient address (typically worker address or FIGGY backend)
     * @param record WorkerActivityRecord containing all activity data
     * @param tokenURI IPFS URI pointing to ERC-721 metadata
     * 
     * @return tokenId New token ID
     * 
     * Requirements:
     * - Only owner (FIGGY backend) can mint
     * - Contract must not be paused
     * - workerIdHash must not be zero
     * - sessionTimestamp must not be zero
     */
    function mintPoWToken(
        address to,
        WorkerActivityRecord calldata record,
        string calldata tokenURI
    ) public onlyOwner whenNotPaused returns (uint256) {
        require(to != address(0), "Invalid recipient");
        require(record.workerIdHash != bytes32(0), "workerIdHash cannot be zero");
        require(record.sessionTimestamp > 0, "sessionTimestamp must be set");
        require(bytes(record.deliveryZoneId).length > 0, "deliveryZoneId required");
        
        uint256 tokenId = _tokenIdCounter.current();
        _tokenIdCounter.increment();
        
        // Mint ERC-721 token
        _safeMint(to, tokenId);
        _setTokenURI(tokenId, tokenURI);
        
        // Store activity record (immutable)
        tokenData[tokenId] = WorkerActivityRecord({
            workerIdHash: record.workerIdHash,
            deliveryZoneId: record.deliveryZoneId,
            activeMinutes: record.activeMinutes,
            deliveryAttempts: record.deliveryAttempts,
            triggerType: record.triggerType,
            disruptionSeverity: record.disruptionSeverity,
            compositeClaimScore: record.compositeClaimScore,
            sessionTimestamp: record.sessionTimestamp,
            payoutReleased: false,
            featureVectorHash: record.featureVectorHash
        });
        
        // Index token by workerIdHash for efficient lookup
        workerTokens[record.workerIdHash].push(tokenId);
        
        emit PoWTokenMinted(
            tokenId,
            record.workerIdHash,
            record.sessionTimestamp,
            record.deliveryZoneId,
            record.disruptionSeverity
        );
        
        return tokenId;
    }
    
    // ========================================================================
    // PUBLIC: QUERIES
    // ========================================================================
    
    /**
     * @dev Get WorkerActivityRecord for a token
     * @param tokenId Token to look up
     * @return Activity record (or zero-struct if token doesn't exist)
     */
    function getTokenData(uint256 tokenId)
        public
        view
        returns (WorkerActivityRecord memory)
    {
        return tokenData[tokenId];
    }
    
    /**
     * @dev Get all token IDs for a worker (by workerIdHash)
     * @param workerIdHash Hashed worker ID
     * @return Array of token IDs belonging to this worker
     */
    function getWorkerTokens(bytes32 workerIdHash)
        public
        view
        returns (uint256[] memory)
    {
        return workerTokens[workerIdHash];
    }
    
    /**
     * @dev Verify if valid, non-payout-released token exists in time window
     * 
     * @param workerIdHash Hashed worker ID to check
     * @param minTimestamp Minimum session timestamp (inclusive)
     * @param maxTimestamp Maximum session timestamp (inclusive)
     * 
     * @return exists True if valid token found
     * @return tokenId ID of first matching token (0 if none)
     * 
     * Used by FIGGYPayoutVault to gate payout releases.
     */
    function verifyWorkerToken(
        bytes32 workerIdHash,
        uint64 minTimestamp,
        uint64 maxTimestamp
    ) public view returns (bool exists, uint256 tokenId) {
        uint256[] memory tokens = workerTokens[workerIdHash];
        
        for (uint256 i = 0; i < tokens.length; i++) {
            uint256 tid = tokens[i];
            WorkerActivityRecord memory record = tokenData[tid];
            
            // Check: token exists, not yet paid out, within timestamp window
            if (
                !record.payoutReleased &&
                record.sessionTimestamp >= minTimestamp &&
                record.sessionTimestamp <= maxTimestamp
            ) {
                return (true, tid);
            }
        }
        
        return (false, 0);
    }
    
    /**
     * @dev Get current token count (for pagination, admin)
     * @return Current tokenId counter (next tokenId to be minted)
     */
    function getCurrentTokenId() public view returns (uint256) {
        return _tokenIdCounter.current();
    }
    
    // ========================================================================
    // INTERNAL: PAYOUT TRACKING
    // ========================================================================
    
    /**
     * @dev Mark token as paid out (called by FIGGYPayoutVault)
     * @param tokenId Token to mark as released
     * 
     * Requirements:
     * - Only FIGGYPayoutVault can call this
     * - Token must exist
     * - Cannot be called twice (payoutReleased must be false)
     */
    function markPayoutReleased(uint256 tokenId) external {
        require(msg.sender == payoutVaultAddress, "Only PayoutVault can mark released");
        require(_exists(tokenId), "Token does not exist");
        require(!tokenData[tokenId].payoutReleased, "Payout already released");
        
        tokenData[tokenId].payoutReleased = true;
        
        emit PayoutReleased(
            tokenId,
            tokenData[tokenId].workerIdHash,
            block.timestamp
        );
    }
    
    /**
     * @dev Set FIGGYPayoutVault address (called during initialization)
     * @param vaultAddress Address of deployed FIGGYPayoutVault
     * 
     * Requirements:
     * - Only owner
     * - Address must not be zero
     */
    function setPayoutVault(address vaultAddress) external onlyOwner {
        require(vaultAddress != address(0), "Invalid vault address");
        payoutVaultAddress = vaultAddress;
        emit PayoutVaultSet(vaultAddress);
    }
    
    // ========================================================================
    // ADMIN: PAUSE / RESUME
    // ========================================================================
    
    /**
     * @dev Emergency pause: stop all minting
     * @notice Allows owner to pause contract in case of security issues
     */
    function pause() public onlyOwner {
        _pause();
    }
    
    /**
     * @dev Resume from pause
     */
    function unpause() public onlyOwner {
        _unpause();
    }
    
    // ========================================================================
    // INTERNAL: ERC-721 OVERRIDES
    // ========================================================================
    
    function _burn(uint256 tokenId)
        internal
        override(ERC721, ERC721URIStorage)
    {
        super._burn(tokenId);
    }
    
    function tokenURI(uint256 tokenId)
        public
        view
        override(ERC721, ERC721URIStorage)
        returns (string memory)
    {
        return super.tokenURI(tokenId);
    }
    
    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC721URIStorage)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
