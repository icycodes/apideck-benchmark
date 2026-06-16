import { Apideck } from '@apideck/unify';
import * as fs from 'fs/promises';

async function main() {
  try {
    const apideck = new Apideck({
      token: process.env.APIDECK_API_KEY || '',
      appId: process.env.APIDECK_APP_ID || '',
      consumerId: process.env.APIDECK_CONSUMER_ID || '',
    });

    const targetDriveName = process.env.APIDECK_FILE_STORAGE_DRIVE_NAME;
    const runId = process.env.ZEALT_RUN_ID;

    if (!targetDriveName) {
      throw new Error('APIDECK_FILE_STORAGE_DRIVE_NAME is not set');
    }

    const response = await apideck.fileStorage.drives.list({
      serviceId: 'onedrive',
    });

    const drives = response.getDrivesResponse?.data || [];
    const drive = drives.find((d: any) => d.name === targetDriveName);

    if (!drive) {
      throw new Error(`Drive with name ${targetDriveName} not found`);
    }

    await fs.writeFile('drive.json', JSON.stringify({ id: drive.id, name: drive.name }, null, 2));
    await fs.writeFile('output.log', `Run ID: ${runId}\nDrive ID: ${drive.id}\n`);
    
    console.log('Successfully wrote drive.json and output.log');
  } catch (error) {
    console.error('Error:', error);
    process.exit(1);
  }
}

main();