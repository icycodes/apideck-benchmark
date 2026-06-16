import os
import json
import urllib.request

API_KEY = os.environ.get('APIDECK_API_KEY')
APP_ID = os.environ.get('APIDECK_APP_ID')
CONSUMER_ID = os.environ.get('APIDECK_CONSUMER_ID')

headers = {
    'Authorization': f'Bearer {API_KEY}',
    'x-apideck-app-id': APP_ID,
    'x-apideck-consumer-id': CONSUMER_ID,
    'x-apideck-service-id': 'onedrive'
}

req = urllib.request.Request('https://unify.apideck.com/file-storage/drives', headers=headers)
try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except Exception as e:
    print(e)
