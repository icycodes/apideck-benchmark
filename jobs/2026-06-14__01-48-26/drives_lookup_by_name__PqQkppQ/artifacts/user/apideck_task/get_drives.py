import os
import requests
import json

api_key = os.environ.get("APIDECK_API_KEY")
app_id = os.environ.get("APIDECK_APP_ID")
consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
drive_name_to_find = os.environ.get("APIDECK_FILE_STORAGE_DRIVE_NAME")

headers = {
    "Authorization": f"Bearer {api_key}",
    "x-apideck-app-id": app_id,
    "x-apideck-consumer-id": consumer_id,
    "x-apideck-service-id": "REDACTED",
    "Content-Type": "application/json"
}

url = "https://unify.apideck.com/file-storage/drives"

print(f"Fetching drives from {url} with service-id REDACTED...")
response = requests.get(url, headers=headers)
print(f"Status Code: {response.status_code}")
try:
    data = response.json()
    print(json.dumps(data, indent=2))
except Exception as e:
    print("Failed to parse JSON:", e)
    print(response.text)
