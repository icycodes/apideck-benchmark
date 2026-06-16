import os
import json
import urllib.request

API_KEY = os.environ.get('APIDECK_API_KEY')
APP_ID = os.environ.get('APIDECK_APP_ID')
CONSUMER_ID = os.environ.get('APIDECK_CONSUMER_ID')
DRIVE_NAME = os.environ.get('APIDECK_FILE_STORAGE_DRIVE_NAME')

headers = {
    'Authorization': f'Bearer {API_KEY}',
    'x-apideck-app-id': APP_ID,
    'x-apideck-consumer-id': CONSUMER_ID,
    'x-apideck-service-id': 'onedrive'
}

req = urllib.request.Request('https://unify.apideck.com/file-storage/drives', headers=headers)
with urllib.request.urlopen(req) as response:
    drives = json.loads(response.read().decode())['data']

drive_id = next(d['id'] for d in drives if d['name'] == DRIVE_NAME)
print("Drive ID:", drive_id)

metadata = {
    "name": "test-upload.txt",
    "parent_folder_id": "root",
    "drive_id": drive_id
}

upload_headers = headers.copy()
upload_headers['Content-Type'] = 'text/plain'
upload_headers['x-apideck-metadata'] = json.dumps(metadata)

req = urllib.request.Request('https://upload.apideck.com/file-storage/files', data=b"hello world", headers=upload_headers, method='POST')
try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except urllib.error.HTTPError as e:
    print(e.code)
    print(e.read().decode())
