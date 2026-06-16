import { Apideck } from '@apideck/unify';

async function main() {
  try {
    const apideck = new Apideck({
      token: process.env.APIDECK_API_KEY || '',
      appId: process.env.APIDECK_APP_ID || '',
      consumerId: process.env.APIDECK_CONSUMER_ID || '',
    });

    const response = await apideck.fileStorage.drives.list({
      serviceId: 'onedrive',
    });

    console.log(JSON.stringify(response, null, 2));
  } catch (error) {
    console.error('Error:', error);
  }
}

main();