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

consumer_ids = ["REDACTED", "onedrive", "REDACTED", "REDACTED-onedrive"]

for cid in consumer_ids:
    headers["x-apideck-consumer-id"] = cid
    url = f"https://unify.apideck.com/vault/connections"
    print(f"Checking consumer {cid}...")
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Count: {len(data.get('data', []))}")
        for conn in data.get('data', []):
            print(f"  - {conn.get('id')}: {conn.get('service_id')} ({conn.get('state')}/{conn.get('integration_state')})")
    else:
        print(response.text)
