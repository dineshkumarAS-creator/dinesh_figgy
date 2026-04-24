# FIGGY PoW Blockchain Layer Design

## Overview

The **Proof-of-Work (PoW) Activity Token** is an ERC-721 NFT minted on Polygon that creates an immutable on-chain record of every verified worker disruption claim.

**Purpose**: Link off-chain claim verification (FIGGY backend) to on-chain payout authorization, creating transparency and fraud resistance.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ FIGGY Backend (Python)                                          │
│                                                                 │
│  Claims Approved (Layer 6) → Income Calculated (Layer 7)       │
│                           ↓                                     │
│                   PoW Minting Service                           │
│                   (minting_service.py)                          │
│                           ↓                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. Build WorkerActivityRecord                           │  │
│  │ 2. Hash feature vector (SHA-256)                        │  │
│  │ 3. Upload metadata to IPFS (Pinata)                     │  │
│  │ 4. Sign + broadcast mintPoWToken transaction            │  │
│  │ 5. Wait for receipt, parse event → tokenId              │  │
│  │ 6. Save to PostgreSQL pow_tokens table                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│           ↓                                                      │
└───────────┼──────────────────────────────────────────────────────┘
            │ web3.py (transaction broadcast)
            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Polygon Blockchain (Mumbai Testnet / Mainnet)                   │
│                                                                 │
│  FIGGYPoWToken (ERC-721)                                        │
│  ├─ mintPoWToken()  ← FIGGY minter only                       │
│  ├─ getTokenData(tokenId) → WorkerActivityRecord              │
│  ├─ verifyWorkerToken(hash, minTime, maxTime) → bool          │
│  └─ markPayoutReleased(tokenId) ← vault only                  │
│                                                                 │
│  FIGGYPayoutVault (AccessControl)                              │
│  ├─ depositNative() — accept MATIC/USDC                       │
│  ├─ releasePayoutNative(tokenId, ...) ← gate on verifyWorker  │
│  ├─ releasePayoutUsdc(tokenId, ...) ← gate on verifyWorker    │
│  └─ markPayoutReleased(tokenId) → calls pow_token contract    │
│                                                                 │
│  [IPFS pinned metadata via Pinata]                             │
│   {                                                             │
│     "name": "FIGGY PoW Token #1",                              │
│     "attributes": [                                             │
│       {"trait_type": "Delivery Zone", "value": "Zone_7"},      │
│       {"trait_type": "Disruption Severity", "value": 82},      │
│       ...                                                       │
│     ]                                                           │
│   }                                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Token Data Structure

### WorkerActivityRecord (On-Chain)

```solidity
struct WorkerActivityRecord {
    bytes32 workerIdHash;           // keccak256(worker_id) — privacy
    string deliveryZoneId;          // "Chennai_Zone_7"
    uint32 activeMinutes;           // Duration in minutes
    uint16 deliveryAttempts;        // # of delivery attempts
    string triggerType;             // "rainfall" | "aqi" | "curfew_strike"
    uint8 disruptionSeverity;       // 0-100 (composite_disruption_index * 100)
    uint8 compositeClaimScore;      // 0-100 (ML fraud likelihood)
    uint64 sessionTimestamp;        // Unix timestamp (immutable proof-of-work)
    bool payoutReleased;            // true when insurance → worker
    bytes32 featureVectorHash;      // SHA-256 of feature vector JSON
}
```

**Stored in**: `tokenData[tokenId]` mapping on `FIGGYPoWToken`

**Immutable**: Once minted, cannot be modified. Only `payoutReleased` can transition from false → true.

---

## Key Design Decisions

### 1. Why ERC-721 (NFTs)?

**Alternative**: ERC-1155 (semi-fungible) or simple state registry

**Chosen**: ERC-721 because:
- Each disruption session is **unique** event (not interchangeable)
- Ownership model (worker can own their PoW token)
- Standard interface (wallets, explorers, marketplaces)
- Transferability (worker can delegate earnings)
- Future: collectible badge economy

### 2. Why Polygon, Not Ethereum?

**Costs (as of 2025)**:
- Ethereum mainnet: $50-200 per mint (layer 1 gas)
- Polygon mainnet: $0.05-0.50 per mint (1000x cheaper)
- Mumbai testnet: $0.001-0.01 per mint (free MATIC from faucet)

**Chosen**: Polygon because:
- Insurance margin: pay out ₹50-2000 per claim, but gas cost only ₹2-10
- Throughput: handles 1000+ claims/sec vs Ethereum 15 tx/sec
- Finality: 2.5 second blocks vs Ethereum 12 second blocks
- 2-way bridge to Ethereum for settlement if needed

### 3. Why Hash Worker ID?

**Privacy concern**: On-chain data is forever public.

**Solution**: Store `workerIdHash = keccak256(worker_id)` instead of plaintext

**Why works**:
- Uniquely identifies worker (no collisions)
- Cannot reverse (keccak256 is one-way)
- Allows verification: `keccak256("worker_12345") == stored_hash`

**Where full ID stored**: PostgreSQL only, never on-chain

### 4. Why Feature Vector Hash?

