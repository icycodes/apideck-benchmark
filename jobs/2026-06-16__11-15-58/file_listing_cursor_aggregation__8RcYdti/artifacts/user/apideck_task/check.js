const https = require('https');

async function request(url, options, body) {
  return new Promise((resolve, reject) => {
    const req = https.request(url, options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({ status: res.statusCode, data: JSON.parse(data) }));
    });
    req.on('error', reject);
    if (body) {
      req.write(body);
    }
    req.end();
  });
}

(async () => {
  const headers = {
    'Authorization': `Bearer ${process.env.APIDECK_API_KEY}`,
    'x-apideck-app-id': process.env.APIDECK_APP_ID,
    'x-apideck-consumer-id': process.env.APIDECK_CONSUMER_ID,
    'x-apideck-service-id': 'onedrive'
  };

  const res = await request('https://unify.apideck.com/file-storage/drives', { headers });
  console.log(JSON.stringify(res.data, null, 2));
})();