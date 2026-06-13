import os
import requests
import json

api_key = os.environ.get('APIDECK_API_KEY')
app_id = os.environ.get('APIDECK_APP_ID')
consumer_id = os.environ.get('APIDECK_CONSUMER_ID')
run_id = os.environ.get('ZEALT_RUN_ID')
service_id = 'onedrive'

# The file ID returned from upload.py
file_id = "eyJpZCI6IjNBREEwNzlCNzg1MzRGRjEhczU1YzU5ODUzYjJmYzQzNWY4Mjc3NzkyYWNmYTNlZjcwIiwiZHJpdmVfaWQiOiIzYWRhMDc5Yjc4NTM0ZmYxIn0="

headers = {
    'Authorization': f'Bearer {api_key}',
    'x-apideck-app-id': app_id,
    'x-apideck-consumer-id': consumer_id,
    'x-apideck-service-id': service_id,
    'Content-Type': 'application/json'
}

url = f'https://unify.apideck.com/file-storage/files/{file_id}'
payload = {
    'name': f'renamed-{run_id}.txt'
}

print("Patching URL:", url)
print("Payload:", payload)

response = requests.patch(url, headers=headers, json=payload)
print("Status Code:", response.status_code)
print("Response JSON:")
try:
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(response.text)
