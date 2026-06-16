import os
import requests

app_id = os.environ.get('APIDECK_APP_ID')
api_key = os.environ.get('APIDECK_API_KEY')
consumer_id = os.environ.get('APIDECK_CONSUMER_ID')

headers = {
    'Authorization': f'Bearer {api_key}',
    'x-apideck-app-id': app_id,
    'x-apideck-consumer-id': consumer_id,
    'x-apideck-service-id': 'onedrive'
}

file_id = "eyJpZCI6IjNBREEwNzlCNzg1MzRGRjEhc2NlMmZjYzQ4YzM2ZDQ0NDhiMGIzYzRhN2YwYWQxZTIzIiwiZHJpdmVfaWQiOiIzYWRhMDc5Yjc4NTM0ZmYxIn0="
url = f"https://unify.apideck.com/file-storage/files/{file_id}"
resp = requests.delete(url, headers=headers)
print(resp.status_code)
