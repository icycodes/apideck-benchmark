import os
import json
import urllib.request
import urllib.error

API_KEY = os.environ.get('APIDECK_API_KEY')
APP_ID = os.environ.get('APIDECK_APP_ID')
CONSUMER_ID = os.environ.get('APIDECK_CONSUMER_ID')
RUN_ID = os.environ.get('ZEALT_RUN_ID')

headers = {
    'Authorization': f'Bearer {API_KEY}',
    'x-apideck-app-id': APP_ID,
    'x-apideck-consumer-id': CONSUMER_ID,
    'x-apideck-service-id': 'onedrive'
}

search_query = f"KEEP-{RUN_ID}"
search_body = json.dumps({
    "query": search_query
}).encode('utf-8')

search_headers = headers.copy()
search_headers['Content-Type'] = 'application/json'

req = urllib.request.Request('https://unify.apideck.com/file-storage/files/search', data=search_body, headers=search_headers, method='POST')
try:
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode())
        print(json.dumps(res_data, indent=2))
except urllib.error.HTTPError as e:
    print(f"Search failed: {e.code}")
    print(e.read().decode())
