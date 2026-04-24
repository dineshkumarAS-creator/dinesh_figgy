const { expect } = require("chai");
const { ethers } = require("hardhat");

/**
 * FIGGYPoWToken & FIGGYPayoutVault test suite
 * 
 * Tests cover:
 * - Token minting and data storage
 * - Access control (only owner can mint)
 * - Worker token verification time windows
 * - Payout release tracking
 * - Payout vault integration
 * - Emergency pause functionality
 */

describe("FIGGYPoWToken", function () {
  let powToken, vault;
  let owner, minter, worker, recipient;
  
  const WORKER_ID = "worker_12345";
  const DELIVERY_ZONE = "Chennai_Zone_7";
  const TRIGGER_TYPE = "rainfall";
  const DISRUPTION_SEVERITY = 82; // 0-100
  const COMPOSITE_SCORE = 45; // 0-100
  const ACTIVE_MINUTES = 45;
  const DELIVERY_ATTEMPTS = 8;
  
  beforeEach(async function () {
    [owner, minter, worker, recipient] = await ethers.getSigners();
    
    // Deploy FIGGYPoWToken
    const FIGGYPoWToken = await ethers.getContractFactory("FIGGYPoWToken");
    powToken = await FIGGYPoWToken.deploy();
    await powToken.deployed();
    
    // Deploy FIGGYPayoutVault
    const FIGGYPayoutVault = await ethers.getContractFactory("FIGGYPayoutVault");
    vault = await FIGGYPayoutVault.deploy(powToken.address);
    await vault.deployed();
    
    // Link vault to token
    await powToken.setPayoutVault(vault.address);
    
    // Grant minter role to minter address
    const MINTER_ROLE = await vault.MINTER_ROLE();
    await vault.grantRole(MINTER_ROLE, minter.address);
  });
  
  // ==========================================================================
  // MINTING TESTS
  // ==========================================================================
  
  describe("Minting", function () {
    it("Should mint token with correct data", async function () {
      const now = Math.floor(Date.now() / 1000);
      const workerIdHash = ethers.utils.keccak256(
        ethers.utils.toUtf8Bytes(WORKER_ID)
      );
      
      const record = {
        workerIdHash: workerIdHash,
        deliveryZoneId: DELIVERY_ZONE,
        activeMinutes: ACTIVE_MINUTES,
        deliveryAttempts: DELIVERY_ATTEMPTS,
        triggerType: TRIGGER_TYPE,
        disruptionSeverity: DISRUPTION_SEVERITY,
        compositeClaimScore: COMPOSITE_SCORE,
        sessionTimestamp: now,
        payoutReleased: false,
        featureVectorHash: ethers.utils.keccak256(ethers.utils.toUtf8Bytes("vector")),
      };
      
      const tokenURI = "ipfs://QmXxxx...";
      const tx = await powToken.mintPoWToken(
        worker.address,
        record,
        tokenURI
      );
      
      // Check event emitted
      await expect(tx)
        .to.emit(powToken, "PoWTokenMinted")
        .withArgs(1, workerIdHash, now, DELIVERY_ZONE, DISRUPTION_SEVERITY);
      
      // Verify token data
      const storedRecord = await powToken.getTokenData(1);
      expect(storedRecord.workerIdHash).to.equal(workerIdHash);
      expect(storedRecord.deliveryZoneId).to.equal(DELIVERY_ZONE);
      expect(storedRecord.activeMinutes).to.equal(ACTIVE_MINUTES);
      expect(storedRecord.disruptionSeverity).to.equal(DISRUPTION_SEVERITY);
      expect(storedRecord.compositeClaimScore).to.equal(COMPOSITE_SCORE);
      expect(storedRecord.sessionTimestamp).to.equal(now);
      expect(storedRecord.payoutReleased).to.equal(false);
    });
    
    it("Should auto-increment token IDs", async function () {
      const now = Math.floor(Date.now() / 1000);
      const workerIdHash = ethers.utils.keccak256(
        ethers.utils.toUtf8Bytes(WORKER_ID)
      );
      
      const record = {
        workerIdHash: workerIdHash,
        deliveryZoneId: DELIVERY_ZONE,
        activeMinutes: ACTIVE_MINUTES,
        deliveryAttempts: DELIVERY_ATTEMPTS,
        triggerType: TRIGGER_TYPE,
        disruptionSeverity: DISRUPTION_SEVERITY,
        compositeClaimScore: COMPOSITE_SCORE,
        sessionTimestamp: now,
        payoutReleased: false,
        featureVectorHash: ethers.utils.keccak256(ethers.utils.toUtf8Bytes("vector1")),
      };
      
      const tx1 = await powToken.mintPoWToken(worker.address, record, "ipfs://1");
      const tx2 = await powToken.mintPoWToken(worker.address, record, "ipfs://2");
      
      // Both should succeed with different token IDs
      const receipt1 = await tx1.wait();
      const receipt2 = await tx2.wait();
      
      expect(receipt1.status).to.equal(1);
      expect(receipt2.status).to.equal(1);
      
      const currentId = await powToken.getCurrentTokenId();
      expect(currentId).to.equal(3); // Started at 1, now at 3
    });
    
    it("Should reject non-owner mint", async function () {
      const now = Math.floor(Date.now() / 1000);
      const workerIdHash = ethers.utils.keccak256(
        ethers.utils.toUtf8Bytes(WORKER_ID)
      );
      
      const record = {
        workerIdHash: workerIdHash,
        deliveryZoneId: DELIVERY_ZONE,
        activeMinutes: ACTIVE_MINUTES,
        deliveryAttempts: DELIVERY_ATTEMPTS,
        triggerType: TRIGGER_TYPE,
        disruptionSeverity: DISRUPTION_SEVERITY,
        compositeClaimScore: COMPOSITE_SCORE,
        sessionTimestamp: now,
        payoutReleased: false,
        featureVectorHash: ethers.utils.keccak256(ethers.utils.toUtf8Bytes("vector")),
      };
      
      // Mint as non-owner should fail
      await expect(
        powToken.connect(minter).mintPoWToken(worker.address, record, "ipfs://x")
      ).to.be.revertedWith("Ownable: caller is not the owner");
    });
    
    it("Should reject zero workerIdHash", async function () {
      const now = Math.floor(Date.now() / 1000);
      
      const record = {
        workerIdHash: ethers.constants.HashZero, // Zero hash
        deliveryZoneId: DELIVERY_ZONE,
        activeMinutes: ACTIVE_MINUTES,
        deliveryAttempts: DELIVERY_ATTEMPTS,
        triggerType: TRIGGER_TYPE,
        disruptionSeverity: DISRUPTION_SEVERITY,
        compositeClaimScore: COMPOSITE_SCORE,
        sessionTimestamp: now,
        payoutReleased: false,
        featureVectorHash: ethers.utils.keccak256(ethers.utils.toUtf8Bytes("vector")),
      };
      
      await expect(
        powToken.mintPoWToken(worker.address, record, "ipfs://x")
      ).to.be.revertedWith("workerIdHash cannot be zero");
    });
  });
  
  // ==========================================================================
  // VERIFICATION TESTS
  // ==========================================================================
  
  describe("Token Verification", function () {
    let workerIdHash;
    
    beforeEach(async function () {
      workerIdHash = ethers.utils.keccak256(
        ethers.utils.toUtf8Bytes(WORKER_ID)
      );
      
      const now = Math.floor(Date.now() / 1000);
      const record = {
        workerIdHash: workerIdHash,
        deliveryZoneId: DELIVERY_ZONE,
        activeMinutes: ACTIVE_MINUTES,
        deliveryAttempts: DELIVERY_ATTEMPTS,
        triggerType: TRIGGER_TYPE,
        disruptionSeverity: DISRUPTION_SEVERITY,
        compositeClaimScore: COMPOSITE_SCORE,
        sessionTimestamp: now,
        payoutReleased: false,
        featureVectorHash: ethers.utils.keccak256(ethers.utils.toUtf8Bytes("vector")),
      };
      
      await powToken.mintPoWToken(worker.address, record, "ipfs://1");
    });
    
    it("Should verify token within time window", async function () {
      const now = Math.floor(Date.now() / 1000);
      
      const [exists, tokenId] = await powToken.verifyWorkerToken(
        workerIdHash,
        now - 1000,
        now + 1000
      );
      
      expect(exists).to.be.true;
      expect(tokenId).to.equal(1);
    });
    
    it("Should reject token outside time window (too early)", async function () {
      const now = Math.floor(Date.now() / 1000);
      
      const [exists, tokenId] = await powToken.verifyWorkerToken(
        workerIdHash,
        now + 100,  // minimum timestamp is in future
        now + 1000
      );
      
      expect(exists).to.be.false;
      expect(tokenId).to.equal(0);
    });
    
    it("Should reject token outside time window (too late)", async function () {
      const now = Math.floor(Date.now() / 1000);
      
      const [exists, tokenId] = await powToken.verifyWorkerToken(
        workerIdHash,
        now - 10000,
        now - 1000  // maximum timestamp is in past
      );
      
      expect(exists).to.be.false;
      expect(tokenId).to.equal(0);
    });
    
    it("Should reject verification for non-existent worker", async function () {
      const now = Math.floor(Date.now() / 1000);
      const unknownHash = ethers.utils.keccak256(
        ethers.utils.toUtf8Bytes("unknown_worker")
      );
      
      const [exists, tokenId] = await powToken.verifyWorkerToken(
        unknownHash,
        now - 1000,
        now + 1000
      );
      
      expect(exists).to.be.false;
      expect(tokenId).to.equal(0);
    });
  });
  
  // ==========================================================================
  // PAYOUT TESTS
  // ==========================================================================
  
  describe("Payout Release", function () {
    let tokenId, workerIdHash, sessionTimestamp;
    
    beforeEach(async function () {
      workerIdHash = ethers.utils.keccak256(
        ethers.utils.toUtf8Bytes(WORKER_ID)
      );
      sessionTimestamp = Math.floor(Date.now() / 1000);
      
      const record = {
        workerIdHash: workerIdHash,
        deliveryZoneId: DELIVERY_ZONE,
        activeMinutes: ACTIVE_MINUTES,
        deliveryAttempts: DELIVERY_ATTEMPTS,
        triggerType: TRIGGER_TYPE,
        disruptionSeverity: DISRUPTION_SEVERITY,
        compositeClaimScore: COMPOSITE_SCORE,
        sessionTimestamp: sessionTimestamp,
        payoutReleased: false,
        featureVectorHash: ethers.utils.keccak256(ethers.utils.toUtf8Bytes("vector")),
      };
      
      const tx = await powToken.mintPoWToken(worker.address, record, "ipfs://1");
      const receipt = await tx.wait();
      tokenId = 1;
    });
    
    it("Should mark token as paid out", async function () {
      const recordBefore = await powToken.getTokenData(tokenId);
      expect(recordBefore.payoutReleased).to.be.false;
      
      // Only vault can call this
      await powToken.markPayoutReleased(tokenId);
      
      const recordAfter = await powToken.getTokenData(tokenId);
      expect(recordAfter.payoutReleased).to.be.true;
    });
    
    it("Should emit PayoutReleased event", async function () {
      await expect(powToken.markPayoutReleased(tokenId))
        .to.emit(powToken, "PayoutReleased")
        .withArgs(tokenId, workerIdHash, expect.any(Number));
    });
    
    it("Should prevent double payout", async function () {
      await powToken.markPayoutReleased(tokenId);
      
      // Second call should revert
      await expect(
        powToken.markPayoutReleased(tokenId)
      ).to.be.revertedWith("Payout already released");
    });
    
    it("Should only allow vault to mark payout released", async function () {
      // Non-vault call should fail
      await expect(
        powToken.connect(minter).markPayoutReleased(tokenId)
      ).to.be.revertedWith("Only PayoutVault can mark released");
    });
  });
  
  // ==========================================================================
  // PAUSE TESTS
  // ==========================================================================
  
  describe("Pause & Resume", function () {
    it("Should prevent minting when paused", async function () {
      // Pause contract
      await powToken.pause();
      
      const now = Math.floor(Date.now() / 1000);
      const workerIdHash = ethers.utils.keccak256(
        ethers.utils.toUtf8Bytes(WORKER_ID)
      );
      
      const record = {
        workerIdHash: workerIdHash,
        deliveryZoneId: DELIVERY_ZONE,
        activeMinutes: ACTIVE_MINUTES,
        deliveryAttempts: DELIVERY_ATTEMPTS,
        triggerType: TRIGGER_TYPE,
        disruptionSeverity: DISRUPTION_SEVERITY,
        compositeClaimScore: COMPOSITE_SCORE,
        sessionTimestamp: now,
        payoutReleased: false,
        featureVectorHash: ethers.utils.keccak256(ethers.utils.toUtf8Bytes("vector")),
      };
      
      await expect(
        powToken.mintPoWToken(worker.address, record, "ipfs://x")
      ).to.be.revertedWith("Pausable: paused");
    });
    
    it("Should allow minting after unpause", async function () {
      await powToken.pause();
      await powToken.unpause();
      
      const now = Math.floor(Date.now() / 1000);
      const workerIdHash = ethers.utils.keccak256(
        ethers.utils.toUtf8Bytes(WORKER_ID)
      );
      
      const record = {
        workerIdHash: workerIdHash,
        deliveryZoneId: DELIVERY_ZONE,
        activeMinutes: ACTIVE_MINUTES,
        deliveryAttempts: DELIVERY_ATTEMPTS,
        triggerType: TRIGGER_TYPE,
        disruptionSeverity: DISRUPTION_SEVERITY,
        compositeClaimScore: COMPOSITE_SCORE,
        sessionTimestamp: now,
        payoutReleased: false,
        featureVectorHash: ethers.utils.keccak256(ethers.utils.toUtf8Bytes("vector")),
      };
      
      const tx = await powToken.mintPoWToken(worker.address, record, "ipfs://x");
      expect(tx).to.not.be.reverted;
    });
  });
});

