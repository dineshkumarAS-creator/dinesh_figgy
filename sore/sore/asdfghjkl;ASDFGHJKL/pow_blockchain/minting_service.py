"""
PoW Blockchain Minting Service

Mints FIGGY PoW tokens on Polygon blockchain using web3.py.
Handles transaction signing, gas management, and event parsing.
"""

import json
import logging
import os
import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, Field
from web3 import Web3
from web3.contract import Contract
from eth_account import Account
from eth_account.messages import encode_defunct

logger = logging.getLogger(__name__)


class PoWTokenResult(BaseModel):
    """Result of minting a PoW token."""
    
    token_id: int = Field(..., description="On-chain token ID")
    tx_hash: str = Field(..., description="Transaction hash (0x...)")
    block_number: int = Field(..., description="Block number where minted")
    ipfs_uri: str = Field(..., description="ipfs://Qm... URI")
    feature_vector_hash: str = Field(..., description="SHA-256 of feature vector")
    gas_used: int = Field(..., description="Gas consumed by transaction")
    minted_at: datetime
    network: str = Field(..., description="Network name: 'mumbai' | 'polygon' | 'localhost'")


class PoWMintingService:
    """
    Mints PoW tokens on Polygon blockchain.
    
    - Validates worker sessions
    - Uploads metadata to IPFS
    - Signs + broadcasts transactions
    - Tracks token IDs
    - Manages gas prices
    """
    
    def __init__(
        self,
        pow_token_address: str,
        payout_vault_address: str,
        rpc_url: str,
        private_key: str,
        network: str = "mumbai",
        max_gas_gwei: float = 100.0,
    ):
        """
        Initialize minting service.
        
        Args:
            pow_token_address: FIGGYPoWToken contract address
            payout_vault_address: FIGGYPayoutVault contract address
            rpc_url: Polygon RPC endpoint
            private_key: Private key (from FIGGY_MINTER_PRIVATE_KEY env)
            network: 'mumbai' (testnet) or 'polygon' (mainnet)
            max_gas_gwei: Max gas price to accept (gwei)
            
        Raises:
            ValueError: If private key invalid or network not recognized
        """
        self.network = network
        self.max_gas_gwei = max_gas_gwei
        self.pow_token_address = Web3.toChecksumAddress(pow_token_address)
        self.payout_vault_address = Web3.toChecksumAddress(payout_vault_address)
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if not self.w3.isConnected():
            raise ValueError(f"Cannot connect to RPC: {rpc_url}")
        
        logger.info(f"✅ Connected to {network}: {rpc_url}")
        
        # Load account from private key
        try:
            self.account = Account.from_key(private_key)
            self.minter_address = self.account.address
        except ValueError as e:
            raise ValueError(f"Invalid private key: {e}")
        
        logger.info(f"🔑 Minter account: {self.minter_address}")
        
        # Load contract ABIs
        self.pow_token_contract = self._load_contract(
            pow_token_address,
            "FIGGYPoWToken",
        )
        
        self.vault_contract = self._load_contract(
            payout_vault_address,
            "FIGGYPayoutVault",
        )
    
    def _load_contract(self, address: str, contract_name: str) -> Contract:
        """
        Load contract ABI and create contract object.
        
        Args:
            address: Contract address
            contract_name: Name of contract (e.g., 'FIGGYPoWToken')
            
        Returns:
            Web3 Contract object
            
        Raises:
            FileNotFoundError: If ABI file not found
        """
        abi_file = os.path.join(
            os.path.dirname(__file__),
            f"../abis/{contract_name}.json"
        )
        
        if not os.path.exists(abi_file):
            raise FileNotFoundError(f"ABI not found: {abi_file}")
        
        with open(abi_file, "r") as f:
            abi = json.load(f)
        
        return self.w3.eth.contract(address=address, abi=abi)
    
    async def mint_pow_token(
        self,
        token_id: int,
        worker_id_hash: str,
        delivery_zone: str,
        active_minutes: int,
        delivery_attempts: int,
        trigger_type: str,
        disruption_severity: int,
        composite_claim_score: int,
        session_timestamp: int,
        feature_vector_json: str,
        ipfs_uri: str,
    ) -> PoWTokenResult:
        """
        Mint a PoW token on-chain.
        
        Args:
            token_id: FIGGY internal token ID (for tracking)
            worker_id_hash: keccak256(worker_id) as hex string
            delivery_zone: Zone identifier
            active_minutes: Working minutes
            delivery_attempts: Number of attempts
            trigger_type: 'rainfall' | 'aqi' | 'curfew_strike' | 'composite'
            disruption_severity: 0-100
            composite_claim_score: 0-100 (ML fraud score)
            session_timestamp: Unix timestamp
            feature_vector_json: Full feature vector as JSON string (for hash)
            ipfs_uri: ipfs://Qm... URI pointing to metadata
            
        Returns:
            PoWTokenResult with transaction details
            
        Raises:
            ValueError: If validation fails
            Exception: If transaction fails
        """
        logger.info(f"🔷 Minting PoW Token #{token_id}")
        
        # Validate inputs
        if not worker_id_hash.startswith("0x"):
            raise ValueError("worker_id_hash must be hex string (0x...)")
        
        if disruption_severity < 0 or disruption_severity > 100:
            raise ValueError("disruption_severity must be 0-100")
        
        if composite_claim_score < 0 or composite_claim_score > 100:
            raise ValueError("composite_claim_score must be 0-100")
        
        # Compute feature vector hash (SHA-256)
        feature_vector_hash = hashlib.sha256(
            feature_vector_json.encode()
        ).hexdigest()
        
        # Build WorkerActivityRecord struct
        worker_activity_record = (
            worker_id_hash,  # workerIdHash
            delivery_zone,    # deliveryZoneId
            active_minutes,   # activeMinutes (uint32)
            delivery_attempts,  # deliveryAttempts (uint16)
            trigger_type,     # triggerType
            disruption_severity,  # disruptionSeverity (uint8)
            composite_claim_score,  # compositeClaimScore (uint8)
            session_timestamp,  # sessionTimestamp (uint64)
            False,            # payoutReleased
            f"0x{feature_vector_hash}",  # featureVectorHash (bytes32)
        )
        
        # Estimate gas
        try:
            gas_estimate = self.pow_token_contract.functions.mintPoWToken(
                self.minter_address,  # recipient
                worker_activity_record,
                ipfs_uri,
            ).estimateGas({"from": self.minter_address})
            
            gas_limit = int(gas_estimate * 1.2)  # Add 20% buffer
            logger.info(f"⛽ Gas estimate: {gas_estimate}, limit: {gas_limit}")
            
        except Exception as e:
            logger.error(f"❌ Gas estimation failed: {e}")
            raise
        
        # Check gas price
        gas_price_wei = self.w3.eth.gas_price
        gas_price_gwei = gas_price_wei / 1e9
        
        if gas_price_gwei > self.max_gas_gwei:
            logger.warning(
                f"⚠️  Gas price too high ({gas_price_gwei:.2f} gwei > {self.max_gas_gwei}). "
                f"Queuing for retry in 5 minutes."
            )
            raise ValueError(f"Gas price too high: {gas_price_gwei:.2f} gwei")
        
        logger.info(f"⛽ Gas price: {gas_price_gwei:.2f} gwei")
        
        # Get nonce
        nonce = self.w3.eth.get_transaction_count(self.minter_address)
        
        # Build transaction
        tx = self.pow_token_contract.functions.mintPoWToken(
            self.minter_address,
            worker_activity_record,
            ipfs_uri,
        ).buildTransaction({
            "from": self.minter_address,
            "nonce": nonce,
            "gasPrice": gas_price_wei,
            "gas": gas_limit,
            "chainId": self.w3.eth.chain_id,
        })
        
        logger.info(f"📝 Transaction built. Size: {len(str(tx))} bytes")
        
        # Sign transaction
        try:
            signed_tx = self.w3.eth.account.sign_transaction(
                tx,
                private_key=self.account.key,
            )
            logger.info(f"🔐 Transaction signed")
        except Exception as e:
            logger.error(f"❌ Transaction signing failed: {e}")
            raise
        
        # Send transaction
        try:
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_hex = tx_hash.hex()
            logger.info(f"📤 Sent transaction: {tx_hash_hex}")
        except Exception as e:
            logger.error(f"❌ Transaction broadcast failed: {e}")
            raise
        
        # Wait for receipt (with timeout)
        logger.info("⏳ Waiting for confirmation...")
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(
                tx_hash,
                timeout=120,  # 2 minute timeout
            )
        except Exception as e:
            logger.error(f"❌ Transaction timeout or failed: {e}")
            raise
        
        if receipt["status"] != 1:
            logger.error(f"❌ Transaction reverted")
            raise Exception("Transaction reverted")
        
        logger.info(f"✅ Transaction confirmed in block {receipt['blockNumber']}")
        
        # Parse PoWTokenMinted event to extract tokenId
        parsed_logs = self.pow_token_contract.events.PoWTokenMinted().processReceipt(
            receipt
        )
        
        if not parsed_logs:
            raise Exception("No PoWTokenMinted event found in receipt")
        
        minted_token_id = parsed_logs[0]["args"]["tokenId"]
        logger.info(f"🎁 Minted token ID: {minted_token_id}")
        
        # Build result
        result = PoWTokenResult(
            token_id=minted_token_id,
            tx_hash=tx_hash_hex,
            block_number=receipt["blockNumber"],
            ipfs_uri=ipfs_uri,
            feature_vector_hash=f"0x{feature_vector_hash}",
            gas_used=receipt["gasUsed"],
            minted_at=datetime.now(timezone.utc),
            network=self.network,
        )
        
        logger.info(f"🎉 PoW token minting complete: {result.token_id}")
        
        return result
    
    def verify_token(self, token_id: int) -> Optional[dict]:
        """
        Retrieve token data from on-chain.
        
        Args:
            token_id: Token ID to look up
            
        Returns:
            Token data dict or None if not found
        """
        try:
            record = self.pow_token_contract.functions.getTokenData(
                token_id
            ).call()
            
            return {
                "workerIdHash": record[0],
                "deliveryZoneId": record[1],
                "activeMinutes": record[2],
                "deliveryAttempts": record[3],
                "triggerType": record[4],
                "disruptionSeverity": record[5],
                "compositeClaimScore": record[6],
                "sessionTimestamp": record[7],
                "payoutReleased": record[8],
                "featureVectorHash": record[9].hex(),
            }
        except Exception as e:
            logger.error(f"Failed to retrieve token {token_id}: {e}")
            return None
    
    def verify_worker_token(
        self,
        worker_id_hash: str,
        min_timestamp: int,
        max_timestamp: int,
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if valid token exists for worker in time window.
        
        Args:
            worker_id_hash: keccak256(worker_id)
            min_timestamp: Minimum session timestamp
            max_timestamp: Maximum session timestamp
            
        Returns:
            (exists, token_id) tuple
        """
        try:
            exists, token_id = self.pow_token_contract.functions.verifyWorkerToken(
                worker_id_hash,
                min_timestamp,
                max_timestamp,
            ).call()
            
            return (exists, token_id if exists else None)
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return (False, None)
    
    def get_current_token_id(self) -> int:
        """Get next token ID that will be minted."""
        try:
            return self.pow_token_contract.functions.getCurrentTokenId().call()
        except Exception as e:
            logger.error(f"Failed to get current token ID: {e}")
            return 0