**Use case**: Dispute resolution

**Flow**:
1. Token minted with `featureVectorHash = SHA-256(weather_data + gps + earnings + ...)`
2. Months later, worker disputes payout
3. FIGGY provides full `FeatureVector` JSON
4. Check: `SHA-256(provided_data) == token.featureVectorHash`
5. If match: proof that this data wasn't tampered with

**Why SHA-256, not on-chain storage**:
- Full feature vector = 5KB JSON file
- Storage cost: ~$0.50 per token (ETH/Polygon)
- Hash cost: ~$0.001 per token (1000x cheaper)
- Blockchain as append-only audit log, not data warehouse

### 5. Condition-Gated Payouts

**Smart contract logic** (FIGGYPayoutVault):

```solidity
function releasePayoutNative(tokenId, workerIdHash, recipient, amount, minTime, maxTime) {
    // Verify PoW token exists & hasn't been paid
    (bool exists, uint256 verifiedTokenId) = powToken.verifyWorkerToken(
        workerIdHash,
        minTime,
        maxTime
    );
    require(exists, "No valid token");
    
    // Transfer funds (conditional execution)
    payable(recipient).transfer(amount);
    
    // Mark as paid on FIGGYPoWToken
    powToken.markPayoutReleased(tokenId);
}
```

**Benefits**:
- Payout can only happen if PoW token exists (verified work proof)
- Cannot double-pay (once released, token.payoutReleased = true forever)
- Funds locked in contract until verification passes
- Trustless execution (no intermediate handoff)

### 6. Append-Only by Design

**Problem**: If a token's data could be modified, audits fail

**Solution**: Solidity `WorkerActivityRecord` stored in immutable mapping

```solidity
mapping(uint256 => WorkerActivityRecord) public tokenData; // Read-only after mint
```

**Only state that changes**: `payoutReleased` boolean (false → true, one-way)

**Comparison**:

| Operation | Allowed? | Reason |
|-----------|----------|--------|
| Modify disruption_severity | ❌ No | Would be fraud (inflate claims) |
| Modify sessionTimestamp | ❌ No | Would break proof-of-work |
| Modify payoutReleased | ✅ Yes | Vault can mark released (one-way) |
| Delete token | ❌ No | Mapping keys immutable |

---

## Workflow: End-to-End

### Scenario: Worker "worker_12345" suffers 45-minute curfew

**Off-chain (FIGGY Backend)**:
```python
# Layer 6: Manual review approved claim
claim = { claim_id: "uuid1", worker_id: "worker_12345", ... }

# Layer 7: Calculated payout
payout = ₹536

# NEW Layer 7B: Mint PoW token
feature_vector = {
    "worker_id_hash": keccak256("worker_12345"),
    "delivery_zone": "Chennai_Zone_7",
    "active_minutes": 45,
    "delivery_attempts": 8,
    "trigger_type": "curfew",
    "disruption_severity": 82,
    "composite_claim_score": 45,
    "session_timestamp": 1713081000,
}

# Step 1: Upload metadata to IPFS
ipfs_uploader.upload_token_metadata(
    token_id=1,
    request=IPFSUploadRequest(
        worker_tier="silver",
        delivery_zone="Chennai_Zone_7",
        active_minutes=45,
        trigger_type="curfew",
        disruption_severity=82,
        composite_claim_score=45,
        session_date="2025-04-16",
    )
)
# → Returns: ipfs_uri = "ipfs://QmAbc123..."

# Step 2: Mint PoW token
minting_service.mint_pow_token(
    token_id=1,
    worker_id_hash="0x" + keccak256("worker_12345"),
    delivery_zone="Chennai_Zone_7",
    active_minutes=45,
    delivery_attempts=8,
    trigger_type="curfew",
    disruption_severity=82,
    composite_claim_score=45,
    session_timestamp=1713081000,
    feature_vector_json=feature_vector.model_dump_json(),
    ipfs_uri="ipfs://QmAbc123...",
)
# → Returns: PoWTokenResult(token_id=1, tx_hash="0x123...", block_number=30000, ...)

# Step 3: Save to PostgreSQL
token_registry.save_token(
    token_id=1,
    claim_id=uuid1,
    worker_id="worker_12345",
    tx_hash="0x123...",
    block_number=30000,
    network="mumbai",
    ipfs_uri="ipfs://QmAbc123...",
    feature_vector_hash="0x" + sha256(feature_vector_json),
    gas_used=150000,
)

# Step 4: Update claim record with token_id + tx_hash
claims.update(claim_id, {
    "pow_token_id": 1,
    "pow_tx_hash": "0x123...",
    "pow_block_number": 30000,
})
```

**On-chain (Polygon)**:

```
FIGGYPoWToken.mintPoWToken(
    to: minter_address,
    record: WorkerActivityRecord(
        workerIdHash: 0x...,
        deliveryZoneId: "Chennai_Zone_7",
        activeMinutes: 45,
        deliveryAttempts: 8,
        triggerType: "curfew",
        disruptionSeverity: 82,
        compositeClaimScore: 45,
        sessionTimestamp: 1713081000,
        payoutReleased: false,
        featureVectorHash: 0x...
    ),
    tokenURI: "ipfs://QmAbc123..."
)

→ Event emitted: PoWTokenMinted(tokenId=1, workerIdHash=0x..., timestamp=1713081000)
→ Token stored in FIGGYPoWToken.tokenData[1]
```