// ==========================================================================
// PAYOUT VAULT TESTS
// ==========================================================================

describe("FIGGYPayoutVault", function () {
  let powToken, vault;
  let owner, minter, recipient;
  let tokenId, workerIdHash, sessionTimestamp;
  
  const WORKER_ID = "worker_vault_test";
  const DELIVERY_ZONE = "Mumbai_Zone_5";
  
  beforeEach(async function () {
    [owner, minter, recipient] = await ethers.getSigners();
    
    // Deploy contracts
    const FIGGYPoWToken = await ethers.getContractFactory("FIGGYPoWToken");
    powToken = await FIGGYPoWToken.deploy();
    await powToken.deployed();
    
    const FIGGYPayoutVault = await ethers.getContractFactory("FIGGYPayoutVault");
    vault = await FIGGYPayoutVault.deploy(powToken.address);
    await vault.deployed();
    
    // Link
    await powToken.setPayoutVault(vault.address);
    
    // Grant minter role
    const MINTER_ROLE = await vault.MINTER_ROLE();
    await vault.grantRole(MINTER_ROLE, owner.address);
    
    // Mint a token
    workerIdHash = ethers.utils.keccak256(
      ethers.utils.toUtf8Bytes(WORKER_ID)
    );
    sessionTimestamp = Math.floor(Date.now() / 1000);
    
    const record = {
      workerIdHash: workerIdHash,
      deliveryZoneId: DELIVERY_ZONE,
      activeMinutes: 45,
      deliveryAttempts: 8,
      triggerType: "rainfall",
      disruptionSeverity: 82,
      compositeClaimScore: 45,
      sessionTimestamp: sessionTimestamp,
      payoutReleased: false,
      featureVectorHash: ethers.utils.keccak256(ethers.utils.toUtf8Bytes("vector")),
    };
    
    const tx = await powToken.mintPoWToken(owner.address, record, "ipfs://1");
    const receipt = await tx.wait();
    tokenId = 1;
  });
  
  describe("Native MATIC Deposits & Payouts", function () {
    it("Should accept MATIC deposits", async function () {
      const amount = ethers.utils.parseEther("1");
      const tx = await vault.depositNative({ value: amount });
      
      await expect(tx)
        .to.emit(vault, "Deposit")
        .withArgs(owner.address, amount, "MATIC");
      
      const balance = await vault.getNativeBalance();
      expect(balance).to.equal(amount);
    });
    
    it("Should release MATIC payout on valid token", async function () {
      // Deposit funds
      const depositAmount = ethers.utils.parseEther("10");
      await vault.depositNative({ value: depositAmount });
      
      // Release payout
      const payoutAmount = ethers.utils.parseEther("1");
      const tx = await vault.releasePayoutNative(
        tokenId,
        workerIdHash,
        recipient.address,
        payoutAmount,
        sessionTimestamp - 1000,
        sessionTimestamp + 1000
      );
      
      await expect(tx)
        .to.emit(vault, "PayoutExecuted")
        .withArgs(
          tokenId,
          workerIdHash,
          recipient.address,
          payoutAmount,
          "MATIC"
        );
      
      // Check token marked as released
      const record = await powToken.getTokenData(tokenId);
      expect(record.payoutReleased).to.be.true;
      
      // Check recipient received funds
      const recipientBalance = await ethers.provider.getBalance(recipient.address);
      // (Note: in actual test would need to account for initial balance)
    });
    
    it("Should reject payout without valid token", async function () {
      const depositAmount = ethers.utils.parseEther("10");
      await vault.depositNative({ value: depositAmount });
      
      const invalidTokenId = 999;
      const payoutAmount = ethers.utils.parseEther("1");
      
      await expect(
        vault.releasePayoutNative(
          invalidTokenId,
          workerIdHash,
          recipient.address,
          payoutAmount,
          sessionTimestamp - 1000,
          sessionTimestamp + 1000
        )
      ).to.be.revertedWith("No valid PoW token found");
    });
    
    it("Should reject payout when vault insufficient funds", async function () {
      // Don't deposit
      const payoutAmount = ethers.utils.parseEther("1");
      
      await expect(
        vault.releasePayoutNative(
          tokenId,
          workerIdHash,
          recipient.address,
          payoutAmount,
          sessionTimestamp - 1000,
          sessionTimestamp + 1000
        )
      ).to.be.revertedWith("Insufficient vault balance");
    });
    
    it("Should only allow MINTER_ROLE to release payout", async function () {
      const depositAmount = ethers.utils.parseEther("10");
      await vault.depositNative({ value: depositAmount });
      
      const payoutAmount = ethers.utils.parseEther("1");
      
      await expect(
        vault.connect(minter).releasePayoutNative(
          tokenId,
          workerIdHash,
          recipient.address,
          payoutAmount,
          sessionTimestamp - 1000,
          sessionTimestamp + 1000
        )
      ).to.be.revertedWith(`AccessControl: account ${minter.address.toLowerCase()} is missing role`);
    });
  });
  
  describe("Payout History", function () {
    it("Should track payout history", async function () {
      // Deposit
      const depositAmount = ethers.utils.parseEther("10");
      await vault.depositNative({ value: depositAmount });
      
      // Release payout
      const payoutAmount = ethers.utils.parseEther("1");
      await vault.releasePayoutNative(
        tokenId,
        workerIdHash,
        recipient.address,
        payoutAmount,
        sessionTimestamp - 1000,
        sessionTimestamp + 1000
      );
      
      // Check history
      const history = await vault.getPayoutHistory();
      expect(history.length).to.equal(1);
      expect(history[0].tokenId).to.equal(tokenId);
      expect(history[0].recipient).to.equal(recipient.address);
      expect(history[0].amountWei).to.equal(payoutAmount);
    });
  });
});
