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

services = ["onedrive", "google-drive", "REDACTED", "box", "sharepoint", "egnyte"]

for service in services:
    headers["x-apideck-service-id"] = service
    url = "https://unify.apideck.com/file-storage/drives"
    print(f"Calling GET /file-storage/drives for service {service}...")
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        if response.status_code == 200:
            print(f"Success for {service}!")
            print(json.dumps(data, indent=2))
        else:
            print(f"Error for {service}: {data.get('message')} ({data.get('type_name')})")
    except Exception as e:
        print(f"Failed to parse JSON for {service}: {e}")
        print(response.text)
