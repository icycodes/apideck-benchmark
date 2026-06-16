import { Apideck } from "@apideck/unify";
import * as fs from "fs";
import * as path from "path";

async function main() {
  const appId = process.env.APIDECK_APP_ID!;
  const apiKey = process.env.APIDECK_API_KEY!;
  const consumerId = process.env.APIDECK_CONSUMER_ID!;
  const driveName = process.env.APIDECK_FILE_STORAGE_DRIVE_NAME!;
  const runId = process.env.ZEALT_RUN_ID!;

  const apideck = new Apideck({
    apiKey,
    appId,
    consumerId,
  });

  // Step 1: Find the drive matching APIDECK_FILE_STORAGE_DRIVE_NAME
  let driveId: string | undefined;

  const drivesIterator = await apideck.fileStorage.drives.list({
    serviceId: "onedrive",
  });

  for await (const page of drivesIterator) {
    const drives = page.getDrivesResponse?.data ?? [];
    for (const drive of drives) {
      if (drive.name === driveName) {
        driveId = drive.id;
        break;
      }
    }
    if (driveId) break;
  }

  if (!driveId) {
    throw new Error(`Drive with name "${driveName}" not found`);
  }

  console.log(`Found drive: id=${driveId}, name=${driveName}`);

  // Step 2: Create parent folder at root
  const parentFolderName = `apideck-parent-${runId}`;
  const parentResponse = await apideck.fileStorage.folders.create({
    serviceId: "onedrive",
    createFolderRequest: {
      name: parentFolderName,
      parentFolderId: "root",
      driveId: driveId,
    },
  });

  const parentFolderId = parentResponse.createFolderResponse?.data.id;
  if (!parentFolderId) {
    throw new Error("Failed to create parent folder: no ID returned");
  }

  console.log(`Created parent folder: id=${parentFolderId}, name=${parentFolderName}`);

  // Step 3: Create child folder inside parent
  const childFolderName = `apideck-child-${runId}`;
  const childResponse = await apideck.fileStorage.folders.create({
    serviceId: "onedrive",
    createFolderRequest: {
      name: childFolderName,
      parentFolderId: parentFolderId,
      driveId: driveId,
    },
  });

  const childFolderId = childResponse.createFolderResponse?.data.id;
  if (!childFolderId) {
    throw new Error("Failed to create child folder: no ID returned");
  }

  console.log(`Created child folder: id=${childFolderId}, name=${childFolderName}`);

  // Step 4: Write output log
  const output = {
    drive_id: driveId,
    parent_folder_id: parentFolderId,
    parent_folder_name: parentFolderName,
    child_folder_id: childFolderId,
    child_folder_name: childFolderName,
  };

  const outputPath = path.join("/home/user/myproject", "output.log");
  fs.writeFileSync(outputPath, JSON.stringify(output, null, 2));
  console.log(`Output written to ${outputPath}`);
  console.log(JSON.stringify(output, null, 2));
}

main().catch((err) => {
  console.error("Error:", err);
  process.exit(1);
});