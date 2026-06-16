import os
import json
import urllib.request

app_id = os.environ.get('APIDECK_APP_ID')
api_key = os.environ.get('APIDECK_API_KEY')
consumer_id = os.environ.get('APIDECK_CONSUMER_ID')

headers = {
    'Authorization': f'Bearer {api_key}',
    'x-apideck-app-id': app_id,
    'x-apideck-consumer-id': consumer_id,
    'x-apideck-service-id': 'onedrive'
}

req = urllib.request.Request('https://unify.apideck.com/file-storage/drives', headers=headers)
with urllib.request.urlopen(req) as response:
    print(json.dumps(json.loads(response.read()), indent=2))
