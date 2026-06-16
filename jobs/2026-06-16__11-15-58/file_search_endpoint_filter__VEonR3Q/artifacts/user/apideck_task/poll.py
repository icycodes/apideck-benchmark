import os
import json
import urllib.request
import urllib.error
import time

API_KEY = os.environ.get('APIDECK_API_KEY')
APP_ID = os.environ.get('APIDECK_APP_ID')
CONSUMER_ID = os.environ.get('APIDECK_CONSUMER_ID')
DRIVE_NAME = os.environ.get('APIDECK_FILE_STORAGE_DRIVE_NAME')
RUN_ID = os.environ.get('ZEALT_RUN_ID')

headers = {
    'Authorization': f'Bearer {API_KEY}',
    'x-apideck-app-id': APP_ID,
    'x-apideck-consumer-id': CONSUMER_ID,
    'x-apideck-service-id': 'onedrive'
}

# Search Files
search_query = f"KEEP-{RUN_ID}"
search_body = json.dumps({"query": search_query}).encode('utf-8')

search_headers = headers.copy()
search_headers['Content-Type'] = 'application/json'

url = 'https://unify.apideck.com/file-storage/files/search'

while True:
    search_results = []
    current_url = url
    
    while current_url:
        req = urllib.request.Request(current_url, data=search_body, headers=search_headers, method='POST')
        try:
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode())
                search_results.extend(res_data.get('data', []))
                current_url = res_data.get('links', {}).get('next')
        except urllib.error.HTTPError as e:
            print(f"Search failed: {e.code}")
            print(e.read().decode())
            break
            
    matching_files = [f for f in search_results if f['name'].startswith(f"KEEP-{RUN_ID}")]
    
    if len(matching_files) >= 2:
        print("Found the files!")
        break
        
    print(f"Found {len(matching_files)} matching files. OneDrive indexing... Retrying in 15s...")
    time.sleep(15)

matching_ids = [f['id'] for f in matching_files if f['name'].startswith(f"KEEP-{RUN_ID}")]

print(f"Found IDs: {matching_ids}")

with open('/home/user/apideck_task/output.log', 'w') as f:
    json.dump({"search_result_ids": matching_ids}, f)
