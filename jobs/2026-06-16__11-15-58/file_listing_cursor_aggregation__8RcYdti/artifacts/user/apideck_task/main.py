import os
import json
import requests
import time
from urllib.parse import urlencode

def main():
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
    resp.raise_for_status()
    drives = resp.json().get('data', [])
    drive_id = next((d['id'] for d in drives if d['name'] == drive_name), None)

    if not drive_id:
        raise ValueError(f"Drive {drive_name} not found")

    print(f"Drive ID: {drive_id}")

    prefix = f"AGG-{run_id}-"

    # Walk the file listing using cursor pagination
    files_url = 'https://unify.apideck.com/file-storage/files'
    params = {
        'filter[folder_id]': 'root',
        'filter[drive_id]': drive_id,
        'limit': 3
    }

    cursor = None
    matched_ids = []

    while True:
        if cursor:
            params['cursor'] = cursor
        elif 'cursor' in params:
            del params['cursor']
            
        url = f"{files_url}?{urlencode(params)}"
        print(f"Fetching page... cursor={cursor}")
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        
        page_files = data.get('data', [])
        for f in page_files:
            if f.get('name', '').startswith(prefix):
                matched_ids.append(f['id'])
        
        cursor = data.get('meta', {}).get('cursors', {}).get('next')
        if not cursor:
            break

    # Write output.log
    output = {
        "count": len(matched_ids),
        "ids": matched_ids
    }
    
    output_path = '/home/user/apideck_task/output.log'
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Done. Wrote {len(matched_ids)} ids to {output_path}")

if __name__ == "__main__":
    main()
