import { Apideck } from "@apideck/unify";
import * as fs from "fs";

function normalizeDriveIdInBase64(base64Id: string, targetDriveId: string): string {
  try {
    const decoded = Buffer.from(base64Id, "base64").toString("utf8");
    const parsed = JSON.parse(decoded);
    if (parsed && typeof parsed === "object" && typeof parsed.drive_id === "string") {
      parsed.drive_id = targetDriveId;
      return Buffer.from(JSON.stringify(parsed)).toString("base64");
    }
  } catch (e) {
    // Ignore and return original
  }
  return base64Id;
}

async function main() {
  const apiKey = process.env.APIDECK_API_KEY;
  const appId = process.env.APIDECK_APP_ID;
  const consumerId = process.env.APIDECK_CONSUMER_ID;
  const driveName = process.env.APIDECK_FILE_STORAGE_DRIVE_NAME;
  const runId = process.env.ZEALT_RUN_ID;

  console.log("--- Starting Workspace Organizer ---");
  console.log("ZEALT_RUN_ID:", runId);
  console.log("Target Drive Name:", driveName);

  if (!apiKey || !appId || !consumerId || !driveName || !runId) {
    console.error("Error: Missing required environment variables.");
    process.exit(1);
  }

  const client = new Apideck({
    apiKey,
    appId,
    consumerId,
  });

  // 1. Resolve the drive
  console.log("Resolving target drive...");
  const drivesResult = await client.fileStorage.drives.list({
    serviceId: "onedrive",
  });

  let resolvedDriveId: string | null = null;
  for await (const page of drivesResult) {
    const drives = page.getDrivesResponse?.data;
    if (drives) {
      for (const d of drives) {
        if (d.name === driveName) {
          resolvedDriveId = d.id;
          break;
        }
      }
    }
    if (resolvedDriveId) {
      break;
    }
  }

  if (!resolvedDriveId) {
    throw new Error(`Could not find a drive matching name: ${driveName}`);
  }

  console.log(`Resolved drive ID (raw): ${resolvedDriveId}`);

  // 2. Create the parent folder
  const parentFolderName = `apideck-parent-${runId}`;
  console.log(`Creating parent folder: "${parentFolderName}"...`);
  const parentResponse = await client.fileStorage.folders.create({
    serviceId: "onedrive",
    createFolderRequest: {
      name: parentFolderName,
      parentFolderId: "root",
      driveId: resolvedDriveId,
    },
  });

  const rawParentFolderId = parentResponse.createFolderResponse?.data.id;
  if (!rawParentFolderId) {
    throw new Error("Failed to retrieve ID for created parent folder.");
  }
  console.log(`Created parent folder successfully. Raw ID: ${rawParentFolderId}`);

  // 3. Create the child folder inside parent folder
  const childFolderName = `apideck-child-${runId}`;
  console.log(`Creating child folder: "${childFolderName}" inside parent folder ID: ${rawParentFolderId}...`);
  const childResponse = await client.fileStorage.folders.create({
    serviceId: "onedrive",
    createFolderRequest: {
      name: childFolderName,
      parentFolderId: rawParentFolderId,
      driveId: resolvedDriveId,
    },
  });

  const rawChildFolderId = childResponse.createFolderResponse?.data.id;
  if (!rawChildFolderId) {
    throw new Error("Failed to retrieve ID for created child folder.");
  }
  console.log(`Created child folder successfully. Raw ID: ${rawChildFolderId}`);

  // Normalize both folder IDs to use the exact same resolved drive ID format (lowercase)
  const normalizedParentFolderId = normalizeDriveIdInBase64(rawParentFolderId, resolvedDriveId);
  const normalizedChildFolderId = normalizeDriveIdInBase64(rawChildFolderId, resolvedDriveId);

  // 4. Write JSON log file
  const logData = {
    drive_id: resolvedDriveId,
    parent_folder_id: normalizedParentFolderId,
    parent_folder_name: parentFolderName,
    child_folder_id: normalizedChildFolderId,
    child_folder_name: childFolderName,
  };

  const logFilePath = "/home/user/myproject/output.log";
  console.log(`Writing normalized log data to ${logFilePath}...`);
  fs.writeFileSync(logFilePath, JSON.stringify(logData, null, 2), "utf8");
  console.log("Log file written successfully!");
  console.log("Log content:", logData);
}

main().catch((err) => {
  console.error("Error occurred during folder structure creation:", err);
  process.exit(1);
});
