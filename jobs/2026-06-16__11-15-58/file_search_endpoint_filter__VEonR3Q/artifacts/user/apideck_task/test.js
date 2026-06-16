const https = require('https');

const API_KEY = process.env.APIDECK_API_KEY;
const APP_ID = process.env.APIDECK_APP_ID;
const CONSUMER_ID = process.env.APIDECK_CONSUMER_ID;

const headers = {
  'Authorization': `Bearer ${API_KEY}`,
  'x-apideck-app-id': APP_ID,
  'x-apideck-consumer-id': CONSUMER_ID,
  'x-apideck-service-id': 'onedrive'
};

function request(url, options, body = null) {
  return new Promise((resolve, reject) => {
    const req = https.request(url, options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, headers: res.headers, data: JSON.parse(data) });
        } catch (e) {
          resolve({ status: res.statusCode, headers: res.headers, data });
        }
      });
    });
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}

async function run() {
  const drivesRes = await request('https://unify.apideck.com/file-storage/drives', { headers });
  console.log('Drives:', JSON.stringify(drivesRes.data, null, 2));
}

run().catch(console.error);
