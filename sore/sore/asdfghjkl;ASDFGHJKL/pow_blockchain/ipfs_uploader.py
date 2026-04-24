"""
IPFS metadata uploader for FIGGY PoW tokens.

Uses Pinata API to pin ERC-721 metadata to IPFS.
Metadata follows ERC-721 metadata standard with privacy considerations.
"""

import json
import httpx
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class IPFSUploadRequest(BaseModel):
    """Request to upload metadata to IPFS."""
    
    worker_tier: str = Field(..., description="new | silver | gold | flagged")
    delivery_zone: str
    active_minutes: int
    trigger_type: str
    disruption_severity: int = Field(..., ge=0, le=100)
    composite_claim_score: int = Field(..., ge=0, le=100)
    session_date: str = Field(..., description="ISO date YYYY-MM-DD")
    settlement_zone_json: Optional[str] = Field(None, description="Delivery zone geometry as JSON string")


class IPFSUploadResponse(BaseModel):
    """Response from IPFS upload."""
    
    ipfs_hash: str = Field(..., description="IPFS CID (Qm...)")
    ipfs_uri: str = Field(..., description="ipfs://Qm... URI for token metadata")
    timestamp: datetime


class IPFSMetadataUploader:
    """
    Upload ERC-721 metadata to IPFS via Pinata.
    
    Privacy:
    - Worker ID is NOT included in public metadata
    - Only hashed version (workerIdHash) is stored on-chain
    - This metadata is read-only, immutable record of activity
    """
    
    def __init__(self, pinata_api_key: str, pinata_api_secret: str):
        """
        Initialize uploader.
        
        Args:
            pinata_api_key: Pinata API key from https://app.pinata.cloud
            pinata_api_secret: Pinata API secret
        """
        self.pinata_api_key = pinata_api_key
        self.pinata_api_secret = pinata_api_secret
        self.pinata_base_url = "https://api.pinata.cloud"
        
        # Create Pinata auth headers
        self.headers = {
            "pinata_api_key": pinata_api_key,
            "pinata_secret_api_key": pinata_api_secret,
            "Content-Type": "application/json",
        }
    
    def upload_token_metadata(
        self,
        token_id: int,
        request: IPFSUploadRequest,
    ) -> IPFSUploadResponse:
        """
        Upload ERC-721 metadata to IPFS.
        
        Args:
            token_id: FIGGY PoW token ID
            request: Metadata request
            
        Returns:
            IPFSUploadResponse with IPFS URI
            
        Raises:
            httpx.HTTPError: If Pinata upload fails
        """
        # Build ERC-721 metadata
        metadata = {
            "name": f"FIGGY PoW Token #{token_id}",
            "description": (
                "Proof of Work activity token for verified disruption claim. "
                "This token encodes environmental conditions and worker activity "
                "during a disruption event, creating an immutable record on blockchain."
            ),
            "attributes": [
                {
                    "trait_type": "Delivery Zone",
                    "value": request.delivery_zone,
                },
                {
                    "trait_type": "Active Minutes",
                    "value": request.active_minutes,
                    "display_type": "number",
                },
                {
                    "trait_type": "Delivery Attempts",
                    "value": request.active_minutes,  # Estimate from duration
                    "display_type": "number",
                },
                {
                    "trait_type": "Trigger Type",
                    "value": request.trigger_type,
                    "enum": ["rainfall", "aqi", "curfew_strike", "composite"],
                },
                {
                    "trait_type": "Disruption Severity",
                    "value": request.disruption_severity,
                    "display_type": "number",
                    "max_value": 100,
                },
                {
                    "trait_type": "Composite Claim Score",
                    "value": request.composite_claim_score,
                    "display_type": "number",
                    "max_value": 100,
                },
                {
                    "trait_type": "Session Date",
                    "value": request.session_date,
                },
                {
                    "trait_type": "Worker Tier",
                    "value": request.worker_tier,
                    "enum": ["new", "silver", "gold", "flagged"],
                },
            ],
            "image": "ipfs://QmXxxx...",  # Placeholder for FIGGY logo/badge
            "external_url": "https://figgy.claims/",
        }
        
        # If settlement zone provided, add as metadata
        if request.settlement_zone_json:
            metadata["settlement_zone"] = json.loads(request.settlement_zone_json)
        
        # Create pinning request
        pinning_payload = {
            "pinataContent": metadata,
            "pinataOptions": {
                "cidVersion": 1,
            },
            "pinataMetadata": {
                "name": f"figgy_pow_token_{token_id}",
                "keyvalues": {
                    "token_id": str(token_id),
                    "trigger_type": request.trigger_type,
                    "worker_tier": request.worker_tier,
                },
            },
        }
        
        logger.debug(f"Uploading to IPFS: token_id={token_id}")
        
        # Upload to Pinata
        with httpx.Client() as client:
            response = client.post(
                f"{self.pinata_base_url}/pinning/pinJSONToIPFS",
                json=pinning_payload,
                headers=self.headers,
                timeout=30,
            )
            
            if response.status_code != 200:
                logger.error(
                    f"Pinata upload failed: {response.status_code} - {response.text}"
                )
                response.raise_for_status()
        
        result = response.json()
        ipfs_hash = result["IpfsHash"]
        ipfs_uri = f"ipfs://{ipfs_hash}"
        
        logger.info(f"✅ Uploaded to IPFS: {ipfs_uri}")
        
        return IPFSUploadResponse(
            ipfs_hash=ipfs_hash,
            ipfs_uri=ipfs_uri,
            timestamp=datetime.utcnow(),
        )
    
    def verify_upload(self, ipfs_hash: str) -> bool:
        """
        Verify that metadata is pinned on Pinata.
        
        Args:
            ipfs_hash: IPFS CID to check
            
        Returns:
            True if pinned, False otherwise
        """
        with httpx.Client() as client:
            response = client.get(
                f"{self.pinata_base_url}/data/pinList?hashContains={ipfs_hash}",
                headers=self.headers,
                timeout=10,
            )
            
            if response.status_code == 200:
                data = response.json()
                return len(data.get("rows", [])) > 0
        
        return False
    
    def unpin_metadata(self, ipfs_hash: str) -> bool:
        """
        Unpin metadata from Pinata (for cleanup/storage optimization).
        
        Args:
            ipfs_hash: IPFS CID to unpin
            
        Returns:
            True if successful
        """
        with httpx.Client() as client:
            response = client.delete(
                f"{self.pinata_base_url}/pinning/unpin/{ipfs_hash}",
                headers=self.headers,
                timeout=10,
            )
            
            return response.status_code in (200, 204)
