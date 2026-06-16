import { Apideck } from "@apideck/unify";
import fs from "node:fs/promises";

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

  console.log(`Initializing Apideck SDK with App ID: ${appId}, Consumer ID: ${consumerId}`);
  const apideck = new Apideck({
    apiKey,
    appId,
    consumerId,
  });

  console.log(`Listing drives for service 'onedrive' to find drive: '${driveName}'`);

  let matchedDrive: { id: string; name: string } | null = null;

  try {
    const response = await apideck.fileStorage.drives.list({
      serviceId: "onedrive",
    });

    for await (const page of response) {
      const drives = page.getDrivesResponse?.data;
      if (drives) {
        for (const drive of drives) {
          console.log(`Found drive: ${drive.name} (${drive.id})`);
          if (drive.name === driveName) {
            matchedDrive = {
              id: drive.id,
              name: drive.name,
            };
            break;
          }
        }
      }
      if (matchedDrive) {
        break;
      }
    }
  } catch (error) {
    console.error("Error listing drives from Apideck API:", error);
    process.exit(1);
  }

  if (!matchedDrive) {
    console.error(`Drive with name '${driveName}' not found.`);
    process.exit(1);
  }

  console.log(`Matched drive: ${matchedDrive.name} with ID: ${matchedDrive.id}`);

  const driveJsonPath = "/home/user/myproject/drive.json";
  const logFilePath = "/home/user/myproject/output.log";

  // Persist matched drive's metadata as JSON
  await fs.writeFile(driveJsonPath, JSON.stringify(matchedDrive, null, 2), "utf-8");
  console.log(`Saved drive metadata to ${driveJsonPath}`);

  // Write log file
  const logContent = `Run ID: ${runId}\nDrive ID: ${matchedDrive.id}\n`;
  await fs.writeFile(logFilePath, logContent, "utf-8");
  console.log(`Saved log to ${logFilePath}`);
}

main().catch((err) => {
  console.error("Unexpected error:", err);
  process.exit(1);
});
