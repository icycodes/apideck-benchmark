import os
import json
import urllib.request

API_KEY = os.environ.get('APIDECK_API_KEY')
APP_ID = os.environ.get('APIDECK_APP_ID')
CONSUMER_ID = os.environ.get('APIDECK_CONSUMER_ID')
RUN_ID = os.environ.get('ZEALT_RUN_ID')

headers = {
    'Authorization': f'Bearer {API_KEY}',
    'x-apideck-app-id': APP_ID,
    'x-apideck-consumer-id': CONSUMER_ID,
    'x-apideck-service-id': 'onedrive'
}

url = 'https://unify.apideck.com/file-storage/files'
found = []

while url:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode())
            for f in res_data.get('data', []):
                if RUN_ID in f.get('name', ''):
                    found.append(f['name'])
            url = res_data.get('links', {}).get('next')
    except Exception as e:
        print(e)
        break

print("Found files:", found)
