import { writeFile } from "node:fs/promises";
import { Apideck } from "@apideck/unify";

type RequiredEnv = {
  APIDECK_APP_ID: string;
  APIDECK_API_KEY: string;
  APIDECK_CONSUMER_ID: string;
  APIDECK_FILE_STORAGE_DRIVE_NAME: string;
  ZEALT_RUN_ID: string;
};

function requireEnv(): RequiredEnv {
  const names: Array<keyof RequiredEnv> = [
    "APIDECK_APP_ID",
    "APIDECK_API_KEY",
    "APIDECK_CONSUMER_ID",
    "APIDECK_FILE_STORAGE_DRIVE_NAME",
    "ZEALT_RUN_ID",
  ];

  const missing = names.filter((name) => !process.env[name]);
  if (missing.length > 0) {
    throw new Error(`Missing required environment variables: ${missing.join(", ")}`);
  }

  return Object.fromEntries(names.map((name) => [name, process.env[name] as string])) as RequiredEnv;
}

function requireCreatedId(response: unknown, label: string): string {
  const id = (response as { createFolderResponse?: { data?: { id?: string } } }).createFolderResponse?.data?.id;
  if (!id) {
    throw new Error(`Apideck did not return an id for the ${label} folder create response: ${JSON.stringify(response)}`);
  }
  return id;
}

async function main() {
  const env = requireEnv();
  const serviceId = "onedrive";

  const apideck = new Apideck({
    apiKey: env.APIDECK_API_KEY,
    appId: env.APIDECK_APP_ID,
    consumerId: env.APIDECK_CONSUMER_ID,
  });

  let drive: { id: string; name: string } | undefined;
  const drivePages = await apideck.fileStorage.drives.list({
    serviceId,
    limit: 200,
  });

  for await (const page of drivePages) {
    const matchingDrive = page.getDrivesResponse?.data.find(
      (candidate) => candidate.name === env.APIDECK_FILE_STORAGE_DRIVE_NAME,
    );

    if (matchingDrive) {
      drive = matchingDrive;
      break;
    }
  }

  if (!drive) {
    throw new Error(`No OneDrive drive found with exact name ${JSON.stringify(env.APIDECK_FILE_STORAGE_DRIVE_NAME)}`);
  }

  const parentFolderName = `apideck-parent-${env.ZEALT_RUN_ID}`;
  const childFolderName = `apideck-child-${env.ZEALT_RUN_ID}`;

  const parentResponse = await apideck.fileStorage.folders.create({
    serviceId,
    createFolderRequest: {
      name: parentFolderName,
      parentFolderId: "root",
      driveId: drive.id,
    },
  });
  const parentFolderId = requireCreatedId(parentResponse, "parent");

  const childResponse = await apideck.fileStorage.folders.create({
    serviceId,
    createFolderRequest: {
      name: childFolderName,
      parentFolderId: parentFolderId,
      driveId: drive.id,
    },
  });
  const childFolderId = requireCreatedId(childResponse, "child");

  const log = {
    drive_id: drive.id,
    drive_name: drive.name,
    parent_folder_id: parentFolderId,
    parent_folder_name: parentFolderName,
    child_folder_id: childFolderId,
    child_folder_name: childFolderName,
  };

  await writeFile("output.log", `${JSON.stringify(log, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(log, null, 2));
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack ?? error.message : error);
  process.exitCode = 1;
});
