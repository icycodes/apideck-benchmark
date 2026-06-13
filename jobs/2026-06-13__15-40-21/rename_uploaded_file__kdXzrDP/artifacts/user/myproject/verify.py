import os
import requests
import json

api_key = os.environ.get('APIDECK_API_KEY')
app_id = os.environ.get('APIDECK_APP_ID')
consumer_id = os.environ.get('APIDECK_CONSUMER_ID')
run_id = os.environ.get('ZEALT_RUN_ID')
service_id = 'onedrive'

file_id = "eyJpZCI6IjNBREEwNzlCNzg1MzRGRjEhczU1YzU5ODUzYjJmYzQzNWY4Mjc3NzkyYWNmYTNlZjcwIiwiZHJpdmVfaWQiOiIzYWRhMDc5Yjc4NTM0ZmYxIn0="
expected_name = f'renamed-{run_id}.txt'
original_name = f'original-{run_id}.txt'

headers = {
    'Authorization': f'Bearer {api_key}',
    'x-apideck-app-id': app_id,
    'x-apideck-consumer-id': consumer_id,
    'x-apideck-service-id': service_id
}

# 1. Get the file directly
url_file = f'https://unify.apideck.com/file-storage/files/{file_id}'
response_file = requests.get(url_file, headers=headers)
print("GET File Status Code:", response_file.status_code)
assert response_file.status_code == 200, f"Expected 200, got {response_file.status_code}"

file_data = response_file.json()
print("GET File Response:")
print(json.dumps(file_data, indent=2))

actual_name = file_data.get('data', {}).get('name')
assert actual_name == expected_name, f"Expected name to be '{expected_name}', but got '{actual_name}'"
print("SUCCESS: File name correctly updated in metadata!")

# 2. List files to make sure the original name is not there
# Let's list files in the root folder or the configured drive
# Note: GET /file-storage/files lists files. It might take filter parameters like drive_id.
url_list = 'https://unify.apideck.com/file-storage/files'
params = {
    'filter[drive_id]': '3ada079b78534ff1'
}
response_list = requests.get(url_list, headers=headers, params=params)
print("List Files Status Code:", response_list.status_code)
assert response_list.status_code == 200, f"Expected 200, got {response_list.status_code}"

list_data = response_list.json()
files = list_data.get('data', [])
print(f"Found {len(files)} files in the configured drive.")

original_found = False
for f in files:
    name = f.get('name')
    if name == original_name:
        original_found = True
        print(f"WARNING: Found file with original name: {name} (ID: {f.get('id')})")

assert not original_found, f"Original file '{original_name}' still exists in the file list!"
print("SUCCESS: Original file name does not appear in any file name returned by GET /file-storage/files!")

# 3. Write outputs to output.log
log_path = '/home/user/myproject/output.log'
log_content = f"File ID: {file_id}\nFile Name: {expected_name}\n"
with open(log_path, 'w') as f_log:
    f_log.write(log_content)

print(f"SUCCESS: Log written to {log_path}")
print("Log content:")
print(log_content)