**Payout Release** (user-initiated or backend automated):

```python
# When worker requests/triggers payout
payout_vault.releasePayoutNative(
    tokenId=1,
    workerIdHash=0x...,
    recipient=worker_eth_address,
    amountWei=536_000_000_000_000_000_000,  # ₹536 in WEI (scaled for ether)
    minTimestamp=1713081000 - 3600,  # ±1 hour window
    maxTimestamp=1713081000 + 3600,
)

→ On-chain verification:
   FIGGYPoWToken.verifyWorkerToken(
       workerIdHash: 0x...,
       minTimestamp: ...,
       maxTimestamp: ...
   )
   → Returns (true, tokenId=1) ✅

→ Transfer MATIC to recipient
→ Call FIGGYPoWToken.markPayoutReleased(tokenId=1)
   → Sets tokenData[1].payoutReleased = true
   → Event PayoutReleased(tokenId=1)

→ Update PostgreSQL: pow_tokens[1].payout_released = true
```

---

## Security Model

### Threat: Double Payout

**Attack**: Release payout twice for same token

**Defense**:
1. `payoutReleased` boolean prevents second call
2. `verifyWorkerToken()` checks `!payoutReleased` before allowing payout
3. Database unique constraint on `token_id`

### Threat: Minting Invalid Tokens

**Attack**: Mint token for fake worker/claim

**Defense**:
1. Only `owner` (FIGGY backend) can call `mintPoWToken()`
2. Backend validates claim before minting
3. Private key secured in environment, never in code
4. All transactions signed + verified

### Threat: Feature Vector Tampering

**Attack**: Later claim different feature vector (dispute resolution attack)

**Defense**:
1. `featureVectorHash = SHA-256(content)` stored on-chain
2. Cannot reverse SHA-256
3. Verification: recompute hash of provided data, compare to token hash

---

## Deployment

### Local Development
```bash
# Start hardhat node
npx hardhat node

# Deploy to local network
npx hardhat run scripts/deploy_pow_token.js --network localhost
npx hardhat run scripts/deploy_payout_vault.js --network localhost

# Run tests
npx hardhat test
```

### Mumbai Testnet
```bash
# Get free MATIC from faucet: https://faucet.polygon.technology/

# Set environment
export MUMBAI_RPC_URL="https://rpc-mumbai.maticvigil.com"
export PRIVATE_KEY="0x..."
export POLYGONSCAN_API_KEY="your_key"

# Deploy
npx hardhat run scripts/deploy_pow_token.js --network mumbai
npx hardhat run scripts/deploy_payout_vault.js --network mumbai

# Verify on Polygonscan
npx hardhat verify --network mumbai <CONTRACT_ADDRESS>
```

### Polygon Mainnet (Production)
```bash
# Use mainnet RPC
export POLYGON_RPC_URL="https://polygon-rpc.com"

# Same deployment scripts
npx hardhat run scripts/deploy_pow_token.js --network polygon
```

---

## Gas Costs

**Per Token Mint** (Mumbai testnet):

| Operation | Gas | USD Cost |
|-----------|-----|----------|
| `mintPoWToken()` | ~150,000 | ~$0.001 |
| Metadata upload (IPFS) | 0 | $0.001 (Pinata) |
| Database save | 0 | negligible |
| **Total** | - | **~$0.002** |

**Per Payout Release** (Mumbai testnet):

| Operation | Gas | USD Cost |
|-----------|-----|----------|
| `releasePayoutNative()` | ~80,000 | ~$0.0005 |
| `markPayoutReleased()` | ~60,000 | ~$0.0004 |
| **Total** | - | **~$0.001** |

**Polygon Mainnet** (50 gwei gas price):
- Mint: ~$0.10
- Release: ~$0.05

**Budget for 1M claims/year**:
- Mint: 1M × $0.10 = $100,000
- Release: 1M × $0.05 = $50,000
- **Total: $150,000** (insurance cost)

---

## Future Enhancements

1. **Collectible Badges**: Golden NFT for workers with 100+ verified claims
2. **Earnings Aggregation**: NFTs represent cumulative earnings, tradeable bonds
3. **Smart Contract Upgrades**: Proxy pattern for contract improvements
4. **Multi-Chain Bridging**: Move tokens between Polygon ↔ Ethereum L2
5. **DAO Governance**: Token holders vote on disruption classification

---

## References

- [ERC-721](https://eips.ethereum.org/EIPS/eip-721) — NFT standard
- [Polygon Docs](https://polygon.technology/developers) — Network details
- [web3.py](https://web3py.readthedocs.io/) — Python Ethereum library
- [OpenZeppelin Contracts](https://docs.openzeppelin.com/contracts/) — Smart contract libraries
- [IPFS](https://ipfs.io/) — Distributed file system
- [Pinata](https://www.pinata.cloud/) — IPFS pinning service

