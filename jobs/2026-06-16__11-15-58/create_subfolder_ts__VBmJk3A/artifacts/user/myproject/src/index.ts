import { Apideck } from "@apideck/unify";
import * as fs from "fs";
import * as path from "path";

async function main(): Promise<void> {
  // Read configuration from environment variables
  const apiKey = process.env.APIDECK_API_KEY;
  const appId = process.env.APIDECK_APP_ID;
  const consumerId = process.env.APIDECK_CONSUMER_ID;
  const driveName = process.env.APIDECK_FILE_STORAGE_DRIVE_NAME;
  const runId = process.env.ZEALT_RUN_ID;

  if (!apiKey) throw new Error("Missing env var: APIDECK_API_KEY");
  if (!appId) throw new Error("Missing env var: APIDECK_APP_ID");
  if (!consumerId) throw new Error("Missing env var: APIDECK_CONSUMER_ID");
  if (!driveName)
    throw new Error("Missing env var: APIDECK_FILE_STORAGE_DRIVE_NAME");
  if (!runId) throw new Error("Missing env var: ZEALT_RUN_ID");

  const parentFolderName = `apideck-parent-${runId}`;
  const childFolderName = `apideck-child-${runId}`;

  console.log(`Initializing Apideck SDK...`);
  const apideck = new Apideck({
    apiKey,
    appId,
    consumerId,
  });

  // Step 1: List drives and find the one matching APIDECK_FILE_STORAGE_DRIVE_NAME
  console.log(`Searching for drive named: "${driveName}"...`);

  let targetDriveId: string | undefined;

  const driveIterator = await apideck.fileStorage.drives.list({
    serviceId: "onedrive",
    limit: 200,
  });

  outerLoop: for await (const page of driveIterator) {
    if (page.getDrivesResponse?.data) {
      for (const drive of page.getDrivesResponse.data) {
        console.log(`  Found drive: "${drive.name}" (id: ${drive.id})`);
        if (drive.name === driveName) {
          targetDriveId = drive.id;
          console.log(`  --> Matched! Drive ID: ${targetDriveId}`);
          break outerLoop;
        }
      }
    }
  }

  if (!targetDriveId) {
    throw new Error(
      `Drive named "${driveName}" not found in OneDrive drives listing`
    );
  }

  // Step 2: Create the parent folder at the drive root
  console.log(`\nCreating parent folder: "${parentFolderName}"...`);

  const parentCreateResult =
    await apideck.fileStorage.folders.create({
      serviceId: "onedrive",
      createFolderRequest: {
        name: parentFolderName,
        parentFolderId: "root",
        driveId: targetDriveId,
      },
    });

  if (!parentCreateResult.createFolderResponse?.data?.id) {
    throw new Error(
      `Failed to create parent folder. Response: ${JSON.stringify(
        parentCreateResult
      )}`
    );
  }

  const parentFolderId = parentCreateResult.createFolderResponse.data.id;
  console.log(`Parent folder created. ID: ${parentFolderId}`);

  // Step 3: Create the child folder inside the parent folder
  console.log(
    `\nCreating child folder: "${childFolderName}" inside parent (id: ${parentFolderId})...`
  );

  const childCreateResult =
    await apideck.fileStorage.folders.create({
      serviceId: "onedrive",
      createFolderRequest: {
        name: childFolderName,
        parentFolderId: parentFolderId,
        driveId: targetDriveId,
      },
    });

  if (!childCreateResult.createFolderResponse?.data?.id) {
    throw new Error(
      `Failed to create child folder. Response: ${JSON.stringify(
        childCreateResult
      )}`
    );
  }

  const childFolderId = childCreateResult.createFolderResponse.data.id;
  console.log(`Child folder created. ID: ${childFolderId}`);

  // Step 4: Write the JSON log file
  const logData = {
    drive_id: targetDriveId,
    parent_folder_id: parentFolderId,
    parent_folder_name: parentFolderName,
    child_folder_id: childFolderId,
    child_folder_name: childFolderName,
  };

  const logPath = path.join("/home/user/myproject", "output.log");
  fs.writeFileSync(logPath, JSON.stringify(logData, null, 2), "utf-8");

  console.log(`\nLog written to: ${logPath}`);
  console.log(JSON.stringify(logData, null, 2));
  console.log("\nDone!");
}

main().catch((err) => {
  console.error("Error:", err);
  process.exit(1);
});
