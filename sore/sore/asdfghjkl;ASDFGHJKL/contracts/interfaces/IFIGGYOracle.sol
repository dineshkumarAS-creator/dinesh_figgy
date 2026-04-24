// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IFIGGYOracle
 * @dev Interface for FIGGY Disruption Verification Oracle
 * 
 * This interface defines how the insurance vault receives oracle callbacks
 * to verify environmental disruption claims on-chain via Chainlink.
 */
interface IFIGGYOracle {
    
    /**
     * @dev Request disruption verification from Chainlink oracle
     * 
     * Initiates an off-chain verification job that calls FIGGY's API
     * to confirm whether the disruption claim is valid based on:
     * - Real-time weather data (rainfall, temperature, wind)
     * - Real-time AQI data (air quality index)
     * - Matching disruption_index from FIGGY's internal system
     * 
     * The oracle will call back to vault.fulfillPayout(tokenId, confirmed).
     * 
     * @param tokenId the PoW token ID for disruption verification
     * @return requestId Chainlink request identifier (for tracking)
     */
    function requestDisruptionVerification(uint256 tokenId) 
        external 
        returns (bytes32 requestId);
    
    /**
     * @dev Check if a disruption verification is pending for a token
     * 
     * @param tokenId the PoW token ID
     * @return pending true if oracle is still processing the request
     */
    function isDisruptionPending(uint256 tokenId) 
        external 
        view 
        returns (bool pending);
}
