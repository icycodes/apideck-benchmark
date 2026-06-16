import os
import json
import requests
from urllib.parse import urlencode

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

files_url = 'https://unify.apideck.com/file-storage/files'
params = {
    'filter[folder_id]': 'root',
    'filter[drive_id]': drive_id,
    'limit': 3
}

url = f"{files_url}?{urlencode(params)}"
resp = requests.get(url, headers=headers)
print(resp.status_code)
print(json.dumps(resp.json(), indent=2))
