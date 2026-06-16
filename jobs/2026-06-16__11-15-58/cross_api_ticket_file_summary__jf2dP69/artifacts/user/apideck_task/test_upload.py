import os
import requests
import json

api_key = os.environ.get("APIDECK_API_KEY")
app_id = os.environ.get("APIDECK_APP_ID")
consumer_id = os.environ.get("APIDECK_CONSUMER_ID")

headers = {
    "Authorization": f"Bearer {api_key}",
    "x-apideck-app-id": app_id,
    "x-apideck-consumer-id": consumer_id,
    "x-apideck-service-id": "onedrive",
    "x-apideck-metadata": json.dumps({"name": "test.txt", "parent_folder_id": "root"})
}

files = {'file': ('test.txt', 'hello world', 'text/plain')}

resp = requests.post("https://unify.apideck.com/file-storage/files", headers=headers, files=files)
print(resp.status_code, resp.text)
