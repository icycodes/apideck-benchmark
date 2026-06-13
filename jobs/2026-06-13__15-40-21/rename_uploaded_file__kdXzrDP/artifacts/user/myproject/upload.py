import os
import requests
import json

api_key = os.environ.get('APIDECK_API_KEY')
app_id = os.environ.get('APIDECK_APP_ID')
consumer_id = os.environ.get('APIDECK_CONSUMER_ID')
run_id = os.environ.get('ZEALT_RUN_ID')
service_id = 'onedrive'

# From interact.py, we found the drive named 'OneDrive' has ID '3ada079b78534ff1'
drive_id = '3ada079b78534ff1'

headers = {
    'Authorization': f'Bearer {api_key}',
    'x-apideck-app-id': app_id,
    'x-apideck-consumer-id': consumer_id,
    'x-apideck-service-id': service_id,
    'Content-Type': 'text/plain',
    'x-apideck-metadata': json.dumps({
        'name': f'original-{run_id}.txt',
        'parent_folder_id': 'root',
        'drive_id': drive_id
    })
}

url = 'https://upload.apideck.com/file-storage/files'
data = b'hello apideck'

print("Uploading to:", url)
print("Headers:", {k: v for k, v in headers.items() if k != 'Authorization'})

response = requests.post(url, headers=headers, data=data)
print("Status Code:", response.status_code)
print("Response JSON:")
try:
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(response.text)
