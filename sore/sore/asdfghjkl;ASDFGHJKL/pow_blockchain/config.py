"""
Configuration for FIGGY PoW Blockchain Layer.

Loaded from environment variables.
"""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class BlockchainConfig(BaseSettings):
    """Blockchain layer configuration."""
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
    
    # ========================================================================
    # POLYGON NETWORK
    # ========================================================================
    
    BLOCKCHAIN_NETWORK: str = "mumbai"
    """Network: 'mumbai' (testnet), 'polygon' (mainnet), 'localhost' (hardhat)"""
    
    POLYGON_RPC_URL: str = "https://rpc-mumbai.maticvigil.com"
    """RPC endpoint for Polygon network"""
    
    POLYGONSCAN_API_KEY: str = ""
    """API key for Polygonscan (for verification)"""
    
    # ========================================================================
    # SMART CONTRACT ADDRESSES
    # ========================================================================
    
    POW_TOKEN_ADDRESS: str
    """FIGGYPoWToken contract address (deployed)"""
    
    PAYOUT_VAULT_ADDRESS: str
    """FIGGYPayoutVault contract address (deployed)"""
    
    # ========================================================================
    # MINTING KEYS
    # ========================================================================
    
    FIGGY_MINTER_PRIVATE_KEY: str
    """Private key for minting transactions (NEVER commit to git)"""
    
    # ========================================================================
    # GAS MANAGEMENT
    # ========================================================================
    
    MAX_GAS_GWEI: float = 50.0
    """Max gas price (gwei) to accept. If exceeded, queue for retry."""
    
    GAS_RETRY_DELAY_MINUTES: int = 5
    """Minutes to wait before retrying high-gas mint"""
    
    # ========================================================================
    # IPFS / PINATA
    # ========================================================================
    
    PINATA_API_KEY: str
    """Pinata API key from https://app.pinata.cloud"""
    
    PINATA_API_SECRET: str
    """Pinata API secret"""
    
    PINATA_GATEWAY_URL: str = "https://gateway.pinata.cloud"
    """Pinata public gateway for metadata retrieval"""
    
    # ========================================================================
    # DATABASE
    # ========================================================================
    
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/figgy"
    """PostgreSQL connection string for async SQLAlchemy"""
    
    # ========================================================================
    # LOGGING
    # ========================================================================
    
    LOG_LEVEL: str = "INFO"
    """Logging level: DEBUG, INFO, WARNING, ERROR"""
    
    # ========================================================================
    # DEPLOYMENT
    # ========================================================================
    
    HARDHAT_COMPILED_ARTIFACTS: str = "./artifacts/contracts"
    """Path to Hardhat compiled contract artifacts"""
    
    DEPLOYMENTS_DIR: str = "./deployments"
    """Directory containing deployment info (deployments.json per network)"""


# Singleton instance
blockchain_config = BlockchainConfig()
