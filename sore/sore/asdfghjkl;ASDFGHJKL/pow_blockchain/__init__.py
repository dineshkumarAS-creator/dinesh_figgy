"""
FIGGY Blockchain Layer - PoW Token Minting

Mints immutable ERC-721 tokens on Polygon representing proof-of-work
activity records for verified disruption claims.

Components:
- FIGGYPoWToken.sol: ERC-721 NFT contract (stores activity records)
- FIGGYPayoutVault.sol: Smart contract vault (condition-gated payouts)
- ipfs_uploader.py: Pinata integration (metadata pinning)
- minting_service.py: web3.py service (mint transactions)
- token_registry.py: PostgreSQL tracking (audit trail)

Privacy: Worker IDs are hashed (SHA-256) before on-chain storage.
Network: Polygon (low gas, high throughput) - Mumbai testnet by default.
"""

from .ipfs_uploader import (
    IPFSMetadataUploader,
    IPFSUploadRequest,
    IPFSUploadResponse,
)
from .minting_service import PoWMintingService, PoWTokenResult
from .token_registry import TokenRegistryService, PoWTokenModel, PoWTokenRecord

__all__ = [
    "IPFSMetadataUploader",
    "IPFSUploadRequest",
    "IPFSUploadResponse",
    "PoWMintingService",
    "PoWTokenResult",
    "TokenRegistryService",
    "PoWTokenModel",
    "PoWTokenRecord",
]

__version__ = "1.0.0"
