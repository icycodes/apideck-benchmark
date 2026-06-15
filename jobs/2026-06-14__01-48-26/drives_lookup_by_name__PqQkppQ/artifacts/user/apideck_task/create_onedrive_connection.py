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
    "Content-Type": "application/json"
}

url = "https://unify.apideck.com/vault/connections"

payload = {
    "service_id": "onedrive",
    "unified_api": "file-storage",
    "enabled": True
}

print(f"Trying to create/enable onedrive connection via POST {url}...")
response = requests.post(url, headers=headers, json=payload)
print(f"Status Code: {response.status_code}")
try:
    data = response.json()
    print(json.dumps(data, indent=2))
except Exception as e:
    print("Failed to parse JSON:", e)
    print(response.text)
