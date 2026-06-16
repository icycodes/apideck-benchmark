import { Apideck } from '@apideck/unify';

const apideck = new Apideck({
  apiKey: 'fake',
  appId: 'fake',
  consumerId: 'fake',
});

async function test() {
  const drivesResponse = await apideck.fileStorage.drives.list({
    serviceId: 'onedrive',
  });
  console.log(drivesResponse);
}
