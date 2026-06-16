import { Apideck } from "@apideck/unify";

const apiKey = process.env.APIDECK_API_KEY;
const appId = process.env.APIDECK_APP_ID;
const consumerId = process.env.APIDECK_CONSUMER_ID;
const driveName = process.env.APIDECK_FILE_STORAGE_DRIVE_NAME;
const runId = process.env.ZEALT_RUN_ID;

console.log("Env check:");
console.log("apiKey exists:", !!apiKey);
console.log("appId:", appId);
console.log("consumerId:", consumerId);
console.log("driveName:", driveName);
console.log("runId:", runId);

if (!apiKey || !appId || !consumerId || !driveName) {
  console.error("Missing required environment variables!");
  process.exit(1);
}

const client = new Apideck({
  apiKey,
  appId,
  consumerId,
});

async function main() {
  console.log("Listing drives...");
  const result = await client.fileStorage.drives.list({
    serviceId: "onedrive",
  });

  let foundDrive = null;
  for await (const page of result) {
    console.log("Page status code:", page.httpMeta.response.status);
    const drives = page.getDrivesResponse?.data;
    if (drives) {
      console.log(`Found ${drives.length} drives on this page.`);
      for (const d of drives) {
        console.log(`Drive: ID=${d.id}, Name=${d.name}`);
        if (d.name === driveName) {
          foundDrive = d;
        }
      }
    }
  }

  if (foundDrive) {
    console.log("SUCCESS! Found matching drive:", foundDrive);
  } else {
    console.log("FAILED! Drive not found matching name:", driveName);
  }
}

main().catch(err => {
  console.error("Error in main:", err);
});
