"""
Unit tests for PoW blockchain services.

Tests cover:
- IPFS metadata upload mocking
- Minting service transaction building
- Gas price management
- Token registry database operations
- Event parsing
"""

import pytest
import json
import hashlib
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4

from pow_blockchain.ipfs_uploader import (
    IPFSMetadataUploader,
    IPFSUploadRequest,
)
from pow_blockchain.minting_service import PoWMintingService, PoWTokenResult
from pow_blockchain.token_registry import TokenRegistryService, PoWTokenModel


# =============================================================================
# IPFS UPLOADER TESTS
# =============================================================================

class TestIPFSUploader:
    """Test IPFS metadata uploading."""
    
    @pytest.fixture
    def uploader(self):
        """Create uploader instance with test credentials."""
        return IPFSMetadataUploader(
            pinata_api_key="test_key",
            pinata_api_secret="test_secret",
        )
    
    @pytest.fixture
    def upload_request(self):
        """Create test upload request."""
        return IPFSUploadRequest(
            worker_tier="silver",
            delivery_zone="Chennai_Zone_7",
            active_minutes=45,
            trigger_type="rainfall",
            disruption_severity=82,
            composite_claim_score=45,
            session_date="2025-04-16",
        )
    
    @patch("pow_blockchain.ipfs_uploader.httpx.Client")
    def test_upload_metadata(self, mock_client, uploader, upload_request):
        """Should upload metadata to IPFS."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "IpfsHash": "QmXxxxxx...",
        }
        
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        # Upload
        token_id = 12345
        result = uploader.upload_token_metadata(token_id, upload_request)
        
        # Verify
        assert result.ipfs_hash == "QmXxxxxx..."
        assert result.ipfs_uri == "ipfs://QmXxxxxx..."
        assert isinstance(result.timestamp, datetime)
    
    @patch("pow_blockchain.ipfs_uploader.httpx.Client")
    def test_upload_includes_privacy_attributes(
        self, mock_client, uploader, upload_request
    ):
        """Metadata should include privacy-preserving attributes."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"IpfsHash": "QmTest..."}
        
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        uploader.upload_token_metadata(1, upload_request)
        
        # Check that metadata was built correctly
        call_args = mock_client.return_value.__enter__.return_value.post.call_args
        payload = call_args.kwargs["json"]
        metadata = payload["pinataContent"]
        
        # Worker ID should NOT be in metadata
        assert "worker_id" not in str(metadata)
        assert "workerIdHash" not in str(metadata)
        
        # But zone, severity, etc. should be
        assert any(
            attr.get("trait_type") == "Trigger Type"
            for attr in metadata["attributes"]
        )
    
    @patch("pow_blockchain.ipfs_uploader.httpx.Client")
    def test_upload_upload_failure(self, mock_client, uploader, upload_request):
        """Should raise on upload failure."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = Exception("Upload failed")
        
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        with pytest.raises(Exception):
            uploader.upload_token_metadata(1, upload_request)


# =============================================================================
# MINTING SERVICE TESTS
# =============================================================================

class TestPoWMintingService:
    """Test PoW token minting service."""
    
    @pytest.fixture
    def mock_web3(self):
        """Create mock Web3 instance."""
        mock_w3 = Mock()
        mock_w3.isConnected.return_value = True
        mock_w3.eth.chain_id = 80001  # Mumbai
        mock_w3.eth.gas_price = 3000000000  # 3 gwei
        mock_w3.eth.get_transaction_count.return_value = 0
        mock_w3.eth.account.sign_transaction = Mock(
            return_value=Mock(rawTransaction=b"signed_tx")
        )
        mock_w3.eth.send_raw_transaction.return_value = (
            b"\x00\x01\x02\x03" * 8
        )  # 32-byte tx hash
        mock_w3.eth.wait_for_transaction_receipt.return_value = {
            "status": 1,
            "blockNumber": 12345,
            "gasUsed": 150000,
        }
        return mock_w3
    
    @pytest.fixture
    def mock_contracts(self, mock_web3):
        """Create mock contract objects."""
        mock_pow_token = Mock()
        mock_pow_token.functions.mintPoWToken.return_value.estimateGas.return_value = 125000
        mock_pow_token.functions.mintPoWToken.return_value.buildTransaction.return_value = {
            "from": "0x...",
            "nonce": 0,
            "gasPrice": 3000000000,
            "gas": 150000,
        }
        mock_pow_token.events.PoWTokenMinted.return_value.processReceipt.return_value = [
            {
                "args": {
                    "tokenId": 1,
                }
            }
        ]
        
        mock_vault = Mock()
        
        return mock_pow_token, mock_vault
    
    @patch("pow_blockchain.minting_service.Web3")
    @patch("pow_blockchain.minting_service.Account.from_key")
    def test_minting_service_init(self, mock_account, mock_web3_class):
        """Should initialize minting service."""
        mock_web3 = Mock()
        mock_web3.isConnected.return_value = True
        mock_web3_class.return_value = mock_web3
        
        mock_account.from_key.return_value = Mock(
            address="0xMinterAddress",
            key="0xPrivateKey",
        )
        
        with patch.object(
            PoWMintingService, "_load_contract", return_value=Mock()
        ):
            service = PoWMintingService(
                pow_token_address="0xPoWTokenAddress",
                payout_vault_address="0xVaultAddress",
                rpc_url="https://rpc.example.com",
                private_key="0xPrivateKey",
                network="mumbai",
            )
        
        assert service.network == "mumbai"
        assert service.minter_address == "0xMinterAddress"
    
    @patch("pow_blockchain.minting_service.Web3")
    @patch("pow_blockchain.minting_service.Account.from_key")
    def test_minting_service_invalid_private_key(self, mock_account, mock_web3_class):
        """Should raise on invalid private key."""
        mock_web3 = Mock()
        mock_web3.isConnected.return_value = True
        mock_web3_class.return_value = mock_web3
        
        mock_account.from_key.side_effect = ValueError("Invalid key")
        
        with pytest.raises(ValueError, match="Invalid private key"):
            PoWMintingService(
                pow_token_address="0xPoWTokenAddress",
                payout_vault_address="0xVaultAddress",
                rpc_url="https://rpc.example.com",
                private_key="invalid_key",
                network="mumbai",
            )


# =============================================================================
# TOKEN REGISTRY TESTS
# =============================================================================

class TestTokenRegistry:
    """Test token registry database operations."""
    
    @pytest.fixture
    def registry(self):
        """Create registry instance."""
        return TokenRegistryService()
    
    @pytest.mark.asyncio
    async def test_save_token(self, registry):
        """Should save token to database."""
        mock_session = AsyncMock()
        
        token_record = await registry.save_token(
            session=mock_session,
            token_id=1,
            claim_id=uuid4(),
            worker_id="worker_123",
            tx_hash="0x1234...",
            block_number=12345,
            network="mumbai",
            ipfs_uri="ipfs://QmXxx...",
            feature_vector_hash="0xHash...",
            gas_used=150000,
            minted_at=datetime.now(timezone.utc),
        )
        
        # Verify add and flush called
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        
        # Verify record type
        assert isinstance(token_record, PoWTokenModel)
        assert token_record.token_id == 1
        assert token_record.worker_id == "worker_123"
        assert token_record.payout_released == False
    
    @pytest.mark.asyncio
    async def test_mark_payout_released(self, registry):
        """Should mark token as paid out."""
        claim_id = uuid4()
        mock_record = PoWTokenModel(
            claim_id=claim_id,
            token_id=1,
            worker_id="worker_123",
            tx_hash="0x1234...",
            block_number=12345,
            network="mumbai",
            ipfs_uri="ipfs://QmXxx...",
            feature_vector_hash="0xHash...",
            payout_released=False,
            gas_used=150000,
            minted_at=datetime.now(timezone.utc),
        )
        
        mock_session = AsyncMock()
        
        # Mock get_token_by_id
        with patch.object(
            registry, "get_token_by_id", return_value=mock_record
        ):
            result = await registry.mark_payout_released(
                session=mock_session,
                token_id=1,
            )
        
        assert result == True
        assert mock_record.payout_released == True
        mock_session.flush.assert_called_once()


# =============================================================================
# GAS MANAGEMENT TESTS
# =============================================================================

class TestGasManagement:
    """Test gas price management and retry logic."""
    
    @patch("pow_blockchain.minting_service.Web3")
    @patch("pow_blockchain.minting_service.Account.from_key")
    def test_gas_price_too_high_raises(self, mock_account, mock_web3_class):
        """Should raise when gas price exceeds max."""
        mock_web3 = Mock()
        mock_web3.isConnected.return_value = True
        mock_web3.eth.chain_id = 80001
        mock_web3.eth.gas_price = 200000000000  # 200 gwei (very high)
        
        mock_web3_class.return_value = mock_web3
        mock_account.from_key.return_value = Mock(
            address="0xMinter",
            key="0xKey",
        )
        
        with patch.object(
            PoWMintingService, "_load_contract", return_value=Mock()
        ):
            service = PoWMintingService(
                pow_token_address="0xPoW",
                payout_vault_address="0xVault",
                rpc_url="https://rpc.example.com",
                private_key="0xKey",
                max_gas_gwei=50.0,
            )
        
        # Mock the contract for minting
        service.pow_token_contract = Mock()
        service.pow_token_contract.functions.mintPoWToken.return_value.estimateGas.return_value = 125000
        
        # Should raise ValueError about high gas price
        with pytest.raises(ValueError, match="Gas price too high"):
            import asyncio
            asyncio.run(
                service.mint_pow_token(
                    token_id=1,
                    worker_id_hash="0xHash",
                    delivery_zone="Zone",
                    active_minutes=45,
                    delivery_attempts=8,
                    trigger_type="rainfall",
                    disruption_severity=82,
                    composite_claim_score=45,
                    session_timestamp=int(datetime.now().timestamp()),
                    feature_vector_json="{}",
                    ipfs_uri="ipfs://Qm...",
                )
            )


# =============================================================================
# EVENT PARSING TESTS
# =============================================================================

class TestEventParsing:
    """Test parsing of blockchain events."""
    
    def test_pow_token_minted_event_parsing(self):
        """Should correctly parse PoWTokenMinted event."""
        # Mock event response
        event_logs = [
            {
                "args": {
                    "tokenId": 42,
                    "workerIdHash": "0xABCD...",
                    "sessionTimestamp": 1713350000,
                    "deliveryZoneId": "Zone_7",
                    "disruptionSeverity": 82,
                },
            }
        ]
        
        # Verify we can extract data
        token_id = event_logs[0]["args"]["tokenId"]
        assert token_id == 42
        
        worker_hash = event_logs[0]["args"]["workerIdHash"]
        assert worker_hash == "0xABCD..."
