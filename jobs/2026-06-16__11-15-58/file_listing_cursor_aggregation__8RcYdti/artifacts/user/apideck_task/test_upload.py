import os
import json
import requests

app_id = os.environ.get('APIDECK_APP_ID')
api_key = os.environ.get('APIDECK_API_KEY')
consumer_id = os.environ.get('APIDECK_CONSUMER_ID')
run_id = os.environ.get('ZEALT_RUN_ID')
drive_name = os.environ.get('APIDECK_FILE_STORAGE_DRIVE_NAME')

headers = {
    'Authorization': f'Bearer {api_key}',
    'x-apideck-app-id': app_id,
    'x-apideck-consumer-id': consumer_id,
    'x-apideck-service-id': 'onedrive'
}

# Get drive id
drives_url = 'https://unify.apideck.com/file-storage/drives'
resp = requests.get(drives_url, headers=headers)
drives = resp.json().get('data', [])
drive_id = None
for d in drives:
    if d.get('name') == drive_name:
        drive_id = d.get('id')
        break

print(f"Drive ID: {drive_id}")

# Let's try to upload a file
upload_url = 'https://upload.apideck.com/file-storage/files'
files = {
    'file': ('test.txt', b'Hello world', 'text/plain')
}
data = {
    'name': f'AGG-{run_id}-test.txt',
    'drive_id': drive_id
}

resp = requests.post(upload_url, headers=headers, files=files, data=data)
print(resp.status_code)
print(resp.text)
