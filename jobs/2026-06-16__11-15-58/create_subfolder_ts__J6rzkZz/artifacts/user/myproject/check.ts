import { Apideck } from '@apideck/unify';
const apideck = new Apideck({ apiKey: 'a', appId: 'a', consumerId: 'a' });

async function check() {
  const drivesResponse = await apideck.fileStorage.drives.list({
    serviceId: 'onedrive',
  });
  console.log(Object.keys(drivesResponse));
}
check().catch(console.error);
