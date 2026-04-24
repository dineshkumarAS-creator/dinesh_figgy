/**
 * Deploy FIGGYPoWToken contract
 * 
 * Usage:
 *   - Local: npx hardhat run scripts/deploy_pow_token.js --network localhost
 *   - Mumbai: npx hardhat run scripts/deploy_pow_token.js --network mumbai
 *   - Polygon: npx hardhat run scripts/deploy_pow_token.js --network polygon
 */

const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("🔷 Deploying FIGGYPoWToken...");
  
  const [deployer] = await ethers.getSigners();
  console.log(`📍 Deployer: ${deployer.address}`);
  
  const network = hre.network.name;
  console.log(`🌐 Network: ${network}`);
  
  // Deploy contract
  const FIGGYPoWToken = await hre.ethers.getContractFactory("FIGGYPoWToken");
  const powToken = await FIGGYPoWToken.deploy();
  
  await powToken.deployed();
  console.log(`✅ FIGGYPoWToken deployed at: ${powToken.address}`);
  
  // Save deployment info
  const deployments = {
    network: network,
    FIGGYPoWToken: {
      address: powToken.address,
      deployer: deployer.address,
      deployedAt: new Date().toISOString(),
      blockNumber: await ethers.provider.getBlockNumber(),
    },
  };
  
  // Create deployments directory if it doesn't exist
  const deploymentsDir = path.join(__dirname, "../deployments");
  if (!fs.existsSync(deploymentsDir)) {
    fs.mkdirSync(deploymentsDir, { recursive: true });
  }
  
  // Save to JSON
  const deploymentFile = path.join(deploymentsDir, `${network}.json`);
  const existingDeployments = fs.existsSync(deploymentFile)
    ? JSON.parse(fs.readFileSync(deploymentFile, "utf8"))
    : {};
  
  const updated = {
    ...existingDeployments,
    ...deployments,
  };
  
  fs.writeFileSync(deploymentFile, JSON.stringify(updated, null, 2));
  console.log(`📄 Deployment saved to: ${deploymentFile}`);
  
  // Also save ABI for web3.py integration
  const abiDir = path.join(__dirname, "../abis");
  if (!fs.existsSync(abiDir)) {
    fs.mkdirSync(abiDir, { recursive: true });
  }
  
  const artifact = require(path.join(
    __dirname,
    "../artifacts/contracts/FIGGYPoWToken.sol/FIGGYPoWToken.json"
  ));
  const abiFile = path.join(abiDir, "FIGGYPoWToken.json");
  fs.writeFileSync(abiFile, JSON.stringify(artifact.abi, null, 2));
  console.log(`📋 ABI saved to: ${abiFile}`);
  
  console.log("\n✨ FIGGYPoWToken deployment complete!");
  console.log(`
Contract Details:
  Address: ${powToken.address}
  Network: ${network}
  Deployer: ${deployer.address}
  
Integration:
  - Use ${powToken.address} in pow_blockchain/.env as POW_TOKEN_ADDRESS
  - Use ${deploymentFile} for Python web3 integration
  - Call setPayoutVault(${deployer.address}) after deploying FIGGYPayoutVault
  `);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
