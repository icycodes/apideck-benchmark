import os
import requests
import json

api_key = os.environ.get('APIDECK_API_KEY')
app_id = os.environ.get('APIDECK_APP_ID')
consumer_id = os.environ.get('APIDECK_CONSUMER_ID')
service_id = 'onedrive'

headers = {
    'Authorization': f'Bearer {api_key}',
    'x-apideck-app-id': app_id,
    'x-apideck-consumer-id': consumer_id,
    'x-apideck-service-id': service_id
}

url = 'https://unify.apideck.com/file-storage/drives'
response = requests.get(url, headers=headers)
print("Status Code:", response.status_code)
print("Response JSON:")
try:
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(response.text)
