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

# Get Drive ID
req = urllib.request.Request('https://unify.apideck.com/file-storage/drives', headers=headers)
with urllib.request.urlopen(req) as response:
    drives = json.loads(response.read().decode())['data']

drive_id = next(d['id'] for d in drives if d['name'] == DRIVE_NAME)
print("Drive ID:", drive_id)

files_to_upload = [
    f"KEEP-{RUN_ID}-1.txt",
    f"KEEP-{RUN_ID}-2.txt",
    f"SKIP-{RUN_ID}-1.txt",
    f"SKIP-{RUN_ID}-2.txt"
]

for filename in files_to_upload:
    metadata = {
        "name": filename,
        "parent_folder_id": "root",
        "drive_id": drive_id
    }
    
    upload_headers = headers.copy()
    upload_headers['Content-Type'] = 'text/plain'
    upload_headers['x-apideck-metadata'] = json.dumps(metadata)
    
    req = urllib.request.Request('https://upload.apideck.com/file-storage/files', data=b"content", headers=upload_headers, method='POST')
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Uploaded {filename}")
    except urllib.error.HTTPError as e:
        print(f"Failed to upload {filename}: {e.code}")
        print(e.read().decode())

# Give it a few seconds for the files to be indexed by OneDrive search
time.sleep(10)

# Search Files
search_query = f"KEEP-{RUN_ID}"
search_body = json.dumps({"query": search_query}).encode('utf-8')

search_headers = headers.copy()
search_headers['Content-Type'] = 'application/json'

# Handle pagination
search_results = []
url = 'https://unify.apideck.com/file-storage/files/search'

# Wait and retry search since OneDrive indexing might be slow
max_retries = 5
for attempt in range(max_retries):
    current_url = url
    search_results = []
    
    while current_url:
        req = urllib.request.Request(current_url, data=search_body, headers=search_headers, method='POST')
        try:
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode())
                search_results.extend(res_data.get('data', []))
                
                # Check for next page
                links = res_data.get('links', {})
                current_url = links.get('next')
        except urllib.error.HTTPError as e:
            print(f"Search failed: {e.code}")
            print(e.read().decode())
            break
            
    # Filter for our specific files just in case
    matching_files = [f for f in search_results if f['name'].startswith(f"KEEP-{RUN_ID}")]
    
    if len(matching_files) >= 2:
        break
        
    print(f"Found {len(matching_files)} matching files. Retrying in 10s...")
    time.sleep(10)

matching_ids = [f['id'] for f in matching_files if f['name'].startswith(f"KEEP-{RUN_ID}")]

print(f"Found IDs: {matching_ids}")

with open('/home/user/apideck_task/output.log', 'w') as f:
    json.dump({"search_result_ids": matching_ids}, f)
