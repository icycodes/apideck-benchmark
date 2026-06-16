import { Apideck } from "@apideck/unify";
import * as fs from "fs";

async function main() {
  const apiKey = process.env.APIDECK_API_KEY;
  const appId = process.env.APIDECK_APP_ID;
  const consumerId = process.env.APIDECK_CONSUMER_ID;

  if (!apiKey || !appId || !consumerId) {
    console.error("Missing required environment variables for verification.");
    process.exit(1);
  }

  const logFilePath = "/home/user/myproject/output.log";
  if (!fs.existsSync(logFilePath)) {
    console.error("Log file output.log does not exist!");
    process.exit(1);
  }

  const logData = JSON.parse(fs.readFileSync(logFilePath, "utf8"));
  console.log("Read log data:", logData);

  const client = new Apideck({
    apiKey,
    appId,
    consumerId,
  });

  console.log(`Fetching parent folder with ID: ${logData.parent_folder_id}...`);
  const parentFolderRes = await client.fileStorage.folders.get({
    id: logData.parent_folder_id,
    serviceId: "onedrive",
  });

  const parentFolder = parentFolderRes.getFolderResponse?.data;
  if (!parentFolder) {
    throw new Error("Could not fetch parent folder!");
  }
  console.log("Parent folder name fetched:", parentFolder.name);
  if (parentFolder.name !== logData.parent_folder_name) {
    throw new Error(`Name mismatch for parent folder: ${parentFolder.name} !== ${logData.parent_folder_name}`);
  }

  console.log(`Fetching child folder with ID: ${logData.child_folder_id}...`);
  const childFolderRes = await client.fileStorage.folders.get({
    id: logData.child_folder_id,
    serviceId: "onedrive",
  });

  const childFolder = childFolderRes.getFolderResponse?.data;
  if (!childFolder) {
    throw new Error("Could not fetch child folder!");
  }
  console.log("Child folder name fetched:", childFolder.name);
  if (childFolder.name !== logData.child_folder_name) {
    throw new Error(`Name mismatch for child folder: ${childFolder.name} !== ${logData.child_folder_name}`);
  }

  console.log("Child folder parentFolders chain:", childFolder.parentFolders);
  const hasParentInChain = childFolder.parentFolders.some(pf => pf.id === logData.parent_folder_id);
  if (!hasParentInChain) {
    throw new Error(`Child folder parentFolders chain does not include the parent folder ID: ${logData.parent_folder_id}`);
  }

  console.log("VERIFICATION SUCCESSFUL! Folder hierarchy verified successfully via Apideck File Storage API.");
}

main().catch(err => {
  console.error("Verification failed:", err);
  process.exit(1);
});
