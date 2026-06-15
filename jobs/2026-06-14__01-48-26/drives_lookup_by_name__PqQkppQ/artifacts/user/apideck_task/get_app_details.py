import os
import requests
import json

api_key = os.environ.get("APIDECK_API_KEY")
app_id = os.environ.get("APIDECK_APP_ID")

headers = {
    "Authorization": f"Bearer {api_key}",
    "x-apideck-app-id": app_id,
    "Content-Type": "application/json"
}

url = "https://unify.apideck.com/vault/connections"

print(f"Fetching connections from {url}...")
response = requests.get(url, headers=headers)
print(f"Status Code: {response.status_code}")
try:
    data = response.json()
    print(json.dumps(data, indent=2))
except Exception as e:
    print("Failed to parse JSON:", e)
    print(response.text)
