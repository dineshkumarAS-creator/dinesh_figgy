// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IFIGGYPoWToken
 * @dev Interface for FIGGY Proof-of-Work Activity Token (ERC-721)
 * 
 * This interface defines the external functions required by the insurance vault
 * to verify worker PoW tokens and mark payouts as released.
 */
interface IFIGGYPoWToken {
    
    /**
     * @dev Verify that a worker has a valid PoW token within a time window
     * 
     * Used by insurance vault to gate payouts:
     * - Confirms token exists and belongs to the worker
     * - Validates token was created within acceptable timeframe
     * - Prevents payouts for non-existent workers
     * 
     * @param workerIdHash keccak256 hash of worker ID (privacy protection)
     * @param minTime minimum token creation timestamp (to prevent stale tokens)
     * @param maxTime maximum token creation timestamp
     * @return verified true if token exists, valid, and within time window
     * @return tokenId the valid token ID (0 if not verified)
     */
    function verifyWorkerToken(
        bytes32 workerIdHash,
        uint64 minTime,
        uint64 maxTime
    ) external view returns (bool verified, uint256 tokenId);
    
    /**
     * @dev Mark a PoW token as having its payout released
     * 
     * Called by insurance vault AFTER transferring funds to worker.
     * Prevents double-payouts by setting immutable flag on token.
     * 
     * @param tokenId the PoW token ID to mark as released
     * @notice Set to be called only by the authorized payout vault
     */
    function markPayoutReleased(uint256 tokenId) external;
    
    /**
     * @dev Get complete token data for a specific token ID
     * 
     * @param tokenId the token ID to retrieve
     * @return workerIdHash keccak256(worker_id) for privacy
     * @return activeMinutes duration of activity
     * @return disruptionSeverity 0-100 disruption index * 100
     * @return compositeClaimScore ML fraud score 0-100
     * @return sessionTimestamp when the activity occurred
     * @return payoutReleased whether payout was already released
     */
    function getTokenData(uint256 tokenId) external view returns (
        bytes32 workerIdHash,
        uint32 activeMinutes,
        uint8 disruptionSeverity,
        uint8 compositeClaimScore,
        uint64 sessionTimestamp,
        bool payoutReleased
    );
}
