import os
import json
import urllib.request
import urllib.error

API_KEY = os.environ.get('APIDECK_API_KEY')
APP_ID = os.environ.get('APIDECK_APP_ID')
CONSUMER_ID = os.environ.get('APIDECK_CONSUMER_ID')
DRIVE_NAME = os.environ.get('APIDECK_FILE_STORAGE_DRIVE_NAME')
RUN_ID = os.environ.get('ZEALT_RUN_ID')

headers = {
    'Authorization': f'Bearer {API_KEY}',
    'x-apideck-app-id': APP_ID,
    'x-apideck-consumer-id': CONSUMER_ID,
    'x-apideck-service-id': 'onedrive'
}

req = urllib.request.Request('https://unify.apideck.com/file-storage/folders/root/contents?drive_id=3ada079b78534ff1', headers=headers)
try:
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode())
        for f in res_data.get('data', []):
            print(f['name'], f['id'])
except urllib.error.HTTPError as e:
    print(f"List failed: {e.code}")
    print(e.read().decode())
