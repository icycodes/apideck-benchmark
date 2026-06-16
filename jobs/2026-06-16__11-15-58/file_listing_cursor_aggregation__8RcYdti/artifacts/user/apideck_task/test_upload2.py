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

drives_url = 'https://unify.apideck.com/file-storage/drives'
resp = requests.get(drives_url, headers=headers)
drives = resp.json().get('data', [])
drive_id = next((d['id'] for d in drives if d['name'] == drive_name), None)

print(f"Drive ID: {drive_id}")

# Let's try to upload a file
upload_url = 'https://upload.apideck.com/file-storage/files'
file_name = f'AGG-{run_id}-test.txt'

headers['x-apideck-metadata'] = json.dumps({
    'name': file_name,
    'drive_id': drive_id
})

files = {
    'file': ('test.txt', b'Hello world', 'text/plain')
}

resp = requests.post(upload_url, headers=headers, files=files)
print(resp.status_code)
print(resp.text)
