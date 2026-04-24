/**
 * Deploy FIGGYPayoutVault contract
 * 
 * Prerequisites:
 *   - FIGGYPoWToken must be deployed first
 *   - Run: npx hardhat run scripts/deploy_pow_token.js first
 * 
 * Usage:
 *   npx hardhat run scripts/deploy_payout_vault.js --network mumbai
 */

const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("🔷 Deploying FIGGYPayoutVault...");
  
  const [deployer] = await ethers.getSigners();
  console.log(`📍 Deployer: ${deployer.address}`);
  
  const network = hre.network.name;
  console.log(`🌐 Network: ${network}`);
  
  // Load existing deployments
  const deploymentsDir = path.join(__dirname, "../deployments");
  const deploymentFile = path.join(deploymentsDir, `${network}.json`);
  
  if (!fs.existsSync(deploymentFile)) {
    throw new Error(`Deployment file not found: ${deploymentFile}`);
  }
  
  const deployments = JSON.parse(fs.readFileSync(deploymentFile, "utf8"));
  const powTokenAddress = deployments.FIGGYPoWToken?.address;
  
  if (!powTokenAddress) {
    throw new Error("FIGGYPoWToken address not found. Please deploy it first.");
  }
  
  console.log(`🔗 Using FIGGYPoWToken at: ${powTokenAddress}`);
  
  // Deploy FIGGYPayoutVault
  const FIGGYPayoutVault = await hre.ethers.getContractFactory("FIGGYPayoutVault");
  const vault = await FIGGYPayoutVault.deploy(powTokenAddress);
  
  await vault.deployed();
  console.log(`✅ FIGGYPayoutVault deployed at: ${vault.address}`);
  
  // Link PoW token to vault
  const powToken = await hre.ethers.getContractAt("FIGGYPoWToken", powTokenAddress);
  const tx = await powToken.setPayoutVault(vault.address);
  await tx.wait();
  console.log(`🔗 FIGGYPoWToken now linked to PayoutVault`);
  
  // Update deployments file
  deployments.FIGGYPayoutVault = {
    address: vault.address,
    powTokenAddress: powTokenAddress,
    deployer: deployer.address,
    deployedAt: new Date().toISOString(),
    blockNumber: await ethers.provider.getBlockNumber(),
  };
  
  fs.writeFileSync(deploymentFile, JSON.stringify(deployments, null, 2));
  console.log(`📄 Deployment updated: ${deploymentFile}`);
  
  // Save Vault ABI
  const abiDir = path.join(__dirname, "../abis");
  if (!fs.existsSync(abiDir)) {
    fs.mkdirSync(abiDir, { recursive: true });
  }
  
  const artifact = require(path.join(
    __dirname,
    "../artifacts/contracts/FIGGYPayoutVault.sol/FIGGYPayoutVault.json"
  ));
  const abiFile = path.join(abiDir, "FIGGYPayoutVault.json");
  fs.writeFileSync(abiFile, JSON.stringify(artifact.abi, null, 2));
  console.log(`📋 ABI saved to: ${abiFile}`);
  
  console.log("\n✨ FIGGYPayoutVault deployment complete!");
  console.log(`
Contract Details:
  PoW Token: ${powTokenAddress}
  Vault: ${vault.address}
  Network: ${network}
  Deployer: ${deployer.address}
  
Integration:
  - Use ${vault.address} in pow_blockchain/.env as PAYOUT_VAULT_ADDRESS
  - Use ${deploymentFile} for Python web3 integration
  `);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
