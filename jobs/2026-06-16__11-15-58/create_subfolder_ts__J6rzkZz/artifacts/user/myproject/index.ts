import { Apideck } from '@apideck/unify';
import * as fs from 'fs';

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

  console.log('Fetching drives...');
  let targetDriveId: string | undefined;
  
  const drivesResponse = await apideck.fileStorage.drives.list({
    serviceId: 'onedrive',
  });

  // The drives listing endpoint returns a paginated iterable
  for await (const page of drivesResponse) {
    const drives = page.getDrivesResponse?.data || [];
    for (const drive of drives) {
      if (drive.name === driveName) {
        targetDriveId = drive.id;
        break;
      }
    }
    if (targetDriveId) break;
  }

  if (!targetDriveId) {
    throw new Error(`Drive with name ${driveName} not found`);
  }

  console.log(`Found drive: ${targetDriveId}`);

  const parentFolderName = `apideck-parent-${runId}`;
  const childFolderName = `apideck-child-${runId}`;

  console.log(`Creating parent folder: ${parentFolderName}`);
  const parentResponse = await apideck.fileStorage.folders.create({
    serviceId: 'onedrive',
    createFolderRequest: {
      name: parentFolderName,
      parentFolderId: 'root',
      driveId: targetDriveId,
    },
  });

  const parentFolderId = parentResponse.createFolderResponse?.data.id;
  if (!parentFolderId) {
    throw new Error('Failed to create parent folder: no ID returned');
  }
  console.log(`Parent folder created: ${parentFolderId}`);

  console.log(`Creating child folder: ${childFolderName}`);
  const childResponse = await apideck.fileStorage.folders.create({
    serviceId: 'onedrive',
    createFolderRequest: {
      name: childFolderName,
      parentFolderId: parentFolderId,
      driveId: targetDriveId,
    },
  });

  const childFolderId = childResponse.createFolderResponse?.data.id;
  if (!childFolderId) {
    throw new Error('Failed to create child folder: no ID returned');
  }
  console.log(`Child folder created: ${childFolderId}`);

  const logData = {
    drive_id: targetDriveId,
    parent_folder_id: parentFolderId,
    parent_folder_name: parentFolderName,
    child_folder_id: childFolderId,
    child_folder_name: childFolderName,
  };

  fs.writeFileSync('/home/user/myproject/output.log', JSON.stringify(logData, null, 2));
  console.log('Log file written successfully.');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
