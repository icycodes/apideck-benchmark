import { Apideck } from "@apideck/unify";

async function main() {
  const apiKey = process.env.APIDECK_API_KEY;
  const appId = process.env.APIDECK_APP_ID;
  const consumerId = process.env.APIDECK_CONSUMER_ID;
  const driveName = process.env.APIDECK_FILE_STORAGE_DRIVE_NAME;
  const runId = process.env.ZEALT_RUN_ID;

  if (!apiKey || !appId || !consumerId || !driveName || !runId) {
    console.error("Missing required environment variables.");
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

  console.log(`Listing items in drive: ${resolvedDriveId} to clean up...`);
  
  // List files/folders in the root
  const filesResult = await client.fileStorage.files.list({
    serviceId: "onedrive",
    filter: {
      driveId: resolvedDriveId,
    }
  });

  for await (const page of filesResult) {
    const files = page.getFilesResponse?.data;
    if (files) {
      for (const item of files) {
        if (item.name && item.name.includes(runId)) {
          console.log(`Found item to delete: ${item.name} (ID: ${item.id}, Type: ${item.type})`);
          if (item.type === "folder") {
            try {
              await client.fileStorage.folders.delete({
                id: item.id!,
                serviceId: "onedrive",
              });
              console.log(`Deleted folder: ${item.name}`);
            } catch (err) {
              console.error(`Failed to delete folder ${item.name}:`, err);
            }
          } else {
            try {
              await client.fileStorage.files.delete({
                id: item.id!,
                serviceId: "onedrive",
              });
              console.log(`Deleted file: ${item.name}`);
            } catch (err) {
              console.error(`Failed to delete file ${item.name}:`, err);
            }
          }
        }
      }
    }
  }
  console.log("Cleanup complete!");
}

main().catch(err => {
  console.error("Cleanup failed:", err);
});
