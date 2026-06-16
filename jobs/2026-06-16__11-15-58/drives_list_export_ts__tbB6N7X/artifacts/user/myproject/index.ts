import { Apideck } from "@apideck/unify";
import { promises as fs } from "fs";
import path from "path";

async function main() {
  const apiKey = process.env.APIDECK_API_KEY!;
  const appId = process.env.APIDECK_APP_ID!;
  const consumerId = process.env.APIDECK_CONSUMER_ID!;
  const driveName = process.env.APIDECK_FILE_STORAGE_DRIVE_NAME!;
  const runId = process.env.ZEALT_RUN_ID!;

  const apideck = new Apideck({
    apiKey,
    appId,
    consumerId,
  });

  const response = await apideck.fileStorage.drives.list({
    serviceId: "onedrive",
  });

  // The SDK returns the response with drives under getDrivesResponse.data
  const drives = response.getDrivesResponse?.data ?? [];
  const matchedDrive = drives.find((drive) => drive.name === driveName);

  if (!matchedDrive) {
    throw new Error(
      `No drive found with name "${driveName}". Available drives: ${drives.map((d) => d.name).join(", ")}`
    );
  }

  const driveMetadata = {
    id: matchedDrive.id,
    name: matchedDrive.name,
  };

  // Write drive.json
  const driveJsonPath = path.join("/home/user/myproject", "drive.json");
  await fs.writeFile(driveJsonPath, JSON.stringify(driveMetadata, null, 2));

  // Write output.log
  const logPath = path.join("/home/user/myproject", "output.log");
  const logContent = `Run ID: ${runId}\nDrive ID: ${matchedDrive.id}\n`;
  await fs.writeFile(logPath, logContent);

  console.log(logContent);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});