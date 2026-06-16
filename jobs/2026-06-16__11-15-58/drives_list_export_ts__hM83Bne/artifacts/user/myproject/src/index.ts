import { Apideck } from "@apideck/unify";
import { writeFile } from "fs/promises";
import { join } from "path";

async function main() {
  const apiKey = process.env.APIDECK_API_KEY;
  const appId = process.env.APIDECK_APP_ID;
  const consumerId = process.env.APIDECK_CONSUMER_ID;
  const driveName = process.env.APIDECK_FILE_STORAGE_DRIVE_NAME;
  const runId = process.env.ZEALT_RUN_ID;

  if (!apiKey) throw new Error("Missing APIDECK_API_KEY");
  if (!appId) throw new Error("Missing APIDECK_APP_ID");
  if (!consumerId) throw new Error("Missing APIDECK_CONSUMER_ID");
  if (!driveName) throw new Error("Missing APIDECK_FILE_STORAGE_DRIVE_NAME");
  if (!runId) throw new Error("Missing ZEALT_RUN_ID");

  const client = new Apideck({
    apiKey,
    appId,
    consumerId,
  });

  const iterator = await client.fileStorage.drives.list({
    serviceId: "onedrive",
    limit: 200,
  });

  let matchedDrive: { id: string; name: string } | null = null;

  for await (const page of iterator) {
    const drives = page.getDrivesResponse?.data ?? [];
    for (const drive of drives) {
      if (drive.name === driveName) {
        matchedDrive = {
          id: drive.id as string,
          name: drive.name as string,
        };
        break;
      }
    }
    if (matchedDrive) break;
  }

  if (!matchedDrive) {
    throw new Error(`No drive found with name: ${driveName}`);
  }

  const projectDir = "/home/user/myproject";

  // Write drive.json
  await writeFile(
    join(projectDir, "drive.json"),
    JSON.stringify(matchedDrive, null, 2),
    "utf-8"
  );

  // Write output.log
  const logContent = `Run ID: ${runId}\nDrive ID: ${matchedDrive.id}\n`;
  await writeFile(join(projectDir, "output.log"), logContent, "utf-8");

  console.log(`Run ID: ${runId}`);
  console.log(`Drive ID: ${matchedDrive.id}`);
  console.log(`Drive Name: ${matchedDrive.name}`);
  console.log("Artifacts written successfully.");
}

main().catch((err) => {
  console.error("Error:", err);
  process.exit(1);
});
